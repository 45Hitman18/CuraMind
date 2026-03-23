from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
	list_display = ("timestamp", "action", "user", "object_type", "object_id", "ip_address")
	list_filter = ("action", "object_type", "timestamp")
	search_fields = ("action", "user__username", "object_type", "object_id", "ip_address")
	ordering = ("-timestamp",)
	readonly_fields = ("timestamp", "action", "user", "object_type", "object_id", "ip_address")

	def has_add_permission(self, request):
		return False

	def has_change_permission(self, request, obj=None):
		return False

	def has_delete_permission(self, request, obj=None):
		return False
