from django.contrib.auth import login
from django.shortcuts import redirect, render

from .forms import RegistrationForm


def role_redirect_for(user):
	if user.role == "patient":
		return redirect("patient_dashboard")
	if user.role == "doctor":
		return redirect("doctor_dashboard")
	if user.role == "admin":
		return redirect("admin_overview")
	return redirect("landing_page")


def register(request):
	if request.user.is_authenticated:
		return role_redirect_for(request.user)

	if request.method == "POST":
		form = RegistrationForm(request.POST)
		if form.is_valid():
			user = form.save()
			login(request, user)
			return role_redirect_for(user)
	else:
		form = RegistrationForm()

	return render(request, "registration/register.html", {"form": form})

def mark_notifications_read(request):
	if request.user.is_authenticated:
		request.user.notifications.filter(is_read=False).update(is_read=True)
	return redirect(request.META.get('HTTP_REFERER', 'landing_page'))
