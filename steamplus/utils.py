from django.utils import timezone

from .models import Activity, Playtime


def log_activity(user, activity_type, text, game=None):
    if not user or not user.is_authenticated:
        return None
    return Activity.objects.create(
        user=user,
        activity_type=activity_type,
        text=text[:300],
        game=game,
    )


def get_or_create_playtime(user, game):
    pt, _ = Playtime.objects.get_or_create(user=user, game=game)
    return pt


def record_play_session(user, game, minutes=15):
    pt = get_or_create_playtime(user, game)
    pt.add_session(minutes=minutes)
    log_activity(
        user,
        'play',
        f'запустил «{game.title}» (+{minutes} мин.)',
        game=game,
    )
    # Steam Points: 1 очко за каждые 5 минут
    try:
        profile = user.profile
        profile.steam_points = getattr(profile, 'steam_points', 0) + max(1, minutes // 5)
        profile.status = 'online'
        profile.custom_status = f'В игре: {game.title}'[:80]
        profile.last_seen = timezone.now()
        profile.save(update_fields=['steam_points', 'status', 'custom_status', 'last_seen'])
    except Exception:
        pass
    return pt
