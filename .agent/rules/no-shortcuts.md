---
activation: always-on
---

# No-shortcuts discipline (applies to every task, every area)

- Never leave a "TODO: handle this properly later" in place of real error
  handling on a payment or inventory code path.
- Never fetch a full/unscoped dataset (all vouchers, all transactions, all
  advisor sessions) and filter client-side where a server-side scoped query
  should be used instead.
- Never add a new public-facing route or admin capability during a task
  that wasn't specifically about adding one, without flagging it first.
- If you're not sure a change preserves an existing guarantee (no
  double-allocation, no persisted grade data, admin unreachable publicly),
  say so explicitly in your summary rather than presenting it as verified.
- Never copy a template, component, or utility between the storefront and
  the advisor rather than sharing it properly — if both need the same
  thing, it goes in one shared location, used by both.
