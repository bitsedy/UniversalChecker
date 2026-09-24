# 🇬🇭 UniversalChecker - Ghanaian Result Checker & eVoucher Reselling Platform

A modern, high-concurrency digital voucher reselling platform tailored to the Ghanaian educational ecosystem (**WAEC WASSCE**, **WAEC BECE**, **CSSPS Placement**, and **CTVET / NABPTEX**).

---

## 🌟 Key Features

1. **Digital Voucher Reseller Gateway (Model A)**:
   - Eliminates automated scraping hazards (*"Voucher Burn"* on official portals under traffic spikes).
   - Complies with Ghana's **Data Protection Act, 2012 (Act 843)** by never storing student PII or educational records.
   - Automatically directs candidates to official verification portals with step-by-step guidance.

2. **Automated Category-Specific Portal Routing & 6-Second Countdown**:
   - **BECE** &rarr; Automatically launches [**`https://eresults.waecgh.org`**](https://eresults.waecgh.org)
   - **WASSCE** &rarr; Automatically launches [**`https://ghana.waecdirect.org`**](https://ghana.waecdirect.org)
   - **CSSPS** &rarr; Automatically launches [**`https://cssps.gov.gh`**](https://cssps.gov.gh)
   - **CTVET** &rarr; Automatically launches [**`https://ctvet.gov.gh`**](https://ctvet.gov.gh)
   - Includes a visual progress bar, "Pause / Resume" controls, and instant "Go Now ↗" hyperlinks.

3. **Ghanaian Payment Stack**:
   - **Paystack (Ghana)**: Direct API integration supporting MTN MoMo, Telecel Cash, AT Money, and Cards in GHS with HMAC SHA512 webhook signature verification.
   - **Direct Ghanaian MoMo USSD Simulator**: Integrated sandbox for testing showing USSD prompt simulation (`*170#`, `*110#`) with automatic network detection from Ghanaian prefixes (`024`, `054`, `020`, `027`, etc.).

4. **Concurrency-Safe Atomic Inventory Locking**:
   - SQLite in **WAL (Write-Ahead Logging)** mode with `BEGIN IMMEDIATE` row-locking transactions.
   - Tested under 25 simultaneous threads: guaranteed zero double-allocations.
   - 10-minute reservation expiry mechanism with automatic background recycling worker.

5. **Customer Self-Service & Merchant Management**:
   - **Self-Service Voucher Retrieval (`/lookup`)**: Retrieve past PINs and serials anytime using phone number or order reference.
   - **Portal Traps & Guidelines (`/guides`)**: Educational guide covering the WAEC 3-check limit, CSSPS 10-digit + 2-digit completion year rule (`101010101026`), and CTVET center codes.
   - **Admin Operations (`/admin`)**: Live inventory stock levels, bulk CSV/PIN importer, price configuration, and recent transaction history.

---

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the Platform
```bash
python run_server.py
```

### 3. Open in Browser
- **Storefront**: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **Voucher Recovery**: [http://127.0.0.1:8000/lookup](http://127.0.0.1:8000/lookup)
- **Portal Guides**: [http://127.0.0.1:8000/guides](http://127.0.0.1:8000/guides)
- **Merchant Admin**: [http://127.0.0.1:8000/admin](http://127.0.0.1:8000/admin)
- **API Documentation**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

### 4. Run Automated Tests
```bash
python -m unittest discover -s checker_platform/tests
```
