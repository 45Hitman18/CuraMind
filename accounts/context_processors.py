from .models import Notification

def user_notifications(request):
    if request.user.is_authenticated:
        qs = request.user.notifications.all()
        return {
            'navbar_notifications': qs[:5],
            'unread_notifications_count': qs.filter(is_read=False).count()
        }
    return {
        'navbar_notifications': [],
        'unread_notifications_count': 0
    }
