from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage


@pytest.fixture
def bot():
    mock_bot = AsyncMock(spec=Bot)
    mock_bot.id = 123456789
    return mock_bot


@pytest.fixture
def dp():
    return Dispatcher(storage=MemoryStorage())


@pytest.fixture
def mock_api_request(mocker):
    return mocker.patch("services.api_client.api_request", new_callable=AsyncMock)
