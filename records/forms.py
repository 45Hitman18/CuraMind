from django import forms

from .models import MedicalRecord


class MedicalRecordUploadForm(forms.ModelForm):
    class Meta:
        model = MedicalRecord
        fields = ("uploaded_file", "scan_type")

    def clean_uploaded_file(self):
        uploaded_file = self.cleaned_data["uploaded_file"]
        allowed_extensions = {".dcm", ".dicom", ".pdf", ".jpg", ".jpeg", ".png"}
        file_name = uploaded_file.name.lower()
        if not any(file_name.endswith(ext) for ext in allowed_extensions):
            raise forms.ValidationError("Unsupported file type.")
        return uploaded_file
