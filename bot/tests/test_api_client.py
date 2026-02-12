from unittest.mock import AsyncMock, MagicMock

import aiohttp
import pytest
from config import API_KEY, API_URL
from services.api_client import api_request


@pytest.mark.asyncio
async def test_api_request_success(mocker):
    # Arrange
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={"data": "test"})

    mock_ctx = MagicMock()
    mock_ctx.__aenter__.return_value = mock_response

    # Mocking ClientSession.request
    mocker.patch("aiohttp.ClientSession.request", return_value=mock_ctx)

    # Act
    result = await api_request("GET", "/test/")

    # Assert
    assert result == {"data": "test"}


@pytest.mark.asyncio
async def test_api_request_error(mocker):
    # Arrange
    mock_response = AsyncMock()
    mock_response.status = 400

    mock_ctx = MagicMock()
    mock_ctx.__aenter__.return_value = mock_response

    mocker.patch("aiohttp.ClientSession.request", return_value=mock_ctx)

    # Act
    result = await api_request("GET", "/test/")

    # Assert
    assert "error" in result
    assert "HTTP 400" in result["error"]
