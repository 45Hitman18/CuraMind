from django.urls import path

from .views import admin_overview, admin_settings, system_logs, user_management, admin_feedback_page

urlpatterns = [
    path("", admin_overview, name="admin_overview"),
    path("users/", user_management, name="admin_user_management"),
    path("logs/", system_logs, name="admin_system_logs"),
    path("settings/", admin_settings, name="admin_settings"),
    path("feedback/", admin_feedback_page, name="admin_feedback"),
]
