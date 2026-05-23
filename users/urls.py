from django.urls import path
from django.contrib.auth import views as auth_views
from .views import (
    register_view,
    login_view,
    logout_view,
    profile_view,
    edit_profile,
    verify_email_view,
    resend_verification_code_view,
)

urlpatterns = [
    # 🔐 Аутентификация
    path('register/', register_view, name='register'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),

    # 📧 Подтверждение email
    path('verify-email/', verify_email_view, name='verify_email'),
    path('resend-code/', resend_verification_code_view, name='resend_code'),

    # 🔑 Сброс пароля
    path('password-reset/', auth_views.PasswordResetView.as_view(
        template_name='users/password_reset_form.html'
    ), name='password_reset'),

    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='users/password_reset_done.html'
    ), name='password_reset_done'),

    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='users/password_reset_confirm.html'
    ), name='password_reset_confirm'),

    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='users/password_reset_complete.html'
    ), name='password_reset_complete'),

    # 👤 ПРОФИЛЬ (ВАЖНО: порядок!)
    path('profile/edit/', edit_profile, name='edit_profile'),
    path('profile/<str:username>/', profile_view, name='profile'),
]