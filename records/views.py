import os
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.contrib import messages
from django.shortcuts import redirect, render

from accounts.decorators import patient_required
from patients.models import ChatMessage

from .forms import MedicalRecordUploadForm
from .models import MedicalRecord


@patient_required
def upload_scan(request):
	if request.method == "POST":
		form = MedicalRecordUploadForm(request.POST, request.FILES)
		if form.is_valid():
			medical_record = form.save(commit=False)
			medical_record.patient = request.user
			medical_record.save()

			messages.success(request, "Scan uploaded successfully.")
			return redirect("patient_dashboard")
	else:
		form = MedicalRecordUploadForm()

	context = {
		"form": form,
		"unread_messages_count": ChatMessage.objects.filter(recipient=request.user, is_read=False).count(),
	}

	return render(request, "records/upload_scan.html", context)


@patient_required
def medical_record_file(request, record_id):
	medical_record = get_object_or_404(MedicalRecord, id=record_id, patient=request.user)
	return FileResponse(medical_record.uploaded_file.open("rb"), as_attachment=False)

@patient_required
def patient_view_report(request, record_id):
	medical_record = get_object_or_404(MedicalRecord, id=record_id, patient=request.user)
	
	file_extension = os.path.splitext(medical_record.uploaded_file.name)[1].lower()
	is_image_file = file_extension in {".jpg", ".jpeg", ".png", ".gif", ".webp"}
	is_pdf_file = file_extension == ".pdf"
	
	context = {
		"record": medical_record,
		"is_image_file": is_image_file,
		"is_pdf_file": is_pdf_file,
		"file_extension": file_extension,
	}
	return render(request, "records/patient_view_report.html", context)
