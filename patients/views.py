from django.contrib.auth import get_user_model
from django.contrib import messages
from django.db.models import Count
from django.shortcuts import redirect, render
from django.utils import timezone
from datetime import datetime, timedelta

from accounts.decorators import patient_required
from appointments.models import Appointment
from records.models import MedicalRecord

from .models import ChatMessage, PatientProfile


def _patient_base_context(user):
	medical_records = MedicalRecord.objects.filter(patient=user)
	now = timezone.now()
	upcoming_appointments = (
		Appointment.objects.filter(
			patient=user,
			datetime__gte=now,
			status__in=[
				Appointment.Status.PENDING,
				Appointment.Status.APPROVED,
				Appointment.Status.SCHEDULED,
			],
		)
		.select_related("doctor")
		.order_by("datetime")
	)

	return {
		"medical_records": medical_records,
		"upcoming_appointment": upcoming_appointments.first(),
		"upcoming_appointments": upcoming_appointments[:2],
		"unread_messages_count": ChatMessage.objects.filter(recipient=user, is_read=False).count(),
		"pending_scans_count": medical_records.filter(
			ai_status__in=[MedicalRecord.AIStatus.UPLOADED, MedicalRecord.AIStatus.PROCESSING]
		).count(),
		"total_records": medical_records.count(),
		"recent_scans_30d": medical_records.filter(created_at__gte=now - timedelta(days=30)).count(),
		"ai_anomalies_count": medical_records.filter(
			ai_status__in=[MedicalRecord.AIStatus.HIGH, MedicalRecord.AIStatus.MEDIUM]
		).count(),
	}


@patient_required
def dashboard(request):
	context = _patient_base_context(request.user)
	return render(request, "patients/dashboard.html", context)


@patient_required
def medical_records_page(request):
	context = _patient_base_context(request.user)
	return render(request, "patients/medical_records.html", context)


@patient_required
def appointments_page(request):
	now = timezone.now()
	appointments = (
		Appointment.objects.filter(patient=request.user)
		.select_related("doctor")
		.order_by("datetime")
	)

	context = _patient_base_context(request.user)
	context.update(
		{
			"upcoming_patient_appointments": appointments.filter(
				datetime__gte=now,
				status__in=[
					Appointment.Status.PENDING,
					Appointment.Status.APPROVED,
					Appointment.Status.SCHEDULED,
				],
			),
			"past_patient_appointments": appointments.exclude(
				status__in=[
					Appointment.Status.PENDING,
					Appointment.Status.APPROVED,
					Appointment.Status.SCHEDULED,
				]
			).order_by("-datetime"),
		}
	)
	return render(request, "patients/appointments.html", context)


@patient_required
def schedule_appointment_page(request):
	user_model = get_user_model()
	registered_doctors = user_model.objects.filter(
		role=user_model.Role.DOCTOR,
		is_active=True,
		email__isnull=False,
	).exclude(
		email__exact="",
	).select_related("doctor_profile").order_by("username").distinct()

	time_slot_values = ["09:00", "10:30", "13:00", "14:30", "16:00", "17:30"]
	now = timezone.localtime()
	selected_date = timezone.localdate()
	selected_doctor = None
	selected_doctor_id = request.POST.get("doctor_id") or request.GET.get("doctor")
	selected_date_input = request.POST.get("appointment_date") or request.GET.get("date")

	if selected_date_input:
		try:
			selected_date = datetime.strptime(selected_date_input, "%Y-%m-%d").date()
		except ValueError:
			messages.error(request, "Invalid date selected.")
			selected_date = timezone.localdate()

	if selected_doctor_id:
		selected_doctor = registered_doctors.filter(id=selected_doctor_id).first()
	if selected_doctor is None:
		selected_doctor = registered_doctors.first()

	booked_by_doctor = {
		item["doctor_id"]: item["total"]
		for item in Appointment.objects.filter(
			doctor__in=registered_doctors,
			datetime__date=selected_date,
			status__in=[
				Appointment.Status.PENDING,
				Appointment.Status.APPROVED,
				Appointment.Status.SCHEDULED,
			],
		)
		.values("doctor_id")
		.annotate(total=Count("id"))
	}

	available_doctors = []
	for doctor in registered_doctors:
		available_slots_count = 0
		for slot in time_slot_values:
			slot_hour, slot_minute = map(int, slot.split(":"))
			slot_datetime = timezone.make_aware(
				datetime.combine(selected_date, datetime.min.time().replace(hour=slot_hour, minute=slot_minute)),
			)
			if slot_datetime <= now:
				continue
			if not Appointment.objects.filter(
				doctor=doctor,
				datetime=slot_datetime,
				status__in=[
					Appointment.Status.PENDING,
					Appointment.Status.APPROVED,
					Appointment.Status.SCHEDULED,
				],
			).exists():
				available_slots_count += 1

		available_doctors.append(
			{
				"user": doctor,
				"specialization": getattr(getattr(doctor, "doctor_profile", None), "specialization", "General Specialist"),
				"available_slots_count": available_slots_count,
				"booked_slots_count": booked_by_doctor.get(doctor.id, 0),
			}
		)

	available_slots = []
	if selected_doctor:
		for slot in time_slot_values:
			slot_hour, slot_minute = map(int, slot.split(":"))
			slot_datetime = timezone.make_aware(
				datetime.combine(selected_date, datetime.min.time().replace(hour=slot_hour, minute=slot_minute)),
			)
			is_available = slot_datetime > now and not Appointment.objects.filter(
				doctor=selected_doctor,
				datetime=slot_datetime,
				status__in=[
					Appointment.Status.PENDING,
					Appointment.Status.APPROVED,
					Appointment.Status.SCHEDULED,
				],
			).exists()
			available_slots.append(
				{
					"value": slot,
					"label": slot_datetime.strftime("%I:%M %p"),
					"is_available": is_available,
				}
			)

	if request.method == "POST":
		appointment_time = request.POST.get("appointment_time")
		reason = request.POST.get("reason", "").strip()
		insurance_provider = request.POST.get("insurance", "").strip()
		patient_notes = request.POST.get("notes", "").strip()
		if not selected_doctor:
			messages.error(request, "Please select a doctor.")
		elif not appointment_time:
			messages.error(request, "Please choose an available time slot.")
		else:
			try:
				time_hour, time_minute = map(int, appointment_time.split(":"))
				appointment_datetime = timezone.make_aware(
					datetime.combine(selected_date, datetime.min.time().replace(hour=time_hour, minute=time_minute)),
				)
			except (TypeError, ValueError):
				messages.error(request, "Invalid time selected.")
			else:
				if appointment_datetime <= now:
					messages.error(request, "Please choose a future date and time.")
				elif Appointment.objects.filter(
					doctor=selected_doctor,
					datetime=appointment_datetime,
					status__in=[
						Appointment.Status.PENDING,
						Appointment.Status.APPROVED,
						Appointment.Status.SCHEDULED,
					],
				).exists():
					messages.error(request, "This time slot was just booked. Please choose another slot.")
				else:
					Appointment.objects.create(
						patient=request.user,
						doctor=selected_doctor,
						datetime=appointment_datetime,
						status=Appointment.Status.PENDING,
						reason=reason,
						insurance_provider=insurance_provider,
						patient_notes=patient_notes,
					)
					messages.success(request, "Appointment request sent. Waiting for doctor approval.")
					return redirect("patient_appointments")

	context = _patient_base_context(request.user)
	context.update(
		{
			"available_doctors": available_doctors,
			"selected_doctor": selected_doctor,
			"selected_date": selected_date.isoformat(),
			"available_slots": available_slots,
		}
	)
	return render(request, "patients/schedule_appointment.html", context)


@patient_required
def messages_page(request):
	user_model = get_user_model()
	registered_doctors = user_model.objects.filter(
		role=user_model.Role.DOCTOR,
		is_active=True,
		email__isnull=False,
	).exclude(
		email__exact="",
	).order_by("username").distinct()

	selected_doctor_id = request.POST.get("doctor_id") or request.GET.get("doctor")
	selected_doctor = None
	if selected_doctor_id:
		selected_doctor = registered_doctors.filter(id=selected_doctor_id).first()
	if selected_doctor is None:
		selected_doctor = registered_doctors.first()

	if request.method == "POST" and selected_doctor:
		body = request.POST.get("body", "").strip()
		attachment = request.FILES.get("attachment")
		if body or attachment:
			ChatMessage.objects.create(
				patient=request.user,
				doctor=selected_doctor,
				sender=request.user,
				recipient=selected_doctor,
				body=body,
				attachment=attachment,
				is_read=False,
			)
			return redirect(f"{request.path}?doctor={selected_doctor.id}")

	thread_messages = ChatMessage.objects.none()
	if selected_doctor:
		thread_messages = ChatMessage.objects.filter(
			patient=request.user,
			doctor=selected_doctor,
		).select_related("sender", "recipient")
		thread_messages.filter(recipient=request.user, is_read=False).update(is_read=True)

	doctor_conversations = []
	for doctor in registered_doctors:
		conversation_messages = ChatMessage.objects.filter(patient=request.user, doctor=doctor)
		doctor_conversations.append(
			{
				"doctor": doctor,
				"last_message": conversation_messages.order_by("-created_at").first(),
				"unread_count": conversation_messages.filter(recipient=request.user, is_read=False).count(),
			}
		)

	context = _patient_base_context(request.user)
	context.update(
		{
			"registered_doctors": registered_doctors,
			"selected_doctor": selected_doctor,
			"thread_messages": thread_messages,
			"doctor_conversations": doctor_conversations,
		}
	)
	return render(request, "patients/messages.html", context)


@patient_required
def profile_page(request):
	patient_profile = getattr(request.user, "patient_profile", None)

	if request.method == "POST":
		has_error = False
		first_name = request.POST.get("first_name", "").strip()
		last_name = request.POST.get("last_name", "").strip()
		email = request.POST.get("email", "").strip()
		date_of_birth = request.POST.get("date_of_birth", "").strip()
		contact_info = request.POST.get("contact_info", "").strip()

		request.user.first_name = first_name
		request.user.last_name = last_name
		request.user.email = email
		request.user.save(update_fields=["first_name", "last_name", "email"])

		if patient_profile and date_of_birth and contact_info:
			patient_profile.date_of_birth = date_of_birth
			patient_profile.contact_info = contact_info
			patient_profile.full_name = request.user.get_full_name() or request.user.username
			patient_profile.save(update_fields=["date_of_birth", "contact_info", "full_name"])
		elif patient_profile and (date_of_birth or contact_info):
			has_error = True
			messages.error(request, "Both date of birth and contact info are required to update patient profile details.")
		elif not patient_profile and (date_of_birth or contact_info):
			has_error = True
			messages.error(request, "Patient profile details are not initialized for this account yet.")

		if not has_error:
			messages.success(request, "Profile updated successfully.")

		return redirect("patient_profile")

	context = _patient_base_context(request.user)
	context.update(
		{
			"patient_profile": patient_profile,
			"last_login": request.user.last_login,
			"total_messages": ChatMessage.objects.filter(patient=request.user).count(),
		}
	)
	return render(request, "patients/profile.html", context)


@patient_required
def feedback_page(request):
	from .models import Feedback
	user_model = get_user_model()
	registered_doctors = user_model.objects.filter(
		role=user_model.Role.DOCTOR,
		is_active=True,
		email__isnull=False,
	).exclude(email__exact="").select_related("doctor_profile").order_by("username").distinct()

	if request.method == "POST":
		doctor_id = request.POST.get("doctor_id")
		rating = request.POST.get("rating")
		comments = request.POST.get("comments", "").strip()

		doctor = registered_doctors.filter(id=doctor_id).first()
		if not doctor:
			messages.error(request, "Please select a valid doctor.")
		elif not rating or not rating.isdigit() or not (1 <= int(rating) <= 5):
			messages.error(request, "Please provide a valid rating between 1 and 5.")
		elif not comments:
			messages.error(request, "Please provide some comments.")
		else:
			Feedback.objects.create(
				patient=request.user,
				doctor=doctor,
				rating=int(rating),
				comments=comments,
			)
			messages.success(request, "Feedback submitted successfully.")
			return redirect("patient_feedback")

	feedbacks = Feedback.objects.filter(patient=request.user).select_related("doctor")

	context = _patient_base_context(request.user)
	context.update({
		"registered_doctors": registered_doctors,
		"feedbacks": feedbacks,
	})
	return render(request, "patients/feedback.html", context)
