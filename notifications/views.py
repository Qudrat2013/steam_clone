from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .models import Notification


@login_required
def notification_list_view(request):
    notifications = request.user.notifications.all()
    return render(request, 'notifications/notifications.html', {
        'notifications': notifications,
    })


@login_required
def mark_notifications_read_view(request):
    request.user.notifications.filter(is_read=False).update(is_read=True)
    return redirect('notification_list')