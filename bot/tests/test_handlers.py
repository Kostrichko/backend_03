from unittest.mock import ANY, AsyncMock, MagicMock

import pytest
from aiogram.types import Chat, Message, User

from config import (
    MAX_ARCHIVE_TASKS_PER_USER,
    MAX_PENDING_TASKS_PER_USER,
    MAX_TAGS_PER_USER,
)
from handlers.common import cmd_start
from handlers.tasks import cmd_list_tasks


@pytest.mark.asyncio
async def test_cmd_start(mock_api_request):
    # Arrange
    message = AsyncMock(spec=Message)
    message.answer = AsyncMock()
    message.from_user = MagicMock(spec=User)
    message.from_user.id = 123
    message.from_user.username = "testuser"
    mock_api_request.return_value = {"status": "ok"}

    # Act
    await cmd_start(message)

    # Assert
    mock_api_request.assert_called_once_with(
        "POST", "/register/", json={"telegram_id": 123, "username": "testuser"}
    )
    message.answer.assert_called_once()
    args, kwargs = message.answer.call_args
    assert "Бот управления задачами" in args[0]
    assert f"макс. {MAX_TAGS_PER_USER}" in args[0]


@pytest.mark.asyncio
async def test_cmd_list_tasks_empty(mock_api_request):
    # Arrange
    message = AsyncMock(spec=Message)
    message.answer = AsyncMock()
    message.from_user = MagicMock(spec=User)
    message.from_user.id = 123
    mock_api_request.return_value = {"tasks": []}

    # Act
    await cmd_list_tasks(message)

    # Assert
    message.answer.assert_called_once_with("📋 Нет активных задач", reply_markup=ANY)


@pytest.mark.asyncio
async def test_cmd_list_tasks_with_results(mock_api_request):
    # Arrange
    message = AsyncMock(spec=Message)
    message.answer = AsyncMock()
    message.from_user = MagicMock(spec=User)
    message.from_user.id = 123
    mock_api_request.return_value = {
        "tasks": [
            {
                "id": 1,
                "title": "Test Task",
                "tags": ["work"],
                "created_at": "2024-01-01",
                "due_date": "2024-01-02",
            }
        ]
    }

    # Act
    await cmd_list_tasks(message)

    # Assert
    message.answer.assert_called_once()
    text = message.answer.call_args[0][0]
    assert "📋 Задачи" in text
    assert "Test Task" in text
    assert "[work]" in text
