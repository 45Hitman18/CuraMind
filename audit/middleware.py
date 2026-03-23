from audit.models import AuditLog


class AuditLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        actor_before = request.user if getattr(request, "user", None) and request.user.is_authenticated else None
        response = self.get_response(request)

        resolver_match = getattr(request, "resolver_match", None)
        view_name = resolver_match.view_name if resolver_match else ""
        kwargs = resolver_match.kwargs if resolver_match else {}

        user_after = request.user if getattr(request, "user", None) and request.user.is_authenticated else None
        ip_address = self._get_ip(request)

        if view_name == "login" and request.method == "POST" and response.status_code in (200, 302) and user_after:
            self._log(user_after, "LOGIN", "User", str(user_after.id), ip_address)

        if view_name == "logout" and response.status_code in (200, 302):
            logout_user = actor_before or user_after
            self._log(logout_user, "LOGOUT", "User", str(logout_user.id) if logout_user else "", ip_address)

        if view_name in {"medical_record_file", "doctor_record_file"} and response.status_code == 200:
            record_id = str(kwargs.get("record_id", ""))
            self._log(user_after, "VIEW_RECORD", "MedicalRecord", record_id, ip_address)

        if view_name == "upload_scan" and request.method == "POST" and response.status_code == 302:
            self._log(user_after, "UPLOAD_RECORD", "MedicalRecord", "", ip_address)

        if view_name == "doctor_start_review" and response.status_code == 200:
            record_id = str(kwargs.get("record_id", ""))
            self._log(user_after, "START_REVIEW", "MedicalRecord", record_id, ip_address)

        if view_name in {"medical_record_file", "doctor_record_file", "doctor_start_review"} and response.status_code == 404:
            object_id = str(kwargs.get("record_id", ""))
            self._log(user_after or actor_before, "PERMISSION_DENIED", "MedicalRecord", object_id, ip_address)

        if response.status_code == 403:
            object_id = str(kwargs.get("record_id", "")) if kwargs else ""
            self._log(user_after or actor_before, "PERMISSION_DENIED", view_name or "View", object_id, ip_address)

        return response

    @staticmethod
    def _get_ip(request):
        forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")

    @staticmethod
    def _log(user, action, object_type, object_id, ip_address):
        AuditLog.objects.create(
            user=user,
            action=action,
            object_type=object_type,
            object_id=object_id,
            ip_address=ip_address,
        )
