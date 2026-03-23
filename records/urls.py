from django.urls import path

from .views import medical_record_file, upload_scan, patient_view_report

urlpatterns = [
    path("upload/", upload_scan, name="upload_scan"),
    path("<int:record_id>/report/", patient_view_report, name="patient_view_report"),
    path("<int:record_id>/file/", medical_record_file, name="medical_record_file"),
]
