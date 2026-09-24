# Architecture Summary — keep this current

*Last known state, based on README + live site review. Update as things
change — this is what AGENTS.md tells the agent to check before big
structural work, so keep it honest.*

## Two products, one backend
1. **Checker/Voucher Store** — the money-making path. Storefront →
   Select Result Checker → pay via Paystack → instant PIN (on-screen, SMS,
   WhatsApp) → redirect-with-countdown to the real WAEC/CSSPS/CTVET portal.
2. **Pathway Advisor** (`/advisor`) — placement guidance. Enter grades →
   Act 843 consent → aggregate + category verdict → Official Admissions
   Dossier / WhatsApp Placement Card / Print briefing.

## Known routes
- `/` — storefront, hero + Select Result Checker grid
- `/lookup` — self-service voucher retrieval by phone/order reference
- `/guides` — WAEC 3-check limit, CSSPS 12-digit index rule, CTVET center
  codes
- `/admin` — provisioned-only, stock levels, bulk import, pricing,
  transaction history
- `/advisor` — Pathway Advisor
- `/docs` — auto-generated API documentation

## Design system
Navy `#14213D` / cream `#FDFBF5` / burnt-orange `#B8712C` / teal `#0F6B5C`.
Playfair Display for headings, Inter for body. Pill-shaped bordered CTA
buttons throughout.

## Open items to fill in as they're decided
- Exact route/anchor for the "Select Result Checker" section (currently
  referenced as `#select-checker` in the homepage How It Works section —
  confirm or correct).
- Whether the three Advisor output artifacts are always generated, or
  conditional on grade level/category.
- Current hosting: Render subdomain (`universalchecker.onrender.com`) —
  update this file if/when a custom domain and separate deployments per
  surface are set up.
