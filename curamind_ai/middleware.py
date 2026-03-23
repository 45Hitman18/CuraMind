from django.conf import settings
from django.contrib.auth.views import redirect_to_login


class LoginRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            return self.get_response(request)

        path = request.path
        login_url = settings.LOGIN_URL
        exempt_paths = {
            "/",
            "/accounts/register/",
        }

        if path in exempt_paths:
            return self.get_response(request)

        exempt_prefixes = [
            "/admin/",
            login_url,
            getattr(settings, "STATIC_URL", ""),
            getattr(settings, "MEDIA_URL", ""),
        ]

        if any(prefix and path.startswith(prefix) for prefix in exempt_prefixes):
            return self.get_response(request)

        return redirect_to_login(request.get_full_path(), login_url=login_url)