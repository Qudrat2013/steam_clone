from django.utils import timezone
from .models import SaleEvent, Gift


def steamplus_globals(request):
    sale = (
        SaleEvent.objects.filter(
            is_active=True,
            starts_at__lte=timezone.now(),
            ends_at__gte=timezone.now(),
        )
        .order_by('-starts_at')
        .first()
    )
    pending_gifts = 0
    steam_points = 0
    if request.user.is_authenticated:
        pending_gifts = Gift.objects.filter(receiver=request.user, status='pending').count()
        try:
            steam_points = request.user.profile.steam_points
        except Exception:
            steam_points = 0
    return {
        'active_sale': sale,
        'pending_gifts_count': pending_gifts,
        'user_steam_points': steam_points,
    }
