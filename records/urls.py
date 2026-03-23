from django.urls import path

from .views import medical_record_file, upload_scan

urlpatterns = [
    path("upload/", upload_scan, name="upload_scan"),
    path("<int:record_id>/file/", medical_record_file, name="medical_record_file"),
]
