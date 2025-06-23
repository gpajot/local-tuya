FROM python:3.13-slim AS python-builder-base

RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        curl \
        build-essential

ENV POETRY_VERSION=1.8.4 \
    POETRY_HOME=/etc/poetry \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

RUN curl -sSL https://install.python-poetry.org | python -

WORKDIR /app
COPY ./pyproject.toml ./poetry.lock ./
RUN $POETRY_HOME/venv/bin/poetry install --only main --no-root && rm -rf $POETRY_CACHE_DIR

FROM python:3.13-slim

WORKDIR /app
COPY --from=python-builder-base /app/.venv ./.venv
COPY ./local_tuya ./local_tuya

ENV PATH="/app/.venv/bin:$PATH"
ENV CONFIG="/app/config/conf.yaml"

ENTRYPOINT ["python", "-m", "local_tuya"]
