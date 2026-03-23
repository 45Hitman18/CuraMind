from django.conf import settings
from django.db import models


class AuditLog(models.Model):
	user = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name="audit_logs",
	)
	action = models.CharField(max_length=100)
	object_type = models.CharField(max_length=100, blank=True)
	object_id = models.CharField(max_length=100, blank=True)
	timestamp = models.DateTimeField(auto_now_add=True)
	ip_address = models.GenericIPAddressField(null=True, blank=True)

	class Meta:
		ordering = ["-timestamp"]

	def save(self, *args, **kwargs):
		if self.pk:
			raise ValueError("AuditLog entries are immutable and cannot be updated.")
		return super().save(*args, **kwargs)

	def delete(self, *args, **kwargs):
		raise ValueError("AuditLog entries are immutable and cannot be deleted.")

	def __str__(self):
		return f"{self.action} @ {self.timestamp:%Y-%m-%d %H:%M:%S}"
