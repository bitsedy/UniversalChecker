---
scope: checker_platform/**/payment*.py, checker_platform/**/paystack*.py, checker_platform/**/webhook*.py, checker_platform/**/momo*.py
activation: glob
---

# Rules for payment / Paystack integration code

- Never store or log raw card data, full API keys, or webhook secrets — any
  logging added here must redact them.
- Every webhook handler must verify the HMAC SHA512 signature **before**
  processing the payload. Never process the body first and verify after,
  and never add a "skip verification in dev" branch that could plausibly
  ship to production.
- Webhook handlers must be idempotent. Paystack can and will retry a
  webhook delivery — a retried webhook must never re-credit a payment or
  re-allocate a voucher. Check for an existing processed-transaction record
  *inside the same transaction* that performs the allocation, not as a
  separate earlier check.
- Keep the MoMo USSD sandbox/simulator code clearly and structurally
  separated from the live Paystack integration path — a simulator code path
  must never be reachable in a production build, not even behind a flag
  that could be left on by accident.
- Any change to price calculation, refund/reversal handling, or discount
  logic needs explicit test cases from you describing the real-world rule
  being encoded — don't infer the business rule from the code you're
  replacing.
