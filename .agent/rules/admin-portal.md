---
scope: checker_platform/**/admin*.py, templates/admin*
activation: glob
---

# Rules for admin routes/portal

- No public-facing page, nav item, or sitemap entry may link to any admin
  route. Entry is by provisioned credential only.
- Bulk CSV/PIN import must validate and explicitly reject malformed rows —
  never silently skip a bad row or silently overwrite an existing inventory
  record without surfacing that it happened.
- Price configuration changes and manual inventory adjustments should be
  logged with who/when (an admin action audit trail). This operational
  logging is fine and encouraged — it must never include end-customer PII
  or any Pathway Advisor grade data, which stay governed by
  advisor-privacy.md regardless of which surface touches them.
- If a task here would add a new capability beyond what's listed in the
  README (live stock levels, bulk import, price config, transaction
  history), flag it before building it — admin surface growth should be a
  deliberate decision, not a side effect of an unrelated task.
