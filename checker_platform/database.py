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
from typing import List, Dict, Any, Optional, Tuple

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

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS admission_benchmarks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                institution_code TEXT NOT NULL,
                institution_name TEXT NOT NULL,
                institution_type TEXT NOT NULL,
                programme_name TEXT NOT NULL,
                faculty_category TEXT NOT NULL,
                cutoff_aggregate INTEGER NOT NULL,
                cutoff_range_min INTEGER DEFAULT 6,
                cutoff_range_max INTEGER DEFAULT 12,
                mandatory_requirements TEXT NOT NULL,
                application_deadline TEXT,
                admission_status TEXT DEFAULT 'OPEN',
                voucher_cost_ghs REAL DEFAULT 220.0,
                portal_url TEXT NOT NULL,
                source_url TEXT,
                last_synced_at REAL NOT NULL,
                UNIQUE(institution_code, programme_name)
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS idempotency_records (
                idempotency_key TEXT PRIMARY KEY,
                request_path TEXT NOT NULL,
                request_digest TEXT NOT NULL,
                status TEXT NOT NULL,
                response_code INTEGER,
                response_body TEXT,
                created_at REAL NOT NULL,
                expires_at REAL NOT NULL
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS compliance_audit_ledger (
                block_index INTEGER PRIMARY KEY AUTOINCREMENT,
                previous_block_hash TEXT NOT NULL,
                current_block_hash TEXT NOT NULL UNIQUE,
                timestamp REAL NOT NULL,
                action_type TEXT NOT NULL,
                payload_digest TEXT NOT NULL,
                actor TEXT NOT NULL,
                nonce TEXT NOT NULL,
                verification_status TEXT DEFAULT 'VERIFIED'
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS advisory_telemetry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                exam_type TEXT NOT NULL,
                aggregate_value INTEGER NOT NULL,
                aggregate_bracket TEXT NOT NULL,
                field_of_interest TEXT NOT NULL,
                scholarships_matched INTEGER DEFAULT 0,
                timestamp REAL NOT NULL
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS customer_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_reference TEXT,
                customer_phone TEXT,
                customer_name TEXT,
                rating INTEGER NOT NULL,
                category TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                client_ip TEXT,
                status TEXT DEFAULT 'NEW'
            );
        """)

        # Performance and concurrency indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_vouchers_cat_status ON vouchers(category, status);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_vouchers_order_ref ON vouchers(order_reference);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_ref ON orders(order_reference);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_phone ON orders(customer_phone);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_vouchers_reserved_at ON vouchers(reserved_at);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_adm_type ON admission_benchmarks(institution_type);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_adm_faculty ON admission_benchmarks(faculty_category);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_adm_code ON admission_benchmarks(institution_code);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_idem_expires ON idempotency_records(expires_at);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_hash ON compliance_audit_ledger(current_block_hash);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_adv_tel_time ON advisory_telemetry(timestamp);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_adv_tel_exam ON advisory_telemetry(exam_type);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_feedback_created ON customer_feedback(created_at);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_feedback_rating ON customer_feedback(rating);")

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
            ("support_whatsapp", "+233509512942"),
            ("inventory_mode", "BATCH"), # 'BATCH' or 'DEMO_GENERATE'
            ("admin_username", "admin"),
            ("admin_password", "pbkdf2:sha256:100000$819e68795004da0b7d103dc1f7ea4bda$6d629dc72822847627fc5308b32ab1da9638b3b67cc13ef578a9f19e8b7c3d21"),
            ("admin_gate_key", "ghana2026_gate"),
            ("admin_allowed_ips", "127.0.0.1,::1"),
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
                "badge": "TVET Direct",
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
                avail = unsold_count if unsold_count > 0 else 999
            else:
                avail = unsold_count
            data["available_stock"] = avail

            if avail > 10:
                data["stock_status"] = "IN_STOCK"
                data["stock_label"] = "In Stock"
                data["stock_class"] = "in-stock"
            elif avail > 0:
                data["stock_status"] = "LOW_STOCK"
                data["stock_label"] = "Almost Out of Stock"
                data["stock_class"] = "low-stock"
            else:
                data["stock_status"] = "OUT_OF_STOCK"
                data["stock_label"] = "Out of Stock"
                data["stock_class"] = "out-of-stock"
            
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

        # Fetch sold vouchers
        rows = conn.execute(
            "SELECT serial_number, pin, category, sold_at FROM vouchers WHERE order_reference = ? AND status = 'SOLD'",
            (order_ref,)
        ).fetchall()

        expected_qty = order["quantity"]
        if len(rows) < expected_qty:
            conn.execute("ROLLBACK;")
            raise RuntimeError(
                f"Voucher allocation discrepancy for {order_ref}: "
                f"order requires {expected_qty} vouchers, but only {len(rows)} were allocated "
                f"(reservation may have expired before payment completion)."
            )

        # Update order status to PAID
        conn.execute(
            """
            UPDATE orders 
            SET payment_status = 'PAID',
                updated_at = datetime('now')
            WHERE order_reference = ?
            """,
            (order_ref,)
        )

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

def get_admission_benchmarks(
    institution_type: Optional[str] = None,
    faculty_category: Optional[str] = None,
    institution_code: Optional[str] = None,
    search: Optional[str] = None,
    search_query: Optional[str] = None,
    limit: int = 150
) -> List[Dict[str, Any]]:
    """Retrieves live admission benchmarks, cut-off points, and deadlines."""
    active_search = search or search_query
    conn = get_db_connection()
    try:
        query = "SELECT * FROM admission_benchmarks WHERE 1=1"
        params: List[Any] = []
        if institution_type:
            query += " AND institution_type = ?"
            params.append(institution_type)
        if faculty_category:
            query += " AND faculty_category = ?"
            params.append(faculty_category)
        if institution_code:
            query += " AND institution_code = ?"
            params.append(institution_code)
        if active_search:
            query += " AND (programme_name LIKE ? OR institution_name LIKE ? OR mandatory_requirements LIKE ?)"
            s_param = f"%{active_search.strip()}%"
            params.extend([s_param, s_param, s_param])
        query += " ORDER BY cutoff_aggregate ASC, institution_name ASC LIMIT ?"
        params.append(limit)
        
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]
    except sqlite3.OperationalError:
        return []
    finally:
        conn.close()

def upsert_admission_benchmark(benchmark_data: Optional[Dict[str, Any]] = None, **kwargs):
    """Inserts or updates a single admission benchmark record."""
    data = dict(benchmark_data) if benchmark_data else dict(kwargs)
    conn = get_db_connection()
    try:
        conn.execute(
            """
            INSERT INTO admission_benchmarks (
                institution_code, institution_name, institution_type,
                programme_name, faculty_category, cutoff_aggregate,
                cutoff_range_min, cutoff_range_max, mandatory_requirements,
                application_deadline, admission_status, voucher_cost_ghs,
                portal_url, source_url, last_synced_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(institution_code, programme_name) DO UPDATE SET
                institution_name = excluded.institution_name,
                institution_type = excluded.institution_type,
                faculty_category = excluded.faculty_category,
                cutoff_aggregate = excluded.cutoff_aggregate,
                cutoff_range_min = excluded.cutoff_range_min,
                cutoff_range_max = excluded.cutoff_range_max,
                mandatory_requirements = excluded.mandatory_requirements,
                application_deadline = excluded.application_deadline,
                admission_status = excluded.admission_status,
                voucher_cost_ghs = excluded.voucher_cost_ghs,
                portal_url = excluded.portal_url,
                source_url = excluded.source_url,
                last_synced_at = excluded.last_synced_at;
            """,
            (
                data["institution_code"],
                data["institution_name"],
                data["institution_type"],
                data["programme_name"],
                data["faculty_category"],
                data["cutoff_aggregate"],
                data.get("cutoff_range_min", 6),
                data.get("cutoff_range_max", 12),
                data["mandatory_requirements"],
                data.get("application_deadline"),
                data.get("admission_status", "OPEN"),
                data.get("voucher_cost_ghs", 220.0),
                data["portal_url"],
                data.get("source_url"),
                data.get("last_synced_at", time.time())
            )
        )
        conn.commit()
    finally:
        conn.close()

def bulk_upsert_admission_benchmarks(benchmarks: List[Dict[str, Any]]) -> int:
    """Inserts or updates multiple admission benchmark records in a single transaction."""
    if not benchmarks:
        return 0
    conn = get_db_connection()
    try:
        now = time.time()
        for b in benchmarks:
            conn.execute(
                """
                INSERT INTO admission_benchmarks (
                    institution_code, institution_name, institution_type,
                    programme_name, faculty_category, cutoff_aggregate,
                    cutoff_range_min, cutoff_range_max, mandatory_requirements,
                    application_deadline, admission_status, voucher_cost_ghs,
                    portal_url, source_url, last_synced_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(institution_code, programme_name) DO UPDATE SET
                    institution_name = excluded.institution_name,
                    institution_type = excluded.institution_type,
                    faculty_category = excluded.faculty_category,
                    cutoff_aggregate = excluded.cutoff_aggregate,
                    cutoff_range_min = excluded.cutoff_range_min,
                    cutoff_range_max = excluded.cutoff_range_max,
                    mandatory_requirements = excluded.mandatory_requirements,
                    application_deadline = excluded.application_deadline,
                    admission_status = excluded.admission_status,
                    voucher_cost_ghs = excluded.voucher_cost_ghs,
                    portal_url = excluded.portal_url,
                    source_url = excluded.source_url,
                    last_synced_at = excluded.last_synced_at;
                """,
                (
                    b["institution_code"],
                    b["institution_name"],
                    b["institution_type"],
                    b["programme_name"],
                    b["faculty_category"],
                    b["cutoff_aggregate"],
                    b.get("cutoff_range_min", 6),
                    b.get("cutoff_range_max", 12),
                    b["mandatory_requirements"],
                    b.get("application_deadline"),
                    b.get("admission_status", "OPEN"),
                    b.get("voucher_cost_ghs", 220.0),
                    b["portal_url"],
                    b.get("source_url"),
                    b.get("last_synced_at", now)
                )
            )
        conn.commit()
        return len(benchmarks)
    finally:
        conn.close()

def get_admissions_summary_metrics() -> Dict[str, Any]:
    """Returns summary statistics of the admissions benchmark database."""
    conn = get_db_connection()
    try:
        total = conn.execute("SELECT COUNT(*) as c FROM admission_benchmarks;").fetchone()["c"]
        open_count = conn.execute("SELECT COUNT(*) as c FROM admission_benchmarks WHERE admission_status IN ('OPEN', 'CLOSING_SOON');").fetchone()["c"]
        institutions = conn.execute("SELECT COUNT(DISTINCT institution_code) as c FROM admission_benchmarks;").fetchone()["c"]
        last_sync_row = conn.execute("SELECT MAX(last_synced_at) as m FROM admission_benchmarks;").fetchone()
        last_sync = last_sync_row["m"] if last_sync_row and last_sync_row["m"] else 0
        return {
            "total_programmes": total,
            "open_admissions": open_count,
            "institutions_tracked": institutions,
            "total_institutions": institutions,
            "last_synced_at": last_sync,
            "latest_scrape": last_sync
        }
    except sqlite3.OperationalError:
        return {
            "total_programmes": 0,
            "open_admissions": 0,
            "institutions_tracked": 0,
            "total_institutions": 0,
            "last_synced_at": 0,
            "latest_scrape": 0
        }
    finally:
        conn.close()

# ============================================================================
# ENTERPRISE IDEMPOTENCY & AUDIT LEDGER SERVICES
# ============================================================================

def acquire_idempotency_lock(
    key: str, 
    path: str, 
    digest: str, 
    ttl_seconds: int = 300
) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Acquires an atomic idempotency lock.
    Returns (True, None) if lock acquired.
    Returns (False, existing_record) if key was already seen or in-flight.
    """
    conn = get_db_connection()
    now = time.time()
    try:
        conn.execute("BEGIN IMMEDIATE;")
        row = conn.execute("SELECT * FROM idempotency_records WHERE idempotency_key = ?", (key,)).fetchone()
        
        if row:
            if row["status"] == "COMPLETED":
                conn.execute("COMMIT;")
                return False, {
                    "status": "COMPLETED",
                    "response_code": row["response_code"],
                    "response_body": row["response_body"]
                }
            elif row["status"] == "IN_FLIGHT" and row["expires_at"] > now:
                conn.execute("COMMIT;")
                return False, {
                    "status": "IN_FLIGHT",
                    "response_code": 409,
                    "response_body": '{"error": "Concurrent request in-flight. Please retry in a moment."}'
                }
            # Lock expired; allow takeover
            conn.execute(
                """
                UPDATE idempotency_records 
                SET request_path = ?, request_digest = ?, status = 'IN_FLIGHT', 
                    created_at = ?, expires_at = ?
                WHERE idempotency_key = ?
                """,
                (path, digest, now, now + ttl_seconds, key)
            )
            conn.execute("COMMIT;")
            return True, None
        else:
            conn.execute(
                """
                INSERT INTO idempotency_records (
                    idempotency_key, request_path, request_digest, status, created_at, expires_at
                ) VALUES (?, ?, ?, 'IN_FLIGHT', ?, ?)
                """,
                (key, path, digest, now, now + ttl_seconds)
            )
            conn.execute("COMMIT;")
            return True, None
    except Exception as e:
        try:
            conn.execute("ROLLBACK;")
        except Exception:
            pass
        raise e
    finally:
        conn.close()

def complete_idempotency_record(key: str, response_code: int, response_body: str):
    """Marks an idempotency record as COMPLETED with its response payload."""
    conn = get_db_connection()
    try:
        conn.execute(
            """
            UPDATE idempotency_records 
            SET status = 'COMPLETED', response_code = ?, response_body = ?
            WHERE idempotency_key = ?
            """,
            (response_code, response_body, key)
        )
        conn.commit()
    finally:
        conn.close()

def release_idempotency_lock(key: str):
    """Removes an idempotency lock in the event of an early unhandled validation failure."""
    conn = get_db_connection()
    try:
        conn.execute("DELETE FROM idempotency_records WHERE idempotency_key = ? AND status = 'IN_FLIGHT'", (key,))
        conn.commit()
    finally:
        conn.close()

def append_audit_block(action: str, actor: str, payload_data: Any) -> str:
    """
    Appends a new block to the tamper-evident SHA-256 compliance audit ledger.
    Returns the newly minted block hash.
    """
    from .services.security import CryptographicAuditLedger, GENESIS_BLOCK_HASH
    
    conn = get_db_connection()
    now = time.time()
    nonce = os.urandom(8).hex()
    payload_digest = CryptographicAuditLedger.compute_payload_digest(payload_data)

    try:
        conn.execute("BEGIN IMMEDIATE;")
        latest = conn.execute(
            "SELECT current_block_hash FROM compliance_audit_ledger ORDER BY block_index DESC LIMIT 1"
        ).fetchone()
        prev_hash = latest["current_block_hash"] if latest else GENESIS_BLOCK_HASH
        
        current_hash = CryptographicAuditLedger.calculate_block_hash(
            prev_hash=prev_hash,
            timestamp=now,
            action=action,
            payload_digest=payload_digest,
            nonce=nonce
        )

        conn.execute(
            """
            INSERT INTO compliance_audit_ledger (
                previous_block_hash, current_block_hash, timestamp, action_type,
                payload_digest, actor, nonce, verification_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'VERIFIED')
            """,
            (prev_hash, current_hash, now, action, payload_digest, actor, nonce)
        )
        conn.execute("COMMIT;")
        return current_hash
    except Exception as e:
        try:
            conn.execute("ROLLBACK;")
        except Exception:
            pass
        raise e
    finally:
        conn.close()

def verify_audit_chain_integrity() -> Tuple[bool, int, str]:
    """
    Cryptographically verifies the entire compliance audit ledger from genesis block.
    Returns (is_valid, count_verified, message).
    """
    from .services.security import CryptographicAuditLedger, GENESIS_BLOCK_HASH

    conn = get_db_connection()
    try:
        rows = conn.execute("SELECT * FROM compliance_audit_ledger ORDER BY block_index ASC").fetchall()
        if not rows:
            return True, 0, "Audit ledger is empty (genesis pending)."

        expected_prev_hash = GENESIS_BLOCK_HASH
        for row in rows:
            if row["previous_block_hash"] != expected_prev_hash:
                return False, row["block_index"], f"Broken chain link at Block #{row['block_index']}."

            recalculated_hash = CryptographicAuditLedger.calculate_block_hash(
                prev_hash=row["previous_block_hash"],
                timestamp=row["timestamp"],
                action=row["action_type"],
                payload_digest=row["payload_digest"],
                nonce=row["nonce"]
            )
            if recalculated_hash != row["current_block_hash"]:
                return False, row["block_index"], f"Tampered block hash at Block #{row['block_index']}."

            expected_prev_hash = row["current_block_hash"]

        return True, len(rows), f"All {len(rows)} blocks cryptographically verified and unbroken."
    finally:
        conn.close()

def verify_database_integrity() -> Dict[str, Any]:
    """Performs low-level SQLite integrity and relational structure verification."""
    conn = get_db_connection()
    try:
        quick = conn.execute("PRAGMA quick_check;").fetchone()[0]
        fks = conn.execute("PRAGMA foreign_key_check;").fetchall()
        
        tables = [
            "vouchers", "orders", "transactions", "site_settings",
            "admission_benchmarks", "idempotency_records", "compliance_audit_ledger",
            "advisory_telemetry", "customer_feedback"
        ]
        table_counts = {}
        for t in tables:
            try:
                table_counts[t] = conn.execute(f"SELECT COUNT(*) as c FROM {t}").fetchone()["c"]
            except Exception:
                table_counts[t] = -1

        is_intact = (quick == "ok" and len(fks) == 0 and all(c >= 0 for c in table_counts.values()))
        return {
            "intact": is_intact,
            "quick_check": quick,
            "foreign_key_violations": len(fks),
            "table_counts": table_counts
        }
    finally:
        conn.close()

def log_advisory_telemetry(
    exam_type: str, 
    aggregate_value: int, 
    field_of_interest: str, 
    scholarships_matched: int = 0
) -> None:
    """
    Non-blockingly logs an anonymized telemetry entry for educational advisor analytics.
    Strictly zero PII (no phone, no name, no individual grades, no index numbers).
    """
    bracket = "Agg 06 - 09" if aggregate_value <= 9 else (
        "Agg 10 - 15" if aggregate_value <= 15 else (
            "Agg 16 - 24" if aggregate_value <= 24 else (
                "Agg 25 - 36" if aggregate_value <= 36 else "Agg 37+"
            )
        )
    )
    conn = get_db_connection()
    try:
        conn.execute(
            """
            INSERT INTO advisory_telemetry (
                exam_type, aggregate_value, aggregate_bracket, field_of_interest, scholarships_matched, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (exam_type, aggregate_value, bracket, field_of_interest, scholarships_matched, time.time())
        )
        conn.commit()
    except Exception:
        pass
    finally:
        conn.close()

def seed_advisory_telemetry_if_empty() -> int:
    """Seeds baseline synthetic educational telemetry if table is empty for visual dashboard demonstration."""
    conn = get_db_connection()
    try:
        count = conn.execute("SELECT COUNT(*) as c FROM advisory_telemetry").fetchone()["c"]
        if count > 0:
            return count

        now = time.time()
        sample_records = [
            # WASSCE Candidates
            ("WASSCE", 8, "Agg 06 - 09", "Computer Science & Engineering", 6, now - 86400 * 5),
            ("WASSCE", 7, "Agg 06 - 09", "Medicine & Health Sciences", 6, now - 86400 * 4),
            ("WASSCE", 11, "Agg 10 - 15", "Computer Science & Engineering", 5, now - 86400 * 4),
            ("WASSCE", 14, "Agg 10 - 15", "Business, Finance & Law", 4, now - 86400 * 3),
            ("WASSCE", 12, "Agg 10 - 15", "Engineering & Technology", 5, now - 86400 * 3),
            ("WASSCE", 18, "Agg 16 - 24", "Business, Finance & Law", 3, now - 86400 * 2),
            ("WASSCE", 19, "Agg 16 - 24", "Nursing & Allied Health", 3, now - 86400 * 2),
            ("WASSCE", 22, "Agg 16 - 24", "Arts, Humanities & Social Sciences", 2, now - 86400 * 1),
            ("WASSCE", 27, "Agg 25 - 36", "Technical University (HND)", 1, now - 3600 * 18),
            ("WASSCE", 32, "Agg 25 - 36", "Applied Sciences", 0, now - 3600 * 12),
            ("WASSCE", 38, "Agg 37+", "Remedial NOV/DEC Strategy", 0, now - 3600 * 4),
            # BECE Candidates
            ("BECE", 8, "Agg 06 - 09", "General Science", 0, now - 86400 * 5),
            ("BECE", 9, "Agg 06 - 09", "General Science", 0, now - 86400 * 4),
            ("BECE", 13, "Agg 10 - 15", "General Arts", 0, now - 86400 * 3),
            ("BECE", 15, "Agg 10 - 15", "Business", 0, now - 86400 * 2),
            ("BECE", 18, "Agg 16 - 24", "Visual Arts", 0, now - 86400 * 2),
            ("BECE", 22, "Agg 16 - 24", "Home Economics", 0, now - 3600 * 8),
            ("BECE", 28, "Agg 25 - 36", "Technical / Vocational", 0, now - 3600 * 2),
        ]

        conn.executemany(
            """
            INSERT INTO advisory_telemetry (
                exam_type, aggregate_value, aggregate_bracket, field_of_interest, scholarships_matched, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            sample_records
        )
        conn.commit()
        return len(sample_records)
    except Exception:
        return 0
    finally:
        conn.close()

# ============================================================================
# CUSTOMER FEEDBACK SERVICES
# ============================================================================

def save_customer_feedback(
    rating: int,
    category: str,
    message: str,
    order_reference: Optional[str] = None,
    customer_phone: Optional[str] = None,
    customer_name: Optional[str] = None,
    client_ip: Optional[str] = None
) -> int:
    """
    Saves customer feedback to the database.
    Returns the new feedback row ID.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO customer_feedback (
                order_reference, customer_phone, customer_name,
                rating, category, message, client_ip
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                order_reference.strip() if order_reference else None,
                customer_phone.strip() if customer_phone else None,
                customer_name.strip() if customer_name else None,
                int(rating),
                category.strip(),
                message.strip(),
                client_ip
            )
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()

def get_customer_feedback(limit: int = 50, status: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Retrieves recent customer feedback records.
    """
    conn = get_db_connection()
    try:
        if status:
            rows = conn.execute(
                "SELECT * FROM customer_feedback WHERE status = ? ORDER BY id DESC LIMIT ?",
                (status, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM customer_feedback ORDER BY id DESC LIMIT ?",
                (limit,)
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
