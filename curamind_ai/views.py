from django.shortcuts import redirect, render

from accounts.views import role_redirect_for


def landing_page(request):
    if request.user.is_authenticated:
        return role_redirect_for(request.user)
    return render(request, "landing.html")
