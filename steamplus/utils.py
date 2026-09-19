from django.utils import timezone

from .models import Activity, PlaySession, Playtime, format_play_duration

# Если heartbeat не приходит столько секунд — сессия считается брошенной.
STALE_AFTER_SECONDS = 90


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


def _set_in_game(user, game):
    try:
        profile = user.profile
        profile.status = 'online'
        profile.custom_status = f'В игре: {game.title}'[:80]
        profile.last_seen = timezone.now()
        profile.save(update_fields=['status', 'custom_status', 'last_seen'])
    except Exception:
        pass


def _clear_in_game(user, game=None):
    try:
        profile = user.profile
        if game is None or (profile.custom_status or '').startswith('В игре:'):
            profile.custom_status = ''
            profile.last_seen = timezone.now()
            profile.save(update_fields=['custom_status', 'last_seen'])
    except Exception:
        pass


def finalize_session(session):
    """Закрывает сессию и начисляет реально сыгранное время."""
    if not session.is_active:
        return session

    now = timezone.now()
    end = now
    stale_gap = (now - session.last_heartbeat).total_seconds()
    if stale_gap > STALE_AFTER_SECONDS:
        end = session.last_heartbeat

    seconds = max(0, int((end - session.started_at).total_seconds()))
    session.seconds = seconds
    session.ended_at = end
    session.is_active = False
    session.save(update_fields=['seconds', 'ended_at', 'is_active'])

    user = session.user
    game = session.game
    pt = get_or_create_playtime(user, game)
    pt.add_seconds(seconds, new_session=True)

    minutes = seconds // 60
    log_activity(
        user,
        'play',
        f'играл в «{game.title}» ({format_play_duration(seconds)})',
        game=game,
    )

    try:
        from achievements.utils import give_achievement
        if pt.sessions == 1:
            give_achievement(user, 'Первый запуск', 'Запустите игру впервые')
            log_activity(user, 'achievement', 'получил достижение «Первый запуск»', game=game)
        if pt.total_seconds >= 3600:
            give_achievement(user, 'Час в деле', 'Сыграйте 1 час в любой игре')
    except Exception:
        pass

    try:
        profile = user.profile
        points = minutes // 5
        profile.custom_status = ''
        profile.last_seen = now
        if points:
            profile.steam_points = getattr(profile, 'steam_points', 0) + points
        if minutes >= 1:
            profile.add_xp(max(1, minutes // 10))
        else:
            fields = ['custom_status', 'last_seen']
            if points:
                fields.append('steam_points')
            profile.save(update_fields=fields)
    except Exception:
        _clear_in_game(user, game)

    return session


def close_user_sessions(user, stale_only=False):
    """Закрывает активные сессии пользователя (все или только зависшие)."""
    qs = PlaySession.objects.filter(user=user, is_active=True).select_related('game', 'user')
    now = timezone.now()
    closed = []
    for session in qs:
        gap = (now - session.last_heartbeat).total_seconds()
        if stale_only and gap <= STALE_AFTER_SECONDS:
            continue
        closed.append(finalize_session(session))
    return closed


def start_play_session(user, game, source='web'):
    """Начинает новую сессию. Предыдущие активные закрываются с учётом времени."""
    close_user_sessions(user, stale_only=False)
    now = timezone.now()
    session = PlaySession.objects.create(
        user=user,
        game=game,
        started_at=now,
        last_heartbeat=now,
        source=source if source in ('launcher', 'web') else 'web',
        is_active=True,
    )
    _set_in_game(user, game)
    return session


def heartbeat_play_session(user, session_id=None, game=None):
    close_user_sessions(user, stale_only=True)
    qs = PlaySession.objects.filter(user=user, is_active=True)
    if session_id:
        qs = qs.filter(id=session_id)
    elif game is not None:
        qs = qs.filter(game=game)
    session = qs.select_related('game').first()
    if not session:
        return None
    session.last_heartbeat = timezone.now()
    session.save(update_fields=['last_heartbeat'])
    _set_in_game(user, session.game)
    return session


def end_play_session(user, session_id=None, game=None):
    qs = PlaySession.objects.filter(user=user, is_active=True)
    if session_id:
        qs = qs.filter(id=session_id)
    elif game is not None:
        qs = qs.filter(game=game)
    session = qs.select_related('game', 'user').first()
    if not session:
        return None
    return finalize_session(session)


def get_active_session(user):
    close_user_sessions(user, stale_only=True)
    return (
        PlaySession.objects.filter(user=user, is_active=True)
        .select_related('game')
        .first()
    )


def record_play_session(user, game, minutes=15):
    """Совместимость: записать уже закончившуюся сессию известной длины."""
    pt = get_or_create_playtime(user, game)
    seconds = max(1, int(minutes)) * 60
    pt.add_seconds(seconds, new_session=True)
    log_activity(
        user,
        'play',
        f'играл в «{game.title}» ({format_play_duration(seconds)})',
        game=game,
    )
    try:
        profile = user.profile
        profile.steam_points = getattr(profile, 'steam_points', 0) + max(0, int(minutes) // 5)
        profile.status = 'online'
        profile.custom_status = f'В игре: {game.title}'[:80]
        profile.last_seen = timezone.now()
        profile.save(update_fields=['steam_points', 'status', 'custom_status', 'last_seen'])
    except Exception:
        pass
    return pt
