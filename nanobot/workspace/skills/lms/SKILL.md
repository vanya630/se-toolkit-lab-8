---
name: lms
description: Use LMS MCP tools for live backend data and lab-scoped analytics
always: true
---

Use LMS MCP tools as the source of truth.

Tools:

- `mcp_lms_lms_health`: backend health and status
- `mcp_lms_lms_labs`: list labs with ids/names
- `mcp_lms_lms_pass_rates`: pass rates for a lab
- `mcp_lms_lms_timeline`: submissions timeline for a lab
- `mcp_lms_lms_groups`: group-level analytics for a lab
- `mcp_lms_lms_top_learners`: best learners for a lab
- `mcp_lms_lms_completion_rate`: completion stats for a lab
- `mcp_lms_lms_learners`: learner list/details
- `mcp_lms_lms_sync_pipeline`: trigger data sync if data seems stale

Decision strategy:

1. If the user asks about available labs, call `mcp_lms_lms_labs`.
2. For lab-specific analytics without a lab selected (`scores`, `pass rate`, `timeline`, `groups`, `top learners`, `completion`):
- First call `mcp_lms_lms_labs`.
- If multiple labs are available, ask for a lab choice. Prefer structured UI via `mcp_webchat_ui_message` with a `choice` payload.
- Labels must be short and readable.
- Values must be stable machine values (lab id/slug) that can be reused in the follow-up tool call.
3. If backend/tool access fails (401/connection), explain briefly and suggest checking backend + API key.
4. If backend is reachable but data is empty, run `mcp_lms_lms_sync_pipeline` once and retry the original LMS tool.

Formatting:

- Keep responses short and practical.
- Use real tool output, do not invent labs/metrics.
- Use percentages with one decimal place when appropriate.
