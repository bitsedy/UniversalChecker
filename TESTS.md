# 🧪 Mandatory Dual-Tier Testing Protocol: UniversalChecker / CheckerPay

> **MANDATORY POLICY FOR ALL AGENTS & ENGINEERS**  
> Every feature, bug fix, or UI change MUST undergo both testing tiers before being accepted or deployed. Never describe a task as "done" without executing and reporting both tiers.

---

## 🏛️ The Two Mandatory Testing Tiers

```
┌────────────────────────────────────────────────────────────────────────┐
│                   MANDATORY DUAL-TIER TESTING PROTOCOL                 │
├──────────────────────────────────┬─────────────────────────────────────┤
│   TIER 1: SYSTEMATIC AUTOMATED   │     TIER 2: PHYSICAL VERIFICATION   │
│   • Complete pytest suite        │     • Live site navigation & render │
│   • Zero regression failures     │     • Every button clicked & tested │
│   • Concurrency & atomic locks   │     • Mobile & Desktop visual audit │
│   • API contract validation      │     • Copy, wording & tone review   │
└──────────────────────────────────┴─────────────────────────────────────┘
```

---

## ⚙️ Tier 1: Systematic Automated Testing

Before touching any physical testing, the automated test suite must run and pass with **zero failures and zero regressions**.

### Execution Command:
```powershell
.\.venv\Scripts\python.exe -m pytest
```

### Coverage Checklist:
- [ ] **Orders & Inventory:** Atomic inventory locking (`BEGIN EXCLUSIVE`), order creation, 10-minute reservation hold expiry, payment cancellation.
- [ ] **Payments & Webhooks:** HMAC SHA-512 signature validation, Paystack redirect flows, Hubtel fallback.
- [ ] **Pathway Advisor Privacy (Act 843):** Zero persistence of candidate grades, index numbers, or exam identifying data. In-memory calculations only.
- [ ] **API Endpoints:** Rate limiting, CSRF tokens, session expiration, and error responses.
- [ ] **Pages & Routing:** All public routes (`/`, `/lookup`, `/advisor`, `/guides`, `/faq`, `/about`, `/terms`, `/privacy`, `/health`) return `200 OK`.

---

## 👁️ Tier 2: Physical Verification Testing (Upfront Live Inspection)

Physical testing means **literally visiting the running application (`http://127.0.0.1:8000`)** and verifying every visual component, button, navigation link, modal, and text block upfront.

### 1. Ensure Local Server is Active
```powershell
python run_server.py
```
Verify the server responds on `http://127.0.0.1:8000/health`.

---

### 2. Physical Inspection Matrix by Page

#### A. Storefront Home (`/`)
- [ ] **Header & Branding:** Verify logo SVG renders crisply. On mobile ($\le 960\text{px}$), verify the quick-action **"Retrieve Voucher"** button is pinned at top right.
- [ ] **Navigation Track:** Scroll through `.nav-links`. Click every link (`Home`, `Pathway Advisor`, `Guides & Rules`, `FAQs & Support`, `About Us`, `Retrieve My Voucher`). Confirm correct active state highlighting.
- [ ] **Hero Section:** Inspect heading, value proposition, and CTA buttons. Ensure text wrapping is natural with no orphan words or awkward line breaks.
- [ ] **Voucher Cards (WASSCE, BECE, CSSPS, CTVET):**
  - Verify official card names, prices in GH₵, and stock indicators (e.g. "In Stock • Instant Delivery").
  - Click **"Buy Voucher"** on each card to ensure the modal opens with the correct pre-selected category.

#### B. Checkout & Payment Modal
- [ ] **Mobile Bottom Sheet:** On mobile ($\le 640\text{px}$), verify the modal anchors as a bottom sheet with a visible pull handle, `100dvh` viewport safety, and zero background rubber-banding.
- [ ] **Quantity Selector:** Change quantity ($1, 2, 3, 5, 10$). Verify price per card and total price recalculate instantly in GH₵.
- [ ] **Phone Number Input:**
  - Verify the input is full-width with a legible placeholder (`e.g. 024 123 4567 or 050 000 0000`).
  - Test typing `024` / `054` $\rightarrow$ Confirm **MTN MoMo** is detected and the adaptive affirmation bar appears below the field.
  - Test typing `020` / `050` $\rightarrow$ Confirm **Telecel Cash** is detected.
  - Test typing `027` / `026` $\rightarrow$ Confirm **AT Money** is detected.
- [ ] **Validation Feedback (Zero Halting Alerts):**
  - Leave phone blank or enter 4 digits $\rightarrow$ Click **"Pay with Mobile Money"**.
  - Confirm **NO `window.alert()` popup appears**.
  - Confirm the input receives a crimson error border and the inline message appears: *"Please enter a valid 10-digit Ghanaian mobile number."*
- [ ] **Payment Simulation & Cancellation:**
  - Enter a valid test number $\rightarrow$ Click Pay.
  - Confirm the reservation countdown timer (`10:00`) starts ticking.
  - Confirm the live activity indicator ("Listening for payment confirmation...") pulses.
  - Click **"Cancel Payment & Release Card"** $\rightarrow$ Confirm prompt closes and voucher is unlocked.

#### C. Self-Service Voucher Lookup (`/lookup`)
- [ ] **Search Field:** Type a phone number or reference (`ORD-...`).
- [ ] **Submit Button:** Confirm the button is full-width on mobile ($\le 640\text{px}$) and doesn't sit awkwardly left-aligned.
- [ ] **Loading State:** Confirm the YouTube-style skeleton shimmer renders during retrieval without layout shift.
- [ ] **Result Card:** Confirm voucher PIN/Serial reveal cards format clearly with copy-to-clipboard buttons and print slips.

#### D. Pathway Advisor (`/advisor`)
- [ ] **Act 843 Consent Gating:** Confirm the advisory panel is locked until the explicit Act 843 consent checkbox is ticked.
- [ ] **Exam Tabs:** Switch between BECE, WASSCE, and Explorer tabs.
- [ ] **1-Click Presets:** Click example grade buttons (`Distinction`, `Competitive`, `Borderline`). On mobile, confirm presets wrap as a balanced 2-column grid without horizontal clipping.
- [ ] **Grade Evaluator:** Change grade dropdowns (A1 to F9) $\rightarrow$ Confirm aggregate recalculates live in-memory.

#### E. Portal Guides (`/guides`) & FAQs (`/faq`)
- [ ] **Guides:** Click each quick-nav pill. Confirm smooth scroll to WAEC direct portal instructions, 3-check limit rules, and CSSPS 12-digit rules.
- [ ] **FAQs:** Click accordion questions. Verify smooth open/close expansion with accessible chevron rotation.
- [ ] **WhatsApp Desk:** Confirm the school/cafe desk link carries a pre-filled, friendly inquiry message.

---

### 3. Visual & Cross-Device Ergonomics
- [ ] **Mobile Smartphone (360px – 390px):** Test using mobile viewport emulation (iPhone 12/13/14, Samsung Galaxy A-series). Confirm **zero horizontal overflow** (`overflow-x: hidden`), comfortable line lengths, and $\ge 44\times 44\text{px}$ touch targets.
- [ ] **Desktop (1280px+):** Confirm clean, spacious container max-widths, elevated card shadows, and centered alignments.
- [ ] **Color Contrast (WCAG AAA):** Ensure deep obsidian ink (`#0A0F1D`) on crisp stark white (`#FFFFFF`) remains legible under bright outdoor sunlight.
- [ ] **UI Cleanliness Rules (Strict Invariants):**
  1. NEVER use cylindrical floating pill badges above page headings.
  2. NEVER add top rectangular info/authority banner bars above the navbar.
  3. Strictly employ basic, simple, friendly language for all copy and features.

---

## 📋 Required Reporting Format in Task Summaries

Every completed task must report both tiers in this exact structure:

```markdown
### 🧪 Test Verification Report

#### 1. Systematic Automated Tests (Tier 1)
- **Command:** `.\.venv\Scripts\python.exe -m pytest`
- **Result:** 116 passed in 15.50s (0 failures, 0 regressions)

#### 2. Physical Verification Testing (Tier 2)
- **Live URL Inspected:** `http://127.0.0.1:8000`
- **Devices Verified:** Desktop (1440px) & Mobile Smartphone (375px & 390px)
- **Interactive Flows Checked:**
  - [x] Navbar mobile quick-action & horizontal sub-track navigation
  - [x] Voucher cards & category pricing
  - [x] Bottom-sheet checkout modal & quantity recalculation
  - [x] Phone number input, carrier auto-detection & inline error feedback
  - [x] Order reservation hold, status listener & cancellation flow
  - [x] Lookup search, skeleton loading & voucher reveal
  - [x] Pathway Advisor Act 843 consent toggle & grade aggregate calculators
  - [x] Guide anchors & FAQ accordions
- **Copy & Typography Check:** Verified clean, friendly Ghanaian English across all headings, buttons, and helper texts.
```
