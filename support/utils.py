from django.utils import timezone

from .models import AdminAuditLog, UserBan


def log_admin_action(admin, action, target_type='', target_id='', details='', request=None):
    ip = None
    if request is not None:
        ip = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip()
        if not ip:
            ip = request.META.get('REMOTE_ADDR')
    return AdminAuditLog.objects.create(
        admin=admin,
        action=action,
        target_type=str(target_type or ''),
        target_id=str(target_id or ''),
        details=details or '',
        ip_address=ip,
    )


def user_has_active_ban(user, ban_type=None):
    """Проверка активного бана. ban_type=None — любой full/temp."""
    qs = UserBan.objects.filter(user=user, is_active=True)
    if ban_type:
        qs = qs.filter(ban_type__in=[ban_type, 'full', 'temp'])
    else:
        qs = qs.filter(ban_type__in=['full', 'temp'])

    now = timezone.now()
    for ban in qs:
        if ban.ends_at and ban.ends_at < now:
            ban.is_active = False
            ban.save(update_fields=['is_active'])
            continue
        return ban
    return None


def get_client_ip(request):
    ip = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip()
    return ip or request.META.get('REMOTE_ADDR')
