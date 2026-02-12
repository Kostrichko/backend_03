import aiohttp

from config import API_KEY, API_URL


async def api_request(method, endpoint, **kwargs):
    url = f"{API_URL}{endpoint}"
    headers = kwargs.get("headers", {})
    headers["X-API-Key"] = API_KEY
    kwargs["headers"] = headers
    try:
        async with aiohttp.ClientSession() as session:
            async with session.request(method, url, **kwargs) as response:
                data = await response.json()
                if response.status >= 400:
                    error_msg = (
                        data.get("error", f"HTTP {response.status}")
                        if isinstance(data, dict)
                        else f"HTTP {response.status}"
                    )
                    return {"error": error_msg}
                return data
    except aiohttp.ContentTypeError:
        return {"error": "Некорректный ответ сервера"}
    except aiohttp.ClientError as e:
        return {"error": f"Ошибка соединения: {e}"}
    except Exception as e:
        return {"error": str(e)}
