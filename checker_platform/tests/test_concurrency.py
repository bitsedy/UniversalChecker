"""
Concurrency Stress Test for CheckerPay Ghana
Spawns 25 concurrent threads attempting to reserve 5 available vouchers.
Proves zero double-allocation and atomic locking integrity.
"""

import concurrent.futures
import os
import tempfile
import unittest

temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
temp_db_path = temp_db.name
temp_db.close()
os.environ["CHECKER_DB_PATH"] = temp_db_path

from checker_platform.database import (
    init_db,
    get_db_connection,
    bulk_insert_vouchers,
    create_order,
    reserve_vouchers,
    complete_voucher_sale
)

class TestConcurrencyIntegrity(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        init_db()
        conn = get_db_connection()
        conn.execute("DELETE FROM vouchers WHERE category = 'CSSPS';")
        conn.close()

        # Seed exactly 5 vouchers
        vouchers = [
            {"serial_number": f"CONC_CSSPS_{i}", "pin": f"PIN_{i:06d}"}
            for i in range(1, 6)
        ]
        bulk_insert_vouchers("CSSPS", vouchers)

    def test_concurrent_reservations_no_double_sell(self):
        successful_reservations = []
        out_of_stock_count = 0

        def attempt_reservation(buyer_id):
            order_ref = f"ORD_CONC_{buyer_id}"
            try:
                create_order(
                    order_ref=order_ref,
                    category="CSSPS",
                    quantity=1,
                    unit_price=15.0,
                    customer_phone=f"02400000{buyer_id:02d}",
                    customer_email=None,
                    payment_method="MOMO_MTN"
                )
                res = reserve_vouchers("CSSPS", 1, order_ref)
                if res:
                    complete_voucher_sale(order_ref)
                    return ("SUCCESS", res[0]["serial_number"])
                else:
                    return ("OUT_OF_STOCK", None)
            except Exception as e:
                return ("ERROR", str(e))

        # Launch 25 concurrent buyers simultaneously
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(attempt_reservation, i) for i in range(1, 26)]
            results = [f.result() for f in futures]

        for status, serial in results:
            if status == "SUCCESS":
                successful_reservations.append(serial)
            elif status == "OUT_OF_STOCK":
                out_of_stock_count += 1

        print(f"\n[Concurrency Test Results] Successes: {len(successful_reservations)}, Out of Stock: {out_of_stock_count}")

        # Exactly 5 vouchers should have been sold
        self.assertEqual(len(successful_reservations), 5)
        # All 5 sold vouchers must have distinct unique serial numbers
        self.assertEqual(len(set(successful_reservations)), 5)
        # Exactly 20 buyers must have received out of stock
        self.assertEqual(out_of_stock_count, 20)

if __name__ == "__main__":
    unittest.main()
