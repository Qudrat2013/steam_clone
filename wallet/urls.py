from django.urls import path
from . import views

# ИСПРАВЛЕНО: Указываем имя приложения для namespace
app_name = 'wallet'

urlpatterns = [
    path('deposit/', views.create_payment, name='deposit'),
    path('click/webhook/', views.click_webhook, name='click_webhook'),
]