from django.conf import settings
from django.db import models


class Appointment(models.Model):
	class Status(models.TextChoices):
		PENDING = "pending", "Pending"
		APPROVED = "approved", "Approved"
		REJECTED = "rejected", "Rejected"
		SCHEDULED = "scheduled", "Scheduled"
		COMPLETED = "completed", "Completed"
		CANCELLED = "cancelled", "Cancelled"

	patient = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name="patient_appointments",
		limit_choices_to={"role": "patient"},
	)
	doctor = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name="doctor_appointments",
		limit_choices_to={"role": "doctor"},
	)
	datetime = models.DateTimeField()
	status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
	reason = models.CharField(max_length=100, blank=True)
	insurance_provider = models.CharField(max_length=255, blank=True)
	patient_notes = models.TextField(blank=True)

	class Meta:
		ordering = ["datetime"]

	def __str__(self):
		return f"{self.patient} with {self.doctor} at {self.datetime}"
