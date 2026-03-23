from functools import wraps

from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.http import HttpResponseForbidden


def _role_required(required_role):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path(), login_url=settings.LOGIN_URL)

            if request.user.role != required_role:
                return HttpResponseForbidden("You are not allowed to access this resource.")

            return view_func(request, *args, **kwargs)

        return _wrapped_view

    return decorator


patient_required = _role_required("patient")
doctor_required = _role_required("doctor")
admin_required = _role_required("admin")
