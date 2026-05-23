from django.urls import path
from .views import notification_list_view, mark_notifications_read_view

urlpatterns = [
    path('', notification_list_view, name='notification_list'),
    path('read/', mark_notifications_read_view, name='mark_notifications_read'),
]