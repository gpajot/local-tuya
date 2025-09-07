FROM python:3.13-slim AS python-builder-base

COPY --from=ghcr.io/astral-sh/uv:0.8 /uv /uvx /bin/
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy


WORKDIR /app
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-editable
COPY . .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-editable
RUN --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv version --short > ./version.txt

FROM python:3.13-slim

WORKDIR /app
COPY --from=python-builder-base /app/.venv ./.venv
COPY --from=python-builder-base /app/version.txt ./version.txt

ENV PATH="/app/.venv/bin:$PATH"
ENV CONFIG="/app/config/conf.yaml"

ENTRYPOINT ["python", "-m", "local_tuya"]
