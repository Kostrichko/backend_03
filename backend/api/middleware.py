from django.http import JsonResponse
from django.conf import settings


class APIKeyMiddleware:
    """
    Middleware to validate API key in request headers.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Skip API key check for admin and static files
        if request.path.startswith('/admin/') or request.path.startswith('/static/'):
            return self.get_response(request)

        # Check API key in headers
        api_key = request.headers.get('X-API-Key')
        if not api_key or api_key != settings.API_KEY:
            return JsonResponse({'error': 'Invalid API key'}, status=401)

        return self.get_response(request)