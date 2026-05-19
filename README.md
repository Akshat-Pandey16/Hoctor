# Hoctor

> Indoor Wi-Fi fingerprint location tracker. Pick a room, scan, and a trained random-forest
> classifier tells you which room a device is in — using only the surrounding Wi-Fi signals.

[![Python 3.13](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/downloads/)
[![Django 6.0](https://img.shields.io/badge/django-6.0-darkgreen.svg)](https://docs.djangoproject.com/en/6.0/)
[![DRF 3.16](https://img.shields.io/badge/drf-3.16-red.svg)](https://www.django-rest-framework.org/)
[![Managed by uv](https://img.shields.io/badge/managed%20by-uv-purple.svg)](https://docs.astral.sh/uv/)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://docs.astral.sh/ruff/)

---

## Table of contents

- [What it does](#what-it-does)
- [Architecture](#architecture)
- [Tech stack](#tech-stack)
- [Quick start](#quick-start)
- [Configuration](#configuration)
- [REST API](#rest-api)
- [Frontend](#frontend)
- [Domain model](#domain-model)
- [Wi-Fi scanning](#wi-fi-scanning)
- [Testing](#testing)
- [Docker](#docker)
- [Project layout](#project-layout)
- [Make targets](#make-targets)
- [Roadmap](#roadmap)

---

## What it does

Each room in a building has a unique signature of nearby Wi-Fi access points
(BSSID + signal strength). Hoctor lets you:

1. **Capture** that signature per room (a *fingerprint*).
2. **Train** a per-venue scikit-learn classifier on those fingerprints (automatic and cached).
3. **Predict** which room a fresh scan came from, with confidence + per-room probabilities.

It works without any extra hardware — just the Wi-Fi card the host already has — and ships
with a mock scanner so the full stack runs in CI and on hardware without Wi-Fi.

## Architecture

```
┌──────────────┐   POST /api/v1/scans/   ┌────────────────────┐
│ Browser /    │ ───────────────────────►│ ScanListView       │
│ Alpine UI    │                         │ (APIView)          │
└──────────────┘                         └────────┬───────────┘
                                                  │
                                  ┌───────────────┴───────────────┐
                                  ▼                               ▼
                          get_scanner() backend          RoomPredictor (singleton)
                          mock | hardware                  • lazy train per Venue
                                                            • cached in-process
                                                            • persisted to /models/*.joblib
                                                            • invalidated via signals on
                                                              Fingerprint / Sample changes
                                                  │
                                                  ▼
                                          Scan row persisted with
                                          predicted_room + probabilities
```

Apps:

| App                | Responsibility                                           |
|--------------------|----------------------------------------------------------|
| `hoctor.venues`    | `Venue`, `Room` models + nested REST API                 |
| `hoctor.tracking`  | `Device`, `Fingerprint`, `AccessPointSample`, `Scan` models, ML predictor, REST API |
| `hoctor.web`       | Templated UI (landing, dashboard, live tracker, venue detail) |
| `config`           | Settings (`base` / `dev` / `prod` / `test`), URL conf, ASGI/WSGI |

The whole API surface is built with `rest_framework.views.APIView` — explicit
`get / post / patch / delete` methods (no `put`, no `ViewSet`, no router magic).

## Tech stack

- **Python 3.13** (latest CPython)
- **Django 6.0** with split settings (`dev` / `prod` / `test`)
- **Django REST Framework 3.16** + **drf-spectacular** (OpenAPI 3.1 + Swagger UI + ReDoc)
- **scikit-learn 1.6** RandomForest classifier, persisted via `joblib`
- **NumPy 2.x** for feature vectors
- **uv** for environments, lockfile, and packaging (`pyproject.toml`, hatchling backend)
- **PostgreSQL 17** in production via `psycopg[binary]`; SQLite for dev/tests
- **gunicorn** + **whitenoise** for serving in production
- **Tailwind CSS** (CDN, dark theme) + **HTMX** + **Alpine.js** for the UI — zero build step
- **pytest** + **pytest-django** + **factory-boy** for testing
- **ruff** for lint + format
- **Docker** + **docker compose** for a one-command full stack
- **GitHub Actions** CI: lint → format check → tests → image build

## Quick start

```bash
# 0. requires: python 3.13, uv >=0.5 (`brew install uv` or `pipx install uv`)

# 1. install + create the venv
make install

# 2. seed env + database
make env          # writes .env from .env.example
make migrate      # apply migrations
make seed         # populate demo venues, rooms, fingerprints

# 3. run
make run          # http://127.0.0.1:8000

# 4. or do all of the above in one shot
make all
```

Then open:

| URL                       | What                                |
|---------------------------|--------------------------------------|
| http://127.0.0.1:8000/    | Landing                              |
| /dashboard/               | Venues + devices + recent scans      |
| /track/                   | Live scan + per-room probability bars|
| /admin/                   | Django admin (create a superuser)    |
| /api/v1/                  | Browsable DRF API                    |
| /api/docs/                | Swagger UI                           |
| /api/redoc/               | ReDoc                                |
| /api/schema/              | OpenAPI JSON                         |

Create an admin login:

```bash
make superuser
```

## Configuration

All configuration is via environment variables (12-factor). See [`.env.example`](.env.example).

| Variable                          | Default                       | Notes                                  |
|-----------------------------------|-------------------------------|----------------------------------------|
| `DJANGO_SETTINGS_MODULE`          | `config.settings.dev`         | `dev` / `prod` / `test`                |
| `DJANGO_SECRET_KEY`               | dev-only fallback             | **Required in prod**                   |
| `DJANGO_DEBUG`                    | `false`                       | `true` in dev settings                 |
| `DJANGO_ALLOWED_HOSTS`            | `localhost,127.0.0.1`         | Comma-separated                        |
| `DJANGO_CSRF_TRUSTED_ORIGINS`     | local origins                 | Comma-separated full URLs              |
| `DATABASE_URL`                    | `sqlite:///db.sqlite3`        | `postgres://user:pw@host:5432/db` etc. |
| `HOCTOR_SCANNER_BACKEND`          | `mock`                        | `mock` or `hardware`                   |
| `HOCTOR_MODEL_DIR`                | `./models`                    | Joblib persisted classifier cache      |
| `HOCTOR_PREDICTION_MIN_SAMPLES`   | `3`                           | Min fingerprints before training       |

Settings are layered:

- `config.settings.base` — shared truth
- `config.settings.dev` — debug toolbar, permissive hosts, console emails
- `config.settings.prod` — HSTS, secure cookies, SSL redirect, JSON-only DRF renderer
- `config.settings.test` — in-memory SQLite, fast password hasher

## REST API

Versioned under `/api/v1/`. All endpoints use `APIView` with explicit verbs.

### Venues

| Method  | Path                                              | Notes                          |
|---------|---------------------------------------------------|--------------------------------|
| GET     | `/api/v1/venues/`                                 | List, `?search=` substring     |
| POST    | `/api/v1/venues/`                                 | Create                         |
| GET     | `/api/v1/venues/{slug}/`                          | Detail incl. nested rooms      |
| PATCH   | `/api/v1/venues/{slug}/`                          | Partial update                 |
| DELETE  | `/api/v1/venues/{slug}/`                          | Cascade-deletes rooms          |
| GET     | `/api/v1/venues/{slug}/rooms/`                    | Rooms for venue                |
| POST    | `/api/v1/venues/{slug}/rooms/`                    | Create room                    |
| GET     | `/api/v1/venues/{slug}/rooms/{room_slug}/`        | Room detail                    |
| PATCH   | `/api/v1/venues/{slug}/rooms/{room_slug}/`        | Update                         |
| DELETE  | `/api/v1/venues/{slug}/rooms/{room_slug}/`        | Delete                         |

### Devices

| Method  | Path                                |
|---------|-------------------------------------|
| GET / POST   | `/api/v1/devices/`              |
| GET / PATCH / DELETE | `/api/v1/devices/{name}/` |

### Fingerprints (training data)

| Method  | Path                                                |
|---------|-----------------------------------------------------|
| GET     | `/api/v1/fingerprints/?venue=&room=`                |
| POST    | `/api/v1/fingerprints/`                             |
| GET     | `/api/v1/fingerprints/{id}/`                        |
| DELETE  | `/api/v1/fingerprints/{id}/`                        |

Create payload:

```json
{
  "room": 12,
  "captured_at": "2026-05-19T16:00:00Z",
  "samples": [
    {"ssid": "office-5g", "bssid": "aa:bb:cc:dd:ee:01", "signal": -42},
    {"ssid": "office-5g", "bssid": "aa:bb:cc:dd:ee:02", "signal": -68}
  ]
}
```

### Scans (predict where a device is)

| Method  | Path                                |
|---------|-------------------------------------|
| GET     | `/api/v1/scans/?venue=&device=&limit=` |
| POST    | `/api/v1/scans/`                    |
| GET     | `/api/v1/scans/{id}/`               |

Create payload (either provide `samples` or set `use_scanner: true` to use the host's Wi-Fi):

```json
{
  "venue": "bitdurg-cse-block",
  "device": "tejas",
  "samples": [
    {"ssid": "office-5g", "bssid": "aa:bb:cc:dd:ee:01", "signal": -45}
  ]
}
```

Response:

```json
{
  "id": 42,
  "venue_slug": "bitdurg-cse-block",
  "predicted_room_name": "Lab 02",
  "confidence": 0.87,
  "probabilities": {"Lab 02": 0.87, "Lab 01": 0.09, "Faculty Room": 0.04},
  "status": "predicted",
  "created_at": "2026-05-19T16:01:32Z"
}
```

### Health

`GET /api/v1/health/` → `{"status": "ok", "time": ...}` (used by the Docker healthcheck).

## Frontend

Server-rendered Django templates styled with **Tailwind via CDN** (dark theme, brand-orange
accents). **Alpine.js** drives the live tracker; **HTMX** is loaded for any future
interactivity. Zero JS build step. Responsive from 320 px up.

- `/` — landing with sample prediction card and feature blocks
- `/dashboard/` — venues + devices + recent-scan table
- `/track/` — pick a venue + device, run a scan (mock samples or hardware), see prediction & probability bars in real time
- `/venues/<slug>/` — venue detail with per-room training status and venue scan history

## Domain model

```
Venue ──1:N── Room ──1:N── Fingerprint ──1:N── AccessPointSample
                              │
Device ──1:N──────────────────┘

Scan ── FK Venue
      ── FK Device         (nullable, auto-created from name on POST)
      ── FK Room            (predicted_room, nullable)
      ── JSON probabilities + raw_samples
      ── status: pending | predicted | failed
```

Indexes:

- `Venue.slug`
- `Room (venue, floor)`, unique `(venue, slug)`, unique `(venue, name)`
- `Fingerprint (room, -captured_at)`
- `AccessPointSample (ssid, bssid)`, partial unique `(fingerprint, bssid)` when bssid != ''
- `Scan (venue, -created_at)`, `Scan (device, -created_at)`, `Scan.status`

## Wi-Fi scanning

The scanner is a small Protocol with two implementations:

```python
from hoctor.tracking.services import get_scanner
readings = get_scanner().scan()
```

| Backend        | When to use                                     | Setup                                   |
|----------------|-------------------------------------------------|-----------------------------------------|
| `mock`         | dev, CI, demos without Wi-Fi hardware           | default                                 |
| `hardware`     | real device on Linux/macOS/Windows              | `uv sync --extra scan` (`access-points`)|

Toggle with `HOCTOR_SCANNER_BACKEND=hardware` in `.env`.

## Testing

```bash
make test           # pytest
make cov            # coverage HTML report under htmlcov/
make check          # lint + format check + tests
```

The test suite covers:

- Model constraints (unique-per-venue, slug auto-fill, indexes)
- Scanner determinism and backend dispatch
- Predictor: empty/insufficient/successful training, cache invalidation via signals
- API: list / create / patch / delete, `PUT` correctly returns 405, validation errors,
  scan end-to-end including auto-device-creation and venue filtering

## Docker

Production-ready multi-stage build with a non-root user, healthcheck, and gunicorn.

```bash
make docker-up      # docker compose up Postgres + web
make docker-logs    # tail web
make docker-down
```

`docker-compose.yml` provisions PostgreSQL 17, runs migrations on start, and exposes the
app on `:8000`. Set `DJANGO_SECRET_KEY` in your environment before bringing the stack up.

## Project layout

```
.
├── config/                  # Django project (settings, urls, asgi/wsgi)
│   └── settings/
│       ├── base.py
│       ├── dev.py
│       ├── prod.py
│       └── test.py
├── hoctor/
│   ├── venues/              # Venue + Room app
│   ├── tracking/            # Device, Fingerprint, Scan, predictor, scanner
│   │   ├── services/        # predictor.py, scanner.py
│   │   └── management/commands/seed_demo.py
│   └── web/                 # Templated UI
│       └── templates/web/
├── templates/               # base.html
├── static/                  # CSS/JS/img
├── tests/                   # cross-app integration tests
├── conftest.py              # root pytest fixtures (api_client, predictor reset)
├── pyproject.toml           # deps + ruff/mypy/pytest config
├── Dockerfile               # multi-stage production image
├── docker-compose.yml       # Postgres + web stack
├── Makefile                 # dev workflow
└── manage.py
```

## Make targets

Run `make help` for the full menu. The most-used ones:

| Target           | Purpose                                              |
|------------------|------------------------------------------------------|
| `make install`   | Sync deps via uv                                     |
| `make env`       | Copy `.env.example` → `.env`                         |
| `make migrate`   | Apply DB migrations                                  |
| `make seed`      | Populate demo data                                   |
| `make run`       | Run dev server on `:8000` (override `PORT=...`)      |
| `make test`      | pytest                                               |
| `make check`     | Lint + format check + tests                          |
| `make fmt`       | Auto-fix + format with ruff                          |
| `make schema`    | Dump validated OpenAPI schema to `schema.yml`        |
| `make reset-db`  | Drop sqlite, re-migrate, re-seed                     |
| `make docker-up` | Start Postgres + web via docker compose              |
| `make all`       | First-run: install, env, migrate, seed, run          |

## Roadmap

- Authenticated multi-tenant scoping per venue
- WebSocket live updates on the dashboard
- Heatmap visualization of room probability over time
- Per-device home-room with anomaly alerts
- Optional kNN backend for tiny training sets

## License

MIT — see `pyproject.toml`.
