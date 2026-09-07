"""
Batch Voucher Generator for CheckerPay Ghana
Generates batches of 50 test vouchers for each exam category:
- WAEC WASSCE (50 vouchers)
- WAEC BECE (50 vouchers)
- CSSPS Senior High School Placement (50 vouchers)
- CTVET / NABPTEX Technical Examinations (50 vouchers)

Outputs text batch files (ready for /admin import) and inserts into checker.db.
"""

import os
import csv
import random
import time
from checker_platform.database import init_db, bulk_insert_vouchers, get_admin_metrics

CATEGORIES = {
    "WASSCE": {
        "prefix": "WSC2026",
        "pin_length": 12,
        "filename": "wassce_batch_50.txt"
    },
    "BECE": {
        "prefix": "BEC2026",
        "pin_length": 12,
        "filename": "bece_batch_50.txt"
    },
    "CSSPS": {
        "prefix": "CSS2026",
        "pin_length": 11,
        "filename": "cssps_batch_50.txt"
    },
    "CTVET": {
        "prefix": "CTV2026",
        "pin_length": 12,
        "filename": "ctvet_batch_50.txt"
    }
}

def generate_pin(length: int) -> str:
    first = str(random.randint(1, 9))
    rest = "".join([str(random.randint(0, 9)) for _ in range(length - 1)])
    return first + rest

def generate_batch(category: str, count: int = 50, batch_tag: str = "T") -> list:
    cfg = CATEGORIES[category]
    prefix = cfg["prefix"]
    pin_len = cfg["pin_length"]
    
    timestamp_sub = str(int(time.time()))[-4:]
    vouchers = []
    
    for i in range(1, count + 1):
        serial = f"{prefix}{batch_tag}{timestamp_sub}{i:03d}"
        pin = generate_pin(pin_len)
        vouchers.append({
            "category": category,
            "serial_number": serial,
            "pin": pin
        })
    return vouchers

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(base_dir, "test_batches")
    os.makedirs(output_dir, exist_ok=True)
    
    init_db()
    
    all_vouchers = []
    summary = {}
    
    for cat, cfg in CATEGORIES.items():
        vouchers = generate_batch(cat, count=50)
        all_vouchers.extend(vouchers)
        
        # Write category text file (format: SERIAL, PIN)
        txt_path = os.path.join(output_dir, cfg["filename"])
        with open(txt_path, "w", encoding="utf-8") as f:
            for v in vouchers:
                f.write(f"{v['serial_number']}, {v['pin']}\n")
        
        # Bulk insert into database
        db_items = [{"serial_number": v["serial_number"], "pin": v["pin"]} for v in vouchers]
        res = bulk_insert_vouchers(cat, db_items)
        summary[cat] = {
            "generated": len(vouchers),
            "inserted": res["inserted"],
            "duplicates": res["duplicates"],
            "file": os.path.relpath(txt_path, base_dir)
        }
    
    # Also write a combined CSV file
    csv_path = os.path.join(output_dir, "all_test_vouchers_200.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Category", "Serial Number", "PIN", "Status"])
        for v in all_vouchers:
            writer.writerow([v["category"], v["serial_number"], v["pin"], "UNSOLD"])
            
    print("=" * 60)
    print("TEST VOUCHER BATCHES GENERATED SUCCESSFULLY (50 PER CATEGORY)")
    print("=" * 60)
    for cat, info in summary.items():
        print(f"[{cat:6}] +{info['inserted']} inserted into DB | Saved to: {info['file']}")
    print(f"[COMBINED] Saved all 200 vouchers to: {os.path.relpath(csv_path, base_dir)}")
    
    metrics = get_admin_metrics()
    print("\nCURRENT INVENTORY TOTALS IN DATABASE:")
    for s in metrics["stock"]:
        print(f"  * {s['category']:6} -> Available (Unsold): {s['unsold']} | Reserved: {s['reserved']} | Sold: {s['sold']}")
    print("=" * 60)

if __name__ == "__main__":
    main()
