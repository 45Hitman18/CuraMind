from django.urls import include, path

from .views import register, mark_notifications_read

urlpatterns = [
    path("register/", register, name="register"),
    path("notifications/read/", mark_notifications_read, name="mark_notifications_read"),
    path("", include("django.contrib.auth.urls")),
]
