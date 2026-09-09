"""
Database Layer for Ghanaian Result Checker Reseller Platform
Handles SQLite initialization with WAL mode, atomic voucher reservations,
order lifecycle, and concurrency protection.
"""

import sqlite3
import os
import random
import time
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

DB_PATH = os.environ.get("CHECKER_DB_PATH", os.path.join(os.path.dirname(__file__), "checker.db"))

def get_db_connection():
    """Returns a SQLite connection configured for concurrent web workloads."""
    conn = sqlite3.connect(DB_PATH, timeout=20.0, isolation_level=None)
    conn.row_factory = sqlite3.Row
    # Enable WAL mode for high concurrency read/write isolation
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=10000;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn

def init_db():
    """Initializes tables and indexes if they do not exist."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS vouchers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL, -- 'WASSCE', 'BECE', 'CSSPS', 'CTVET'
                serial_number TEXT NOT NULL UNIQUE,
                pin TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'UNSOLD', -- 'UNSOLD', 'RESERVED', 'SOLD', 'REFUNDED'
                order_reference TEXT,
                reserved_at TIMESTAMP,
                sold_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_reference TEXT NOT NULL UNIQUE,
                category TEXT NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 1,
                unit_price REAL NOT NULL,
                total_amount REAL NOT NULL,
                customer_phone TEXT NOT NULL,
                customer_email TEXT,
                payment_method TEXT NOT NULL, -- 'MOMO_MTN', 'MOMO_TELECEL', 'MOMO_AT', 'PAYSTACK', 'CARD'
                payment_status TEXT NOT NULL DEFAULT 'PENDING', -- 'PENDING', 'PAID', 'FAILED', 'EXPIRED'
                paystack_reference TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_reference TEXT NOT NULL,
                provider TEXT NOT NULL,
                provider_reference TEXT UNIQUE,
                amount REAL NOT NULL,
                currency TEXT DEFAULT 'GHS',
                status TEXT NOT NULL,
                payload TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (order_reference) REFERENCES orders(order_reference)
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS site_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
        """)

        # Performance and concurrency indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_vouchers_cat_status ON vouchers(category, status);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_vouchers_order_ref ON vouchers(order_reference);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_ref ON orders(order_reference);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_phone ON orders(customer_phone);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_vouchers_reserved_at ON vouchers(reserved_at);")

        # Default pricing in GHS (Ghanaian Cedis)
        default_settings = [
            ("price_WASSCE", "22.00"),
            ("price_BECE", "18.00"),
            ("price_CSSPS", "15.00"),
            ("price_CTVET", "25.00"),
            ("paystack_public_key", "pk_test_sample_ghana_waec"),
            ("paystack_secret_key", "sk_test_sample_ghana_waec"),
            ("sms_sender_id", "CHECKER_GH"),
            ("support_phone", "+233 24 000 0000"),
            ("support_whatsapp", "+233240000000"),
            ("inventory_mode", "BATCH"), # 'BATCH' or 'DEMO_GENERATE'
            ("admin_username", "admin"),
            ("admin_password", "ghana2026"),
        ]
        for key, val in default_settings:
            cursor.execute("INSERT OR IGNORE INTO site_settings (key, value) VALUES (?, ?);", (key, val))

    finally:
        conn.close()

def get_setting(key: str, default: str = "") -> str:
    """Retrieves a site setting."""
    conn = get_db_connection()
    try:
        row = conn.execute("SELECT value FROM site_settings WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default
    except sqlite3.OperationalError:
        return default
    finally:
        conn.close()

def update_setting(key: str, value: str):
    """Updates or sets a site setting."""
    conn = get_db_connection()
    try:
        conn.execute("INSERT OR REPLACE INTO site_settings (key, value) VALUES (?, ?)", (key, value))
        conn.commit()
    except sqlite3.OperationalError:
        pass
    finally:
        conn.close()

def generate_dynamic_vouchers(category: str, count: int, order_ref: Optional[str] = None) -> List[Dict[str, Any]]:
    """Generates authentic-style vouchers with unique serial numbers and PINs for demo/testing."""
    prefixes = {
        "WASSCE": "WSC2026",
        "BECE": "BEC2026",
        "CSSPS": "CSS2026",
        "CTVET": "CTV2026"
    }
    prefix = prefixes.get(category, "VCH2026")
    vouchers = []
    
    for _ in range(count):
        ts_part = str(int(time.time() * 1000))[-5:]
        rand_part = random.randint(1000, 9999)
        serial = f"{prefix}D{ts_part}{rand_part}"
        
        pin_len = 11 if category == "CSSPS" else 12
        first = str(random.randint(1, 9))
        rest = "".join([str(random.randint(0, 9)) for _ in range(pin_len - 1)])
        pin = first + rest
        
        vouchers.append({
            "category": category,
            "serial_number": serial,
            "pin": pin,
            "order_reference": order_ref
        })
    return vouchers

def get_product_catalog() -> Dict[str, Dict[str, Any]]:
    """Returns the current product catalog with real-time stock levels and prices."""
    conn = get_db_connection()
    try:
        categories = {
            "WASSCE": {
                "name": "WAEC WASSCE Result Checker",
                "short_title": "WASSCE (May/June & Nov/Dec)",
                "description": "Valid for May/June School Candidates & Private Nov/Dec Candidates. Official check limit: 3 times.",
                "official_url": "https://ghana.waecdirect.org",
                "badge": "Popular",
                "check_limit": 3,
                "index_format": "10-Digit Candidate Index (e.g. 0010101010)"
            },
            "BECE": {
                "name": "WAEC BECE Result Checker",
                "short_title": "BECE (School & Private)",
                "description": "Valid for Basic Education Certificate Examination graduates. Official check limit: 3 times.",
                "official_url": "https://eresults.waecgh.org",
                "badge": "High Demand",
                "check_limit": 3,
                "index_format": "10-Digit Candidate Index (e.g. 1010101010)"
            },
            "CSSPS": {
                "name": "CSSPS School Placement Checker",
                "short_title": "Senior High School Placement",
                "description": "Valid for checking 2026/2027 SHS placement status and self-placement. Unlimited checks for same candidate.",
                "official_url": "https://cssps.gov.gh",
                "badge": "Placement 2026",
                "check_limit": 999,
                "index_format": "12-Digit String (10-Digit Index + 2-Digit Year, e.g. 101010101026)"
            },
            "CTVET": {
                "name": "CTVET / NABPTEX Result Checker",
                "short_title": "CTVET Technical & Vocational",
                "description": "Valid for May/June Certificate & Nov/Dec Technical Examinations across all regions.",
                "official_url": "https://ctvet.gov.gh",
                "badge": "Technical/Vocational",
                "check_limit": 5,
                "index_format": "Region + Center Code + Index Number"
            }
        }

        mode_row = conn.execute("SELECT value FROM site_settings WHERE key = 'inventory_mode'").fetchone()
        inventory_mode = mode_row["value"] if mode_row else "BATCH"

        # Query stock count and pricing
        for cat, data in categories.items():
            price_row = conn.execute("SELECT value FROM site_settings WHERE key = ?", (f"price_{cat}",)).fetchone()
            data["price"] = float(price_row["value"]) if price_row else 20.00
            data["inventory_mode"] = inventory_mode
            data["is_demo_mode"] = (inventory_mode == "DEMO_GENERATE")
            
            stock_row = conn.execute(
                "SELECT COUNT(*) as count FROM vouchers WHERE category = ? AND status = 'UNSOLD'", 
                (cat,)
            ).fetchone()
            unsold_count = stock_row["count"] if stock_row else 0
            if inventory_mode == "DEMO_GENERATE":
                data["available_stock"] = unsold_count if unsold_count > 0 else 999
            else:
                data["available_stock"] = unsold_count
            
        return categories
    finally:
        conn.close()

def reserve_vouchers(category: str, quantity: int, order_ref: str, hold_minutes: int = 10) -> Optional[List[Dict[str, Any]]]:
    """
    Safely and atomically reserves vouchers under high concurrency.
    In DEMO_GENERATE mode, on-the-fly generates fresh authentic-style vouchers.
    In BATCH mode, strictly draws from pre-uploaded inventory batches.
    Uses SQLite BEGIN IMMEDIATE to lock the database and avoid race conditions.
    """
    conn = get_db_connection()
    try:
        # Acquire immediate write lock
        conn.execute("BEGIN IMMEDIATE;")
        
        mode_row = conn.execute("SELECT value FROM site_settings WHERE key = 'inventory_mode'").fetchone()
        inventory_mode = mode_row["value"] if mode_row else "BATCH"

        if inventory_mode == "DEMO_GENERATE":
            # Dynamic demo generator: mint unique authentic codes on demand
            dynamic_items = generate_dynamic_vouchers(category, quantity, order_ref=order_ref)
            res_list = []
            for item in dynamic_items:
                cursor = conn.execute(
                    """
                    INSERT INTO vouchers (category, serial_number, pin, status, order_reference, reserved_at)
                    VALUES (?, ?, ?, 'RESERVED', ?, datetime('now'))
                    """,
                    (category, item["serial_number"], item["pin"], order_ref)
                )
                res_list.append({
                    "id": cursor.lastrowid,
                    "serial_number": item["serial_number"],
                    "pin": item["pin"]
                })
            conn.execute("COMMIT;")
            return res_list

        # Strict Batch Mode: Select available vouchers from existing database inventory
        rows = conn.execute(
            """
            SELECT id, serial_number, pin 
            FROM vouchers 
            WHERE category = ? AND status = 'UNSOLD' 
            LIMIT ?
            """, 
            (category, quantity)
        ).fetchall()

        if len(rows) < quantity:
            conn.execute("ROLLBACK;")
            return None # Out of stock

        voucher_ids = [r["id"] for r in rows]
        placeholders = ",".join("?" for _ in voucher_ids)
        
        # Mark as RESERVED
        conn.execute(
            f"""
            UPDATE vouchers 
            SET status = 'RESERVED',
                order_reference = ?,
                reserved_at = datetime('now')
            WHERE id IN ({placeholders})
            """,
            [order_ref] + voucher_ids
        )
        
        conn.execute("COMMIT;")
        return [{"id": r["id"], "serial_number": r["serial_number"], "pin": r["pin"]} for r in rows]
    except Exception as e:
        try:
            conn.execute("ROLLBACK;")
        except Exception:
            pass
        raise e
    finally:
        conn.close()

def complete_voucher_sale(order_ref: str) -> List[Dict[str, Any]]:
    """
    Marks reserved vouchers as SOLD upon verified payment.
    Idempotent: if already sold, simply returns the vouchers.
    """
    conn = get_db_connection()
    try:
        conn.execute("BEGIN IMMEDIATE;")
        
        # Check order
        order = conn.execute("SELECT * FROM orders WHERE order_reference = ?", (order_ref,)).fetchone()
        if not order:
            conn.execute("ROLLBACK;")
            raise ValueError(f"Order {order_ref} not found")

        # Update vouchers
        conn.execute(
            """
            UPDATE vouchers 
            SET status = 'SOLD',
                sold_at = datetime('now')
            WHERE order_reference = ? AND status = 'RESERVED'
            """,
            (order_ref,)
        )

        # Update order status
        conn.execute(
            """
            UPDATE orders 
            SET payment_status = 'PAID',
                updated_at = datetime('now')
            WHERE order_reference = ?
            """,
            (order_ref,)
        )

        # Fetch sold vouchers
        rows = conn.execute(
            "SELECT serial_number, pin, category, sold_at FROM vouchers WHERE order_reference = ?",
            (order_ref,)
        ).fetchall()

        conn.execute("COMMIT;")
        return [dict(r) for r in rows]
    except Exception as e:
        try:
            conn.execute("ROLLBACK;")
        except Exception:
            pass
        raise e
    finally:
        conn.close()

def release_expired_reservations(timeout_minutes: int = 10) -> int:
    """
    Worker task: releases vouchers that were reserved but never paid for within timeout.
    Cycles status back from 'RESERVED' to 'UNSOLD'.
    """
    conn = get_db_connection()
    try:
        conn.execute("BEGIN IMMEDIATE;")
        cursor = conn.execute(
            """
            UPDATE vouchers 
            SET status = 'UNSOLD',
                order_reference = NULL,
                reserved_at = NULL
            WHERE status = 'RESERVED' 
              AND (strftime('%s', 'now') - strftime('%s', reserved_at)) > (? * 60)
            """,
            (timeout_minutes,)
        )
        count = cursor.rowcount
        conn.execute("COMMIT;")
        return count
    except Exception as e:
        try:
            conn.execute("ROLLBACK;")
        except Exception:
            pass
        raise e
    finally:
        conn.close()

def create_order(
    order_ref: str, 
    category: str, 
    quantity: int, 
    unit_price: float, 
    customer_phone: str, 
    customer_email: Optional[str], 
    payment_method: str
) -> Dict[str, Any]:
    """Creates a pending order record."""
    total_amount = round(quantity * unit_price, 2)
    conn = get_db_connection()
    try:
        conn.execute(
            """
            INSERT INTO orders (
                order_reference, category, quantity, unit_price, total_amount,
                customer_phone, customer_email, payment_method, payment_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'PENDING')
            """,
            (order_ref, category, quantity, unit_price, total_amount, customer_phone, customer_email or "", payment_method)
        )
        return {
            "order_reference": order_ref,
            "category": category,
            "quantity": quantity,
            "unit_price": unit_price,
            "total_amount": total_amount,
            "customer_phone": customer_phone,
            "customer_email": customer_email,
            "payment_method": payment_method,
            "payment_status": "PENDING"
        }
    finally:
        conn.close()

def get_order_details(order_ref: str) -> Optional[Dict[str, Any]]:
    """Retrieves full order information along with allocated vouchers if paid."""
    conn = get_db_connection()
    try:
        order = conn.execute("SELECT * FROM orders WHERE order_reference = ?", (order_ref,)).fetchone()
        if not order:
            return None
            
        data = dict(order)
        # Fetch vouchers if paid or reserved
        vouchers = conn.execute(
            "SELECT serial_number, pin, category, status FROM vouchers WHERE order_reference = ?",
            (order_ref,)
        ).fetchall()
        
        # Only expose credentials if paid
        if data["payment_status"] == "PAID":
            data["vouchers"] = [dict(v) for v in vouchers]
        else:
            data["vouchers"] = []
            data["vouchers_reserved_count"] = len(vouchers)
            
        return data
    finally:
        conn.close()

def lookup_orders_by_customer(query: str) -> List[Dict[str, Any]]:
    """
    Self-service portal query: finds orders by customer phone number or order reference.
    Standardizes Ghanaian phone formats (e.g., '0241234567', '+233241234567', '233241234567').
    """
    raw_query = query.strip()
    phone_clean = raw_query.replace(" ", "").replace("-", "")
    variants = [phone_clean, raw_query]
    if phone_clean.startswith("0") and len(phone_clean) == 10:
        variants.append("+233" + phone_clean[1:])
        variants.append("233" + phone_clean[1:])
    elif phone_clean.startswith("+233") and len(phone_clean) == 13:
        variants.append("0" + phone_clean[4:])
        variants.append(phone_clean[1:])
    elif phone_clean.startswith("233") and len(phone_clean) == 12:
        variants.append("0" + phone_clean[3:])
        variants.append("+" + phone_clean)

    conn = get_db_connection()
    try:
        placeholders = ",".join("?" for _ in variants)
        sql = f"""
            SELECT * FROM orders 
            WHERE order_reference = ? 
               OR customer_phone IN ({placeholders})
            ORDER BY created_at DESC 
            LIMIT 10
        """
        params = [raw_query] + variants
        orders = conn.execute(sql, params).fetchall()
        
        results = []
        for o in orders:
            item = dict(o)
            if item["payment_status"] == "PAID":
                v_rows = conn.execute(
                    "SELECT serial_number, pin, category FROM vouchers WHERE order_reference = ?",
                    (item["order_reference"],)
                ).fetchall()
                item["vouchers"] = [dict(v) for v in v_rows]
            else:
                item["vouchers"] = []
            results.append(item)
            
        return results
    finally:
        conn.close()

def bulk_insert_vouchers(category: str, vouchers: List[Dict[str, str]]) -> Dict[str, int]:
    """Bulk inserts inventory batches, skipping duplicates."""
    conn = get_db_connection()
    inserted = 0
    duplicates = 0
    try:
        conn.execute("BEGIN IMMEDIATE;")
        for v in vouchers:
            serial = v.get("serial_number", "").strip()
            pin = v.get("pin", "").strip()
            if not serial or not pin:
                continue
            try:
                conn.execute(
                    "INSERT INTO vouchers (category, serial_number, pin, status) VALUES (?, ?, ?, 'UNSOLD')",
                    (category, serial, pin)
                )
                inserted += 1
            except sqlite3.IntegrityError:
                duplicates += 1
        conn.execute("COMMIT;")
        return {"inserted": inserted, "duplicates": duplicates}
    except Exception as e:
        try:
            conn.execute("ROLLBACK;")
        except Exception:
            pass
        raise e
    finally:
        conn.close()

def get_admin_metrics() -> Dict[str, Any]:
    """Provides inventory and revenue statistics for admin dashboard."""
    conn = get_db_connection()
    try:
        stock_stats = conn.execute(
            """
            SELECT category, 
                   COUNT(CASE WHEN status = 'UNSOLD' THEN 1 END) as unsold,
                   COUNT(CASE WHEN status = 'RESERVED' THEN 1 END) as reserved,
                   COUNT(CASE WHEN status = 'SOLD' THEN 1 END) as sold
            FROM vouchers
            GROUP BY category
            """
        ).fetchall()

        sales_stats = conn.execute(
            """
            SELECT COUNT(*) as total_orders,
                   COALESCE(SUM(total_amount), 0) as total_revenue
            FROM orders 
            WHERE payment_status = 'PAID'
            """
        ).fetchone()

        recent_orders = conn.execute(
            """
            SELECT order_reference, category, quantity, total_amount, customer_phone, 
                   payment_method, payment_status, created_at 
            FROM orders 
            ORDER BY created_at DESC 
            LIMIT 15
            """
        ).fetchall()

        return {
            "stock": [dict(r) for r in stock_stats],
            "total_orders": sales_stats["total_orders"],
            "total_revenue": round(sales_stats["total_revenue"], 2),
            "recent_orders": [dict(r) for r in recent_orders]
        }
    finally:
        conn.close()
