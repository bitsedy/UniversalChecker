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
- Never describe a stub, shortcut, or simplification as "done" — describe
  it as what it is, and say so explicitly in your task summary.

## Reference
`docs/architecture-summary.md` in this folder has the current system-level
picture (routes, the two user journeys, design system). Update it as the
architecture evolves — an agent following a stale reference doc is worse
than one following no doc, because it'll be followed with equal confidence
either way.
