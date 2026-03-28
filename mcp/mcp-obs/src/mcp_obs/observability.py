"""Async clients and typed models for VictoriaLogs and VictoriaTraces."""

from __future__ import annotations

import json
from collections import Counter
from typing import Any

import httpx
from pydantic import BaseModel, Field


class LogEntry(BaseModel):
    time: str = ""
    service: str = ""
    severity: str = ""
    event: str = ""
    trace_id: str = ""
    message: str = ""
    raw: dict[str, Any] = Field(default_factory=dict)


class LogsErrorCountResult(BaseModel):
    window_minutes: int
    total_errors: int
    by_service: dict[str, int]


class TraceSummary(BaseModel):
    trace_id: str
    span_count: int
    services: list[str]
    root_operations: list[str]


class TraceSpan(BaseModel):
    span_id: str
    operation: str
    service: str
    duration_us: int
    start_time_us: int
    has_error_tag: bool


class TraceDetails(BaseModel):
    trace_id: str
    span_count: int
    services: list[str]
    spans: list[TraceSpan]


def _escape_logsql_value(value: str) -> str:
    return value.replace('"', '\\"')


def _compose_logsql(
    *,
    query: str,
    keyword: str,
    service: str,
    severity: str,
    minutes: int,
) -> str:
    parts: list[str] = [f"_time:{minutes}m"]
    if query.strip():
        parts.append(query.strip())
    if service.strip():
        parts.append(f'service.name:"{_escape_logsql_value(service.strip())}"')
    if severity.strip():
        parts.append(f"severity:{severity.strip().upper()}")
    if keyword.strip():
        parts.append(f'"{_escape_logsql_value(keyword.strip())}"')
    return " ".join(parts)


class ObservabilityClient:
    def __init__(
        self,
        victorialogs_url: str,
        victoriatraces_url: str,
        *,
        timeout: float = 15.0,
    ) -> None:
        self._http = httpx.AsyncClient(timeout=timeout)
        self._logs_url = victorialogs_url.rstrip("/")
        self._traces_url = victoriatraces_url.rstrip("/")

    async def __aenter__(self) -> ObservabilityClient:
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._http.aclose()

    async def logs_search(
        self,
        *,
        query: str = "",
        keyword: str = "",
        service: str = "",
        severity: str = "",
        minutes: int = 10,
        limit: int = 20,
    ) -> list[LogEntry]:
        logsql = _compose_logsql(
            query=query,
            keyword=keyword,
            service=service,
            severity=severity,
            minutes=minutes,
        )
        response = await self._http.get(
            f"{self._logs_url}/select/logsql/query",
            params={"query": logsql, "limit": max(1, min(limit, 200))},
        )
        response.raise_for_status()

        records: list[LogEntry] = []
        for raw_line in response.text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            records.append(
                LogEntry(
                    time=str(payload.get("_time", "")),
                    service=str(payload.get("service.name", "")),
                    severity=str(payload.get("severity", "")),
                    event=str(payload.get("event", "")),
                    trace_id=str(payload.get("trace_id", "")),
                    message=str(payload.get("_msg", "")),
                    raw=payload,
                )
            )
        return records

    async def logs_error_count(
        self,
        *,
        minutes: int = 10,
        service: str = "",
    ) -> LogsErrorCountResult:
        records = await self.logs_search(
            service=service,
            severity="ERROR",
            minutes=minutes,
            limit=500,
        )
        counter = Counter(entry.service or "unknown" for entry in records)
        return LogsErrorCountResult(
            window_minutes=minutes,
            total_errors=len(records),
            by_service=dict(counter),
        )

    async def traces_list(
        self,
        *,
        service: str,
        limit: int = 5,
    ) -> list[TraceSummary]:
        response = await self._http.get(
            f"{self._traces_url}/select/jaeger/api/traces",
            params={"service": service, "limit": max(1, min(limit, 50))},
        )
        response.raise_for_status()
        payload = response.json()
        traces: list[dict[str, Any]] = payload.get("data", [])

        summaries: list[TraceSummary] = []
        for trace in traces:
            processes = trace.get("processes", {})
            spans = trace.get("spans", [])
            services = sorted(
                {
                    str(processes.get(span.get("processID", ""), {}).get("serviceName", ""))
                    for span in spans
                    if span.get("processID")
                }
            )
            span_ids = {str(span.get("spanID", "")) for span in spans}
            child_ids = {
                str(ref.get("spanID", ""))
                for span in spans
                for ref in span.get("references", [])
                if ref.get("refType") == "CHILD_OF"
            }
            root_ops = [
                str(span.get("operationName", ""))
                for span in spans
                if str(span.get("spanID", "")) in span_ids - child_ids
            ]
            summaries.append(
                TraceSummary(
                    trace_id=str(trace.get("traceID", "")),
                    span_count=len(spans),
                    services=[s for s in services if s],
                    root_operations=[op for op in root_ops if op],
                )
            )
        return summaries

    async def traces_get(self, trace_id: str) -> TraceDetails:
        response = await self._http.get(
            f"{self._traces_url}/select/jaeger/api/traces/{trace_id}"
        )
        response.raise_for_status()
        payload = response.json()
        data = payload.get("data", [])
        if not data:
            raise RuntimeError(f"Trace not found: {trace_id}")

        trace = data[0]
        processes = trace.get("processes", {})
        spans = trace.get("spans", [])
        parsed_spans: list[TraceSpan] = []
        services_seen: set[str] = set()

        for span in spans:
            process = processes.get(span.get("processID", ""), {})
            service_name = str(process.get("serviceName", "unknown"))
            services_seen.add(service_name)
            tags = span.get("tags", [])
            has_error_tag = any(
                str(tag.get("key", "")).lower() in {"error", "otel.status_code"}
                and str(tag.get("value", "")).lower() in {"true", "error"}
                for tag in tags
            )
            parsed_spans.append(
                TraceSpan(
                    span_id=str(span.get("spanID", "")),
                    operation=str(span.get("operationName", "")),
                    service=service_name,
                    duration_us=int(span.get("duration", 0)),
                    start_time_us=int(span.get("startTime", 0)),
                    has_error_tag=has_error_tag,
                )
            )

        return TraceDetails(
            trace_id=str(trace.get("traceID", trace_id)),
            span_count=len(parsed_spans),
            services=sorted(services_seen),
            spans=parsed_spans,
        )

