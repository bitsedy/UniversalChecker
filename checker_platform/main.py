"""
CheckerPay Ghana - High-Concurrency Result Checker Reseller Platform
FastAPI Application Entrypoint
"""

import asyncio
import os
import random
import time
import logging
from contextlib import asynccontextmanager
from typing import Optional, List

from fastapi import FastAPI, Request, HTTPException, BackgroundTasks, Header
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

@app.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request):
    """Admin operations and inventory dashboard."""
    metrics = get_admin_metrics()
    settings = {
        "price_WASSCE": get_setting("price_WASSCE", "22.00"),
        "price_BECE": get_setting("price_BECE", "18.00"),
        "price_CSSPS": get_setting("price_CSSPS", "15.00"),
        "price_CTVET": get_setting("price_CTVET", "25.00"),
        "sms_sender_id": get_setting("sms_sender_id", "CHECKER_GH"),
        "paystack_public_key": get_setting("paystack_public_key", "pk_test_sample_ghana_waec"),
        "paystack_secret_key": get_setting("paystack_secret_key", "sk_test_sample_ghana_waec"),
        "inventory_mode": get_setting("inventory_mode", "BATCH")
    }
    return templates.TemplateResponse(
        request=request,
        name="admin.html",
        context={"active_page": "admin", "metrics": metrics, "settings": settings}
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
async def api_admin_bulk_import(req: BulkImportRequest):
    """Parses and imports wholesale voucher batches."""
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
    return {
        "success": True,
        "inserted": res["inserted"],
        "duplicates": res["duplicates"]
    }

@app.post("/api/admin/settings")
async def api_admin_save_settings(req: SettingsUpdateRequest):
    """Updates retail pricing and portal settings."""
    update_setting("price_WASSCE", str(req.price_WASSCE))
    update_setting("price_BECE", str(req.price_BECE))
    update_setting("price_CSSPS", str(req.price_CSSPS))
    update_setting("price_CTVET", str(req.price_CTVET))
    update_setting("sms_sender_id", req.sms_sender_id)
    if req.paystack_public_key:
        update_setting("paystack_public_key", req.paystack_public_key.strip())
    if req.paystack_secret_key:
        update_setting("paystack_secret_key", req.paystack_secret_key.strip())
    if req.inventory_mode:
        update_setting("inventory_mode", req.inventory_mode.strip())
    return {"success": True}

@app.post("/api/admin/inventory/generate-demo")
async def api_admin_generate_demo_batch(req: GenerateBatchRequest):
    """Generates random authentic-style vouchers directly into inventory."""
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
        
    return {
        "success": True,
        "total_inserted": total_inserted,
        "breakdown": breakdown,
        "message": f"Successfully generated and inserted {total_inserted} test vouchers into inventory."
    }
