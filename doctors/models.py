from django.conf import settings
from django.db import models


class DoctorProfile(models.Model):
	user = models.OneToOneField(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name="doctor_profile",
	)
	specialization = models.CharField(max_length=255)
	license_id = models.CharField(max_length=100, unique=True)

	def __str__(self):
		return f"{self.user.get_full_name() or self.user.username} - {self.specialization}"
