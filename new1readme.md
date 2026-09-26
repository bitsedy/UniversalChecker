# 🇬🇭 CheckerPay Ghana (UniversalChecker)
## Sovereign Digital Examination Voucher Gateway & Educational Pathway Intelligence Platform

---

## 1. Executive Summary & Main Purpose of the System

**CheckerPay Ghana** (architecturally designated **UniversalChecker**) is an enterprise-grade digital voucher distribution gateway and educational pathway intelligence platform built specifically for the Ghanaian secondary and tertiary educational ecosystems. 

### 1.1 The Primary Mandate
Every academic cycle across Ghana, over 550,000 junior high school graduates sit for the Basic Education Certificate Examination (**BECE**), more than 450,000 senior high school students write the West African Senior School Certificate Examination (**WASSCE**), tens of thousands sit for **CTVET / NABPTEX** technical examinations, and hundreds of thousands of candidates await placement through the Computerized School Selection and Placement System (**CSSPS**).

The core purpose of CheckerPay Ghana is to:
1. **Provide 100% Guaranteed, Concurrency-Safe Digital Distribution** of official examination result checker PINs and school placement vouchers directly to students, parents, and schools nationwide.
2. **Eliminate Friction, Card Scarcity, and Extortionate Price Gouging** during high-demand national result release windows.
3. **Prevent "Voucher Burn"** through automated category-specific routing and portal education.
4. **Democratize Educational Access & Academic Decision-Making** through an automated, Act 843–compliant **Placement & Pathway Advisory Engine** that objectively analyzes candidate aggregates and matches them to Ghanaian Senior High Schools (Categories A–D) and public/private universities without compromising student data privacy.

---

## 2. Core Problems Solved

### 2.1 The "Voucher Burn" Dilemma & Automated Scraping Hazards
Official verification portals administered by the West African Examinations Council (WAEC) enforce a strict **3-check lookup limit** per voucher. Once an index number is validated, the voucher is permanently bound to that candidate, and every subsequent query decrements the remaining attempts. Furthermore, when official portals experience heavy network latency, automated scraping bots or browser auto-refreshers frequently trigger multiple attempts in the background, permanently invalidating the card ("voucher burn") before the candidate ever views their grades.
* **CheckerPay Solution**: Adopts **Model A (Digital Reseller Gateway)**. Instead of executing fragile automated background scrapers against official portals during national release traffic spikes, the platform instantly delivers authentic, pre-loaded wholesale cryptographic PINs and serials directly to the student, and seamlessly launches the candidate into the official portal with step-by-step instructions.

### 2.2 Concurrency Clashes & Double-Allocation During National Release Spikes
During national result release spikes, hundreds of thousands of users attempt to purchase vouchers within minutes. In standard e-commerce or naive database setups, race conditions allow two or more separate buyers to be allocated the identical voucher PIN (double-allocation), resulting in invalid voucher disputes, customer panic, and financial loss.
* **CheckerPay Solution**: Employs an **Atomic Immediate-Locking Concurrency Engine** backed by SQLite in Write-Ahead Logging (WAL) mode with `BEGIN IMMEDIATE` row-level reservation locking. Every voucher is transitionally locked for 10 minutes during checkout and released only upon cryptographically verified payment confirmation or recycled upon session abandonment. Concurrency stress-testing across 25 simultaneous worker threads mathematically guarantees zero duplicate allocations.

### 2.3 Roadside Extortion, Physical Card Scarcity & Black-Market Pricing
When results drop, physical scratch cards at post offices and internet cafes sell out within hours. Roadside middlemen routinely double or triple card prices (charging GH₵ 50.00 to GH₵ 80.00 for cards with an official face value of GH₵ 20.00 to GH₵ 25.00). In remote rural regions, candidates must travel long distances simply to find a working scratch card.
* **CheckerPay Solution**: Provides instant 24/7/365 digital access from any smartphone, tablet, or PC across Ghana at regulated, transparent merchant prices, payable in local currency via all Ghanaian Mobile Money networks.

### 2.4 Credential Loss, Sudden Power Outages (Dumsor) & Session Disconnections
Unstable mobile data connectivity or sudden power failure (Dumsor) frequently causes users to close their browser tab before saving their Serial Number and PIN. On conventional websites, if a user closes the confirmation page, their purchase is irretrievably lost.
* **CheckerPay Solution**: Provides a multi-layered retrieval architecture:
  - **Instant On-Screen Reveal**: Immediate display of Serial, PIN, and direct portal link with 1-click clipboard copy.
  - **Simultaneous SMS Delivery**: Automatic dispatch of vouchers to the buyer's phone number.
  - **Self-Service Voucher Retrieval Tool (`/lookup`)**: Allows any user to recover their complete Serial, PIN, order reference, and redemption instructions at any time using only their mobile number or order code.
  - **WhatsApp Sharing & Printable Verification Slips**: Direct formatting for instant sharing with family or printing as a standardized physical slip.

### 2.5 Student Privacy Violations & Statutory Non-Compliance (Ghana Act 843 & Act 772)
Commercial platforms often harvest candidate index numbers, subject grades, and parental phone numbers into unencrypted marketing databases, violating Ghana's **Data Protection Act, 2012 (Act 843)** and the **Electronic Transactions Act, 2008 (Act 772)**.
* **CheckerPay Solution**: Strictly enforces **Statutory Privacy by Design**:
  - Educational pathway grading inputs are processed in **Ephemeral RAM Vaults** and instantly shredded upon verdict generation.
  - No candidate academic transcripts, subject scores, or raw grades are ever written to disk or persistent databases.
  - Every advisory execution generates a deterministic **SHA-256 Ephemeral Compliance Attestation Hash** verifying zero data retention.

### 2.6 Portal Input Validation Pitfalls (10-Digit vs. 12-Digit Index Traps)
The single most prevalent cause of failed voucher lookups on Ghanaian portals is format mismatch:
  - WAEC requires a strict **10-digit candidate index number** (e.g., `0010101010`).
  - CSSPS strictly requires candidates to append their **2-digit completion year** to their 10-digit index, creating a **12-digit string** (e.g., `101010101026`). Candidates who enter only 10 digits fail validation and assume their card is fake.
* **CheckerPay Solution**: Built-in interactive educational guides (`/guides`) and real-time input formatting rules visibly display correct vs. invalid examples prior to candidate submission.

### 2.7 Academic Directionless & Tertiary Admission Asymmetry
After receiving results, thousands of Ghanaian students miss university admissions or senior high school placement deadlines due to complex cut-off benchmarks, changing program requirements, or lack of guidance regarding alternative pathways (remedials, TVET institutions, diploma programs).
* **CheckerPay Solution**: An integrated **Pathway & Placement Advisor** and an autonomous **Live Admissions Scraper Fleet** that tracks real admission cut-offs, program benchmarks, and application deadlines across all accredited Ghanaian universities and senior high schools.

---

## 3. Comprehensive Features & System Functionalities

### 3.1 Digital Voucher Reseller Gateway (Model A)
- **Supported National Examination Categories**:
  - **WAEC WASSCE**: Result Checker vouchers valid for both May/June School Candidates and Private Nov/Dec Candidates (Official check limit: 3 times).
  - **WAEC BECE**: Result Checker vouchers valid for Basic Education Certificate Examination graduates (Official check limit: 3 times).
  - **CSSPS Placement**: Senior High School placement verification and self-placement eVouchers (Unlimited checks for the same candidate).
  - **CTVET / NABPTEX**: Technical and vocational examination vouchers valid for May/June Certificate and Nov/Dec Technical Examinations (Check limit: 5 times).
- **Direct Official Portal Integration**: Each product card is explicitly mapped to its statutory governmental portal (`ghana.waecdirect.org`, `eresults.waecgh.org`, `cssps.gov.gh`, `ctvet.gov.gh`).

### 3.2 Automated Category-Specific Portal Routing & Countdown Engine
- **Intelligent Post-Payment Redirection**: The instant Mobile Money or card payment is verified, the success interface automatically identifies the purchased product category and initializes a **6-second redirect countdown**.
- **Interactive Redirection Chrome**:
  - Animated visual progress bar tracking the 6-second window.
  - "Pause / Resume Redirect" control allowing students to halt navigation if they wish to inspect their credentials.
  - Instant "Go Now ↗" deep-link for immediate access.
- **Accredited Destination Matrix**:
  - *WASSCE* &rarr; `https://ghana.waecdirect.org`
  - *BECE* &rarr; `https://eresults.waecgh.org`
  - *CSSPS* &rarr; `https://cssps.gov.gh`
  - *CTVET* &rarr; `https://ctvet.gov.gh`

### 3.3 Atomic Concurrency-Safe Inventory & Reservation Recycling Engine
- **Transaction Isolation**: Backed by SQLite in Write-Ahead Logging (WAL) mode utilizing `BEGIN IMMEDIATE` transactions for all stock queries and mutations.
- **Atomic Locking Protocol**:
  1. *Select & Lock*: Identifies available unsold vouchers (`status = 'UNSOLD'`) and immediately updates their status to `'RESERVED'` with an atomic timestamp.
  2. *10-Minute Expiry Window*: Held vouchers remain locked to the specific order session for 600 seconds.
  3. *Payment Confirmation*: Upon webhook or gateway verification, reserved vouchers atomically transition to `'SOLD'`, recording order reference, buyer phone, and delivery timestamp.
  4. *Automatic Recycling Garbage Collector*: An automated background recycling thread continuously sweeps expired uncompleted reservations (`timestamp > 10 minutes`), returning abandoned vouchers back to `'UNSOLD'` inventory.
- **Deduplication Assurance**: Cryptographic uniqueness constraints ensure no voucher code or serial can exist twice in the catalog.

### 3.4 Multi-Channel Instant Dual Fulfillment System
- **On-Screen Reveal**: Renders the complete Card Serial Number and 12-digit PIN in high-visibility monospaced typography with one-click clipboard copying.
- **Direct SMS Gateway Dispatch**: Simultaneous automated SMS dispatch via integrated telecom gateways (Arkesel, Hubtel, mNotify) with formatted credentials, portal URL, and safety reminders.
- **One-Click WhatsApp Sharing**: Pre-formats an encrypted message template allowing students to forward their voucher directly to parents, guardians, or personal WhatsApp accounts with a single tap.
- **Printable Official Verification Slip**: Built-in CSS print styling that generates a clean, official A4/thermal receipt slip containing order reference, timestamp, serial, PIN, and statutory notices.

### 3.5 Native Ghanaian Telecom & Payment Processing Stack
- **Supported Payment Gateways**:
  - **Paystack (Ghana)**: Direct API integration supporting **MTN Mobile Money**, **Telecel Cash**, **AirtelTigo (AT Money)**, and **Visa / Mastercard** cards in Ghanaian Cedis (GHS).
  - **HMAC-SHA512 Cryptographic Webhook Security**: Server-to-server webhook endpoint verifies every event signature against the merchant secret, rejecting tampered payloads, currency mismatches (e.g. NGN vs GHS), and amount mismatches.
- **Automatic Telco Network Detection**:
  - Real-time client- and server-side regex parsing of Ghanaian phone prefixes:
    - *MTN*: `024`, `054`, `055`, `059`, `053`
    - *Telecel*: `020`, `050`
    - *AirtelTigo (AT)*: `027`, `057`, `026`
- **IETF Idempotency Key Engine**: Protects all payment initiation and verification calls with `Idempotency-Key` headers, completely eliminating duplicate telecom debits on unstable network retries.

### 3.6 Qualitative Stock Level Protection System
- **Scraper-Proof Inventory Messaging**: To prevent competitors and bot networks from scraping exact wholesale inventory levels, the platform suppresses raw numeric stock counts on the storefront:
  - *Healthy Inventory (> 10 vouchers)*: Displays an emerald indicator with the text **"In Stock"**.
  - *Low Inventory (1 to 10 vouchers)*: Displays an amber indicator with the text **"Almost Out of Stock"**.
  - *Zero Inventory (0 vouchers)*: Displays a crimson indicator with the text **"Out of Stock"** and automatically disables the purchase button with an unclickable state.

### 3.7 Educational Pathway & Placement Advisory Engine
- **Dual-Tier Curriculum Assessment**:
  - **BECE to Senior High School (CSSPS)**:
    - Calculates the official Stanine aggregate using the candidate's **Best 4 Core Subjects** (English, Math, Science, Social Studies) plus the **Best 2 Electives** (BDT, ICT, French, Ghanaian Language, RME).
    - Maps aggregates (Scale 6 to 54) to Ghana Education Service (GES) Senior High School categories:
      - *Category A (Merit / National)*: Aggregates 6–9 (e.g., PRESEC Legon, Achimota, Wesley Girls, Prempeh College).
      - *Category B (High Standard Regional)*: Aggregates 10–18 (e.g., St. Thomas Aquinas, Ghana National, Mawuli School).
      - *Category C (Community & Developing)*: Aggregates 19–30.
      - *Category D (Local Day Catchment / 30% Quota)*: Aggregates 25–45.
      - *Remedial / TVET Advice*: Actionable guidance for candidates requiring resits or technical pathways.
  - **WASSCE to University & Tertiary Pathways**:
    - Calculates the standard 36-point tertiary aggregate using: **English Language + Core Mathematics + Best 1 other Core + Best 3 Electives**.
    - Evaluates minimum Grade C6 requirements across all required subjects for degree eligibility.
    - Classifies candidates into admission tiers:
      - *Tier 1 (Public Degree Programs)*: Competitive entry into public universities (UG, KNUST, UCC).
      - *Tier 2 (Technical Universities & Diplomas)*: Direct entry into HND and BTech programs (ATU, KsTU, TTU).
      - *Tier 3 (Colleges of Education & Nursing)*: Specialized teacher training (PRINCOF) and nursing programs (MOH).
      - *Remedial / NOV/DEC Advisement*: Identifies specific subject deficits (e.g., D7 in Core Math) and prescribes remedial strategies.
- **Act 843 Ephemeral RAM Shredder**: Candidate grades and transcripts are processed exclusively in-memory and immediately destroyed following report delivery.

### 3.8 Autonomous Admissions & Cut-Off Points Scraper Fleet
- **Multi-Institutional Benchmark Monitoring**: Continuously tracks, synchronizes, and normalizes public university cut-off points, faculty requirements, and application deadlines across:
  - University of Ghana, Legon (**UG**)
  - Kwame Nkrumah University of Science and Technology (**KNUST**)
  - University of Cape Coast (**UCC**)
  - University of Professional Studies, Accra (**UPSA**)
  - University of Mines and Technology (**UMaT**)
  - University of Education, Winneba (**UEW**)
  - Technical Universities, Teacher Training Colleges (PRINCOF), and Nursing Colleges.
- **Live Admissions Explorer**: A dedicated candidate search interface enabling students to filter admissions benchmarks by institution, faculty category, and cut-off points without submitting grades.
- **SSRF Egress Defense Firewall**: The scraper fleet is shielded by an egress firewall that validates all outbound URLs, verifies DNS destinations, restricts scraping to vetted Ghanaian domains (`.edu.gh`, `.gov.gh`), and blocks loopbacks, private subnets, and cloud metadata IPs (`169.254.169.254`).

### 3.9 Self-Service Voucher Recovery & Lookup Tool (`/lookup`)
- **Instant Candidate Self-Service**: Enables any buyer who closed their browser or lost power to instantly retrieve their purchased credentials.
- **Multi-Parameter Search**: Accepts either the buyer's 10-digit Mobile Money phone number or the unique Order Reference code (`ORD-...`).
- **Full Credential Audit**: Displays the order timestamp, examination category, transaction status, serial numbers, PINs, and direct links to the relevant checking portal.
- **Zero-Blank-Screen Feedback**: Integrates real-time shimmer skeletons to deliver visual feedback during database queries.

### 3.10 Anti-Voucher Burn Educational Guides & Instructions (`/guides`)
- **Curated Portal Instruction Library**: Dedicated educational modules detailing exact rules and pitfalls across Ghanaian portals:
  - *The 3-Check WAEC Rule*: Explains candidate-binding mechanics and why page refreshing burns attempts.
  - *The 12-Digit CSSPS Rule*: Visually illustrates the distinction between the 10-digit index and the required 12-digit string (`Index + Completion Year`).
  - *CTVET Center Codes*: Guidance on region and center code prefixes.
  - *Emergency Recovery Steps*: Actionable advice if a portal crashes during checking.

### 3.11 Anti-Deformity & User Manipulation Immunity Frontend Architecture
- **Rigid Viewport Shielding**: Comprehensive styling ensures absolute layout integrity across all form factors from 320px mobile screens to 4K displays:
  - `overflow-x: hidden` and `max-width: 100vw` containment preventing horizontal scroll blowouts.
  - Fluid grid structures utilizing `minmax(min(100%, Npx), 1fr)` ensuring columns collapse gracefully on narrow viewports.
- **User Manipulation Immunity**:
  - Image and SVG drag protection (`user-drag: none; -webkit-user-drag: none`) preventing ghost-image dragging.
  - Interactive UI element protection (`user-select: none`) across buttons, pills, badges, tabs, and navigation to prevent accidental blue-block highlighting during rapid tapping.
  - Explicit copy selection preservation (`user-select: text !important`) strictly applied to voucher PINs, serial numbers, order references, and educational articles.
  - Textarea boundary locking (`resize: vertical; min-height: 80px; max-height: 320px;`) preventing container deformation.
  - Mobile iOS auto-zoom immunity enforcing standard 16px minimum font size on form controls.
- **Classic Sovereign Typography System**:
  - *Cinzel*: Sovereign Roman serif for brand emblems, national seals, and badges.
  - *Playfair Display*: Classic editorial serif for page titles and headings.
  - *Lora*: Literary serif for body content, instructions, and policy documents.
  - *JetBrains Mono*: High-contrast monospaced font for vouchers, PINs, and hashes.
- **Floating Navigation Tracking Orb**: Bottom-right floating orb with an animated SVG circular progress ring tracking real-time scroll depth (0%–100%) and providing 1-click smooth scroll back to top.

### 3.12 YouTube-Style Shimmer Skeleton Loading System
- **Zero-Blank-Screen UX**: Replaces generic spinners and blank page states with animated keyframe shimmer placeholders:
  - Shimmering university benchmark cards in the Admissions Explorer.
  - Shimmering verdict containers and aggregate badges in the Pathway Advisor.
  - Instant voucher ticket silhouettes in the Lookup tool.
  - Shimmering voucher reveal cards during checkout payment verification.

### 3.13 Sovereign Security, SSRF Egress Firewall & Merkle Audit Ledger
- **Cryptographic Merkle Audit Chain**: Every critical platform action (`ORDER_CREATED`, `PAYMENT_CONFIRMED`, `VOUCHER_ALLOCATED`, `ADMIN_LOGIN`, `SCRAPER_SYNC`) is hashed using SHA-256 and appended to a tamper-evident cryptographic block ledger with parent-hash linking.
- **Stealth Route Concealment**: Unauthorized probes to sensitive operational or scraper synchronization routes are intercepted and returned as stealth HTTP 404 Not Found responses.
- **Rate Limiting & Abuse Prevention**: Token-bucket and sliding-window rate limiters on checkout creation, voucher lookups, and customer feedback submissions.
- **Admin Authentication Defense**: Constant-time password hashing, session tokens, and automated audit logging of failed administrative login attempts.

### 3.14 Merchant Operations & Administrative Control Center (`/admin`)
- **Real-Time Operational Telemetry**:
  - Live inventory ledger categorized by examination product.
  - Dual-axis settlement analytics: Gross Revenue (GH₵) vs. Total Delivered Orders across customizable time windows (24 hours, 7 days, 30 days, all-time).
  - Merkle audit chain verification tool validating ledger cryptographic integrity.
- **Inventory Management & Bulk Importer**:
  - Direct wholesale voucher CSV importer with automatic deduplication.
  - Dynamic price management per voucher category.
  - Inventory mode toggles: *Strict Wholesale Batch* (for production merchant sales) vs. *Dynamic Generator* (for demonstrations).
- **Admissions Scraper Fleet Manager**: Manual trigger and status monitoring for the live admissions cut-off scraper fleet.
- **Payment Gateway Configuration**: In-dashboard Paystack API key configuration (Public & Secret keys) with masked key storage.

### 3.15 Customer Feedback, Rating & Dispute Resolution System
- **Verified Customer Reviews**: Built-in 5-star rating and feedback engine categorized by service aspect (Delivery Speed, Portal Guidance, Payment Processing, Advisor Accuracy).
- **Automated Anti-Spam Rate Limiting**: Maximum 5 submissions per IP within rolling cooldown windows to eliminate review bombing.
- **Admin Review Queue**: Full administrative moderation and audit inspection of buyer feedback.

### 3.16 Statutory Legal, Regulatory & Compliance Architecture
- **Electronic Transactions Act, 2008 (Act 772)**: Comprehensive Terms of Service governing electronic contracts, digital voucher ownership, and merchant fulfillment obligations.
- **Data Protection Act, 2012 (Act 843)**: Fully articulated Privacy Policy establishing zero persistence of academic transcripts, lawful telecom processing, and user access rights.
- **Digital Delivery & Returns Policy**: Explicit consumer guidelines covering the 100% instant digital fulfillment guarantee, replacement protocols for defective cards, and dispute resolution for duplicate telecom debits.

---

## 4. Proposed User Flows & Operational Journeys

### 4.1 User Flow 1: Instant Voucher Purchase & Dual Fulfillment Journey
```
[Storefront Browse] 
        │
        ▼
[Select Exam Category (e.g. WASSCE, BECE, CSSPS, CTVET)] 
        │
        ▼
[Click "Buy Now" -> Checkout Modal Opens]
        │
        ├── Enter Quantity (1 to 10)
        ├── Enter Ghanaian Mobile Number (024/020/027...)
        └── Auto-Detected Network Badge (MTN / Telecel / AT)
        │
        ▼
[Proceed to Payment -> Atomic Immediate-Locking Reservation]
        │
        ├── SQLite WAL row locked (status = 'RESERVED', 10-min TTL)
        └── IETF Idempotency-Key generated
        │
        ▼
[Authorize Mobile Money / Card Payment]
        │
        ├── MTN MoMo / Telecel Cash / AT Money USSD prompt on handset, OR
        └── Paystack Secured Web Popup (MoMo / Debit / Credit Cards)
        │
        ▼
[Cryptographic Webhook / Callback Verification]
        │
        ├── Verifies HMAC-SHA512 signature, currency (GHS), pesewa amount
        └── Atomically transitions voucher status: RESERVED -> SOLD
        │
        ▼
[Instant Multi-Channel Dual Delivery]
        ├── On-Screen Voucher Reveal (Serial + PIN + 1-Click Copy)
        ├── Simultaneous SMS Dispatch to Buyer Handset
        ├── Optional 1-Click WhatsApp Share Pre-Filled Link
        └── Printable Standardized Official Slip
        │
        ▼
[Automated Category-Specific Portal Routing]
        ├── 6-Second Auto-Redirect Countdown Bar
        ├── Pause / Resume Redirect Controls
        └── Seamless Redirection to Official Portal (ghana.waecdirect.org / cssps.gov.gh)
```

#### Step-by-Step Flow Progression:
1. **Discovery & Stock Evaluation**: The buyer visits the homepage, observes the qualitative stock indicator (e.g., emerald *"In Stock"*), reviews category check limits, and clicks *"Buy Now"* on their desired examination card.
2. **Order Configuration**: A responsive modal presents the order form. The buyer inputs their voucher quantity and phone number. The client-side validator instantly detects the telecom carrier from the number prefix (e.g., `054` &rarr; MTN) and displays the network emblem.
3. **Atomic Reservation & Idempotency Locking**: Upon clicking *"Proceed to Payment"*, the backend executes a `BEGIN IMMEDIATE` transaction, atomically reserving available unsold vouchers for 10 minutes and binding them to a unique order reference (`ORD-...`).
4. **Payment Authorization**: The buyer completes the transaction via their chosen channel (approving the MoMo USSD prompt on their phone or completing the Paystack checkout).
5. **Fulfillment & Shimmer Reveal**: The backend validates the payment, updates the Merkle audit ledger, and returns the revealed credentials. Shimmer skeleton placeholders immediately transition to crisp, readable voucher cards.
6. **Dual Dispatch & Portal Handoff**: An SMS is sent to the buyer's phone. Meanwhile, an automated 6-second countdown bar initiates on-screen, automatically directing the candidate into the accredited government checking portal.

---

### 4.2 User Flow 2: Self-Service Lost Voucher Retrieval Journey (`/lookup`)
```
[Candidate Loses Tab / Battery Dies / Network Drops]
        │
        ▼
[Navigate to /lookup Tool]
        │
        ▼
[Enter Buyer Phone Number (024XXXXXXX) OR Order Reference (ORD-...)]
        │
        ▼
[Submit Query -> Instant Shimmer Skeleton Feedback]
        │
        ▼
[System Queries Paid Vouchers for Candidate Session]
        │
        ▼
[Complete Order Audit Displayed]
        ├── Order Reference & Timestamp
        ├── Examination Type (WASSCE / BECE / CSSPS / CTVET)
        ├── Unmasked Card Serial Number & 12-Digit PIN
        ├── Direct Portal Link & Official Verification Instructions
        └── 1-Click Copy & Print Options
```

#### Step-by-Step Flow Progression:
1. **Interruption Event**: A buyer experiences a sudden browser crash, phone shutdown, or telecom SMS delivery delay.
2. **Lookup Entry**: The buyer accesses `/lookup` directly from the navigation bar or footer.
3. **Identification**: The buyer types either their 10-digit mobile number or their order reference into the single search input.
4. **Shimmer Skeleton State**: The interface renders an instant placeholder silhouette, providing fluid visual feedback during the database search.
5. **Credential Restoration**: All previously purchased, paid vouchers matching the query are displayed with full PINs, serials, and one-click copy controls.

---

### 4.3 User Flow 3: Educational Pathway & Placement Advisory Journey (`/advisor`)
```
[Candidate Navigates to /advisor]
        │
        ▼
[Statutory Data Protection Act, 2012 (Act 843) Consent Step]
        ├── Explicit Consent Checkbox required
        └── Unlocks Interactive Grade Evaluator
        │
        ▼
[Select Academic Stream: BECE -> CSSPS OR WASSCE -> Tertiary]
        │
        ▼
[Input Examination Grades]
        ├── BECE: 4 Cores + 5 Electives (Stanine Grades 1-9)
        └── WASSCE: 4 Cores + 4 Electives (Grades A1-F9)
        │
        ▼
[Real-Time Dynamic Aggregate Preview Banner]
        ├── Live Aggregate Calculation on Every Dropdown Change
        └── Immediate Target Benchmark Status Indicator
        │
        ▼
[Submit for Objective Evaluation -> Shimmer Skeleton Feedback]
        │
        ▼
[Act 843 Ephemeral RAM Evaluation (Zero Disk Persistence)]
        │
        ▼
[Personalized Verdict & Advisory Report Rendered]
        ├── Verified Aggregate Score Breakdown
        ├── Institution Tier Categorization (GES Cat A/B/C/D or Degree Tiers 1-3)
        ├── Matched Schools & Programmes with Realistic Admission Probabilities
        ├── Critical Subject Deficit Warnings & Remedial NOV/DEC Action Plan
        ├── Scholarship & Financial Aid Directives
        └── Cryptographic SHA-256 Ephemeral Compliance Attestation Hash
```

#### Step-by-Step Flow Progression:
1. **Statutory Consent**: The candidate encounters the Act 843 compliance banner and checks the explicit data processing consent box to unlock the evaluation form.
2. **Stream Selection**: The user toggles between the **BECE &rarr; CSSPS Senior High Placement** tab and the **WASSCE &rarr; Tertiary Pathways** tab.
3. **Grade Entry**: The candidate selects their grades via intuitive dropdown selectors. An instant preview banner dynamically calculates their aggregate score in real time.
4. **Ephemeral RAM Analysis**: Upon submission, the advisory engine evaluates the grade combinations against admission thresholds in temporary volatile memory.
5. **Comprehensive Verdict**: The candidate receives an in-depth breakdown containing institutional matches, subject deficiency alerts, cut-off benchmarks, and alternative academic pathways.
6. **Data Shredding & Proof**: All student inputs are purged from RAM, and a tamper-evident SHA-256 compliance hash is generated proving zero data was stored.

---

### 4.4 User Flow 4: Portal Traps & Anti-Voucher Burn Guidance Journey (`/guides`)
```
[User Navigates to /guides]
        │
        ▼
[Review Portal Mechanics & Pitfalls Before Validation]
        │
        ├── The 3-Check Limit Rule (WAEC WASSCE & BECE)
        ├── The "Voucher Burn" Network Refresh Danger
        ├── The 12-Digit Index Requirement (CSSPS School Placement)
        └── CTVET Center Code Structure
        │
        ▼
[Candidate Armed with Validation Knowledge]
        │
        ▼
[Direct Launch to Target Governmental Portal]
```

#### Step-by-Step Flow Progression:
1. **Pre-Check Education**: The user visits `/guides` from the homepage safety banner or navigation bar.
2. **Risk Identification**: The user learns why pressing browser refresh on official portals invalidates checks and sees side-by-side examples of valid vs. invalid index numbers.
3. **Confident Submission**: Equipped with step-by-step checklists, the student opens the official portal and verifies their results without burning their voucher.

---

### 4.5 User Flow 5: Merchant Operations, Restocking & Audit Journey (`/admin`)
```
[Merchant Authenticates via Stealth Login]
        │
        ▼
[Dashboard Telemetry Overview]
        ├── Live Categorized Stock Levels
        ├── Financial Settlement Velocity (24h / 7d / 30d / All)
        └── Cryptographic Merkle Block Audit Status
        │
        ▼
[Merchant Management Actions]
        ├── Bulk CSV Voucher Restocking (Serial + PIN Import)
        ├── Unit Price Adjustment per Exam Category
        ├── Inventory Mode Switching (Wholesale Batch vs Demo Generator)
        ├── Scraper Fleet Trigger & Cut-Off Benchmark Synchronization
        └── Paystack Secret & Public API Key Management
```

---

## 5. User Stories & Acceptance Criteria

### 5.1 Persona 1: Secondary School Candidate (Akosua — WASSCE Graduate)

#### User Story 1.1: Instant Voucher Purchase & On-Screen Reveal
* **As a** WASSCE school candidate,
* **I want to** purchase a genuine WAEC Result Checker voucher using my MTN Mobile Money wallet and see the Serial Number and PIN immediately on my phone screen,
* **So that** I do not have to walk to an internet cafe or wait for delayed SMS messages to view my examination results.

> **Acceptance Criteria**:
> - The purchase modal prompts for quantity, phone number, and network provider.
> - Payment verification occurs within sub-second intervals upon MoMo approval.
> - The Serial Number and 12-digit PIN are clearly rendered on-screen with high-contrast monospaced styling.
> - A 1-click copy button copies the PIN directly to the device clipboard with visual confirmation.

#### User Story 1.2: Automatic Portal Redirection
* **As a** candidate holding newly revealed voucher credentials,
* **I want the platform to** automatically open the official WAEC checking portal (`ghana.waecdirect.org`) after a brief countdown,
* **So that** I don't have to search the internet for the correct portal link or risk landing on phishing websites.

> **Acceptance Criteria**:
> - An animated 6-second countdown bar begins immediately upon credential reveal.
> - The portal link correctly points to `https://ghana.waecdirect.org`.
> - A "Pause / Resume Redirect" button allows the user to stop the countdown at any point.
> - A "Go Now ↗" button provides immediate navigation without waiting for the timer.

---

### 5.2 Persona 2: Junior High School Graduate (Kwesi — BECE Candidate)

#### User Story 2.1: Secondary School Placement Advisory
* **As a** BECE graduate awaiting Senior High School placement,
* **I want to** enter my core and elective stanine grades into the Pathway Advisor,
* **So that** I can understand which GES school categories (Category A, B, C, or D) my aggregate qualifies me for before the official CSSPS placement results are released.

> **Acceptance Criteria**:
> - The advisor accepts 4 core subjects and 5 electives on a 1–9 stanine scale.
> - The system automatically identifies the best 4 cores and best 2 electives to compute the official aggregate score.
> - The generated report categorizes matching Senior High Schools into Categories A, B, C, and D based on official GES thresholds.
> - If the aggregate exceeds placement thresholds, constructive guidance on technical/vocational (TVET) institutions or resits is provided.

#### User Story 2.2: CSSPS 12-Digit Format Guidance
* **As a** candidate checking my SHS placement,
* **I want clear instructions** on how to format my CSSPS index number,
* **So that** I do not fail placement verification by entering a 10-digit number instead of the mandatory 12-digit format.

> **Acceptance Criteria**:
> - The platform highlights the 10-digit vs. 12-digit CSSPS rule in both product cards and `/guides`.
> - Side-by-side visual examples clearly demonstrate appending the 2-digit completion year (e.g., `101010101026`).

---

### 5.3 Persona 3: Parent / Guardian (Mr. Mensah — Household Decision Maker)

#### User Story 3.1: Dual Delivery & Receipt Assurance
* **As a** parent purchasing vouchers for my children from my workplace,
* **I want** the purchased PIN and serial sent to my mobile number via SMS and available as a printable slip,
* **So that** I have a permanent physical or digital record to send to my child at home.

> **Acceptance Criteria**:
> - Simultaneous SMS delivery delivers the exact Serial, PIN, and portal URL to the buyer's phone number within 3 seconds.
> - A "Print / Save Official Slip" button generates a standardized, receipt-ready document.
> - A "Share Voucher to WhatsApp" button formats a pre-filled, encrypted WhatsApp message.

#### User Story 3.2: Self-Service Lost Voucher Recovery
* **As a** parent who closed the browser tab before writing down the PIN,
* **I want to** enter my mobile phone number on a recovery page,
* **So that** I can retrieve all vouchers I paid for without paying again or contacting support.

> **Acceptance Criteria**:
> - Navigating to `/lookup` allows queries by 10-digit mobile number or Order Reference.
> - All past paid orders associated with the query are retrieved with full credentials.
> - The lookup interface operates with shimmer skeleton feedback and zero page deformities.

---

### 5.4 Persona 4: Cyber-Cafe Operator & Educational Agent (Yaw)

#### User Story 4.1: Concurrency Safety Under High-Volume Purchasing
* **As a** cyber-cafe operator buying vouchers for multiple students simultaneously,
* **I want** an ironclad guarantee that every voucher I purchase is unique and unallocated,
* **So that** none of my clients experience invalid or duplicate PIN errors on official portals.

> **Acceptance Criteria**:
> - Row-level atomic database locking (`BEGIN IMMEDIATE`) prevents double-allocation under concurrent checkouts.
> - 10-minute temporary reservation holds vouchers during payment execution.
> - Abandoned checkouts automatically recycle back to inventory without manual intervention.

---

### 5.5 Persona 5: Merchant Administrator (Platform Operator)

#### User Story 5.1: Wholesale CSV Restocking & Inventory Control
* **As a** platform administrator,
* **I want to** upload wholesale CSV batches containing thousands of Serial Numbers and PINs,
* **So that** I can replenish stock instantly before major national examination release spikes.

> **Acceptance Criteria**:
> - The admin dashboard (`/admin`) provides a bulk CSV upload interface supporting WASSCE, BECE, CSSPS, and CTVET categories.
> - Duplicate serials or PINs are automatically detected and rejected during database ingestion.
> - Real-time stock counts by category immediately reflect newly ingested cards.

#### User Story 5.2: Cryptographic Audit Ledger & Compliance Verification
* **As a** compliance officer,
* **I want to** verify the cryptographic integrity of the Merkle audit chain,
* **So that** I can prove that all transactions, stock allocations, and admin logins are tamper-evident and compliant with the Ghana Electronic Transactions Act (Act 772).

> **Acceptance Criteria**:
> - Every sensitive state change creates a SHA-256 hashed audit block linked to its predecessor.
> - The admin panel includes a 1-click audit integrity validator verifying block parent hashes.
> - All grade evaluations generate verifiable Act 843 ephemeral attestation proofs confirming zero data retention.

---

## 6. System Requirements & Operational Dependencies

### 6.1 Runtime & Core Software Dependencies
* **Python Runtime**: Python 3.10, 3.11, 3.12, 3.13, or 3.14 (fully verified on 64-bit architectures).
* **Asynchronous Web Framework**: `fastapi >= 0.115.0`
* **ASGI Server**: `uvicorn[standard] >= 0.30.0`
* **Template Engine**: `jinja2 >= 3.1.4`
* **Asynchronous Database Interface**: `aiosqlite >= 0.20.0`
* **Data Validation & Settings**: `pydantic >= 2.9.0`
* **Form & Multipart Processing**: `python-multipart >= 0.0.12`
* **HTTP & Scraper Engine**: `httpx >= 0.27.0`

### 6.2 Operating System & Environment Compatibility
* **Supported Operating Systems**:
  - **Microsoft Windows**: Windows 10, Windows 11, Windows Server 2019/2022.
  - **Linux**: Ubuntu 20.04+, Debian 11+, RHEL/CentOS 8+, Alpine Linux.
  - **macOS**: macOS 12 (Monterey) or higher.
* **Architecture Support**: x86_64, amd64, arm64.

### 6.3 Database Engine & Storage Requirements
* **Database Engine**: SQLite 3.35.0 or higher.
* **Storage Mode**: Write-Ahead Logging (`PRAGMA journal_mode=WAL;`).
* **Concurrency Locking**: `BEGIN IMMEDIATE` transaction support on local or network-attached SSD storage with persistent file-locking semantics.
* **Storage Footprint**: Lightweight base footprint (< 50 MB application core + SQLite database growing proportionally with transaction volume).

### 6.4 Telecom & Payment Gateway Requirements
* **Payment Processor**: Paystack Merchant Account with Ghanaian Cedi (GHS) settlement enabled.
* **API Credentials**: Valid Paystack Public Key (`pk_live_...` or `pk_test_...`) and Secret Key (`sk_live_...` or `sk_test_...`).
* **Webhook Endpoint Access**: Publicly accessible HTTPS domain to receive Paystack webhook callback events (`/api/webhooks/paystack`).
* **Supported Local Payment Rails**:
  - MTN Mobile Money (*170#)
  - Telecel Cash (*110#)
  - AirtelTigo AT Money (*110#)
  - Visa & Mastercard (Ghanaian and international bank cards)

### 6.5 Messaging & SMS Dispatch Requirements
* **SMS Gateway Integration**: Compatible with RESTful Ghanaian SMS aggregators (Arkesel, Hubtel, or mNotify).
* **Sender ID**: Accredited alphanumeric Sender ID (maximum 11 characters, e.g., `CHECKERPAY`) approved by the National Communications Authority (NCA).
* **Local Phone Formatting**: Ghanaian MSISDN formatting supporting standard 10-digit local format (`024XXXXXXX`) or international format (`+233XXXXXXXXX`).

### 6.6 Client Browser & Viewport Requirements
* **Browser Compatibility**: Any modern standards-compliant web browser supporting ES6+, CSS Flexbox, and CSS Grid:
  - Google Chrome / Chromium (Desktop & Mobile)
  - Mozilla Firefox
  - Apple Safari (iOS & macOS)
  - Microsoft Edge
  - Opera & Samsung Internet
* **Supported Viewport Range**: Fully responsive from compact mobile displays (320px width) up to ultra-wide 4K monitors (3840px width).
* **JavaScript Requirements**: Modern JavaScript enabled for dynamic modal management, auto-redirect countdowns, and shimmer skeleton rendering.

### 6.7 Network & Security Egress Requirements
* **Inbound Connectivity**: TCP port 80/443 (HTTP/HTTPS) for client access.
* **Outbound Egress**:
  - HTTPS access to `api.paystack.co` on port 443.
  - HTTPS access to SMS gateway APIs (Arkesel, Hubtel, mNotify) on port 443.
  - Outbound HTTP/HTTPS access restricted by the SSRF firewall to vetted Ghanaian educational domains (`.edu.gh`, `.gov.gh`).
