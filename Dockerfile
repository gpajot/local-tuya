FROM dhi.io/python:3.14-dev AS python-builder-base

WORKDIR /app
RUN --mount=from=ghcr.io/astral-sh/uv:0.9,source=/uv,target=/bin/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=local_tuya,target=local_tuya \
    --mount=type=bind,source=LICENSE,target=LICENSE \
    --mount=type=bind,source=README.md,target=README.md \
    uv sync --frozen --no-dev --no-editable --compile-bytecode

FROM dhi.io/python:3.14

WORKDIR /app
COPY --from=python-builder-base /app/.venv .venv/

ENV PATH="/app/.venv/bin:$PATH"
ENV CONFIG="/app/config/conf.yaml"

ENTRYPOINT ["python", "-m", "local_tuya"]
