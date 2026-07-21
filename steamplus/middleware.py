from django.utils import timezone


class OnlineStatusMiddleware:
    """Держит статус онлайн и last_seen, как Steam Presence."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, 'user', None)
        if user is not None and user.is_authenticated:
            try:
                profile = user.profile
                now = timezone.now()
                last = getattr(profile, 'last_seen', None)
                # Обновляем не чаще раза в 60 сек
                if not last or (now - last).total_seconds() > 60:
                    updates = {'last_seen': now}
                    if profile.status == 'offline':
                        updates['status'] = 'online'
                    for k, v in updates.items():
                        setattr(profile, k, v)
                    profile.save(update_fields=list(updates.keys()))
            except Exception:
                pass
        return self.get_response(request)
