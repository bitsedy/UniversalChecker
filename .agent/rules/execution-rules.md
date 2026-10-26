# Project Architecture & Execution Rules

- **Commands**: Build (`npm run build`), Test (`npm test`), Typecheck (`npx tsc --noEmit`).
- **Search Discipline**: Never read entire files to find a function. Use `grep` or symbol search first, then read specific line ranges.
- **Verification Gate**: Never mark a task complete without running the typechecker and affected unit tests via `run_command`.
- **Edge-Case Audit**: Before writing implementation code, list 3 failure states (null inputs, network timeouts, race conditions) and handle them explicitly.
