---
scope: checker_platform/**/inventory*.py, checker_platform/**/voucher*.py, checker_platform/db/**, checker_platform/**/reservation*.py
activation: glob
---

# Rules for inventory / voucher allocation code

Trust level: highest technical risk in the whole app. A bug here means
double-sold vouchers — a customer paying for a PIN someone else already
received. This is the one failure mode that directly costs money and breaks
the core promise of the product ("zero double-allocation risk," stated on
the homepage itself).

- The atomic locking pattern — SQLite in WAL mode with `BEGIN IMMEDIATE`
  row-locking transactions — is load-bearing. Never replace it with a naive
  read-then-write check, an in-app mutex, or a "check availability, then
  allocate" two-step. All of these reintroduce the exact race condition
  this pattern exists to close, and they will pass single-request testing
  while failing under real concurrent load.
- Any change to the 10-minute reservation-expiry mechanism must preserve:
  (a) expiry is enforced against a server-stored timestamp, never
  client-side timing: (b) the recycling operation itself is an atomic
  transaction, not a read-then-delete-then-reinsert sequence.
- If you're not confident a change preserves "zero double-allocation under
  concurrent load," say so explicitly in your summary and ask for the
  project's concurrency test (the one described in the README as "tested
  under 25 simultaneous threads") to be re-run before merging — don't treat
  a passing single-request test as sufficient proof.
- Changes here get their own task, reviewed on their own — never bundled
  into a broader "add a feature" task, even a small one.
