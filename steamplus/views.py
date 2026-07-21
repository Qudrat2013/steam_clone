import random
from datetime import timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Q, Count, Sum, Avg
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from cart.models import Purchase, Wishlist
from friends.models import Friendship
from games.models import Game, Review
from notifications.utils import create_notification
from achievements.utils import give_achievement

from .models import (
    Activity, DailyBonusClaim, DiscoverySkip, GameNews, Gift,
    Playtime, PointsPurchase, PointsShopItem, SaleEvent,
)
from .utils import log_activity, record_play_session


def _friend_ids(user):
    ids = set()
    for f in Friendship.objects.filter(Q(user1=user) | Q(user2=user)):
        ids.add(f.user2_id if f.user1_id == user.id else f.user1_id)
    return ids


@login_required
def discovery_queue(request):
    """Очередь открытий Steam — рекомендуемые игры по одной."""
    owned = Purchase.objects.filter(user=request.user).values_list('game_id', flat=True)
    skipped = DiscoverySkip.objects.filter(user=request.user).values_list('game_id', flat=True)
    wishlist = Wishlist.objects.filter(user=request.user).values_list('game_id', flat=True)

    qs = (
        Game.objects.filter(is_active=True)
        .exclude(id__in=owned)
        .exclude(id__in=skipped)
        .annotate(review_count=Count('reviews'))
        .order_by('-is_featured', '-discount', '-review_count', '-created_at')
    )

    # лёгкая персонализация по категориям купленных
    owned_cats = (
        Game.objects.filter(id__in=owned)
        .exclude(category=None)
        .values_list('category_id', flat=True)
    )
    preferred = list(qs.filter(category_id__in=owned_cats)[:20])
    rest = list(qs.exclude(id__in=[g.id for g in preferred])[:30])
    pool = preferred + rest
    random.shuffle(pool)

    remaining = len(pool)
    game = pool[0] if pool else None
    positive = 0
    total = 0
    if game:
        revs = game.reviews.all()
        total = revs.count()
        positive = revs.filter(rating=True).count()

    context = {
        'game': game,
        'remaining': remaining,
        'in_wishlist': game.id in wishlist if game else False,
        'rating_percent': int((positive / total) * 100) if total else 0,
        'total_reviews': total,
    }
    return render(request, 'steamplus/discovery.html', context)


@login_required
@require_POST
def discovery_action(request, game_id):
    game = get_object_or_404(Game, id=game_id, is_active=True)
    action = request.POST.get('action')

    if action == 'skip':
        DiscoverySkip.objects.get_or_create(user=request.user, game=game)
        messages.info(request, f'«{game.title}» — не интересно')
    elif action == 'wishlist':
        Wishlist.objects.get_or_create(user=request.user, game=game)
        DiscoverySkip.objects.get_or_create(user=request.user, game=game)
        messages.success(request, f'«{game.title}» в списке желаемого')
    elif action == 'interested':
        DiscoverySkip.objects.get_or_create(user=request.user, game=game)
        messages.success(request, f'Отметили интерес к «{game.title}»')

    return redirect('discovery_queue')


@login_required
def activity_feed(request):
    """Лента друзей + своя активность."""
    fids = _friend_ids(request.user)
    user_ids = list(fids) + [request.user.id]
    activities = (
        Activity.objects.filter(user_id__in=user_ids)
        .select_related('user', 'game', 'user__profile')[:80]
    )
    online_friends = (
        User.objects.filter(id__in=fids, profile__status='online')
        .select_related('profile')[:20]
    )
    return render(request, 'steamplus/activity.html', {
        'activities': activities,
        'online_friends': online_friends,
    })


@login_required
def play_game(request, game_id):
    """«Играть» — запись сессии + очки + статус В игре."""
    purchase = get_object_or_404(Purchase, user=request.user, game_id=game_id)
    game = purchase.game
    minutes = int(request.POST.get('minutes', 15) or 15)
    minutes = max(5, min(minutes, 180))

    pt = record_play_session(request.user, game, minutes=minutes)
    try:
        request.user.profile.add_xp(2)
    except Exception:
        pass

    if pt.sessions == 1:
        give_achievement(request.user, 'Первый запуск', 'Запустите игру впервые')
        log_activity(request.user, 'achievement', 'получил достижение «Первый запуск»', game=game)

    if pt.minutes >= 60:
        give_achievement(request.user, 'Час в деле', 'Сыграйте 1 час в любой игре')

    messages.success(
        request,
        f'Сессия «{game.title}»: +{minutes} мин. Всего {pt.hours_display}. +{max(1, minutes // 5)} очков Steam.',
    )

    # Если есть файл — предложить скачать
    if game.game_file and request.GET.get('download') == '1':
        return redirect('download_game', game_id=game.id)

    return redirect(request.META.get('HTTP_REFERER', 'library'))


@login_required
def gift_game(request, game_id):
    game = get_object_or_404(Game, id=game_id, is_active=True)
    fids = _friend_ids(request.user)
    friends = User.objects.filter(id__in=fids).order_by('username')

    if request.method == 'POST':
        receiver_id = request.POST.get('receiver')
        message_text = (request.POST.get('message') or '')[:250]
        receiver = get_object_or_404(User, id=receiver_id)

        if receiver.id not in fids:
            messages.error(request, 'Дарить можно только друзьям')
            return redirect('gift_game', game_id=game.id)

        if Purchase.objects.filter(user=receiver, game=game).exists():
            messages.error(request, f'У {receiver.username} уже есть эта игра')
            return redirect('gift_game', game_id=game.id)

        if Gift.objects.filter(receiver=receiver, game=game, status='pending').exists():
            messages.error(request, 'Уже есть ожидающий подарок этой игры этому другу')
            return redirect('gift_game', game_id=game.id)

        price = game.get_discounted_price()
        profile = request.user.profile
        if profile.balance < price:
            messages.error(request, f'Недостаточно средств. Нужно {price} UZS')
            return redirect('gift_game', game_id=game.id)

        with transaction.atomic():
            profile.balance -= Decimal(price)
            profile.save(update_fields=['balance'])
            gift = Gift.objects.create(
                sender=request.user,
                receiver=receiver,
                game=game,
                message=message_text,
                price_paid=price,
            )
            log_activity(
                request.user,
                'gift',
                f'отправил подарок «{game.title}» пользователю {receiver.username}',
                game=game,
            )
            try:
                create_notification(
                    receiver,
                    f'{request.user.username} подарил вам «{game.title}»!',
                    link='/plus/gifts/',
                )
            except Exception:
                pass

        messages.success(request, f'Подарок отправлен {receiver.username}!')
        return redirect('gifts_inbox')

    return render(request, 'steamplus/gift.html', {
        'game': game,
        'friends': friends,
        'price': game.get_discounted_price(),
    })


@login_required
def gifts_inbox(request):
    incoming = (
        Gift.objects.filter(receiver=request.user)
        .select_related('sender', 'game')
        .order_by('-created_at')
    )
    outgoing = (
        Gift.objects.filter(sender=request.user)
        .select_related('receiver', 'game')
        .order_by('-created_at')
    )
    return render(request, 'steamplus/gifts.html', {
        'incoming': incoming,
        'outgoing': outgoing,
    })


@login_required
@require_POST
def gift_respond(request, gift_id):
    gift = get_object_or_404(Gift, id=gift_id, receiver=request.user, status='pending')
    action = request.POST.get('action')

    if action == 'accept':
        with transaction.atomic():
            gift.status = 'accepted'
            gift.resolved_at = timezone.now()
            gift.save()
            Purchase.objects.get_or_create(
                user=request.user,
                game=gift.game,
                defaults={'price_paid': 0},
            )
            log_activity(
                request.user,
                'gift',
                f'принял подарок «{gift.game.title}» от {gift.sender.username}',
                game=gift.game,
            )
            try:
                request.user.profile.add_xp(5)
                request.user.profile.steam_points += 25
                request.user.profile.save(update_fields=['xp', 'steam_level', 'steam_points'])
            except Exception:
                pass
            give_achievement(request.user, 'Щедрый друг', 'Примите подарок')
        messages.success(request, f'«{gift.game.title}» добавлена в библиотеку!')
    elif action == 'decline':
        with transaction.atomic():
            gift.status = 'declined'
            gift.resolved_at = timezone.now()
            gift.save()
            # возврат денег отправителю
            sender_profile = gift.sender.profile
            sender_profile.balance += gift.price_paid
            sender_profile.save(update_fields=['balance'])
        messages.info(request, 'Подарок отклонён, средства возвращены отправителю')

    return redirect('gifts_inbox')


@login_required
def points_shop(request):
    items = PointsShopItem.objects.filter(is_active=True).order_by('cost')
    history = PointsPurchase.objects.filter(user=request.user).select_related('item')[:20]
    return render(request, 'steamplus/points_shop.html', {
        'items': items,
        'history': history,
        'points': request.user.profile.steam_points,
    })


@login_required
@require_POST
def buy_points_item(request, item_id):
    item = get_object_or_404(PointsShopItem, id=item_id, is_active=True)
    profile = request.user.profile

    if profile.steam_points < item.cost:
        messages.error(request, f'Недостаточно очков. Нужно {item.cost}, у вас {profile.steam_points}')
        return redirect('points_shop')

    with transaction.atomic():
        profile.steam_points -= item.cost
        if item.reward_type == 'xp':
            profile.add_xp(item.reward_value)
        elif item.reward_type == 'balance':
            profile.balance += Decimal(item.reward_value)
            profile.save()
        elif item.reward_type == 'badge':
            give_achievement(request.user, item.name, item.description or item.name)
            profile.save(update_fields=['steam_points'])
        else:
            profile.save(update_fields=['steam_points'])

        PointsPurchase.objects.create(user=request.user, item=item, cost_paid=item.cost)
        log_activity(request.user, 'level', f'купил в Points Shop: {item.name}')

    messages.success(request, f'Куплено: {item.name}!')
    return redirect('points_shop')


@login_required
@require_POST
def set_status(request):
    status = request.POST.get('status', 'online')
    custom = (request.POST.get('custom_status') or '')[:80]
    allowed = {c[0] for c in request.user.profile.STATUS_CHOICES}
    if status not in allowed:
        status = 'online'
    profile = request.user.profile
    profile.status = status
    profile.custom_status = custom
    profile.last_seen = timezone.now()
    profile.save(update_fields=['status', 'custom_status', 'last_seen'])
    messages.success(request, 'Статус обновлён')
    return redirect(request.META.get('HTTP_REFERER', '/'))


def search_suggest(request):
    """AJAX-подсказки поиска как в Steam."""
    q = (request.GET.get('q') or '').strip()
    if len(q) < 2:
        return JsonResponse({'results': []})

    games = Game.objects.filter(is_active=True).filter(
        Q(title__icontains=q) | Q(developer__icontains=q)
    )[:8]

    results = []
    for g in games:
        results.append({
            'title': g.title,
            'url': g.get_absolute_url(),
            'price': str(g.get_discounted_price()),
            'discount': g.discount,
            'image': g.header_image.url if g.header_image else '',
            'developer': g.developer,
        })
    return JsonResponse({'results': results})


def news_list(request):
    news = GameNews.objects.select_related('game')[:40]
    return render(request, 'steamplus/news.html', {'news_list': news})


def game_news(request, slug):
    game = get_object_or_404(Game, slug=slug, is_active=True)
    news = game.news.all()[:30]
    return render(request, 'steamplus/game_news.html', {'game': game, 'news_list': news})


@login_required
def recently_played(request):
    playtimes = (
        Playtime.objects.filter(user=request.user)
        .select_related('game')
        .order_by('-last_played')[:30]
    )
    return render(request, 'steamplus/recent.html', {'playtimes': playtimes})


@login_required
def friends_playing(request):
    """Друзья в сети / во что играют — как Friends & Chat sidebar."""
    fids = _friend_ids(request.user)
    friends = (
        User.objects.filter(id__in=fids)
        .select_related('profile')
        .order_by('-profile__status', '-profile__last_seen')
    )
    friend_play = (
        Playtime.objects.filter(user_id__in=fids)
        .select_related('user', 'game')
        .order_by('-last_played')[:20]
    )
    return render(request, 'steamplus/friends_playing.html', {
        'friends': friends,
        'friend_play': friend_play,
    })


@login_required
def daily_bonus(request):
    """Ежедневный бонус + streak (как Steam login rewards)."""
    profile = request.user.profile
    today = timezone.localdate()
    already = profile.last_daily_bonus == today
    claim = None

    if request.method == 'POST' and not already:
        yesterday = today - timedelta(days=1)
        streak = (profile.daily_streak + 1) if profile.last_daily_bonus == yesterday else 1
        points = 25 + min(streak * 5, 75)  # 30..100
        xp = 5 + min(streak, 15)

        with transaction.atomic():
            profile.steam_points = (profile.steam_points or 0) + points
            profile.last_daily_bonus = today
            profile.daily_streak = streak
            profile.save(update_fields=['steam_points', 'last_daily_bonus', 'daily_streak'])
            profile.add_xp(xp)
            claim = DailyBonusClaim.objects.create(
                user=request.user,
                claim_date=today,
                points_awarded=points,
                xp_awarded=xp,
                streak=streak,
            )
            log_activity(
                request.user,
                'level',
                f'забрал daily bonus: +{points} очков, серия {streak} дн.',
            )
            if streak >= 7:
                give_achievement(request.user, 'Неделя в Steam', 'Заходите 7 дней подряд')
            if streak >= 30:
                give_achievement(request.user, 'Легенда daily', 'Серия 30 дней')

        already = True
        messages.success(request, f'+{points} очков, +{xp} XP! Серия: {streak} дн.')
        return redirect('daily_bonus')

    history = DailyBonusClaim.objects.filter(user=request.user)[:14]
    if already:
        preview_streak = profile.daily_streak
        # завтрашняя награда
        next_points = 25 + min((profile.daily_streak + 1) * 5, 75)
    else:
        preview_streak = (
            profile.daily_streak + 1
            if profile.last_daily_bonus == today - timedelta(days=1)
            else 1
        )
        next_points = 25 + min(preview_streak * 5, 75)

    return render(request, 'steamplus/daily.html', {
        'already': already,
        'streak': profile.daily_streak,
        'preview_streak': preview_streak,
        'next_points': next_points,
        'history': history,
        'points': profile.steam_points,
    })


def leaderboard(request):
    """Топы: уровень, playtime, points."""
    tab = request.GET.get('tab', 'level')
    by_level = (
        User.objects.filter(profile__isnull=False)
        .select_related('profile')
        .order_by('-profile__steam_level', '-profile__xp')[:25]
    )
    by_points = (
        User.objects.filter(profile__isnull=False)
        .select_related('profile')
        .order_by('-profile__steam_points')[:25]
    )
    by_play = (
        Playtime.objects.values('user_id', 'user__username')
        .annotate(total_min=Sum('minutes'))
        .order_by('-total_min')[:25]
    )
    return render(request, 'steamplus/leaderboard.html', {
        'tab': tab,
        'by_level': by_level,
        'by_points': by_points,
        'by_play': by_play,
    })


@login_required
def recommendations(request):
    """«Вам может понравиться» по категориям библиотеки."""
    owned_ids = list(Purchase.objects.filter(user=request.user).values_list('game_id', flat=True))
    wishlist_ids = list(Wishlist.objects.filter(user=request.user).values_list('game_id', flat=True))
    cats = (
        Game.objects.filter(id__in=owned_ids)
        .exclude(category=None)
        .values_list('category_id', flat=True)
    )
    tags = (
        Game.objects.filter(id__in=owned_ids)
        .values_list('tags', flat=True)
    )

    qs = (
        Game.objects.filter(is_active=True)
        .exclude(id__in=owned_ids)
        .annotate(review_count=Count('reviews'), pos=Count('reviews', filter=Q(reviews__rating=True)))
    )
    preferred = qs.filter(Q(category_id__in=cats) | Q(tags__in=tags)).distinct()
    games = list(preferred.order_by('-is_featured', '-discount', '-review_count')[:18])
    if len(games) < 12:
        extra = list(
            qs.exclude(id__in=[g.id for g in games])
            .order_by('-discount', '-review_count')[:12 - len(games)]
        )
        games.extend(extra)

    recs = []
    for g in games:
        if g.category_id in cats:
            reason = f'Потому что вы играете в {g.category.name if g.category else "похожие"}'
        elif g.discount >= 30:
            reason = f'Горячая скидка −{g.discount}%'
        else:
            reason = 'Популярно в сообществе'
        recs.append({'game': g, 'reason': reason, 'in_wishlist': g.id in wishlist_ids})

    return render(request, 'steamplus/recommendations.html', {
        'recs': recs,
    })


def random_game(request):
    """«Удиви меня» — случайная игра из магазина."""
    owned = []
    if request.user.is_authenticated:
        owned = list(Purchase.objects.filter(user=request.user).values_list('game_id', flat=True))
    qs = Game.objects.filter(is_active=True).exclude(id__in=owned)
    count = qs.count()
    game = None
    if count:
        game = qs[random.randint(0, count - 1)]
    return render(request, 'steamplus/random.html', {'game': game})


def sales_hub(request):
    """Страница распродаж + топ скидок."""
    now = timezone.now()
    live = SaleEvent.objects.filter(is_active=True, starts_at__lte=now, ends_at__gte=now)
    upcoming = SaleEvent.objects.filter(is_active=True, starts_at__gt=now)[:5]
    deals = (
        Game.objects.filter(is_active=True, discount__gt=0)
        .order_by('-discount', '-is_featured')[:24]
    )
    return render(request, 'steamplus/sales.html', {
        'live_sales': live,
        'upcoming': upcoming,
        'deals': deals,
    })


@login_required
def stats_dashboard(request):
    """Личная статистика как Steam year in review (упрощённо)."""
    playtimes = Playtime.objects.filter(user=request.user).select_related('game')
    total_min = playtimes.aggregate(t=Sum('minutes'))['t'] or 0
    total_sessions = playtimes.aggregate(t=Sum('sessions'))['t'] or 0
    top_games = playtimes.order_by('-minutes')[:5]
    library_count = Purchase.objects.filter(user=request.user).count()
    wishlist_count = Wishlist.objects.filter(user=request.user).count()
    review_count = Review.objects.filter(user=request.user).count()
    gifts_sent = Gift.objects.filter(sender=request.user).count()
    gifts_recv = Gift.objects.filter(receiver=request.user, status='accepted').count()
    achievements = request.user.achievements.count() if hasattr(request.user, 'achievements') else 0
    fids = _friend_ids(request.user)

    return render(request, 'steamplus/stats.html', {
        'total_min': total_min,
        'total_hours': round(total_min / 60, 1),
        'total_sessions': total_sessions,
        'top_games': top_games,
        'library_count': library_count,
        'wishlist_count': wishlist_count,
        'review_count': review_count,
        'gifts_sent': gifts_sent,
        'gifts_recv': gifts_recv,
        'achievements': achievements,
        'friends_count': len(fids),
        'level': request.user.profile.steam_level,
        'points': request.user.profile.steam_points,
        'streak': request.user.profile.daily_streak,
    })


@login_required
def compare_friends_library(request):
    """Какие игры есть у друзей, которых нет у вас."""
    fids = _friend_ids(request.user)
    my_games = set(Purchase.objects.filter(user=request.user).values_list('game_id', flat=True))
    friend_games = (
        Purchase.objects.filter(user_id__in=fids)
        .exclude(game_id__in=my_games)
        .values('game_id', 'game__title', 'game__slug', 'game__discount', 'game__price')
        .annotate(owners=Count('user', distinct=True))
        .order_by('-owners')[:30]
    )
    return render(request, 'steamplus/compare.html', {
        'friend_games': friend_games,
        'friends_count': len(fids),
    })
