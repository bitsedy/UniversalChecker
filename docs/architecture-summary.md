# Architecture Summary — AggreGate Ghana / CheckerPay Platform

*Last updated: October 2026. Authoritative architecture reference for development, compliance, and deployment.*

## 1. Two Products, One Unified Backend
The platform operates two distinct services with isolated risk profiles:

1. **Checker/eVoucher Distribution Gateway** (`/`, `/lookup`, `/guides`, `/faq`, `/admin`):
   - Direct B2C inventory purchasing for WAEC (WASSCE / BECE) and CSSPS eVouchers.
   - Atomic SQLite row-level locking (`BEGIN IMMEDIATE` in WAL mode) to guarantee zero double-vending.
   - Dual-rail payment processing: Paystack checkout integration + kinetic Mobile Money USSD prompt simulator for offline and carrier testing.
   - Real-time carrier auto-detection badge on customer phone input (MTN MoMo, Telecel Cash, AT Money) with a 10-minute voucher hold reservation timer.
   - Instant multi-channel fulfillment: clear on-screen credential cards, SMS trigger hooks, copy-ready WhatsApp credentials, and automated 5-second countdown redirects to official verification portals (`ghana.waecdirect.org`, `cssps.gov.gh`).

2. **Pathway Advisor** (`/advisor`):
   - Educational placement intelligence and tertiary cutoff calculation (GES CSSPS Senior High School + GTEC University cut-offs).
   - **Ghana Data Protection Act, 2012 (Act 843) Guarantee**: 100% ephemeral in-memory analysis. Candidate grades, index numbers, or identifying data are NEVER stored to database tables, logs, caches, sessions, or tracking cookies. Verified by automated invariant test suites.
   - Outputs 3 distinct artifacts:
     - **Official Admissions Dossier**: Printable formal academic briefing (`@media print` optimized with institutional header, issue timestamp, and Act 843 verification proof).
     - **WhatsApp Diagnostic Card**: 1-click shareable markdown card with score breakdowns, school probabilities, and recommended action steps.
     - **Remedial Simulator (Nov/Dec)**: Subject upgrade projections demonstrating impact on university qualification thresholds.

---

## 2. Complete Route Map & Security Boundaries

| Route | Purpose | Indexing & Security |
| :--- | :--- | :--- |
| `/` | Storefront & voucher selector (`#select-checker`) | Public, indexed, `WebSite` & `Product` Schema |
| `/lookup` | Self-service voucher retrieval by phone & order reference | Public, indexed |
| `/guides` | Portal rules, anti-burn instructions, and 12-digit index requirements | Public, indexed, `HowTo` & `BreadcrumbList` Schema |
| `/faq` | Frequently asked questions, carrier troubleshooting, refunds | Public, indexed, `FAQPage` Schema |
| `/terms` | Statutory terms of service (Act 772, Act 1038) | Public, indexed |
| `/privacy` | Privacy policy & Act 843 compliance declarations | Public, indexed |
| `/delivery-returns` | 100% digital instant delivery & defective voucher replacement | Public, indexed |
| `/advisor` | Educational placement & pathway advisor | Public, indexed, gated on explicit Act 843 consent |
| `/robots.txt` | Crawler directives; allows public, shields `/admin` | Public (`/robots.txt`) |
| `/sitemap.xml` | Canonical XML sitemap with all public endpoints | Public (`/sitemap.xml`) |
| `/admin` | Provisioned merchant inventory management & telemetry | **Restricted / Stealth 404** (omitted from sitemaps/robots) |
| `/api/admin/*` | Inventory restocking, price overrides, transaction queries | Provisioned-access only |

---

## 3. Design System & Sovereign Editorial FinTech Archetype
- **Archetype**: Modern Ghana Editorial Authority / Sovereign FinTech
- **7-Axis Quality Gates**:
  1. *Accessibility*: WCAG AAA compliance on core copy (7.2:1 contrast), visible focus rings with `outline-offset: 2px`, screen-reader `.sr-only` support.
  2. *Touch / Interaction*: Minimum 44×44px interactive targets across all mobile buttons, tabs, inputs, and modal controls (`touch-action: manipulation`).
  3. *Zero-CLS Performance*: Explicit dimension attributes on logos and telco marks; layout-stable skeletons during data retrieval.
  4. *Responsive Layout*: Fluid typography via `clamp()`, flexible multi-column auto-fit grids, horizontal scroll protection (`overflow-x: hidden`).
  5. *Editorial Typography*: `Playfair Display` (authoritative serif headlines), `Inter` (crisp body copy), `JetBrains Mono` (vouchers, serials, and hashes).
  6. *Micro-Kinetic Motion*: Smooth cubic-bezier transitions (`cubic-bezier(0.16, 1, 0.3, 1)`), pulsing beacons for live inventory, and one-click copy feedback.
  7. *Institutional Trust*: Sovereign top authority strip, statutory compliance seals (Act 843, Act 772, Act 987), bank-grade SSL badges, and unvarnished guidance.
- **Palette Tokens**:
  - Sovereign Cream: `#FDFBF5` (Background canvas `--bg-main`)
  - Crisp White Elevation: `#FFFFFF` (`--bg-card`)
  - Deep Authoritative Navy: `#14213D` (`--navy-primary`, `--text-main`)
  - Ghanaian Burnt Orange / Gold: `#B8712C` (`--gold-accent`, `--ghana-gold`)
  - Savannah Emerald: `#0F6B5C` (`--emerald-accent`, `--ghana-green`)
  - Critical Warning Crimson: `#DC2626` (`--crimson-risk`, `--ghana-red`)
- **Geometry & Elevation**:
  - Cards: `18px` (`--radius-lg`) with warm editorial hairline borders (`--border-subtle: #E5E0D4`).
  - Interactive Elements: `9999px` (`--radius-pill`) for CTAs, tabs, and tags.
  - Elevation: `--shadow-editorial` (subtle ambient depth) and `--shadow-kinetic` (active hover states).

---

## 4. Security, DevOps & Invariants
- **Container Hardening**:
  - Runs in `Dockerfile` under non-root unprivileged `USER appuser` (UID 10001).
  - Hardened `.dockerignore` strictly preventing leakage of local databases, secrets, virtualenvs, or IDE files.
- **Act 843 Verification**:
  - Intercepts and tests SQLite layers via `test_act_843_zero_persistence_invariant` in `test_advisory.py`.
- **Payment & Webhook Integrity**:
  - HMAC-SHA512 verification for Paystack webhooks with strict idempotency tables (`idempotency_records`).
