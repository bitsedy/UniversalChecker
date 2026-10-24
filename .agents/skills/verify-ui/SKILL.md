---
name: verify-ui
description: Critical guidelines for UI verification using CLI browser tools and host Chrome binding instead of the IDE internal browser subagent.
---
- CRITICAL: Never invoke the IDE's internal browser subagent. Always execute browser actions via terminal commands.
- If `npx agent-browser` fails to launch a bundled binary, pass the system Chrome executable path or run Playwright scripts configured with `channel: 'chrome'` so it uses the host machine's installed Google Chrome directly.
