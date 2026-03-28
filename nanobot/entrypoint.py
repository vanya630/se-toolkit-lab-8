import json
import os
from pathlib import Path


def _set_if_env(config: dict, env_name: str, path: list[str], cast=None) -> None:
    raw_value = os.environ.get(env_name)
    if raw_value is None or raw_value == "":
        return
    value = cast(raw_value) if cast else raw_value

    cursor = config
    for key in path[:-1]:
        if key not in cursor or not isinstance(cursor[key], dict):
            cursor[key] = {}
        cursor = cursor[key]
    cursor[path[-1]] = value


def _read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: Path, payload: dict) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")


def main() -> None:
    app_dir = Path(__file__).resolve().parent
    config_path = app_dir / "config.json"
    resolved_path = app_dir / "config.resolved.json"

    config = _read_json(config_path)

    _set_if_env(config, "LLM_API_KEY", ["providers", "custom", "apiKey"])
    _set_if_env(config, "LLM_API_BASE_URL", ["providers", "custom", "apiBase"])
    _set_if_env(config, "LLM_API_MODEL", ["agents", "defaults", "model"])

    _set_if_env(config, "NANOBOT_GATEWAY_CONTAINER_ADDRESS", ["gateway", "host"])
    _set_if_env(
        config,
        "NANOBOT_GATEWAY_CONTAINER_PORT",
        ["gateway", "port"],
        cast=int,
    )

    _set_if_env(
        config,
        "NANOBOT_LMS_BACKEND_URL",
        ["tools", "mcpServers", "lms", "env", "NANOBOT_LMS_BACKEND_URL"],
    )
    _set_if_env(
        config,
        "NANOBOT_LMS_API_KEY",
        ["tools", "mcpServers", "lms", "env", "NANOBOT_LMS_API_KEY"],
    )

    _set_if_env(
        config,
        "NANOBOT_WEBCHAT_CONTAINER_ADDRESS",
        ["channels", "webchat", "host"],
    )
    _set_if_env(
        config,
        "NANOBOT_WEBCHAT_CONTAINER_PORT",
        ["channels", "webchat", "port"],
        cast=int,
    )

    relay_host = os.environ.get("NANOBOT_UI_RELAY_HOST", "127.0.0.1")
    relay_port = os.environ.get("NANOBOT_UI_RELAY_PORT", "8766")
    _set_if_env(
        config,
        "NANOBOT_UI_RELAY_TOKEN",
        ["tools", "mcpServers", "webchat", "env", "NANOBOT_UI_RELAY_TOKEN"],
    )
    config.setdefault("tools", {}).setdefault("mcpServers", {}).setdefault(
        "webchat", {}
    ).setdefault("env", {})["NANOBOT_UI_RELAY_URL"] = (
        f"http://{relay_host}:{relay_port}"
    )

    _set_if_env(
        config,
        "NANOBOT_VICTORIALOGS_URL",
        ["tools", "mcpServers", "obs", "env", "NANOBOT_VICTORIALOGS_URL"],
    )
    _set_if_env(
        config,
        "NANOBOT_VICTORIATRACES_URL",
        ["tools", "mcpServers", "obs", "env", "NANOBOT_VICTORIATRACES_URL"],
    )

    _write_json(resolved_path, config)

    workspace = os.environ.get("NANOBOT_WORKSPACE", str(app_dir / "workspace"))
    os.execvp(
        "nanobot",
        [
            "nanobot",
            "gateway",
            "--config",
            str(resolved_path),
            "--workspace",
            workspace,
        ],
    )


if __name__ == "__main__":
    main()
