from django.urls import include, path

from .views import register

urlpatterns = [
    path("register/", register, name="register"),
    path("", include("django.contrib.auth.urls")),
]
