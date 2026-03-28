ARG REGISTRY_PREFIX_DOCKER_HUB
FROM ${REGISTRY_PREFIX_DOCKER_HUB}astral/uv:python3.14-bookworm-slim AS builder
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_NO_DEV=1 UV_PYTHON_DOWNLOADS=0

WORKDIR /app/nanobot

COPY --from=workspace pyproject.toml uv.lock /app/
COPY pyproject.toml /app/nanobot/pyproject.toml
COPY README.md /app/nanobot/README.md
COPY .python-version /app/nanobot/.python-version
COPY main.py /app/nanobot/main.py
COPY config.json /app/nanobot/config.json
COPY entrypoint.py /app/nanobot/entrypoint.py
COPY workspace /app/nanobot/workspace

COPY --from=workspace mcp /app/mcp
COPY --from=workspace nanobot-websocket-channel /app/nanobot-websocket-channel

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --project /app --package nanobot

ARG REGISTRY_PREFIX_DOCKER_HUB
FROM ${REGISTRY_PREFIX_DOCKER_HUB}python:3.14.2-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV LANG=C.UTF-8

ARG APP_UID=1000
ARG APP_GID=1000
RUN if [ "${APP_UID}" != "0" ]; then \
      groupadd --system --gid ${APP_GID} appgroup && \
      useradd --system --uid ${APP_UID} --gid ${APP_GID} --create-home appuser; \
    fi

COPY --from=builder --chown=${APP_UID}:${APP_GID} /app /app
ENV PATH="/app/.venv/bin:$PATH"

WORKDIR /app/nanobot
USER ${APP_UID}:${APP_GID}

CMD ["python", "/app/nanobot/entrypoint.py"]
