# UniversalChecker / CheckerPay — Agent Operating Rules

## What this project is
Two distinct products sharing one backend — treat them as having different
risk profiles, not as one feature set:

1. **Checker/Voucher Store** (storefront, `/lookup`, `/guides`, `/admin`) —
   resells WAEC WASSCE, WAEC BECE, CSSPS, and CTVET/NABPTEX result-checker
   vouchers. Paystack-based payment (MTN MoMo, Telecel Cash, AirtelTigo
   Money, Visa), atomic SQLite inventory locking, redirect-with-countdown to
   official portals.
2. **Pathway Advisor** (`/advisor`) — ephemeral, in-memory-only grade
   evaluation and tertiary placement guidance. Zero persistence, gated on
   explicit Act 843 consent.

Read this file always. Read the scoped rule file under `.agent/rules/` for
whichever area a task actually touches — they carry the specific detail this
file only summarizes.

## Non-negotiables, both products
- **Never store, log, or persist a candidate's grades, index number, or any
  exam-identifying data** — to a database, a log line, a cache, a session,
  or an analytics event. This is the platform's core legal guarantee under
  Ghana's Data Protection Act, 2012 (Act 843). If a task seems to need this
  ("remember their last result," "track advisor usage by user"), that's a
  real product/legal question — stop and ask, don't implement a workaround.
- **Never touch the atomic inventory-locking logic** without flagging it
  first — see `.agent/rules/inventory-locking.md`. This is the single
  highest-technical-risk area in the app: a bug here means double-sold
  vouchers.
- **Never touch payment or webhook code** without flagging it first — see
  `.agent/rules/payments.md`.
- **The admin surface is provisioned-access only** — see
  `.agent/rules/admin-portal.md`. No public page, nav item, or sitemap entry
  may reference it.

## Task discipline
- If a task would touch more than one of: inventory locking, payments,
  advisor privacy boundary, or admin — stop and propose splitting it first.
- Commit after each accepted task, not batched across several.
- **Mandatory Dual-Tier Testing (Strictly Required)**:
  Before completing any task, execute BOTH testing tiers as documented in [`TESTS.md`](file:///c:/Projects/UniversalChecker/TESTS.md):
  1. *Tier 1: Systematic Automated Tests* (`pytest` with 100% passes and 0 regressions).
  2. *Tier 2: Physical Verification Testing* (literally visit `http://127.0.0.1:8000`, test every button, navigation link, modal, input field, and copy upfront across both Desktop and Mobile Smartphone views).
  Report both tiers in your task summary.
- Never describe a stub, shortcut, or simplification as "done" — describe
  it as what it is, and say so explicitly in your task summary.
- **UI Simplicity & Cleanliness Rules**:
  1. NEVER use cylindrical bar text / floating pill badges above page headings.
  2. NEVER add top rectangular info/authority banner bars above the navbar.
  3. Strictly employ basic, simple, friendly language for all copy and features
     so students, parents, and cafe attendants easily understand everything.

## Project Architecture & Execution Rules
- **Commands**: Build (`npm run build`), Test (`npm test`), Typecheck (`npx tsc --noEmit`).
- **Search Discipline**: Never read entire files to find a function. Use `grep` or symbol search first, then read specific line ranges.
- **Verification Gate**: Never mark a task complete without running the typechecker and affected unit tests via `run_command`.
- **Edge-Case Audit**: Before writing implementation code, list 3 failure states (null inputs, network timeouts, race conditions) and handle them explicitly.

## Reference
`docs/architecture-summary.md` in this folder has the current system-level
picture (routes, the two user journeys, design system). Update it as the
architecture evolves — an agent following a stale reference doc is worse
than one following no doc, because it'll be followed with equal confidence
either way.
