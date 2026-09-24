---
scope: checker_platform/**/advisor*.py, checker_platform/**/pathway*.py, templates/advisor*
activation: glob
---

# Rules for Pathway Advisor code

Trust level: legal/compliance critical. This is the Act 843 boundary the
whole product's privacy claim rests on.

- Grades, index numbers, and any exam-identifying input must never be
  written to a database table, a log line, a cache, a session store, or an
  analytics/telemetry event — for the duration of the request or after.
  Computation happens in memory and is discarded the moment the response is
  sent. No exceptions, including for debugging — don't add a debug log that
  prints the submitted grades "temporarily."
- The consent checkbox gates all processing **server-side**. The evaluation
  endpoint must reject a request with no explicit consent flag in the
  payload — hiding the submit button until the box is checked, client-side
  only, is not sufficient and must never be the only enforcement.
- If a new feature seems to require remembering anything between requests
  for this flow — "let them return to their last verdict," "save their
  grades for next time," "show usage analytics" — that is a real
  product/legal question, not an implementation detail. Stop and ask before
  adding any persistence here, however temporary or well-intentioned it
  seems.
- The three output artifacts (Official Admissions Dossier, WhatsApp
  Placement Card, Print/Save Briefing) must each be generated and handed to
  the user within the same request/response cycle. None of them should
  imply or require server-side storage of the underlying grade data to
  work — if a requested feature for one of these seems to need storage,
  flag it rather than implementing it.
