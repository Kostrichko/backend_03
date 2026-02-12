# Task Manager — Django + Aiogram

Task management system: Django REST API backend + Telegram bot on aiogram with Celery-based notifications.

## Stack

| Component | Technology |
|-----------|-----------|
| Backend | Django 5.2, DRF |
| Bot | aiogram 3.4 |
| Database | PostgreSQL 16 |
| Task queue | Celery 5.4 + Redis |
| Containers | Docker Compose |
| CI | GitHub Actions |

## Quick Start

```bash
git clone <repository-url>
cd django_aiogram
```

Create `.env` in the project root:

```env
BOT_TOKEN=your_token_from_@BotFather
API_KEY=any_secret_key
POSTGRES_DB=django_aiogram
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
```

Run:

```bash
docker compose up -d --build
docker compose exec web python manage.py migrate
```

Open your bot in Telegram and send `/start`.

## Architecture

```
┌──────────────┐     HTTP/JSON      ┌──────────────┐
│  Telegram    │◄──────────────────►│   aiogram    │
│  Bot API     │                    │   (bot/)     │
└──────────────┘                    └──────┬───────┘
                                           │ aiohttp
                                           ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  PostgreSQL  │◄────│    Django    │◄────│    Redis     │
│              │     │  (backend/) │     │              │
└──────────────┘     └──────┬───────┘     └──────┬───────┘
                            │                     │
                            ▼                     │
                     ┌──────────────┐             │
                     │   Celery     │◄────────────┘
                     │   Worker     │
                     └──────────────┘
```

**5 Docker containers:** postgres, redis, web, bot, celery-worker.

### Communication

- Bot communicates with the backend over Docker's internal network via HTTP JSON API
- Authentication via `X-API-Key` header
- Backend is the sole database accessor
- Notifications are scheduled via Celery ETA (no polling)

## Project Structure

```
├── backend/
│   ├── config/                  # Django settings, Celery, URL routing
│   │   ├── settings.py
│   │   ├── settings_test.py     # Test settings (SQLite in-memory)
│   │   ├── celery.py
│   │   └── urls.py
│   ├── api/
│   │   ├── models.py            # User, Task, Tag
│   │   ├── views.py             # API endpoints
│   │   ├── serializers.py       # DRF serializers
│   │   ├── middleware.py        # APIKeyMiddleware
│   │   ├── tasks.py             # Celery notification task
│   │   ├── services/            # Service Layer
│   │   │   ├── user_service.py
│   │   │   ├── task_service.py
│   │   │   └── tag_service.py
│   │   └── tests/               # 54 tests
│   │       ├── test_models.py
│   │       ├── test_serializers.py
│   │       ├── test_services.py
│   │       └── test_views.py
│   ├── pyproject.toml           # Black, isort, mypy, coverage
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   └── run_checks.sh
├── bot/
│   ├── main.py                  # Entry point
│   ├── config.py                # Bot settings
│   ├── handlers/                # Modular handlers
│   │   ├── __init__.py          # register_handlers()
│   │   ├── common.py            # /start, keyboard
│   │   ├── tasks.py             # Task CRUD, FSM
│   │   └── tags.py              # Tag CRUD, FSM
│   ├── services/
│   │   └── api_client.py        # HTTP client to backend
│   ├── tests/                   # 5 tests
│   │   ├── conftest.py
│   │   ├── test_api_client.py
│   │   └── test_handlers.py
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   ├── pytest.ini
│   └── run_checks.sh
├── docker-compose.yml
├── Dockerfile
└── .env
```

## API

All endpoints require `X-API-Key` header. Prefix: `/api/`.

### Endpoints

| Method | URL | Description | Body / Params | Response |
|--------|-----|-------------|---------------|----------|
| POST | `/register/` | Register user | `{telegram_id, username}` | `{telegram_id, username}` |
| GET | `/tasks/` | Active tasks | `?telegram_id=` | `{"tasks": [...]}` |
| POST | `/tasks/create/` | Create task | `{telegram_id, title, due_date?, tags?}` | `{id, title, status, ...}` |
| POST | `/tasks/delete/` | Delete task | `{telegram_id, task_id}` | `{"status": "ok"}` |
| GET | `/tags/` | User tags | `?telegram_id=` | `{"tags": [...]}` |
| POST | `/tags/create/` | Create tag | `{telegram_id, name}` | `{id, name}` |
| POST | `/tags/delete/` | Delete tag | `{telegram_id, tag_id}` | `{"status": "ok"}` |
| GET | `/archive/` | Archived tasks | `?telegram_id=` | `{"tasks": [...]}` |
| POST | `/clear/` | Clear all data | `{telegram_id}` | `{"status": "ok"}` |

### Error Format

```json
{"error": "error description"}
```

Status codes: `400` — validation, `401` — invalid API key, `404` — not found, `500` — server error.

## Data Models

```
User (PK: telegram_id)
 ├── Tag (name, unique per user)
 └── Task (title, status, due_date?, created_at)
      └── tags (M2M → Tag)
```

**Task statuses:** `pending` → `completed` | `deleted`

## Limits

| Parameter | Value | Setting |
|-----------|-------|---------|
| Active tasks | 6 | `MAX_PENDING_TASKS_PER_USER` |
| Tags | 4 | `MAX_TAGS_PER_USER` |
| Archive tasks (displayed) | 5 | `MAX_ARCHIVE_TASKS_PER_USER` |

Configured in `backend/config/settings.py` and mirrored in `bot/config.py`.

## Telegram Bot

### Commands and Buttons

| Command / Button | Action |
|------------------|--------|
| `/start` | Registration, main menu |
| ➕ Новая задача | Create task (FSM: title → time → tags) |
| 📋 Мои задачи | List active tasks |
| 🏷 Теги | Tag management |
| 📦 Архив | Completed and deleted tasks |
| 🗑 Удалить задачу | Select task to delete |
| ➕ Новый тег | Create a tag |

### FSM States

**CreateTaskState:** `title` → `notify_time` → `tags`
- Notification time: 1 min, 2 min, 5 min, 10 min, 1 hour
- Tags: select from existing via inline buttons, can be skipped

**CreateTagState:** `name`

## Notifications

When a task with `due_date` is created, the backend schedules a Celery task with `eta=due_date`. At the scheduled time, the worker sends a message via Telegram Bot API. No polling — the task fires exactly once at the right moment.

## Testing

### Backend — 54 tests

```bash
# Locally (Python 3.11+)
cd backend
pip install -r requirements.txt -r requirements-dev.txt
python manage.py test --settings=config.settings_test

# Via Docker
docker compose exec web python manage.py test --settings=config.settings_test
```

Test settings: SQLite in-memory, DummyCache, rate limiting disabled.

- **test_models.py** — model creation, relations, ordering
- **test_serializers.py** — validation of all serializers
- **test_services.py** — business logic (limits, duplicates, CRUD)
- **test_views.py** — endpoint integration tests + APIKeyMiddleware

### Bot — 5 tests

```bash
cd bot
pip install -r requirements.txt -r requirements-dev.txt
pytest -W ignore::DeprecationWarning tests/
```

- **test_api_client.py** — successful request, HTTP error handling
- **test_handlers.py** — `/start`, task list (empty and with data)

### Linting

```bash
cd backend && ./run_checks.sh    # tests + black + isort + flake8 + mypy
cd bot && ./run_checks.sh        # tests + black + isort + flake8
```

## CI/CD

GitHub Actions (`.github/workflows/ci.yml`) — 3 parallel jobs:

| Job | What it checks |
|-----|----------------|
| `backend-test` | Django tests (SQLite) |
| `bot-test` | Bot pytest suite |
| `lint` | Black, isort, flake8, mypy (backend) |

Triggers: push and PR to `main` and `dev` branches.

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| `telegram_id` as PK | Unique, immutable, direct bot↔API mapping |
| Service Layer | Business logic separated from views, easy to test |
| Celery ETA over beat | Precise notifications without periodic DB polling |
| Wrapped JSON responses | `{"tasks": [...]}` instead of bare arrays — extensibility, consistency |
| ReplyKeyboard | Always-visible menu, fewer input errors |
| FSM for dialogs | Clear structure, per-step validation |
| APIKeyMiddleware | Single-layer protection for all endpoints |
| Rate limiting | django-ratelimit on every endpoint |
