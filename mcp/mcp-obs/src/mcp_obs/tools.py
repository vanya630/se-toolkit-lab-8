"""Tool schemas, handlers, and registry for the observability MCP server."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass

from mcp.types import Tool
from pydantic import BaseModel, Field

from mcp_obs.observability import (
    LogEntry,
    LogsErrorCountResult,
    ObservabilityClient,
    TraceDetails,
    TraceSummary,
)


class LogsSearchQuery(BaseModel):
    query: str = Field(
        default="",
        description="Optional raw LogsQL tail, e.g. event:request_completed",
    )
    keyword: str = Field(default="", description="Free-text keyword filter.")
    service: str = Field(
        default="Learning Management Service",
        description="Service name field value (service.name).",
    )
    severity: str = Field(
        default="",
        description="Optional severity filter (INFO/WARN/ERROR).",
    )
    minutes: int = Field(
        default=10,
        ge=1,
        le=1440,
        description="Lookback window in minutes.",
    )
    limit: int = Field(default=20, ge=1, le=200, description="Max log lines.")


class LogsErrorCountQuery(BaseModel):
    minutes: int = Field(default=10, ge=1, le=1440)
    service: str = Field(
        default="Learning Management Service",
        description="Optional service.name scope.",
    )


class TracesListQuery(BaseModel):
    service: str = Field(
        default="Learning Management Service",
        description="Jaeger service name to list traces for.",
    )
    limit: int = Field(default=5, ge=1, le=50)


class TracesGetQuery(BaseModel):
    trace_id: str = Field(description="Trace ID from logs.trace_id or traces_list.")


ToolPayload = BaseModel | Sequence[BaseModel]
ToolHandler = Callable[[ObservabilityClient, BaseModel], Awaitable[ToolPayload]]


@dataclass(frozen=True, slots=True)
class ToolSpec:
    name: str
    description: str
    model: type[BaseModel]
    handler: ToolHandler

    def as_tool(self) -> Tool:
        schema = self.model.model_json_schema()
        schema.pop("$defs", None)
        schema.pop("title", None)
        return Tool(name=self.name, description=self.description, inputSchema=schema)


def _require[T: BaseModel](args: BaseModel, model: type[T]) -> T:
    if not isinstance(args, model):
        raise TypeError(f"Expected {model.__name__}, got {type(args).__name__}")
    return args


async def _logs_search(client: ObservabilityClient, args: BaseModel) -> list[LogEntry]:
    query = _require(args, LogsSearchQuery)
    return await client.logs_search(
        query=query.query,
        keyword=query.keyword,
        service=query.service,
        severity=query.severity,
        minutes=query.minutes,
        limit=query.limit,
    )


async def _logs_error_count(
    client: ObservabilityClient, args: BaseModel
) -> LogsErrorCountResult:
    query = _require(args, LogsErrorCountQuery)
    return await client.logs_error_count(minutes=query.minutes, service=query.service)


async def _traces_list(
    client: ObservabilityClient, args: BaseModel
) -> list[TraceSummary]:
    query = _require(args, TracesListQuery)
    return await client.traces_list(service=query.service, limit=query.limit)


async def _traces_get(client: ObservabilityClient, args: BaseModel) -> TraceDetails:
    query = _require(args, TracesGetQuery)
    return await client.traces_get(trace_id=query.trace_id)


TOOL_SPECS = (
    ToolSpec(
        "logs_search",
        "Search VictoriaLogs using scope filters (service, severity, keyword, time window).",
        LogsSearchQuery,
        _logs_search,
    ),
    ToolSpec(
        "logs_error_count",
        "Count ERROR-level log records by service over a time window.",
        LogsErrorCountQuery,
        _logs_error_count,
    ),
    ToolSpec(
        "traces_list",
        "List recent traces for a given service from VictoriaTraces.",
        TracesListQuery,
        _traces_list,
    ),
    ToolSpec(
        "traces_get",
        "Fetch and summarize a specific trace by trace_id.",
        TracesGetQuery,
        _traces_get,
    ),
)
TOOLS_BY_NAME = {tool.name: tool for tool in TOOL_SPECS}

