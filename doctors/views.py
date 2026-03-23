import os

from django.http import FileResponse
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.contrib.auth import get_user_model

from accounts.decorators import doctor_required
from appointments.models import Appointment
from records.models import MedicalRecord
from patients.models import ChatMessage
from audit.models import AuditLog
from .models import DoctorProfile


def _assigned_patient_ids(doctor_user):
	return Appointment.objects.filter(doctor=doctor_user).values_list("patient_id", flat=True)


def _doctor_unread_messages_count(doctor_user):
	return ChatMessage.objects.filter(recipient=doctor_user, is_read=False).count()


def _doctor_pending_appointments_count(doctor_user):
	return Appointment.objects.filter(doctor=doctor_user, status=Appointment.Status.PENDING).count()


def _ai_confidence_score(record):
	if record.ai_status == MedicalRecord.AIStatus.HIGH:
		return 97
	if record.ai_status == MedicalRecord.AIStatus.MEDIUM:
		return 86
	if record.ai_status == MedicalRecord.AIStatus.LOW:
		return 74
	if record.ai_status == MedicalRecord.AIStatus.COMPLETE:
		return 80
	return 65


def _ai_findings(record):
	scan_label = record.scan_type or "Scan"
	if record.ai_status == MedicalRecord.AIStatus.HIGH:
		return [
			{
				"title": f"High-risk pattern detected in {scan_label}",
				"severity": "critical",
				"summary": "AI has flagged this scan as high priority. Immediate clinician verification is recommended.",
			},
			{
				"title": "Detailed manual confirmation required",
				"severity": "moderate",
				"summary": "Cross-check lesion boundaries, adjacent structures, and any motion artifacts before finalization.",
			},
		]
	if record.ai_status == MedicalRecord.AIStatus.MEDIUM:
		return [
			{
				"title": f"Moderate anomaly indicators in {scan_label}",
				"severity": "moderate",
				"summary": "Potential abnormal findings detected. Correlate with patient history and prior studies.",
			},
		]
	if record.ai_status == MedicalRecord.AIStatus.LOW:
		return [
			{
				"title": f"Low-risk review for {scan_label}",
				"severity": "neutral",
				"summary": "No strong anomaly signal detected by AI. Proceed with standard diagnostic validation.",
			},
		]
	return [
		{
			"title": "AI processing details",
			"severity": "neutral",
			"summary": "Scan is still in upload/processing pipeline. Final AI flags may update shortly.",
		},
	]


@doctor_required
def dashboard(request):
	patient_ids = _assigned_patient_ids(request.user)
	assigned_records = MedicalRecord.objects.filter(patient_id__in=patient_ids).select_related("patient")

	pending_records = assigned_records.filter(
		review_status__in=[MedicalRecord.ReviewStatus.READY, MedicalRecord.ReviewStatus.IN_PROGRESS]
	)
	urgent_cases_count = assigned_records.filter(ai_status=MedicalRecord.AIStatus.HIGH).count()
	completed_today_count = assigned_records.filter(
		reviewed_by=request.user,
		review_status=MedicalRecord.ReviewStatus.COMPLETED,
		reviewed_at__date=timezone.localdate(),
	).count()
	recent_diagnoses = assigned_records.filter(
		reviewed_by=request.user,
		review_status=MedicalRecord.ReviewStatus.COMPLETED,
		reviewed_at__isnull=False,
	).order_by("-reviewed_at")[:5]
	doctor_specialization = getattr(getattr(request.user, "doctor_profile", None), "specialization", "Radiologist")

	context = {
		"assigned_records": pending_records,
		"pending_count": pending_records.count(),
		"total_assigned_count": assigned_records.count(),
		"urgent_cases_count": urgent_cases_count,
		"completed_today_count": completed_today_count,
		"recent_diagnoses": recent_diagnoses,
		"doctor_specialization": doctor_specialization,
		"unread_doctor_messages_count": _doctor_unread_messages_count(request.user),
		"pending_appointments_count": _doctor_pending_appointments_count(request.user),
	}
	return render(request, "doctors/dashboard.html", context)


@doctor_required
def start_review(request, record_id):
	patient_ids = _assigned_patient_ids(request.user)
	medical_record = get_object_or_404(
		MedicalRecord.objects.select_related("patient", "patient__patient_profile"),
		id=record_id,
		patient_id__in=patient_ids,
	)

	if medical_record.review_status == MedicalRecord.ReviewStatus.READY:
		medical_record.review_status = MedicalRecord.ReviewStatus.IN_PROGRESS
		medical_record.reviewed_by = request.user
		medical_record.reviewed_at = timezone.now()
		medical_record.save(update_fields=["review_status", "reviewed_by", "reviewed_at"])

	if request.method == "POST":
		action = request.POST.get("action")
		notes = request.POST.get("doctor_notes", "").strip()

		if action in {"save_notes", "finalize"}:
			update_fields = ["doctor_notes"]
			medical_record.doctor_notes = notes

			if action == "finalize":
				medical_record.review_status = MedicalRecord.ReviewStatus.COMPLETED
				medical_record.reviewed_by = request.user
				medical_record.reviewed_at = timezone.now()
				update_fields.extend(["review_status", "reviewed_by", "reviewed_at"])
				messages.success(request, "Review finalized and approved successfully.")
				AuditLog.objects.create(
					user=request.user,
					action="FINALIZE_REVIEW",
					object_type="MedicalRecord",
					object_id=str(medical_record.id),
					ip_address=request.META.get("REMOTE_ADDR"),
				)
			else:
				messages.success(request, "Review notes saved.")
				AuditLog.objects.create(
					user=request.user,
					action="SAVE_REVIEW_NOTES",
					object_type="MedicalRecord",
					object_id=str(medical_record.id),
					ip_address=request.META.get("REMOTE_ADDR"),
				)

			medical_record.save(update_fields=list(dict.fromkeys(update_fields)))
			return redirect("doctor_start_review", record_id=medical_record.id)

		if action == "request_peer_review":
			AuditLog.objects.create(
				user=request.user,
				action="REQUEST_PEER_REVIEW",
				object_type="MedicalRecord",
				object_id=str(medical_record.id),
				ip_address=request.META.get("REMOTE_ADDR"),
			)
			messages.success(request, "Peer review request has been logged.")
			return redirect("doctor_start_review", record_id=medical_record.id)

	patient_profile = getattr(medical_record.patient, "patient_profile", None)
	patient_age = None
	if patient_profile and patient_profile.date_of_birth:
		today = timezone.localdate()
		dob = patient_profile.date_of_birth
		patient_age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

	previous_scans = MedicalRecord.objects.filter(patient=medical_record.patient).exclude(id=medical_record.id).order_by("-created_at")[:4]
	patient_appointments = Appointment.objects.filter(patient=medical_record.patient, doctor=request.user).count()
	file_extension = os.path.splitext(medical_record.uploaded_file.name)[1].lower()
	is_image_file = file_extension in {".jpg", ".jpeg", ".png", ".gif", ".webp"}
	is_pdf_file = file_extension == ".pdf"

	doctor_specialization = getattr(getattr(request.user, "doctor_profile", None), "specialization", "Radiologist")
	context = {
		"record": medical_record,
		"patient_profile": patient_profile,
		"patient_age": patient_age,
		"previous_scans": previous_scans,
		"patient_appointments": patient_appointments,
		"is_image_file": is_image_file,
		"is_pdf_file": is_pdf_file,
		"file_extension": file_extension,
		"ai_confidence": _ai_confidence_score(medical_record),
		"ai_findings": _ai_findings(medical_record),
		"doctor_specialization": doctor_specialization,
		"unread_doctor_messages_count": _doctor_unread_messages_count(request.user),
		"pending_appointments_count": _doctor_pending_appointments_count(request.user),
	}

	return render(request, "doctors/review_record.html", context)


@doctor_required
def doctor_record_file(request, record_id):
	patient_ids = _assigned_patient_ids(request.user)
	medical_record = get_object_or_404(
		MedicalRecord,
		id=record_id,
		patient_id__in=patient_ids,
	)
	return FileResponse(medical_record.uploaded_file.open("rb"), as_attachment=False)


@doctor_required
def appointments_page(request):
	status_view = request.GET.get("status", "pending")
	valid_views = {"pending", "approved", "history"}
	if status_view not in valid_views:
		status_view = "pending"

	if request.method == "POST":
		action = request.POST.get("action")
		appointment_id = request.POST.get("appointment_id")
		appointment = get_object_or_404(Appointment, id=appointment_id, doctor=request.user)
		if action == "approve" and appointment.status == Appointment.Status.PENDING:
			appointment.status = Appointment.Status.APPROVED
			appointment.save(update_fields=["status"])
			messages.success(request, "Appointment approved.")
		elif action == "reject" and appointment.status == Appointment.Status.PENDING:
			appointment.status = Appointment.Status.REJECTED
			appointment.save(update_fields=["status"])
			messages.success(request, "Appointment rejected.")
		return redirect(f"{request.path}?status={status_view}")

	doctor_appointments = Appointment.objects.filter(doctor=request.user).select_related("patient")

	pending_appointments = doctor_appointments.filter(status=Appointment.Status.PENDING).order_by("datetime")
	approved_appointments = doctor_appointments.filter(
		status__in=[Appointment.Status.APPROVED, Appointment.Status.SCHEDULED]
	).order_by("datetime")
	history_appointments = doctor_appointments.filter(
		status__in=[Appointment.Status.REJECTED, Appointment.Status.CANCELLED, Appointment.Status.COMPLETED]
	).order_by("-datetime")

	if status_view == "approved":
		appointments = approved_appointments
	elif status_view == "history":
		appointments = history_appointments
	else:
		appointments = pending_appointments

	selected_appointment_id = request.GET.get("appointment")
	selected_appointment = None
	if selected_appointment_id:
		selected_appointment = appointments.filter(id=selected_appointment_id).first()
	if selected_appointment is None:
		selected_appointment = appointments.first()

	doctor_specialization = getattr(getattr(request.user, "doctor_profile", None), "specialization", "Radiologist")
	context = {
		"status_view": status_view,
		"appointments": appointments,
		"selected_appointment": selected_appointment,
		"pending_count": pending_appointments.count(),
		"approved_count": approved_appointments.count(),
		"history_count": history_appointments.count(),
		"doctor_specialization": doctor_specialization,
		"unread_doctor_messages_count": _doctor_unread_messages_count(request.user),
		"pending_appointments_count": pending_appointments.count(),
	}
	return render(request, "doctors/appointments.html", context)


@doctor_required
def my_reviews_page(request):
	patient_ids = _assigned_patient_ids(request.user)
	review_status = request.GET.get("status", "all")
	valid_statuses = {"all", "completed", "in_progress"}
	if review_status not in valid_statuses:
		review_status = "all"

	review_records = MedicalRecord.objects.filter(
		patient_id__in=patient_ids,
		reviewed_by=request.user,
	).select_related("patient")

	if review_status == "completed":
		review_records = review_records.filter(review_status=MedicalRecord.ReviewStatus.COMPLETED)
	elif review_status == "in_progress":
		review_records = review_records.filter(review_status=MedicalRecord.ReviewStatus.IN_PROGRESS)

	review_records = review_records.order_by("-reviewed_at", "-created_at")

	selected_record_id = request.GET.get("record")
	selected_record = None
	if selected_record_id:
		selected_record = review_records.filter(id=selected_record_id).first()
	if selected_record is None:
		selected_record = review_records.first()

	all_review_records = MedicalRecord.objects.filter(
		patient_id__in=patient_ids,
		reviewed_by=request.user,
	)

	total_reviews_count = all_review_records.count()
	completed_reviews_count = all_review_records.filter(
		review_status=MedicalRecord.ReviewStatus.COMPLETED
	).count()
	in_progress_reviews_count = all_review_records.filter(
		review_status=MedicalRecord.ReviewStatus.IN_PROGRESS
	).count()
	reviewed_today_count = all_review_records.filter(
		reviewed_at__date=timezone.localdate(),
	).count()

	doctor_specialization = getattr(getattr(request.user, "doctor_profile", None), "specialization", "Radiologist")
	context = {
		"review_records": review_records,
		"selected_record": selected_record,
		"status_view": review_status,
		"total_reviews_count": total_reviews_count,
		"completed_reviews_count": completed_reviews_count,
		"in_progress_reviews_count": in_progress_reviews_count,
		"reviewed_today_count": reviewed_today_count,
		"doctor_specialization": doctor_specialization,
		"unread_doctor_messages_count": _doctor_unread_messages_count(request.user),
		"pending_appointments_count": _doctor_pending_appointments_count(request.user),
	}
	return render(request, "doctors/my_reviews.html", context)


@doctor_required
def reports_page(request):
	now = timezone.now()
	period = request.GET.get("period", "30d")
	valid_periods = {"24h", "7d", "30d"}
	if period not in valid_periods:
		period = "30d"

	if period == "24h":
		since = now - timezone.timedelta(hours=24)
		previous_since = since - timezone.timedelta(hours=24)
	elif period == "7d":
		since = now - timezone.timedelta(days=7)
		previous_since = since - timezone.timedelta(days=7)
	else:
		since = now - timezone.timedelta(days=30)
		previous_since = since - timezone.timedelta(days=30)

	patient_ids = _assigned_patient_ids(request.user)
	doctor_records_all = MedicalRecord.objects.filter(patient_id__in=patient_ids)
	doctor_records_period = doctor_records_all.filter(created_at__gte=since)
	doctor_reviewed_all = doctor_records_all.filter(reviewed_by=request.user)
	doctor_reviewed_period = doctor_reviewed_all.filter(reviewed_at__gte=since)

	appointments_all = Appointment.objects.filter(doctor=request.user)
	appointments_period = appointments_all.filter(datetime__gte=since)

	total_records_processed = doctor_records_period.count()
	total_reviews_done = doctor_reviewed_period.count()
	appointments_handled = appointments_period.count()

	previous_records_count = doctor_records_all.filter(created_at__gte=previous_since, created_at__lt=since).count()
	if previous_records_count:
		throughput_growth = round(((total_records_processed - previous_records_count) / previous_records_count) * 100, 1)
	else:
		throughput_growth = 100.0 if total_records_processed else 0.0

	completed_reviews = doctor_reviewed_period.filter(
		review_status=MedicalRecord.ReviewStatus.COMPLETED
	).count()
	review_completion_rate = int((completed_reviews / total_reviews_done) * 100) if total_reviews_done else 0

	high_cases = doctor_records_period.filter(ai_status=MedicalRecord.AIStatus.HIGH).count()
	medium_cases = doctor_records_period.filter(ai_status=MedicalRecord.AIStatus.MEDIUM).count()
	low_cases = doctor_records_period.filter(ai_status=MedicalRecord.AIStatus.LOW).count()
	total_categorized_cases = high_cases + medium_cases + low_cases
	ai_confidence_score = int((((low_cases * 100) + (medium_cases * 80) + (high_cases * 60)) / total_categorized_cases)) if total_categorized_cases else 0

	approved_count = appointments_period.filter(
		status__in=[Appointment.Status.APPROVED, Appointment.Status.SCHEDULED]
	).count()
	rejected_count = appointments_period.filter(status=Appointment.Status.REJECTED).count()
	completed_appointments_count = appointments_period.filter(status=Appointment.Status.COMPLETED).count()
	pending_count = appointments_period.filter(status=Appointment.Status.PENDING).count()

	total_appointment_decisions = approved_count + rejected_count + completed_appointments_count
	approval_rate = int((approved_count / total_appointment_decisions) * 100) if total_appointment_decisions else 0

	department_efficiency = [
		{
			"name": "MRI (Magnetic Resonance)",
			"count": doctor_records_period.filter(scan_type__icontains="mri").count(),
		},
		{
			"name": "CT Scans (Tomography)",
			"count": doctor_records_period.filter(scan_type__icontains="ct").count(),
		},
		{
			"name": "X-Ray (Computed Radiography)",
			"count": doctor_records_period.filter(scan_type__icontains="x").count(),
		},
	]
	max_department_count = max([item["count"] for item in department_efficiency], default=0)
	for item in department_efficiency:
		item["percent"] = int((item["count"] / max_department_count) * 100) if max_department_count else 0

	day_bucket_count = 7 if period in {"7d", "30d"} else 1
	if period == "30d":
		day_bucket_count = 10

	trend_data = []
	for index in range(day_bucket_count):
		if period == "24h":
			bucket_start = now - timezone.timedelta(hours=24)
			bucket_end = now
			label = "Last 24h"
		else:
			total_days = 7 if period == "7d" else 30
			window_size = max(1, total_days // day_bucket_count)
			bucket_start = (now - timezone.timedelta(days=total_days)) + timezone.timedelta(days=index * window_size)
			bucket_end = bucket_start + timezone.timedelta(days=window_size)
			label = bucket_end.strftime("%b %d")

		review_count = doctor_reviewed_all.filter(reviewed_at__gte=bucket_start, reviewed_at__lt=bucket_end).count()
		appointment_count = appointments_all.filter(datetime__gte=bucket_start, datetime__lt=bucket_end).count()
		trend_data.append(
			{
				"label": label,
				"reviews": review_count,
				"appointments": appointment_count,
				"total": review_count + appointment_count,
			}
		)

	max_trend_total = max((point["total"] for point in trend_data), default=0)

	audit_events = AuditLog.objects.filter(user=request.user, timestamp__gte=since).order_by("-timestamp")[:8]

	doctor_specialization = getattr(getattr(request.user, "doctor_profile", None), "specialization", "Radiologist")
	context = {
		"period": period,
		"total_records_processed": total_records_processed,
		"throughput_growth": throughput_growth,
		"total_reviews_done": total_reviews_done,
		"appointments_handled": appointments_handled,
		"review_completion_rate": review_completion_rate,
		"ai_confidence_score": ai_confidence_score,
		"high_cases": high_cases,
		"medium_cases": medium_cases,
		"low_cases": low_cases,
		"approved_count": approved_count,
		"rejected_count": rejected_count,
		"completed_appointments_count": completed_appointments_count,
		"pending_count": pending_count,
		"approval_rate": approval_rate,
		"department_efficiency": department_efficiency,
		"trend_data": trend_data,
		"max_trend_total": max_trend_total,
		"audit_events": audit_events,
		"doctor_specialization": doctor_specialization,
		"unread_doctor_messages_count": _doctor_unread_messages_count(request.user),
		"pending_appointments_count": _doctor_pending_appointments_count(request.user),
	}
	return render(request, "doctors/reports.html", context)


@doctor_required
def profile_page(request):
	doctor_profile = getattr(request.user, "doctor_profile", None)

	if request.method == "POST":
		has_error = False
		first_name = request.POST.get("first_name", "").strip()
		last_name = request.POST.get("last_name", "").strip()
		email = request.POST.get("email", "").strip()
		specialization = request.POST.get("specialization", "").strip()
		license_id = request.POST.get("license_id", "").strip()

		request.user.first_name = first_name
		request.user.last_name = last_name
		request.user.email = email
		request.user.save(update_fields=["first_name", "last_name", "email"])

		if doctor_profile and specialization and license_id:
			duplicate_license = DoctorProfile.objects.exclude(user=request.user).filter(license_id=license_id).exists()
			if duplicate_license:
				has_error = True
				messages.error(request, "License ID is already in use by another doctor.")
			else:
				doctor_profile.specialization = specialization
				doctor_profile.license_id = license_id
				doctor_profile.save(update_fields=["specialization", "license_id"])
		elif doctor_profile and (specialization or license_id):
			has_error = True
			messages.error(request, "Both specialization and license ID are required to update doctor details.")
		elif not doctor_profile and (specialization or license_id):
			has_error = True
			messages.error(request, "Doctor profile details are not initialized for this account yet.")

		if not has_error:
			messages.success(request, "Profile updated successfully.")

		return redirect("doctor_profile")

	doctor_specialization = getattr(doctor_profile, "specialization", "Not set")
	context = {
		"doctor_profile": doctor_profile,
		"doctor_specialization": doctor_specialization,
		"unread_doctor_messages_count": _doctor_unread_messages_count(request.user),
		"pending_appointments_count": _doctor_pending_appointments_count(request.user),
		"records_reviewed_count": MedicalRecord.objects.filter(reviewed_by=request.user).count(),
		"last_login": request.user.last_login,
	}
	return render(request, "doctors/profile.html", context)


@doctor_required
def messages_page(request):
	user_model = get_user_model()
	registered_patients = user_model.objects.filter(
		role=user_model.Role.PATIENT,
		is_active=True,
		email__isnull=False,
	).exclude(
		email__exact="",
	).order_by("username").distinct()

	selected_patient_id = request.POST.get("patient_id") or request.GET.get("patient")
	selected_patient = None
	if selected_patient_id:
		selected_patient = registered_patients.filter(id=selected_patient_id).first()
	if selected_patient is None:
		selected_patient = registered_patients.first()

	if request.method == "POST" and selected_patient:
		body = request.POST.get("body", "").strip()
		attachment = request.FILES.get("attachment")
		if body or attachment:
			ChatMessage.objects.create(
				patient=selected_patient,
				doctor=request.user,
				sender=request.user,
				recipient=selected_patient,
				body=body,
				attachment=attachment,
				is_read=False,
			)
			return redirect(f"{request.path}?patient={selected_patient.id}")

	thread_messages = ChatMessage.objects.none()
	if selected_patient:
		thread_messages = ChatMessage.objects.filter(
			patient=selected_patient,
			doctor=request.user,
		).select_related("sender", "recipient")
		thread_messages.filter(recipient=request.user, is_read=False).update(is_read=True)

	patient_conversations = []
	for patient in registered_patients:
		conversation_messages = ChatMessage.objects.filter(patient=patient, doctor=request.user)
		patient_conversations.append(
			{
				"patient": patient,
				"last_message": conversation_messages.order_by("-created_at").first(),
				"unread_count": conversation_messages.filter(recipient=request.user, is_read=False).count(),
			}
		)

	doctor_specialization = getattr(getattr(request.user, "doctor_profile", None), "specialization", "Radiologist")
	context = {
		"registered_patients": registered_patients,
		"selected_patient": selected_patient,
		"thread_messages": thread_messages,
		"patient_conversations": patient_conversations,
		"doctor_specialization": doctor_specialization,
		"unread_doctor_messages_count": _doctor_unread_messages_count(request.user),
		"pending_appointments_count": _doctor_pending_appointments_count(request.user),
	}
	return render(request, "doctors/messages.html", context)


@doctor_required
def feedback_page(request):
	from patients.models import Feedback
	feedbacks = Feedback.objects.filter(doctor=request.user).select_related("patient").order_by("-created_at")
	
	doctor_specialization = getattr(getattr(request.user, "doctor_profile", None), "specialization", "Radiologist")
	context = {
		"feedbacks": feedbacks,
		"doctor_specialization": doctor_specialization,
		"unread_doctor_messages_count": _doctor_unread_messages_count(request.user),
		"pending_appointments_count": _doctor_pending_appointments_count(request.user),
	}
	return render(request, "doctors/feedback.html", context)
