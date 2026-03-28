"""Runtime settings for observability APIs."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Settings:
    victorialogs_url: str
    victoriatraces_url: str


def _required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is required")
    return value.rstrip("/")


def resolve_settings() -> Settings:
    logs_url = os.environ.get("NANOBOT_VICTORIALOGS_URL", "").strip() or os.environ.get(
        "VICTORIALOGS_URL", ""
    ).strip()
    traces_url = os.environ.get(
        "NANOBOT_VICTORIATRACES_URL", ""
    ).strip() or os.environ.get("VICTORIATRACES_URL", "").strip()

    if not logs_url:
        logs_url = _required("NANOBOT_VICTORIALOGS_URL")
    if not traces_url:
        traces_url = _required("NANOBOT_VICTORIATRACES_URL")

    return Settings(
        victorialogs_url=logs_url.rstrip("/"),
        victoriatraces_url=traces_url.rstrip("/"),
    )

