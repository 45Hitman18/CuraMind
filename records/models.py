from uuid import uuid4

from django.conf import settings
from django.db import models


class MedicalRecord(models.Model):
	class AIStatus(models.TextChoices):
		UPLOADED = "uploaded", "Uploaded"
		PROCESSING = "processing", "Processing"
		COMPLETE = "complete", "Complete"
		HIGH = "high", "High"
		MEDIUM = "medium", "Medium"
		LOW = "low", "Low"

	class ReviewStatus(models.TextChoices):
		READY = "ready", "Ready for Review"
		IN_PROGRESS = "in_progress", "In Progress"
		COMPLETED = "completed", "Completed"

	patient = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name="medical_records",
		limit_choices_to={"role": "patient"},
	)
	uploaded_file = models.FileField(upload_to="medical_records/")
	scan_type = models.CharField(max_length=100)
	scan_id = models.CharField(max_length=20, unique=True, editable=False)
	doctor_notes = models.TextField(blank=True, default="")
	ai_status = models.CharField(max_length=20, choices=AIStatus.choices, default=AIStatus.UPLOADED)
	review_status = models.CharField(max_length=20, choices=ReviewStatus.choices, default=ReviewStatus.READY)
	reviewed_by = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name="reviewed_medical_records",
		limit_choices_to={"role": "doctor"},
	)
	reviewed_at = models.DateTimeField(null=True, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ["-created_at"]

	def save(self, *args, **kwargs):
		if not self.scan_id:
			self.scan_id = f"CM-{uuid4().hex[:8].upper()}"
		super().save(*args, **kwargs)

	def __str__(self):
		return f"{self.scan_type} ({self.scan_id})"
