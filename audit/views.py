from datetime import timedelta
import csv

from django.db.models import Count
from django.db.models.functions import TruncDate
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.http import HttpResponse
from django.db.models import Q

from accounts.decorators import admin_required
from doctors.models import DoctorProfile
from patients.models import PatientProfile
from patients.models import ChatMessage
from records.models import MedicalRecord

from .models import AuditLog


@admin_required
def admin_overview(request):
	total_patients = PatientProfile.objects.count()
	total_doctors = DoctorProfile.objects.count()
	total_records = MedicalRecord.objects.count()
	recent_audit_logs = AuditLog.objects.select_related("user")[:10]

	now = timezone.now()
	seven_days_ago = now - timedelta(days=6)

	daily_records = (
		MedicalRecord.objects.filter(created_at__date__gte=seven_days_ago.date())
		.annotate(day=TruncDate("created_at"))
		.values("day")
		.annotate(total=Count("id"))
		.order_by("day")
	)
	records_by_day = {str(item["day"]): item["total"] for item in daily_records}
	day_labels = []
	day_values = []
	for offset in range(7):
		current_day = (seven_days_ago + timedelta(days=offset)).date()
		day_labels.append(current_day.strftime("%a"))
		day_values.append(records_by_day.get(str(current_day), 0))

	last_24h_logs = AuditLog.objects.filter(timestamp__gte=now - timedelta(hours=24))
	total_24h_logs = last_24h_logs.count()
	denial_24h_logs = last_24h_logs.filter(action="PERMISSION_DENIED").count()
	success_24h_logs = max(total_24h_logs - denial_24h_logs, 0)
	compliance_rate = 100 if total_24h_logs == 0 else round((success_24h_logs / total_24h_logs) * 100)

	top_doctors = (
		MedicalRecord.objects.filter(reviewed_by__isnull=False, review_status=MedicalRecord.ReviewStatus.COMPLETED)
		.values("reviewed_by__first_name", "reviewed_by__last_name", "reviewed_by__username")
		.annotate(total=Count("id"))
		.order_by("-total")[:5]
	)

	context = {
		"total_patients": total_patients,
		"total_doctors": total_doctors,
		"total_records": total_records,
		"recent_audit_logs": recent_audit_logs,
		"day_labels": day_labels,
		"day_values": day_values,
		"compliance_rate": compliance_rate,
		"total_24h_logs": total_24h_logs,
		"denial_24h_logs": denial_24h_logs,
		"top_doctors": top_doctors,
	}
	return render(request, "audit/admin_overview.html", context)


@admin_required
def user_management(request):
	user_model = get_user_model()

	def is_demo_user(account):
		username = (account.username or "").lower()
		email = (account.email or "").lower()
		full_name = (account.get_full_name() or "").lower()
		demo_tokens = ("demo", "test", "fake", "sample", "dummy")
		demo_email_tokens = ("@example.com", "@test.com", "@demo.com")
		return (
			any(token in username for token in demo_tokens)
			or any(token in email for token in demo_tokens)
			or any(token in full_name for token in demo_tokens)
			or any(token in email for token in demo_email_tokens)
		)

	query = request.GET.get("q", "").strip()
	role_filter = request.GET.get("role", "all")
	status_filter = request.GET.get("status", "all")
	return_query = request.POST.get("return_query", "")

	if request.method == "POST":
		action = request.POST.get("action")
		user_id = request.POST.get("user_id")
		if action == "toggle_block" and user_id:
			target_user = get_object_or_404(user_model, id=user_id)
			if target_user.id == request.user.id:
				messages.error(request, "You cannot block your own admin account.")
			else:
				target_user.is_active = not target_user.is_active
				target_user.save(update_fields=["is_active"])
				if target_user.is_active:
					AuditLog.objects.create(
						user=request.user,
						action="UNBLOCK_USER",
						object_type="User",
						object_id=str(target_user.id),
						ip_address=request.META.get("REMOTE_ADDR"),
					)
					messages.success(request, f"{target_user.username} has been unblocked.")
				else:
					AuditLog.objects.create(
						user=request.user,
						action="BLOCK_USER",
						object_type="User",
						object_id=str(target_user.id),
						ip_address=request.META.get("REMOTE_ADDR"),
					)
					messages.success(request, f"{target_user.username} has been blocked.")
		redirect_url = request.path
		if return_query:
			redirect_url = f"{redirect_url}?{return_query}"
		return redirect(redirect_url)

	manual_users_qs = user_model.objects.all().select_related("doctor_profile", "patient_profile").order_by("-date_joined")

	real_user_ids_from_messages = set(
		ChatMessage.objects.values_list("patient_id", flat=True)
	) | set(
		ChatMessage.objects.values_list("doctor_id", flat=True)
	) | set(
		ChatMessage.objects.values_list("sender_id", flat=True)
	) | set(
		ChatMessage.objects.values_list("recipient_id", flat=True)
	)

	manual_users = []
	for account in manual_users_qs:
		has_valid_email = bool((account.email or "").strip())
		is_message_user = account.id in real_user_ids_from_messages
		if is_demo_user(account):
			continue
		if not has_valid_email and not is_message_user:
			continue
		manual_users.append(account)

	all_users_count = len(manual_users)
	doctors_count = len([
		account for account in manual_users if account.role == user_model.Role.DOCTOR and account.is_active
	])
	patients_count = len([
		account for account in manual_users if account.role == user_model.Role.PATIENT and account.is_active
	])
	pending_requests = len([
		account for account in manual_users if account.is_active and account.last_login is None
	])

	filtered_users = manual_users

	if query:
		filtered_users = [
			account
			for account in filtered_users
			if (
				query.lower() in (account.username or "").lower()
				or query.lower() in (account.email or "").lower()
				or query.lower() in (account.first_name or "").lower()
				or query.lower() in (account.last_name or "").lower()
			)
		]

	if role_filter in {user_model.Role.DOCTOR, user_model.Role.PATIENT, user_model.Role.ADMIN}:
		filtered_users = [account for account in filtered_users if account.role == role_filter]

	user_rows = []
	for account in filtered_users:
		if not account.is_active:
			account_status = "suspended"
		elif account.last_login is None:
			account_status = "pending"
		else:
			account_status = "active"

		if status_filter != "all" and account_status != status_filter:
			continue

		if account.role == user_model.Role.DOCTOR:
			detail = getattr(getattr(account, "doctor_profile", None), "specialization", "General Medicine")
		elif account.role == user_model.Role.ADMIN:
			detail = "IT & Operations"
		else:
			detail = "Outpatient Department"

		user_rows.append(
			{
				"id": account.id,
				"full_name": account.get_full_name() or account.username,
				"email": account.email or "No email",
				"role": account.role,
				"detail": detail,
				"status": account_status,
				"is_active": account.is_active,
				"last_login": account.last_login,
				"initials": (account.first_name[:1] + account.last_name[:1]).upper() or account.username[:2].upper(),
			}
		)

	paginator = Paginator(user_rows, 10)
	page_obj = paginator.get_page(request.GET.get("page", 1))

	context = {
		"query": query,
		"role_filter": role_filter,
		"status_filter": status_filter,
		"total_users": all_users_count,
		"doctors_count": doctors_count,
		"patients_count": patients_count,
		"pending_requests": pending_requests,
		"page_obj": page_obj,
		"users": page_obj.object_list,
	}
	return render(request, "audit/user_management.html", context)


def _log_level(action):
	if action == "PERMISSION_DENIED":
		return "critical"
	if action in {"BLOCK_USER", "UNBLOCK_USER"}:
		return "warning"
	return "info"


def _log_category(action, object_type):
	if action in {"LOGIN", "LOGOUT", "VIEW_RECORD"}:
		return "access"
	if action in {"PERMISSION_DENIED", "BLOCK_USER", "UNBLOCK_USER"}:
		return "security"
	if action in {"UPLOAD_RECORD", "START_REVIEW"} or object_type == "MedicalRecord":
		return "data"
	if object_type == "User":
		return "user"
	return "system"


@admin_required
def system_logs(request):
	query = request.GET.get("q", "").strip()
	level_filter = request.GET.get("level", "all")
	category_filter = request.GET.get("category", "all")
	period_filter = request.GET.get("period", "7d")

	now = timezone.now()
	if period_filter == "24h":
		since = now - timedelta(hours=24)
	elif period_filter == "30d":
		since = now - timedelta(days=30)
	else:
		since = now - timedelta(days=7)
		period_filter = "7d"

	base_logs = AuditLog.objects.select_related("user").filter(timestamp__gte=since).order_by("-timestamp")

	total_logs = base_logs.count()
	security_alerts = base_logs.filter(action="PERMISSION_DENIED").count()
	critical_actions = base_logs.filter(action__in=["PERMISSION_DENIED", "BLOCK_USER"]).count()
	active_sessions = AuditLog.objects.filter(
		action="LOGIN",
		timestamp__gte=now - timedelta(hours=24),
		user__isnull=False,
	).values("user_id").distinct().count()

	filtered_logs = base_logs
	if query:
		filtered_logs = filtered_logs.filter(
			Q(action__icontains=query)
			| Q(object_type__icontains=query)
			| Q(object_id__icontains=query)
			| Q(ip_address__icontains=query)
			| Q(user__username__icontains=query)
			| Q(user__first_name__icontains=query)
			| Q(user__last_name__icontains=query)
		)

	log_rows = []
	for log in filtered_logs:
		level = _log_level(log.action)
		category = _log_category(log.action, log.object_type)

		if level_filter != "all" and level != level_filter:
			continue
		if category_filter != "all" and category != category_filter:
			continue

		user_full_name = "System"
		user_role = "system"
		user_initials = "SY"
		if log.user:
			user_full_name = log.user.get_full_name() or log.user.username
			user_role = getattr(log.user, "role", "user")
			user_initials = ((log.user.first_name[:1] + log.user.last_name[:1]).upper() or log.user.username[:2].upper())

		action_text = log.action.replace("_", " ").title()
		if log.object_type:
			action_text = f"{action_text} ({log.object_type}{f' #{log.object_id}' if log.object_id else ''})"

		log_rows.append(
			{
				"timestamp": log.timestamp,
				"user_name": user_full_name,
				"user_role": user_role,
				"user_initials": user_initials,
				"action_text": action_text,
				"ip_address": log.ip_address or "N/A",
				"status": "failure" if log.action == "PERMISSION_DENIED" else "success",
				"level": level,
				"category": category,
			}
		)

	if request.GET.get("export") == "csv":
		response = HttpResponse(content_type="text/csv")
		response["Content-Disposition"] = "attachment; filename=system_logs.csv"
		writer = csv.writer(response)
		writer.writerow(["Timestamp", "User", "Role", "Action", "IP Address", "Status", "Level", "Category"])
		for row in log_rows:
			writer.writerow([
				row["timestamp"].strftime("%Y-%m-%d %H:%M:%S"),
				row["user_name"],
				row["user_role"],
				row["action_text"],
				row["ip_address"],
				row["status"],
				row["level"],
				row["category"],
			])
		return response

	paginator = Paginator(log_rows, 10)
	page_obj = paginator.get_page(request.GET.get("page", 1))

	context = {
		"query": query,
		"level_filter": level_filter,
		"category_filter": category_filter,
		"period_filter": period_filter,
		"total_logs": total_logs,
		"security_alerts": security_alerts,
		"critical_actions": critical_actions,
		"active_sessions": active_sessions,
		"page_obj": page_obj,
		"logs": page_obj.object_list,
	}
	return render(request, "audit/system_logs.html", context)


@admin_required
def admin_settings(request):
	settings_key = f"admin_settings_{request.user.id}"
	stored = request.session.get(
		settings_key,
		{
			"two_factor_enabled": True,
			"session_timeout": "30",
			"password_complexity": "hipaa",
			"ai_sensitivity": 50,
			"maintenance_schedule": "monthly_last_sat",
			"maintenance_time": "02:00",
			"backup_frequency": "daily",
			"notify_critical": True,
			"notify_health_reports": False,
		},
	)

	if request.method == "POST":
		action = request.POST.get("action", "save_all")
		if action in {"save_profile", "save_all"}:
			full_name = request.POST.get("full_name", "").strip()
			email = request.POST.get("email", "").strip()
			if full_name:
				parts = full_name.split(" ", 1)
				request.user.first_name = parts[0]
				request.user.last_name = parts[1] if len(parts) > 1 else ""
			if email:
				request.user.email = email
			request.user.save(update_fields=["first_name", "last_name", "email"])

		stored["two_factor_enabled"] = request.POST.get("two_factor_enabled") == "on"
		stored["session_timeout"] = request.POST.get("session_timeout", stored["session_timeout"])
		stored["password_complexity"] = request.POST.get("password_complexity", stored["password_complexity"])
		stored["ai_sensitivity"] = int(request.POST.get("ai_sensitivity", stored["ai_sensitivity"]))
		stored["maintenance_schedule"] = request.POST.get("maintenance_schedule", stored["maintenance_schedule"])
		stored["maintenance_time"] = request.POST.get("maintenance_time", stored["maintenance_time"])
		stored["backup_frequency"] = request.POST.get("backup_frequency", stored["backup_frequency"])
		stored["notify_critical"] = request.POST.get("notify_critical") == "on"
		stored["notify_health_reports"] = request.POST.get("notify_health_reports") == "on"

		request.session[settings_key] = stored
		request.session.modified = True
		messages.success(request, "Settings updated successfully.")
		return redirect("admin_settings")

	context = {
		"settings_data": stored,
	}
	return render(request, "audit/settings.html", context)


@admin_required
def admin_feedback_page(request):
	from patients.models import Feedback
	feedbacks = Feedback.objects.all().select_related("patient", "doctor").order_by("-created_at")
	
	total_feedbacks = feedbacks.count()

	paginator = Paginator(feedbacks, 10)
	page_obj = paginator.get_page(request.GET.get("page", 1))

	context = {
		"total_feedbacks": total_feedbacks,
		"page_obj": page_obj,
		"feedbacks": page_obj.object_list,
	}
	return render(request, "audit/admin_feedback.html", context)
