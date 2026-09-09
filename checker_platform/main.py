"""
CheckerPay Ghana - High-Concurrency Result Checker Reseller Platform
FastAPI Application Entrypoint
"""

import secrets
import hashlib
import asyncio
import os
import random
import time
import logging
from contextlib import asynccontextmanager
from typing import Optional, List, Dict

from fastapi import FastAPI, Request, HTTPException, BackgroundTasks, Header, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from .database import (
    init_db,
    get_product_catalog,
    reserve_vouchers,
    complete_voucher_sale,
    release_expired_reservations,
    create_order,
    get_order_details,
    lookup_orders_by_customer,
    bulk_insert_vouchers,
    get_admin_metrics,
    get_setting,
    update_setting,
    generate_dynamic_vouchers
)
from .services.payment import (
    GhanaMoMoSimulator,
    PaystackProvider,
    detect_ghana_telco,
    validate_ghana_phone,
    record_transaction
)
from .services.dispatch import DispatchManager
from .seed_data import run_seed

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("checker.app")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")

templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Background worker to cycle expired reservations
async def expired_reservation_cleaner():
    """Cycles unfulfilled vouchers from RESERVED back to UNSOLD every 60 seconds."""
    while True:
        try:
            released = release_expired_reservations(timeout_minutes=10)
            if released > 0:
                logger.info(f"[Inventory Worker] Recycled {released} expired voucher reservation(s) back to UNSOLD stock.")
        except Exception as e:
            logger.error(f"[Inventory Worker Error] {e}")
        await asyncio.sleep(60)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure DB exists and has initial stock
    init_db()
    catalog = get_product_catalog()
    total_stock = sum(c["available_stock"] for c in catalog.values())
    if total_stock == 0:
        logger.info("Empty inventory detected. Populating initial seed stock...")
        run_seed()
    
    # Start cleaner task
    cleaner_task = asyncio.create_task(expired_reservation_cleaner())
    yield
    # Shutdown
    cleaner_task.cancel()

app = FastAPI(
    title="CheckerPay Ghana",
    description="High-concurrency digital voucher reseller gateway for WAEC, CSSPS, and CTVET.",
    version="1.0.0",
    lifespan=lifespan
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
 
@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/admin") or request.url.path.startswith("/api/admin"):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response

# ============================================================================
# HEALTH CHECK & SYSTEM ROUTES
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint for cloud load balancers and uptime monitors."""
    return {"status": "healthy", "service": "CheckerPay Ghana", "timestamp": time.time()}

# ============================================================================
# FRONTEND TEMPLATE ROUTES
# ============================================================================

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Storefront homepage with live stock and product options."""
    products = get_product_catalog()
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"active_page": "home", "products": products}
    )

@app.get("/lookup", response_class=HTMLResponse)
async def lookup_page(request: Request, q: Optional[str] = None):
    """Self-service voucher recovery page."""
    orders = lookup_orders_by_customer(q) if q else []
    return templates.TemplateResponse(
        request=request,
        name="lookup.html",
        context={"active_page": "lookup", "query": q, "orders": orders}
    )

@app.get("/guides", response_class=HTMLResponse)
async def guides_page(request: Request):
    """Anti-voucher burn instructions and official portal rules."""
    return templates.TemplateResponse(
        request=request,
        name="guides.html",
        context={"active_page": "guides"}
    )

admin_security = HTTPBasic()

class AdminSecurityManager:
    """
    In-memory rate limiter and brute-force lockout for Admin authentication.
    Locks out an IP address for 15 minutes after 5 failed authentication attempts.
    """
    _failed_attempts: Dict[str, List[float]] = {}
    _lockouts: Dict[str, float] = {}
    MAX_ATTEMPTS = 5
    WINDOW_SECONDS = 300  # 5 minutes
    LOCKOUT_SECONDS = 900  # 15 minutes

    @classmethod
    def get_client_ip(cls, request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "127.0.0.1"

    @classmethod
    def check_lockout(cls, ip: str) -> None:
        now = time.time()
        if ip in cls._lockouts:
            locked_until = cls._lockouts[ip]
            if now < locked_until:
                remaining = int(locked_until - now)
                raise HTTPException(
                    status_code=429,
                    detail=f"Too many failed login attempts. IP temporarily locked out for {remaining} seconds."
                )
            else:
                del cls._lockouts[ip]
                cls._failed_attempts.pop(ip, None)

    @classmethod
    def record_failure(cls, ip: str) -> None:
        now = time.time()
        attempts = [t for t in cls._failed_attempts.get(ip, []) if now - t < cls.WINDOW_SECONDS]
        attempts.append(now)
        cls._failed_attempts[ip] = attempts
        if len(attempts) >= cls.MAX_ATTEMPTS:
            cls._lockouts[ip] = now + cls.LOCKOUT_SECONDS
            logger.warning(f"[Security Alert] IP {ip} locked out from admin for 15 minutes due to repeated failed logins.")

    @classmethod
    def record_success(cls, ip: str) -> None:
        cls._failed_attempts.pop(ip, None)
        cls._lockouts.pop(ip, None)

    @classmethod
    def reset(cls) -> None:
        """Resets all lockouts and attempts (useful for testing)."""
        cls._failed_attempts.clear()
        cls._lockouts.clear()

def hash_password(password: str) -> str:
    """Hashes a password using PBKDF2-HMAC-SHA256 with a random salt."""
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), 100_000)
    return f"pbkdf2:sha256:100000${salt}${key.hex()}"

def verify_password(plain_password: str, stored_hash_or_plain: str) -> bool:
    """Verifies a plain password against a stored PBKDF2 hash or legacy plaintext."""
    if stored_hash_or_plain.startswith("pbkdf2:sha256:"):
        try:
            parts = stored_hash_or_plain.split("$")
            iterations = int(parts[0].split(":")[2])
            salt = bytes.fromhex(parts[1])
            expected_hex = parts[2]
            key = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt, iterations)
            return secrets.compare_digest(key.hex(), expected_hex)
        except Exception:
            return False
    # Legacy plaintext fallback (with constant-time comparison)
    return secrets.compare_digest(plain_password, stored_hash_or_plain)

def get_current_admin(
    request: Request,
    credentials: HTTPBasicCredentials = Depends(admin_security)
) -> str:
    """Validates HTTP Basic Auth credentials with brute-force lockout and hashed password comparison."""
    client_ip = AdminSecurityManager.get_client_ip(request)
    AdminSecurityManager.check_lockout(client_ip)

    expected_username = os.environ.get("ADMIN_USERNAME", get_setting("admin_username", "admin")).strip()
    env_password = os.environ.get("ADMIN_PASSWORD")
    db_password = get_setting("admin_password", "ghana2026").strip()

    is_user_ok = secrets.compare_digest(credentials.username.strip(), expected_username)
    if env_password:
        is_pass_ok = verify_password(credentials.password.strip(), env_password.strip())
    else:
        is_pass_ok = verify_password(credentials.password.strip(), db_password)

    if not (is_user_ok and is_pass_ok):
        AdminSecurityManager.record_failure(client_ip)
        logger.warning(f"[Security Warning] Failed admin login attempt for '{credentials.username}' from IP {client_ip}")
        raise HTTPException(
            status_code=401,
            detail="Invalid admin credentials",
            headers={"WWW-Authenticate": "Basic realm='CheckerPay Admin'"}
        )

    AdminSecurityManager.record_success(client_ip)
    return credentials.username

@app.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request, admin_user: str = Depends(get_current_admin)):
    """Admin operations and inventory dashboard."""
    metrics = get_admin_metrics()

    env_password = os.environ.get("ADMIN_PASSWORD")
    db_password = get_setting("admin_password", "ghana2026").strip()
    is_default_password = (not env_password) and (db_password == "ghana2026")

    raw_secret = get_setting("paystack_secret_key", "").strip()
    masked_secret = ""
    if raw_secret:
        if raw_secret.startswith("sk_test_sample"):
            masked_secret = "Sample Test Key (sk_test_sample_...)"
        elif len(raw_secret) > 8:
            masked_secret = raw_secret[:7] + "•" * 12 + raw_secret[-4:]
        else:
            masked_secret = "••••••••"

    settings = {
        "price_WASSCE": get_setting("price_WASSCE", "22.00"),
        "price_BECE": get_setting("price_BECE", "18.00"),
        "price_CSSPS": get_setting("price_CSSPS", "15.00"),
        "price_CTVET": get_setting("price_CTVET", "25.00"),
        "sms_sender_id": get_setting("sms_sender_id", "CHECKER_GH"),
        "paystack_public_key": get_setting("paystack_public_key", "pk_test_sample_ghana_waec"),
        "has_paystack_secret_key": bool(raw_secret and not raw_secret.startswith("sk_test_sample")),
        "masked_paystack_secret_key": masked_secret,
        "inventory_mode": get_setting("inventory_mode", "BATCH"),
        "admin_username": get_setting("admin_username", "admin"),
        "is_default_password": is_default_password,
        "env_password_override": bool(env_password)
    }
    return templates.TemplateResponse(
        request=request,
        name="admin.html",
        context={"active_page": "admin", "metrics": metrics, "settings": settings, "admin_user": admin_user}
    )

@app.get("/admin/logout", response_class=HTMLResponse)
async def admin_logout():
    """Forces browser to clear cached HTTP Basic Auth credentials."""
    return HTMLResponse(
        status_code=401,
        content="""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Logged Out | CheckerPay Admin</title>
    <meta http-equiv="refresh" content="3;url=/">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { background: #0b0f19; color: #f8fafc; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }
        .card { text-align: center; background: #131b2e; padding: 2.5rem 3rem; border-radius: 16px; border: 1px solid rgba(255,255,255,0.08); box-shadow: 0 20px 40px rgba(0,0,0,0.5); max-width: 420px; }
        .icon { font-size: 2.5rem; margin-bottom: 1rem; }
        h2 { font-size: 1.5rem; margin-bottom: 0.5rem; color: #fff; }
        p { color: #94a3b8; font-size: 0.9rem; line-height: 1.5; }
        .actions { margin-top: 1.75rem; display: flex; gap: 1rem; justify-content: center; }
        .btn { padding: 0.6rem 1.25rem; border-radius: 8px; text-decoration: none; font-size: 0.85rem; font-weight: 700; }
        .btn-login { background: #f59e0b; color: #000; }
        .btn-home { background: rgba(255,255,255,0.06); color: #cbd5e1; }
    </style>
</head>
<body>
    <div class="card">
        <div class="icon">🔒</div>
        <h2>Logged Out Successfully</h2>
        <p>Your admin session credentials have been cleared from this browser session.</p>
        <div class="actions">
            <a href="/admin" class="btn btn-login">Log In Again</a>
            <a href="/" class="btn btn-home">Back to Storefront</a>
        </div>
    </div>
</body>
</html>""",
        headers={"WWW-Authenticate": "Basic realm='CheckerPay Admin (Logged Out)'"}
    )

# ============================================================================
# API MODELS & ROUTES
# ============================================================================

class OrderCreateRequest(BaseModel):
    category: str = Field(..., description="WASSCE, BECE, CSSPS, or CTVET")
    quantity: int = Field(1, ge=1, le=20)
    customer_phone: str
    customer_email: Optional[str] = None
    payment_method: str = "MOMO_MTN"

class OrderVerifyRequest(BaseModel):
    order_reference: str
    provider: str = "MOMO_SIMULATOR"

class BulkImportRequest(BaseModel):
    category: str
    raw_data: str

class SettingsUpdateRequest(BaseModel):
    price_WASSCE: str
    price_BECE: str
    price_CSSPS: str
    price_CTVET: str
    sms_sender_id: str
    paystack_public_key: Optional[str] = None
    paystack_secret_key: Optional[str] = None
    inventory_mode: Optional[str] = "BATCH"
    admin_username: Optional[str] = None
    admin_password: Optional[str] = None

class GenerateBatchRequest(BaseModel):
    category: str = "ALL"
    count: int = Field(50, ge=1, le=500)

@app.get("/api/catalog")
async def api_get_catalog():
    """Returns current real-time stock levels and prices."""
    return get_product_catalog()

@app.post("/api/orders/create")
async def api_create_order(req: OrderCreateRequest):
    """
    Creates an order and atomically reserves vouchers.
    Returns payment authorization instructions (MoMo USSD prompt or Paystack link).
    """
    clean_cat = req.category.strip().upper()
    catalog = get_product_catalog()
    if clean_cat not in catalog:
        raise HTTPException(status_code=400, detail=f"Invalid category: {req.category}")

    # Validate phone
    if not validate_ghana_phone(req.customer_phone):
        return JSONResponse(
            status_code=400,
            content={"success": False, "message": "Invalid Ghanaian phone number. Must be 10 digits (e.g. 0241234567)."}
        )

    product = catalog[clean_cat]
    unit_price = product["price"]

    # Generate unique order reference
    rand_suffix = random.randint(1000, 9999)
    order_ref = f"ORD-{int(time.time())}-{rand_suffix}"

    # Atomic Reservation
    reserved = reserve_vouchers(clean_cat, req.quantity, order_ref, hold_minutes=10)
    if not reserved:
        return JSONResponse(
            status_code=400,
            content={
                "success": False, 
                "message": f"Sorry, not enough available stock for {product['name']}. Current stock: {product['available_stock']}."
            }
        )

    # Create Order Record
    order = create_order(
        order_ref=order_ref,
        category=clean_cat,
        quantity=req.quantity,
        unit_price=unit_price,
        customer_phone=req.customer_phone,
        customer_email=req.customer_email,
        payment_method=req.payment_method
    )

    # Generate Payment Prompt
    prompt_info = GhanaMoMoSimulator.trigger_momo_prompt(
        order_ref=order_ref,
        phone=req.customer_phone,
        amount_ghs=order["total_amount"],
        provider=req.payment_method
    )

    return {
        "success": True,
        "order": order,
        "payment_prompt": prompt_info,
        "paystack_public_key": get_setting("paystack_public_key")
    }

@app.post("/api/orders/verify")
async def api_verify_order(req: OrderVerifyRequest, background_tasks: BackgroundTasks):
    """
    Verifies payment and marks reserved vouchers as SOLD.
    Fulfills multi-channel delivery (on-screen, SMS, WhatsApp format).
    """
    order = get_order_details(req.order_reference)
    if not order:
        raise HTTPException(status_code=404, detail="Order reference not found")

    # In live/real test mode with Paystack, verify status against Paystack API
    secret_key = get_setting("paystack_secret_key", "")
    if req.provider == "PAYSTACK" and secret_key and not secret_key.startswith("sk_test_sample"):
        verify_res = PaystackProvider.verify_transaction(req.order_reference)
        if not verify_res.get("status") or verify_res.get("data", {}).get("status") != "success":
            err_msg = verify_res.get("message") or "Payment has not been confirmed by Paystack."
            raise HTTPException(status_code=400, detail=err_msg)

    # Complete voucher sale atomically
    sold_vouchers = complete_voucher_sale(req.order_reference)
    if not sold_vouchers:
        raise HTTPException(status_code=400, detail="No vouchers could be allocated for this order")

    # Record payment transaction
    record_transaction(
        order_ref=req.order_reference,
        provider=req.provider,
        provider_ref=f"{req.provider}_{req.order_reference}",
        amount=order["total_amount"],
        status="SUCCESS",
        payload={"order_reference": req.order_reference, "verified_at": time.time()}
    )

    # Format multi-channel fulfillment
    fulfillment = DispatchManager.format_on_screen_delivery(order, sold_vouchers)
    sms_text = DispatchManager.generate_sms_text(req.order_reference, order["category"], sold_vouchers)
    whatsapp_text = DispatchManager.generate_whatsapp_share_text(req.order_reference, order["category"], sold_vouchers)

    # Dispatch mock SMS in background
    background_tasks.add_task(DispatchManager.dispatch_sms_mock, order["customer_phone"], sms_text)

    return {
        "success": True,
        "fulfillment": fulfillment,
        "whatsapp_text": whatsapp_text
    }

@app.get("/api/orders/{reference}")
async def api_get_order(reference: str):
    """Fetches details and credentials of an order."""
    data = get_order_details(reference)
    if not data:
        raise HTTPException(status_code=404, detail="Order not found")
    return data

@app.post("/api/webhooks/paystack")
async def paystack_webhook(request: Request, x_paystack_signature: Optional[str] = Header(None)):
    """
    Idempotent Paystack webhook handler.
    Verifies HMAC SHA512 signature before completing voucher sale.
    """
    body_bytes = await request.body()
    
    # In live mode with real keys, verify signature
    secret_key = get_setting("paystack_secret_key")
    if secret_key and x_paystack_signature:
        is_valid = PaystackProvider.verify_webhook_signature(body_bytes, x_paystack_signature)
        if not is_valid:
            logger.warning("Invalid Paystack webhook signature rejected.")
            raise HTTPException(status_code=400, detail="Invalid signature")

    try:
        import json
        event = json.loads(body_bytes.decode("utf-8"))
        if event.get("event") == "charge.success":
            data = event.get("data", {})
            order_ref = data.get("reference") or data.get("metadata", {}).get("order_reference")
            if order_ref:
                logger.info(f"[Paystack Webhook] Fulfilling order {order_ref}")
                complete_voucher_sale(order_ref)
                record_transaction(
                    order_ref=order_ref,
                    provider="PAYSTACK",
                    provider_ref=str(data.get("id")),
                    amount=float(data.get("amount", 0)) / 100.0,
                    status="SUCCESS",
                    payload=data
                )
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Error handling Paystack webhook: {e}")
        return {"status": "error", "message": str(e)}

@app.post("/api/admin/inventory/bulk")
async def api_admin_bulk_import(req: BulkImportRequest, request: Request, admin_user: str = Depends(get_current_admin)):
    """Parses and imports wholesale voucher batches."""
    client_ip = AdminSecurityManager.get_client_ip(request)
    lines = req.raw_data.strip().split("\n")
    vouchers = []
    for line in lines:
        cleaned = line.strip().replace("\t", " ")
        if not cleaned:
            continue
        # Split on comma or space
        if "," in cleaned:
            parts = [p.strip() for p in cleaned.split(",", 1)]
        else:
            parts = [p.strip() for p in cleaned.split(" ", 1)]
        
        if len(parts) >= 2:
            vouchers.append({"serial_number": parts[0], "pin": parts[1]})

    if not vouchers:
        return JSONResponse(status_code=400, content={"success": False, "message": "No valid vouchers found in input."})

    res = bulk_insert_vouchers(req.category.strip().upper(), vouchers)
    logger.info(f"[Admin Audit] User '{admin_user}' ({client_ip}) imported {res['inserted']} {req.category} vouchers ({res['duplicates']} duplicates).")
    return {
        "success": True,
        "inserted": res["inserted"],
        "duplicates": res["duplicates"]
    }

@app.post("/api/admin/settings")
async def api_admin_save_settings(req: SettingsUpdateRequest, request: Request, admin_user: str = Depends(get_current_admin)):
    """Updates retail pricing and portal settings with salted password hashing and audit logging."""
    client_ip = AdminSecurityManager.get_client_ip(request)

    update_setting("price_WASSCE", str(req.price_WASSCE))
    update_setting("price_BECE", str(req.price_BECE))
    update_setting("price_CSSPS", str(req.price_CSSPS))
    update_setting("price_CTVET", str(req.price_CTVET))
    update_setting("sms_sender_id", req.sms_sender_id)

    if req.paystack_public_key and req.paystack_public_key.strip():
        update_setting("paystack_public_key", req.paystack_public_key.strip())

    # Only update secret key if a non-empty string is provided (prevents wiping key on general save)
    if req.paystack_secret_key and req.paystack_secret_key.strip():
        update_setting("paystack_secret_key", req.paystack_secret_key.strip())
        logger.info(f"[Admin Audit] Paystack secret key updated by '{admin_user}' ({client_ip}).")

    if req.inventory_mode:
        update_setting("inventory_mode", req.inventory_mode.strip())

    if req.admin_username and req.admin_username.strip():
        new_username = req.admin_username.strip()
        if len(new_username) < 3:
            return JSONResponse(status_code=400, content={"success": False, "message": "Admin username must be at least 3 characters long."})
        update_setting("admin_username", new_username)
        logger.info(f"[Admin Audit] Admin username changed to '{new_username}' by '{admin_user}' ({client_ip}).")

    if req.admin_password and req.admin_password.strip():
        new_pass = req.admin_password.strip()
        if len(new_pass) < 8:
            return JSONResponse(status_code=400, content={"success": False, "message": "Admin password must be at least 8 characters long."})
        hashed_pass = hash_password(new_pass)
        update_setting("admin_password", hashed_pass)
        logger.info(f"[Admin Audit] Admin password securely changed and hashed by '{admin_user}' ({client_ip}).")

    return {"success": True}

@app.post("/api/admin/inventory/generate-demo")
async def api_admin_generate_demo_batch(req: GenerateBatchRequest, request: Request, admin_user: str = Depends(get_current_admin)):
    """Generates random authentic-style vouchers directly into inventory."""
    client_ip = AdminSecurityManager.get_client_ip(request)
    clean_cat = req.category.strip().upper()
    categories = ["WASSCE", "BECE", "CSSPS", "CTVET"] if clean_cat == "ALL" else [clean_cat]
    total_inserted = 0
    breakdown = {}
    
    for cat in categories:
        items = generate_dynamic_vouchers(cat, req.count)
        db_items = [{"serial_number": v["serial_number"], "pin": v["pin"]} for v in items]
        res = bulk_insert_vouchers(cat, db_items)
        total_inserted += res["inserted"]
        breakdown[cat] = res["inserted"]

    logger.info(f"[Admin Audit] User '{admin_user}' ({client_ip}) generated {total_inserted} demo vouchers across {categories}.")
    return {
        "success": True,
        "total_inserted": total_inserted,
        "breakdown": breakdown,
        "message": f"Successfully generated and inserted {total_inserted} test vouchers into inventory."
    }
