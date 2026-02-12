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
                if response.status >= 400:
                    return {"error": f"HTTP {response.status}"}
                return await response.json()
    except Exception as e:
        return {"error": str(e)}
