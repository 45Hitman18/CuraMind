from django.conf import settings
from django.db import models


class PatientProfile(models.Model):
	user = models.OneToOneField(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name="patient_profile",
	)
	full_name = models.CharField(max_length=255)
	date_of_birth = models.DateField()
	contact_info = models.TextField()

	def __str__(self):
		return self.full_name


class PatientMessage(models.Model):
	patient = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name="patient_messages",
		limit_choices_to={"role": "patient"},
	)
	subject = models.CharField(max_length=255)
	body = models.TextField()
	is_read = models.BooleanField(default=False)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ["-created_at"]

	def __str__(self):
		return self.subject


class ChatMessage(models.Model):
	patient = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name="patient_chat_messages",
		limit_choices_to={"role": "patient"},
	)
	doctor = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name="doctor_chat_messages",
		limit_choices_to={"role": "doctor"},
	)
	sender = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name="sent_chat_messages",
	)
	recipient = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name="received_chat_messages",
	)
	body = models.TextField()
	attachment = models.FileField(upload_to="chat_media/", null=True, blank=True)
	is_read = models.BooleanField(default=False)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ["created_at"]

	def __str__(self):
		return f"Chat {self.patient_id}->{self.doctor_id} @ {self.created_at:%Y-%m-%d %H:%M}"


class Feedback(models.Model):
	patient = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name="feedbacks_given",
		limit_choices_to={"role": "patient"},
	)
	doctor = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name="feedbacks_received",
		limit_choices_to={"role": "doctor"},
	)
	rating = models.IntegerField(
		choices=[(i, str(i)) for i in range(1, 6)],
		help_text="Rating from 1 to 5"
	)
	comments = models.TextField()
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ["-created_at"]

	def __str__(self):
		return f"Feedback by {self.patient} for {self.doctor} - {self.rating} Stars"
