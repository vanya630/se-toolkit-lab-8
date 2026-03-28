---
name: observability
description: Investigate LMS/backend failures using logs and traces via MCP tools
always: true
---

Use observability MCP tools for error investigation:

- `mcp_obs_logs_error_count`
- `mcp_obs_logs_search`
- `mcp_obs_traces_list`
- `mcp_obs_traces_get`

Reasoning strategy:

1. For questions like "Any errors in the last X minutes?", call `mcp_obs_logs_error_count` first with a narrow window and LMS service scope.
2. If errors exist, call `mcp_obs_logs_search` with `severity=ERROR` and the same window to fetch recent records.
3. Extract a recent non-empty `trace_id` from logs and call `mcp_obs_traces_get`.
4. Summarize root cause briefly: affected service, failing operation/event, and whether errors are ongoing.

Investigation intent routing:

- If user asks `What went wrong?`:
  - run `mcp_obs_logs_error_count` for recent 10m (or narrower if requested)
  - run `mcp_obs_logs_search` scoped to `Learning Management Service` and `severity=ERROR`
  - extract most recent `trace_id` and run `mcp_obs_traces_get`
  - answer in one short diagnosis that explicitly includes:
    - one log evidence line (error event + time/service)
    - one trace evidence line (trace id + failing operation/span)
- If user asks `Check system health`:
  - run `mcp_obs_logs_error_count` for recent 2-10m
  - if errors > 0, inspect logs/traces as above
  - return concise healthy/unhealthy summary

Proactive health-check requests:

- If user asks to create recurring health checks in current chat, use built-in `cron` tool:
  - add job on requested interval
  - each run checks recent LMS/backend errors using observability tools
  - posts short summary to same chat (healthy if no recent errors)
- If user asks `List scheduled jobs.`, call cron list.
- If user asks to remove or change interval, call cron remove/update.

Response rules:

- Prefer concise summaries over raw JSON.
- Mention time window used.
- If no errors are found, explicitly say so.
- If the issue seems stale/historical, recommend narrowing window (e.g., 5–10 minutes).
- For `What went wrong?`, mention both log evidence and trace evidence explicitly.
