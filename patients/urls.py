from django.urls import path

from .views import appointments_page, dashboard, medical_records_page, messages_page, profile_page, schedule_appointment_page, feedback_page

urlpatterns = [
    path("dashboard/", dashboard, name="patient_dashboard"),
    path("medical-records/", medical_records_page, name="patient_medical_records"),
    path("appointments/", appointments_page, name="patient_appointments"),
    path("appointments/schedule/", schedule_appointment_page, name="patient_schedule_appointment"),
    path("messages/", messages_page, name="patient_messages"),
    path("profile/", profile_page, name="patient_profile"),
    path("feedback/", feedback_page, name="patient_feedback"),
]
