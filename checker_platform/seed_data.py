"""
Seed Inventory Data for Ghanaian Result Checker Reseller Platform
Generates initial stock of authentic-style vouchers for WASSCE, BECE, CSSPS, and CTVET.
"""

import random
from .database import init_db, bulk_insert_vouchers, get_admin_metrics

def generate_vouchers(category: str, count: int = 25) -> list:
    vouchers = []
    prefixes = {
        "WASSCE": "WSC2026",
        "BECE": "BEC2026",
        "CSSPS": "CSS2026",
        "CTVET": "CTV2026"
    }
    prefix = prefixes.get(category, "VCH2026")

    for i in range(1, count + 1):
        serial_suffix = f"{i:04d}{random.randint(100, 999)}"
        serial = f"{prefix}{serial_suffix}"
        # 12-digit PIN for WAEC & CTVET; 10-12 digit for CSSPS
        pin_len = 10 if category == "CSSPS" and i % 2 == 0 else 12
        pin = "".join([str(random.randint(0, 9)) for _ in range(pin_len)])
        vouchers.append({"serial_number": serial, "pin": pin})
    return vouchers

def run_seed():
    print("Initializing Database...")
    init_db()

    categories = ["WASSCE", "BECE", "CSSPS", "CTVET"]
    for cat in categories:
        items = generate_vouchers(cat, count=30)
        res = bulk_insert_vouchers(cat, items)
        print(f"[{cat}] Inserted {res['inserted']} vouchers ({res['duplicates']} duplicates skipped).")

    metrics = get_admin_metrics()
    print("\nCurrent Inventory Metrics:")
    for s in metrics["stock"]:
        print(f" - {s['category']}: Unsold: {s['unsold']}, Reserved: {s['reserved']}, Sold: {s['sold']}")

if __name__ == "__main__":
    run_seed()
