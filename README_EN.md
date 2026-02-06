# Django Aiogram Task Manager

A production-ready task management system combining Django REST API with a Telegram bot interface. Built for efficient task tracking with tag-based organization and intelligent notification scheduling.

## Features

- **Telegram Bot Interface**: Intuitive keyboard-based UI for task management
- **Smart Notifications**: Precise task reminders using Celery ETA scheduling
- **Tag System**: Organize tasks with custom tags (up to 4 per user)
- **Task Limits**: Enforced limits to maintain focus (6 active tasks maximum)
- **Archive Management**: Separate view for completed and deleted tasks
- **RESTful API**: Clean JSON endpoints for programmatic access

## Tech Stack

- **Backend**: Django 5.2.1
- **Database**: PostgreSQL 16
- **Bot Framework**: aiogram 3.4.1
- **Task Queue**: Celery 5.4.0 with Redis broker
- **Containerization**: Docker Compose
- **Testing**: Django TestCase (14 comprehensive tests)

## Prerequisites

- Docker and Docker Compose
- Telegram Bot Token (obtain from [@BotFather](https://t.me/botfather))

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd django_aiogram
```

2. Create `.env` file in the project root:
```env
BOT_TOKEN=your_telegram_bot_token_here
POSTGRES_DB=django_aiogram
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
```

3. Build and start services:
```bash
docker compose up -d --build
```

4. Apply database migrations:
```bash
docker exec django_aiogram-web-1 python manage.py migrate
```

## Usage

### Telegram Bot

Start a conversation with your bot on Telegram. The main menu provides six operations:

- **➕ Новая задача**: Create a task with optional notification time
- **📋 Мои задачи**: View all active tasks
- **🏷 Теги**: List existing tags
- **📦 Архив**: Browse completed and deleted tasks
- **🗑 Удалить задачу**: Mark a task as deleted
- **➕ Новый тег**: Create a new tag

### API Endpoints

All endpoints accept JSON payloads and return JSON responses.

#### Users
- `POST /api/register/` - Register user by telegram_id

#### Tasks
- `GET /api/tasks/?telegram_id={id}` - Get active tasks
- `POST /api/tasks/create/` - Create new task
- `POST /api/tasks/delete/` - Delete task

#### Tags
- `GET /api/tags/?telegram_id={id}` - Get user tags
- `POST /api/tags/create/` - Create new tag
- `POST /api/tags/delete/` - Delete tag

#### Archive
- `GET /api/archive/?telegram_id={id}` - Get completed/deleted tasks
- `POST /api/clear/` - Clear all user tasks and tags

## Project Structure

```
django_aiogram/
├── backend/
│   ├── config/              # Django settings and configuration
│   │   ├── settings.py
│   │   ├── urls.py
│   │   └── celery.py
│   ├── api/                 # Core application
│   │   ├── models.py        # User, Task, Tag models
│   │   ├── views.py         # API endpoints
│   │   ├── tasks.py         # Celery notification tasks
│   │   └── tests.py         # Test suite
│   ├── manage.py
│   └── requirements.txt
├── bot/
│   ├── main.py              # Bot entry point
│   └── handlers.py          # Bot command handlers and FSM
├── docker-compose.yml       # Service orchestration
├── Dockerfile               # Multi-service container image
└── .env                     # Environment variables
```

## Architecture

### Task Notification System

Tasks with due dates trigger Celery tasks scheduled with ETA (Estimated Time of Arrival). When the scheduled time arrives, the bot sends a notification to the user via Telegram. No polling or periodic checking is required.

### Database Schema

- **User**: `telegram_id` (PK), `username`
- **Tag**: `name`, `user` (FK), unique constraint on `(user, name)`
- **Task**: `title`, `status`, `due_date`, `user` (FK), many-to-many with Tags

### FSM States

The bot uses Finite State Machines for multi-step operations:
- `CreateTaskState`: title → notification_time → tags
- `CreateTagState`: name input

## Testing

Run the test suite:

```bash
docker exec django_aiogram-web-1 python manage.py test api --verbosity=2
```

Test coverage includes:
- Tag operations (create, duplicate check, limits, retrieval, deletion)
- Task operations (create, limits, retrieval, deletion, archiving)
- Notification scheduling (with/without due dates)

## Development

### Services

The application runs as five Docker containers:

- `postgres`: PostgreSQL database with health checks
- `redis`: Celery message broker
- `web`: Django application server
- `celery-worker`: Asynchronous task processor
- `bot`: Telegram bot polling service

### Key Design Decisions

1. **Telegram ID as Primary Key**: Eliminates need for custom user IDs
2. **Plain Status Strings**: Simple 'pending', 'completed', 'deleted' states
3. **ETA-based Scheduling**: Precise notifications without beat scheduler
4. **Single Environment File**: Centralized configuration management
5. **Keyboard UI**: Persistent menu for improved user experience

## License

This project is provided as-is for educational and personal use.
