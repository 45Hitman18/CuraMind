from django.urls import path

from .views import appointments_page, dashboard, doctor_record_file, messages_page, my_reviews_page, profile_page, reports_page, start_review, feedback_page

urlpatterns = [
    path("dashboard/", dashboard, name="doctor_dashboard"),
    path("appointments/", appointments_page, name="doctor_appointments"),
    path("reviews/", my_reviews_page, name="doctor_reviews"),
    path("reports/", reports_page, name="doctor_reports"),
    path("messages/", messages_page, name="doctor_messages"),
    path("profile/", profile_page, name="doctor_profile"),
    path("records/<int:record_id>/review/", start_review, name="doctor_start_review"),
    path("records/<int:record_id>/file/", doctor_record_file, name="doctor_record_file"),
    path("feedback/", feedback_page, name="doctor_feedback"),
]
