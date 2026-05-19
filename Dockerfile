FROM python:3.13-slim-bookworm AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH="/app/.venv/bin:${PATH}"

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        curl \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /usr/local/bin/uv

WORKDIR /app

FROM base AS build

COPY pyproject.toml README.md ./
COPY hoctor ./hoctor
COPY config ./config
RUN uv sync --no-dev --frozen 2>/dev/null || uv sync --no-dev

FROM base AS runtime

ARG APP_USER=hoctor
RUN groupadd --system ${APP_USER} \
    && useradd --system --gid ${APP_USER} --create-home --shell /bin/bash ${APP_USER}

WORKDIR /app

COPY --from=build /app/.venv /app/.venv
COPY --chown=${APP_USER}:${APP_USER} . /app

RUN mkdir -p /app/staticfiles /app/media /app/models /app/logs \
    && chown -R ${APP_USER}:${APP_USER} /app

USER ${APP_USER}

ENV DJANGO_SETTINGS_MODULE=config.settings.prod

RUN python manage.py collectstatic --noinput --settings=config.settings.dev

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8000/api/v1/health/ || exit 1

CMD ["gunicorn", "config.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "3", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
