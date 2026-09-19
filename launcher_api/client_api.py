import json
import time


"""API для нативного лаунчера (авторизация по токену).





Лаунчер - отдельное приложение без cookie-сессии браузера, поэтому он


ходит сюда с заголовком Authorization: Token <key>. Время игры пишется


в те же модели steamplus, что и на сайте (Playtime / PlaySession).


"""


import json





from django.http import JsonResponse


from django.utils import timezone


from django.views.decorators.csrf import csrf_exempt


from django.views.decorators.http import require_GET, require_POST





from rest_framework.authtoken.models import Token





from cart.models import Purchase


from games.models import Game


from steamplus.models import Playtime


from steamplus.utils import (


    start_play_session,


    heartbeat_play_session,


    end_play_session,


    get_active_session,


    get_or_create_playtime,


)








def _token_user(request):


    auth = request.META.get('HTTP_AUTHORIZATION', '')


    if not auth.lower().startswith('token '):


        return None


    try:


        return Token.objects.select_related('user').get(key=auth.split(None, 1)[1].strip()).user


    except Token.DoesNotExist:


        return None








def _unauthorized():


    return JsonResponse({'ok': False, 'detail': 'unauthorized'}, status=401)








def _json_body(request):


    try:


        return json.loads((request.body or b'').decode('utf-8') or '{}')


    except Exception:


        return {}








@require_GET


def client_library(request):


    user = _token_user(request)


    if user is None:


        return _unauthorized()





    pt_map = {pt.game_id: pt for pt in Playtime.objects.filter(user=user)}


    active = get_active_session(user)


    games = []


    purchases = (


        Purchase.objects.filter(user=user)


        .select_related('game')


        .order_by('-purchased_at')


    )


    for p in purchases:


        g = p.game


        pt = pt_map.get(g.id)


        try:


            header = g.header_image.url if g.header_image else ''


        except Exception:


            header = ''


        try:


            exe_path = g.get_local_exe_path() or ''


        except Exception:


            exe_path = ''


        games.append({


            'id': g.id,


            'title': g.title,


            'developer': g.developer or '',


            'header_url': header,


            'exe_path': exe_path,


            'installed': bool(exe_path),


            'playtime_display': pt.hours_display if pt else '0 ч.',


            'playtime_seconds': pt.total_seconds if pt else 0,


            'sessions': pt.sessions if pt else 0,


            'is_playing': bool(active and active.game_id == g.id),


            'page_url': f'/game/{g.slug}/',


        })





    return JsonResponse({


        'ok': True,


        'username': user.username,


        'games': games,


        'active_session_id': active.id if active else None,


    })








@csrf_exempt


@require_POST


def client_play_start(request):


    user = _token_user(request)


    if user is None:


        return _unauthorized()


    data = _json_body(request)


    try:


        game_id = int(data.get('game_id') or 0)


    except (TypeError, ValueError):


        game_id = 0


    if not game_id:


        return JsonResponse({'ok': False, 'detail': 'game_id_required'}, status=400)


    game = Game.objects.filter(id=game_id).first()


    if game is None:


        return JsonResponse({'ok': False, 'detail': 'game_not_found'}, status=404)


    if not Purchase.objects.filter(user=user, game=game).exists():


        return JsonResponse({'ok': False, 'detail': 'not_owned'}, status=403)


    session = start_play_session(user, game, source='launcher')


    return JsonResponse({


        'ok': True,


        'session_id': session.id,


        'game_id': game.id,


        'game_title': game.title,


    })








@csrf_exempt


@require_POST


def client_play_heartbeat(request):


    user = _token_user(request)


    if user is None:


        return _unauthorized()


    session = heartbeat_play_session(user, session_id=_json_body(request).get('session_id'))


    if session is None:


        return JsonResponse({'ok': False, 'playing': False, 'detail': 'no_session'}, status=404)


    elapsed = max(0, int((timezone.now() - session.started_at).total_seconds()))


    return JsonResponse({


        'ok': True,


        'playing': True,


        'session_id': session.id,


        'game_id': session.game_id,


        'elapsed_seconds': elapsed,


    })








@csrf_exempt


@require_POST


def client_play_end(request):


    user = _token_user(request)


    if user is None:


        return _unauthorized()


    data = _json_body(request)


    session = end_play_session(user, session_id=data.get('session_id'))


    if session is not None:


        game, session_seconds = session.game, session.seconds


    else:


        try:


            game = Game.objects.filter(id=int(data.get('game_id') or 0)).first()


        except (TypeError, ValueError):


            game = None


        session_seconds = 0


    if game is None:


        return JsonResponse({'ok': True, 'session_seconds': 0, 'total_display': '0 ч.', 'sessions': 0})


    pt = get_or_create_playtime(user, game)


    return JsonResponse({


        'ok': True,


        'game_id': game.id,


        'session_seconds': session_seconds,


        'total_display': pt.hours_display,


        'total_seconds': pt.total_seconds,


        'sessions': pt.sessions,


    })




# ============================================================== store
def _game_payload(g, owned_ids, user=None):
    try:
        header = g.header_image.url if g.header_image else ''
    except Exception:
        header = ''
    try:
        exe_path = g.get_local_exe_path() or ''
    except Exception:
        exe_path = ''
    shots = []
    for s in g.screenshots.all()[:4]:
        try:
            shots.append(s.image.url)
        except Exception:
            pass
    in_wishlist = False
    if user is not None:
        try:
            from cart.models import Wishlist
            in_wishlist = Wishlist.objects.filter(user=user, game=g).exists()
        except Exception:
            pass
    return {
        'id': g.id,
        'title': g.title,
        'slug': g.slug,
        'developer': g.developer or '',
        'short_description': g.short_description or '',
        'description': g.description or '',
        'header_url': header,
        'screenshots': shots,
        'price': str(g.price),
        'discount': g.discount or 0,
        'final_price': str(g.get_discounted_price()),
        'owned': g.id in owned_ids,
        'in_wishlist': in_wishlist,
        'installed': bool(exe_path),
        'page_url': f'/game/{g.slug}/',
    }


@require_GET
def client_store(request):
    user = _token_user(request)
    if user is None:
        return _unauthorized()
    owned_ids = set(Purchase.objects.filter(user=user).values_list('game_id', flat=True))
    games = []
    for g in Game.objects.filter(is_active=True).prefetch_related('screenshots').order_by('-created_at'):
        games.append(_game_payload(g, owned_ids, user))
    try:
        balance = str(user.profile.balance)
    except Exception:
        balance = '0'
    return JsonResponse({'ok': True, 'balance': balance, 'games': games})


@csrf_exempt
@require_POST
def client_buy(request):
    from django.db import transaction
    from decimal import Decimal

    user = _token_user(request)
    if user is None:
        return _unauthorized()
    data = _json_body(request)
    try:
        game_id = int(data.get('game_id') or 0)
    except (TypeError, ValueError):
        game_id = 0
    game = Game.objects.filter(id=game_id, is_active=True).first()
    if game is None:
        return JsonResponse({'ok': False, 'detail': 'game_not_found'}, status=404)
    with transaction.atomic():
        if Purchase.objects.filter(user=user, game=game).exists():
            return JsonResponse({'ok': False, 'detail': 'already_owned'}, status=409)
        profile, _ = __import__('users.models', fromlist=['Profile']).Profile.objects.get_or_create(user=user)
        price = game.get_discounted_price()
        if profile.balance < price:
            return JsonResponse({
                'ok': False, 'detail': 'insufficient_funds',
                'price': str(price), 'balance': str(profile.balance),
            }, status=402)
        profile.balance -= price
        profile.save(update_fields=['balance'])
        Purchase.objects.create(user=user, game=game, price_paid=price)
    return JsonResponse({
        'ok': True,
        'detail': f'Игра «{game.title}» куплена!',
        'balance': str(profile.balance),
        'game_id': game.id,
    })


# ================================================================ chat
def _dialog_list(user):
    from django.db.models import Q, Max
    from chat.models import ChatMessage
    from django.contrib.auth.models import User

    partners = set(ChatMessage.objects.filter(
        Q(sender=user) | Q(receiver=user)
    ).values_list('sender_id', flat=True)) | set(ChatMessage.objects.filter(
        Q(sender=user) | Q(receiver=user)
    ).values_list('receiver_id', flat=True))
    partners.discard(user.id)
    users = User.objects.filter(id__in=partners)
    out = []
    for u in users:
        last = ChatMessage.objects.filter(
            Q(sender=user, receiver=u) | Q(sender=u, receiver=user)
        ).order_by('-created_at').first()
        unread = ChatMessage.objects.filter(sender=u, receiver=user, is_read=False).count()
        out.append({
            'username': u.username,
            'last_text': (last.text or '[стикер]') if last else '',
            'last_time': last.created_at.strftime('%d.%m %H:%M') if last else '',
            'unread': unread,
        })
    out.sort(key=lambda d: d['last_time'], reverse=True)
    return out


@require_GET
def client_chat_dialogs(request):
    user = _token_user(request)
    if user is None:
        return _unauthorized()
    return JsonResponse({'ok': True, 'dialogs': _dialog_list(user)})


@require_GET
def client_chat_messages(request):
    user = _token_user(request)
    if user is None:
        return _unauthorized()
    from django.db.models import Q
    from chat.models import ChatMessage
    from django.contrib.auth.models import User

    partner = User.objects.filter(username=request.GET.get('with', '')).first()
    if partner is None:
        return JsonResponse({'ok': False, 'detail': 'no_user'}, status=404)
    msgs = ChatMessage.objects.filter(
        Q(sender=user, receiver=partner) | Q(sender=partner, receiver=user)
    ).order_by('created_at')[:500]
    ChatMessage.objects.filter(sender=partner, receiver=user, is_read=False).update(is_read=True)
    return JsonResponse({'ok': True, 'partner': partner.username, 'messages': [
        {
            'id': m.id,
            'mine': m.sender_id == user.id,
            'text': m.text or '[стикер]',
            'time': m.created_at.strftime('%H:%M'),
        } for m in msgs
    ]})


@csrf_exempt
@require_POST
def client_chat_send(request):
    user = _token_user(request)
    if user is None:
        return _unauthorized()
    from chat.models import ChatMessage
    from django.contrib.auth.models import User

    data = _json_body(request)
    partner = User.objects.filter(username=str(data.get('to') or '')).first()
    text = str(data.get('text') or '').strip()[:2000]
    if partner is None:
        return JsonResponse({'ok': False, 'detail': 'no_user'}, status=404)
    if not text:
        return JsonResponse({'ok': False, 'detail': 'empty'}, status=400)
    msg = ChatMessage.objects.create(sender=user, receiver=partner, text=text, message_type='text')
    return JsonResponse({'ok': True, 'id': msg.id})


@require_GET
def client_users(request):
    user = _token_user(request)
    if user is None:
        return _unauthorized()
    from django.contrib.auth.models import User
    from django.utils import timezone
    from datetime import timedelta
    from chat.models import ChatMessage

    cutoff = timezone.now() - timedelta(minutes=7)
    out = []
    for u in User.objects.filter(is_active=True).exclude(id=user.id)[:60]:
        unread = ChatMessage.objects.filter(sender=u, receiver=user, is_read=False).count()
        online = False
        try:
            pr = u.profile
            online = bool(pr.last_seen and pr.last_seen > cutoff)
        except Exception:
            pass
        out.append({'username': u.username, 'unread': unread, 'online': online})
    return JsonResponse({'ok': True, 'users': out})


@csrf_exempt
@require_POST
def client_wishlist_toggle(request):
    user = _token_user(request)
    if user is None:
        return _unauthorized()
    from cart.models import Wishlist
    data = _json_body(request)
    try:
        game_id = int(data.get('game_id') or 0)
    except (TypeError, ValueError):
        game_id = 0
    game = Game.objects.filter(id=game_id).first()
    if game is None:
        return JsonResponse({'ok': False, 'detail': 'game_not_found'}, status=404)
    wl, created = Wishlist.objects.get_or_create(user=user, game=game)
    if not created:
        wl.delete()
    return JsonResponse({'ok': True, 'in_wishlist': created})


@csrf_exempt
@require_POST
def client_bonus(request):
    user = _token_user(request)
    if user is None:
        return _unauthorized()
    from django.utils import timezone
    from decimal import Decimal
    from users.models import Profile

    profile, _ = Profile.objects.get_or_create(user=user)
    today = timezone.localdate()
    if profile.last_daily_bonus == today:
        return JsonResponse({'ok': False, 'detail': 'already_claimed',
                             'streak': profile.daily_streak})
    profile.last_daily_bonus = today
    profile.daily_streak = (profile.daily_streak or 0) + 1
    profile.balance += Decimal('500')
    profile.save(update_fields=['last_daily_bonus', 'daily_streak', 'balance'])
    return JsonResponse({'ok': True, 'amount': '500.00',
                         'balance': str(profile.balance), 'streak': profile.daily_streak})


# ============================================================ QR login
# Пользователь на сайте (с телефона) открывает /launcher-api/qr/<code>/
# и жмёт "Подтвердить" - лаунчер с этим кодом автоматически логинится.
# Код живёт 3 минуты, одноразовый.

import secrets

_qr_pending = {}  # code -> {'created': ts, 'user_id': None|id, 'approved': bool}
QR_TTL = 180  # 3 минуты


def _qr_cleanup():
    now = time.time()
    for c in [c for c, v in _qr_pending.items() if now - v["created"] > QR_TTL]:
        _qr_pending.pop(c, None)


# Ограничение QR: кулдаун 15 сек; каждые 5 QR -> бан \n# с эскалацией: 20 мин -> 1 ч -> 2 ч -> 4 ч
QR_COOLDOWN = 15
QR_FREE_PER_CYCLE = 5
QR_BAN_STEPS_MIN = [20, 60, 120, 240]
_qr_rate = {}  # ip -> {'last': ts}
_qr_bans = {}  # ip -> {'count': n, 'banned_until': ts, 'strikes': n}


def _qr_rate_check(ip):
    now = time.time()
    rec = _qr_rate.setdefault(ip, {"last": 0})
    if now - rec["last"] < QR_COOLDOWN:
        return int(QR_COOLDOWN - (now - rec["last"])) + 1
    rec["last"] = now
    return 0


def _qr_ban_left(ip):
    now = time.time()
    rec = _qr_bans.get(ip)
    if rec and now < rec["banned_until"]:
        return int(rec["banned_until"] - now) + 1
    return 0


def _qr_register_create(ip):
    """Учитывает создание QR. Возвращает минуты бана или 0."""
    rec = _qr_bans.setdefault(ip, {"count": 0, "banned_until": 0, "strikes": 0})
    rec["count"] += 1
    if rec["count"] >= QR_FREE_PER_CYCLE:
        rec["strikes"] += 1
        minutes = QR_BAN_STEPS_MIN[min(rec["strikes"] - 1, len(QR_BAN_STEPS_MIN) - 1)]
        rec["banned_until"] = time.time() + minutes * 60
        rec["count"] = 0
        return minutes
    return 0


def _lan_ip():
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def _is_private_host(host):
    """True для localhost / приватного IP, False для публичного домена."""
    name = host.split(":")[0].strip().lower()
    if name in ("localhost", "0.0.0.0"):
        return True
    try:
        import ipaddress
        ip = ipaddress.ip_address(name)
        return ip.is_private or ip.is_loopback
    except ValueError:
        return False  # это домен (pythonanywhere.com и т.п.)


def _public_base(request):
    """Базовый адрес для QR-ссылки.

    - Локальный запуск (127.0.0.1 / приватный IP) -> http://<LAN-IP>:<port>,
      чтобы телефон в той же Wi-Fi сети мог открыть ссылку.
    - Хостинг (публичный домен)            -> https://<домен>,
      ссылка открывается с телефона откуда угодно.
    """
    host = request.get_host()
    if _is_private_host(host):
        port = host.split(":")[1] if ":" in host else "8000"
        return f"http://{_lan_ip()}:{port}"
    scheme = "https" if request.is_secure() else "http"
    forwarded = request.META.get("HTTP_X_FORWARDED_PROTO", "")
    if forwarded:
        scheme = forwarded.split(",")[0].strip()
    return f"{scheme}://{host}"


def _qr_approve_url(request, code):
    return f"{_public_base(request)}/launcher-api/qr/{code}/"


@require_GET
def client_ping(request):
    """Проверка адреса сервера из лаунчера (работает и на хостинге)."""
    return JsonResponse({
        "ok": True,
        "server": "steam-clone",
        "launcher_api": 1,
        "host": request.get_host(),
    })


@csrf_exempt
@require_POST
def client_qr_create(request):
    ip = request.META.get("REMOTE_ADDR", "?")
    left = _qr_ban_left(ip)
    if left:
        return JsonResponse({"ok": False, "detail": "banned",
                             "retry_after": left}, status=429)
    wait = _qr_rate_check(ip)
    if wait:
        return JsonResponse({"ok": False, "detail": "rate_limited",
                             "retry_after": wait}, status=429)
    ban_minutes = _qr_register_create(ip)
    _qr_cleanup()
    code = secrets.token_urlsafe(12)
    _qr_pending[code] = {"created": time.time(), "user_id": None, "approved": False}
    full_url = _qr_approve_url(request, code)
    return JsonResponse({"ok": True, "code": code,
                         "approve_url": f"/launcher-api/qr/{code}/",
                         "full_url": full_url,
                         "next_ban_minutes": ban_minutes or 0,
                         "ttl": QR_TTL})


@require_GET
def client_qr_status(request):
    code = request.GET.get("code", "")
    v = _qr_pending.get(code)
    if v is None:
        return JsonResponse({"ok": False, "detail": "expired"}, status=404)
    _qr_cleanup()
    if v["approved"] and v["user_id"]:
        from rest_framework.authtoken.models import Token
        from django.contrib.auth.models import User
        user = User.objects.get(id=v["user_id"])
        token, _ = Token.objects.get_or_create(user=user)
        _qr_pending.pop(code, None)  # одноразовый
        return JsonResponse({"ok": True, "approved": True,
                             "token": token.key, "username": user.username})
    return JsonResponse({"ok": True, "approved": False})


def qr_approve_page(request, code):
    """Страница подтверждения (открывается с телефона)."""
    from django.shortcuts import render, get_object_or_404
    from django.contrib.auth.decorators import login_required

    _qr_cleanup()
    v = _qr_pending.get(code)
    if v is None:
        return render(request, "launcher_api/qr_page.html", {"expired": True})

    if request.method == "POST":
        if not request.user.is_authenticated:
            return render(request, "launcher_api/qr_page.html",
                          {"need_login": True, "code": code})
        v["user_id"] = request.user.id
        v["approved"] = True
        return render(request, "launcher_api/qr_page.html", {"done": True})

    return render(request, "launcher_api/qr_page.html", {"code": code})


# ============================================================ register
@csrf_exempt
@require_POST
def client_register(request):
    from django.contrib.auth.models import User
    from rest_framework.authtoken.models import Token
    from users.models import Profile
    import re

    data = _json_body(request)
    username = str(data.get("username") or "").strip()
    password = str(data.get("password") or "")
    email = str(data.get("email") or "").strip()

    if not username or not password:
        return JsonResponse({"ok": False, "detail": "Введите логин и пароль"}, status=400)
    if not re.match(r"^[a-zA-Z0-9_]{3,20}$", username):
        return JsonResponse({"ok": False, "detail": "Логин: 3-20 символов, только латиница, цифры, _"}, status=400)
    if len(password) < 6:
        return JsonResponse({"ok": False, "detail": "Пароль минимум 6 символов"}, status=400)
    if User.objects.filter(username__iexact=username).exists():
        return JsonResponse({"ok": False, "detail": "Этот логин уже занят"}, status=409)
    if email and User.objects.filter(email__iexact=email).exists():
        return JsonResponse({"ok": False, "detail": "Этот email уже занят"}, status=409)

    user = User.objects.create_user(username=username, email=email, password=password)
    Profile.objects.get_or_create(user=user, defaults={"balance": 1000})
    token, _ = Token.objects.get_or_create(user=user)
    return JsonResponse({"ok": True, "token": token.key, "username": username,
                         "detail": "Аккаунт создан! Бонус: 1000 UZS"})


# ============================================================ profile
@require_GET
def client_profile(request):
    user = _token_user(request)
    if user is None:
        return _unauthorized()
    from achievements.models import Achievement
    from users.models import Profile
    from cart.models import Purchase

    try:
        pr = user.profile
    except Exception:
        pr, _ = Profile.objects.get_or_create(user=user)
    try:
        avatar = pr.avatar.url if pr.avatar else ""
    except Exception:
        avatar = ""
    achs = []
    for ua in user.achievements.select_related("achievement").order_by("-unlocked_at")[:12]:
        a = ua.achievement
        try:
            icon = a.icon.url if getattr(a, "icon", None) else ""
        except Exception:
            icon = ""
        achs.append({"name": a.name, "description": a.description, "icon": icon})
    return JsonResponse({
        "ok": True,
        "username": user.username,
        "email": user.email,
        "avatar_url": avatar,
        "balance": str(pr.balance),
        "xp": pr.xp,
        "level": pr.steam_level,
        "steam_points": pr.steam_points,
        "status": pr.status_label,
        "daily_streak": pr.daily_streak,
        "games_owned": Purchase.objects.filter(user=user).count(),
        "achievements": achs,
    })


@require_GET
def client_qr_img(request):
    """PNG QR-код со ссылкой на подтверждение (URL с LAN-IP для телефона)."""
    import io as _io
    import qrcode
    from django.http import HttpResponse

    code = request.GET.get("code", "")
    ext_url = _qr_approve_url(request, code)
    img = qrcode.make(ext_url)
    buf = _io.BytesIO()
    img.save(buf, format="PNG")
    resp = HttpResponse(buf.getvalue(), content_type="image/png")
    resp["Cache-Control"] = "no-store"
    return resp
