from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncDate
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.text import slugify
from django.views.decorators.http import require_POST

from cart.models import Purchase
from games.models import Game, Review, Category, Tag
from inventory.models import InventoryItem, Item
from marketplace.models import MarketListing
from notifications.utils import create_notification
from trades.models import TradeOffer
from users.models import UserDevice
from wallet.models import BalanceRequest

from support.models import (
    AdminAuditLog,
    BroadcastMessage,
    FAQArticle,
    FAQCategory,
    PromoCode,
    RefundRequest,
    SupportTicket,
    TicketMessage,
    UserBan,
    UserReport,
)
from support.utils import log_admin_action
from steamplus.models import GameNews, SaleEvent


def is_admin(user):
    return user.is_authenticated and user.is_staff


# ─────────────────────────────────────────────
# HOME / STATS
# ─────────────────────────────────────────────

@login_required
@user_passes_test(is_admin)
def dashboard_home(request):
    now = timezone.now()
    week_ago = now - timedelta(days=7)

    pending_balance_count = BalanceRequest.objects.filter(status='pending').count()
    open_tickets = SupportTicket.objects.exclude(status__in=('resolved', 'closed')).count()
    pending_reports = UserReport.objects.filter(status='pending').count()
    pending_refunds = RefundRequest.objects.filter(status='pending').count()
    users_count = User.objects.count()
    new_users_week = User.objects.filter(date_joined__gte=week_ago).count()
    active_market_count = MarketListing.objects.filter(status='active').count()
    pending_trades_count = TradeOffer.objects.filter(status='pending').count()
    purchases_count = Purchase.objects.count()
    purchases_week = Purchase.objects.filter(purchased_at__gte=week_ago).count()
    items_count = Item.objects.count()
    games_count = Game.objects.count()
    active_bans = UserBan.objects.filter(is_active=True).count()
    try:
        revenue = Purchase.objects.aggregate(total=Sum('price_paid'))['total'] or Decimal('0')
        revenue_week = (
            Purchase.objects.filter(purchased_at__gte=week_ago)
            .aggregate(total=Sum('price_paid'))['total'] or Decimal('0')
        )
    except Exception:
        revenue = Decimal('0')
        revenue_week = Decimal('0')

    recent_tickets = (
        SupportTicket.objects.select_related('user')
        .exclude(status__in=('resolved', 'closed'))
        .order_by('-updated_at')[:8]
    )
    recent_reports = UserReport.objects.select_related('reporter', 'reported_user').filter(
        status='pending'
    )[:5]
    try:
        recent_purchases = list(
            Purchase.objects.select_related('user', 'game').order_by('-purchased_at')[:8]
        )
    except Exception:
        recent_purchases = []

    # chart data: purchases last 14 days
    days = []
    purchase_counts = []
    for i in range(13, -1, -1):
        day = (now - timedelta(days=i)).date()
        days.append(day.strftime('%d.%m'))
        purchase_counts.append(
            Purchase.objects.filter(purchased_at__date=day).count()
        )

    return render(request, 'dashboard/index.html', {
        'pending_balance_count': pending_balance_count,
        'open_tickets': open_tickets,
        'pending_reports': pending_reports,
        'pending_refunds': pending_refunds,
        'users_count': users_count,
        'new_users_week': new_users_week,
        'active_market_count': active_market_count,
        'pending_trades_count': pending_trades_count,
        'purchases_count': purchases_count,
        'purchases_week': purchases_week,
        'items_count': items_count,
        'games_count': games_count,
        'active_bans': active_bans,
        'revenue': revenue,
        'revenue_week': revenue_week,
        'recent_tickets': recent_tickets,
        'recent_reports': recent_reports,
        'recent_purchases': recent_purchases,
        'chart_labels': days,
        'chart_values': purchase_counts,
        'chart_max': max(purchase_counts) if purchase_counts else 1,
    })


# ─────────────────────────────────────────────
# BALANCE REQUESTS
# ─────────────────────────────────────────────

@login_required
@user_passes_test(is_admin)
def balance_requests_view(request):
    status = request.GET.get('status', 'pending')
    requests_qs = BalanceRequest.objects.select_related('user', 'user__profile')
    if status:
        requests_qs = requests_qs.filter(status=status)
    requests_qs = requests_qs.order_by('-created_at')
    return render(request, 'dashboard/balance_requests.html', {
        'requests': requests_qs,
        'status': status,
    })


@login_required
@user_passes_test(is_admin)
def approve_balance_request_view(request, request_id):
    balance_request = get_object_or_404(BalanceRequest, id=request_id)
    if balance_request.status != 'pending':
        messages.error(request, 'Эта заявка уже обработана.')
        return redirect('dashboard_balance_requests')

    profile = balance_request.user.profile
    profile.balance += balance_request.amount
    profile.save()

    balance_request.status = 'approved'
    balance_request.processed_at = timezone.now()
    balance_request.save()

    create_notification(
        balance_request.user,
        'Баланс пополнен',
        f'Ваша заявка на {balance_request.amount} одобрена.',
        'wallet',
        '/wallet/',
    )
    log_admin_action(
        request.user, 'approve_balance', 'BalanceRequest', balance_request.id,
        f'+{balance_request.amount} → {balance_request.user.username}', request,
    )
    messages.success(request, 'Заявка одобрена, баланс пополнен.')
    return redirect('dashboard_balance_requests')


@login_required
@user_passes_test(is_admin)
def decline_balance_request_view(request, request_id):
    balance_request = get_object_or_404(BalanceRequest, id=request_id)
    if balance_request.status != 'pending':
        messages.error(request, 'Эта заявка уже обработана.')
        return redirect('dashboard_balance_requests')

    balance_request.status = 'declined'
    balance_request.processed_at = timezone.now()
    balance_request.save()

    create_notification(
        balance_request.user,
        'Заявка отклонена',
        f'Ваша заявка на {balance_request.amount} отклонена.',
        'wallet',
        '/wallet/',
    )
    log_admin_action(
        request.user, 'decline_balance', 'BalanceRequest', balance_request.id,
        f'{balance_request.user.username}', request,
    )
    messages.info(request, 'Заявка отклонена.')
    return redirect('dashboard_balance_requests')


# ─────────────────────────────────────────────
# USERS
# ─────────────────────────────────────────────

@login_required
@user_passes_test(is_admin)
def dashboard_users_view(request):
    query = request.GET.get('q', '').strip()
    filter_by = request.GET.get('filter', '')
    users = User.objects.select_related('profile').order_by('-date_joined')

    if query:
        filters = Q(username__icontains=query) | Q(email__icontains=query)
        if query.isdigit():
            filters |= Q(id=int(query))
        users = users.filter(filters)

    if filter_by == 'staff':
        users = users.filter(is_staff=True)
    elif filter_by == 'inactive':
        users = users.filter(is_active=False)
    elif filter_by == 'banned':
        banned_ids = UserBan.objects.filter(is_active=True).values_list('user_id', flat=True)
        users = users.filter(id__in=banned_ids)

    return render(request, 'dashboard/users.html', {
        'users': users[:200],
        'query': query,
        'filter_by': filter_by,
    })


@login_required
@user_passes_test(is_admin)
def dashboard_user_detail_view(request, user_id):
    user_obj = get_object_or_404(User.objects.select_related('profile'), id=user_id)

    if request.method == 'POST':
        action = request.POST.get('action', 'save')

        if action == 'save':
            balance = request.POST.get('balance', '').strip()
            steam_level = request.POST.get('steam_level', '').strip()
            xp = request.POST.get('xp', '').strip()
            steam_points = request.POST.get('steam_points', '').strip()
            is_active = request.POST.get('is_active') == 'on'
            is_staff = request.POST.get('is_staff') == 'on'
            try:
                user_obj.profile.balance = Decimal(balance)
                user_obj.profile.steam_level = int(steam_level)
                user_obj.profile.xp = int(xp)
                if steam_points != '':
                    user_obj.profile.steam_points = int(steam_points)
                user_obj.profile.save()
                user_obj.is_active = is_active
                # prevent self-demotion lockout
                if user_obj.id != request.user.id:
                    user_obj.is_staff = is_staff
                user_obj.save()
                log_admin_action(
                    request.user, 'update_user', 'User', user_obj.id,
                    f'balance={balance} level={steam_level}', request,
                )
                messages.success(request, 'Пользователь обновлён.')
            except (InvalidOperation, ValueError, Exception):
                messages.error(request, 'Ошибка при сохранении данных.')
            return redirect('dashboard_user_detail', user_id=user_obj.id)

        if action == 'add_balance':
            try:
                amount = Decimal(request.POST.get('amount', '0'))
                user_obj.profile.balance += amount
                user_obj.profile.save(update_fields=['balance'])
                create_notification(
                    user_obj, 'Баланс изменён',
                    f'Администратор изменил баланс на {amount:+}',
                    'wallet', '/wallet/',
                )
                log_admin_action(
                    request.user, 'add_balance', 'User', user_obj.id,
                    f'{amount:+}', request,
                )
                messages.success(request, f'Баланс изменён на {amount:+}')
            except (InvalidOperation, ValueError):
                messages.error(request, 'Неверная сумма.')
            return redirect('dashboard_user_detail', user_id=user_obj.id)

        if action == 'give_item':
            item_id = request.POST.get('item_id')
            item = Item.objects.filter(id=item_id).first()
            if item:
                InventoryItem.objects.create(owner=user_obj, item=item)
                create_notification(
                    user_obj, 'Новый предмет',
                    f'Вам выдан предмет: {item.name}',
                    'inventory', '/inventory/',
                )
                log_admin_action(
                    request.user, 'give_item', 'User', user_obj.id,
                    f'item={item.name}', request,
                )
                messages.success(request, f'Предмет «{item.name}» выдан.')
            else:
                messages.error(request, 'Предмет не найден.')
            return redirect('dashboard_user_detail', user_id=user_obj.id)

        if action == 'give_game':
            game_id = request.POST.get('game_id')
            game = Game.objects.filter(id=game_id).first()
            if game:
                _, created = Purchase.objects.get_or_create(
                    user=user_obj, game=game,
                    defaults={'price_paid': Decimal('0.00')},
                )
                if created:
                    create_notification(
                        user_obj, 'Новая игра',
                        f'Вам выдана игра: {game.title}',
                        'purchase', f'/games/{game.slug}/',
                    )
                    log_admin_action(
                        request.user, 'give_game', 'User', user_obj.id,
                        f'game={game.title}', request,
                    )
                    messages.success(request, f'Игра «{game.title}» выдана.')
                else:
                    messages.info(request, 'Игра уже в библиотеке.')
            else:
                messages.error(request, 'Игра не найдена.')
            return redirect('dashboard_user_detail', user_id=user_obj.id)

        if action == 'ban':
            ban_type = request.POST.get('ban_type', 'full')
            reason = request.POST.get('reason', '').strip() or 'Нарушение правил'
            days = request.POST.get('days', '').strip()
            ends_at = None
            if days and days.isdigit() and int(days) > 0:
                ends_at = timezone.now() + timedelta(days=int(days))
            UserBan.objects.create(
                user=user_obj,
                banned_by=request.user,
                ban_type=ban_type if ban_type in dict(UserBan.BAN_TYPE_CHOICES) else 'full',
                reason=reason,
                ends_at=ends_at,
            )
            if ban_type in ('full', 'temp'):
                user_obj.is_active = False
                user_obj.save(update_fields=['is_active'])
            create_notification(
                user_obj, 'Ограничение аккаунта',
                f'На ваш аккаунт наложено ограничение: {reason}',
                'system', '/support/',
            )
            log_admin_action(
                request.user, 'ban_user', 'User', user_obj.id,
                f'{ban_type}: {reason}', request,
            )
            messages.warning(request, f'Бан выдан пользователю {user_obj.username}.')
            return redirect('dashboard_user_detail', user_id=user_obj.id)

        if action == 'unban':
            ban_id = request.POST.get('ban_id')
            ban = UserBan.objects.filter(id=ban_id, user=user_obj, is_active=True).first()
            if ban:
                ban.lift()
            if not UserBan.objects.filter(user=user_obj, is_active=True, ban_type__in=('full', 'temp')).exists():
                user_obj.is_active = True
                user_obj.save(update_fields=['is_active'])
            log_admin_action(request.user, 'unban_user', 'User', user_obj.id, '', request)
            messages.success(request, 'Ограничение снято.')
            return redirect('dashboard_user_detail', user_id=user_obj.id)

        if action == 'force_logout':
            UserDevice.objects.filter(user=user_obj).delete()
            log_admin_action(request.user, 'force_logout', 'User', user_obj.id, '', request)
            messages.success(request, 'Устройства / сессии сброшены.')
            return redirect('dashboard_user_detail', user_id=user_obj.id)

    inventory_items = InventoryItem.objects.filter(owner=user_obj).select_related('item', 'item__game')[:30]
    purchases = Purchase.objects.filter(user=user_obj).select_related('game')[:30]
    bans = UserBan.objects.filter(user=user_obj).select_related('banned_by')[:20]
    devices = UserDevice.objects.filter(user=user_obj).order_by('-last_activity')[:20]
    tickets = SupportTicket.objects.filter(user=user_obj)[:10]
    all_items = Item.objects.select_related('game').order_by('name')[:200]
    all_games = Game.objects.filter(is_active=True).order_by('title')[:200]

    return render(request, 'dashboard/user_detail.html', {
        'user_obj': user_obj,
        'inventory_items': inventory_items,
        'purchases': purchases,
        'bans': bans,
        'devices': devices,
        'tickets': tickets,
        'all_items': all_items,
        'all_games': all_games,
        'ban_types': UserBan.BAN_TYPE_CHOICES,
    })


# ─────────────────────────────────────────────
# MARKET / TRADES / PURCHASES
# ─────────────────────────────────────────────

@login_required
@user_passes_test(is_admin)
def dashboard_market_view(request):
    status = request.GET.get('status', '')
    listings = MarketListing.objects.select_related(
        'seller', 'buyer', 'inventory_item', 'inventory_item__item',
    ).order_by('-created_at')
    if status:
        listings = listings.filter(status=status)
    return render(request, 'dashboard/market.html', {
        'listings': listings[:150],
        'status': status,
    })


@login_required
@user_passes_test(is_admin)
@require_POST
def dashboard_market_cancel(request, listing_id):
    listing = get_object_or_404(MarketListing, id=listing_id)
    if listing.status == 'active':
        listing.status = 'cancelled'
        listing.save(update_fields=['status'])
        log_admin_action(request.user, 'cancel_listing', 'MarketListing', listing.id, '', request)
        messages.success(request, f'Лот #{listing.id} снят с маркета.')
    return redirect('dashboard_market')


@login_required
@user_passes_test(is_admin)
def dashboard_trades_view(request):
    status = request.GET.get('status', '')
    trades = TradeOffer.objects.select_related('sender', 'receiver').order_by('-created_at')
    if status:
        trades = trades.filter(status=status)
    return render(request, 'dashboard/trades.html', {
        'trades': trades[:150],
        'status': status,
    })


@login_required
@user_passes_test(is_admin)
def dashboard_purchases_view(request):
    q = request.GET.get('q', '').strip()
    purchases = Purchase.objects.select_related('user', 'game').order_by('-purchased_at')
    if q:
        purchases = purchases.filter(
            Q(user__username__icontains=q) | Q(game__title__icontains=q)
        )
    total = purchases.aggregate(s=Sum('price_paid'))['s'] or 0
    return render(request, 'dashboard/purchases.html', {
        'purchases': purchases[:200],
        'q': q,
        'total': total,
    })


# ─────────────────────────────────────────────
# GAMES
# ─────────────────────────────────────────────

@login_required
@user_passes_test(is_admin)
def dashboard_games_view(request):
    q = request.GET.get('q', '').strip()
    games = Game.objects.select_related('category').annotate(
        sales=Count('purchase_set'),
    ).order_by('-created_at')
    if q:
        games = games.filter(Q(title__icontains=q) | Q(developer__icontains=q))
    return render(request, 'dashboard/games.html', {
        'games': games[:200],
        'q': q,
    })


@login_required
@user_passes_test(is_admin)
def dashboard_game_edit(request, game_id=None):
    game = get_object_or_404(Game, id=game_id) if game_id else None
    categories = Category.objects.all()
    tags = Tag.objects.all()

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        if not title:
            messages.error(request, 'Название обязательно.')
            return redirect(request.path)

        if game is None:
            base_slug = slugify(title, allow_unicode=True) or 'game'
            slug = base_slug
            n = 1
            while Game.objects.filter(slug=slug).exists():
                slug = f'{base_slug}-{n}'
                n += 1
            game = Game(slug=slug)
            game.price = Decimal('0')
            game.release_date = timezone.now().date()
            game.developer = ''
            game.publisher = ''
            game.description = ''
            game.short_description = ''

        game.title = title
        game.developer = request.POST.get('developer', '')[:200]
        game.publisher = request.POST.get('publisher', '')[:200]
        game.description = request.POST.get('description', '')
        game.short_description = request.POST.get('short_description', '')[:300]
        try:
            game.price = Decimal(request.POST.get('price', '0') or '0')
            game.discount = int(request.POST.get('discount', '0') or '0')
        except (InvalidOperation, ValueError):
            messages.error(request, 'Неверная цена/скидка.')
            return redirect(request.path)

        cat_id = request.POST.get('category')
        game.category = Category.objects.filter(id=cat_id).first() if cat_id else None
        game.is_featured = request.POST.get('is_featured') == 'on'
        game.is_active = request.POST.get('is_active') == 'on'
        if request.FILES.get('header_image'):
            game.header_image = request.FILES['header_image']
        if request.FILES.get('background_image'):
            game.background_image = request.FILES['background_image']
        if request.FILES.get('game_file'):
            game.game_file = request.FILES['game_file']

        # ensure required fields for new games without image
        if not game.pk and not game.header_image:
            messages.error(request, 'Загрузите заглавное изображение.')
            return redirect(request.path)

        game.save()
        tag_ids = request.POST.getlist('tags')
        if tag_ids:
            game.tags.set(Tag.objects.filter(id__in=tag_ids))

        log_admin_action(
            request.user, 'save_game', 'Game', game.id, game.title, request,
        )
        messages.success(request, f'Игра «{game.title}» сохранена.')
        return redirect('dashboard_game_edit', game_id=game.id)

    return render(request, 'dashboard/game_edit.html', {
        'game': game,
        'categories': categories,
        'tags': tags,
    })


@login_required
@user_passes_test(is_admin)
@require_POST
def dashboard_game_toggle(request, game_id):
    game = get_object_or_404(Game, id=game_id)
    game.is_active = not game.is_active
    game.save(update_fields=['is_active'])
    log_admin_action(
        request.user, 'toggle_game', 'Game', game.id,
        f'active={game.is_active}', request,
    )
    messages.info(request, f'Игра «{game.title}»: active={game.is_active}')
    return redirect('dashboard_games')


# ─────────────────────────────────────────────
# SUPPORT TICKETS (admin)
# ─────────────────────────────────────────────

@login_required
@user_passes_test(is_admin)
def dashboard_tickets_view(request):
    status = request.GET.get('status', 'open')
    category = request.GET.get('category', '')
    q = request.GET.get('q', '').strip()

    tickets = SupportTicket.objects.select_related('user', 'assigned_to').annotate(
        msg_count=Count('messages'),
    )

    if status == 'open':
        tickets = tickets.exclude(status__in=('resolved', 'closed'))
    elif status:
        tickets = tickets.filter(status=status)

    if category:
        tickets = tickets.filter(category=category)
    if q:
        q_filter = Q(subject__icontains=q) | Q(user__username__icontains=q)
        if q.isdigit():
            q_filter |= Q(id=int(q))
        tickets = tickets.filter(q_filter)

    return render(request, 'dashboard/tickets.html', {
        'tickets': tickets.order_by('-updated_at')[:150],
        'status': status,
        'category': category,
        'q': q,
        'categories': SupportTicket.CATEGORY_CHOICES,
        'statuses': SupportTicket.STATUS_CHOICES,
    })


@login_required
@user_passes_test(is_admin)
def dashboard_ticket_detail(request, ticket_id):
    ticket = get_object_or_404(
        SupportTicket.objects.select_related('user', 'user__profile', 'assigned_to', 'related_game'),
        id=ticket_id,
    )
    ticket_messages = ticket.messages.select_related('author').all()

    if request.method == 'POST':
        action = request.POST.get('action', 'reply')

        if action == 'reply':
            body = request.POST.get('body', '').strip()
            is_internal = request.POST.get('is_internal') == 'on'
            if not body:
                messages.error(request, 'Пустое сообщение.')
                return redirect('dashboard_ticket_detail', ticket_id=ticket.id)

            TicketMessage.objects.create(
                ticket=ticket,
                author=request.user,
                body=body,
                is_staff_reply=True,
                is_internal=is_internal,
            )
            if not is_internal:
                ticket.status = 'waiting_user'
                ticket.assigned_to = ticket.assigned_to or request.user
                ticket.save(update_fields=['status', 'assigned_to', 'updated_at'])
                create_notification(
                    ticket.user,
                    f'Ответ по тикету #{ticket.id}',
                    body[:120],
                    'support',
                    f'/support/tickets/{ticket.id}/',
                )
            log_admin_action(request.user, 'ticket_reply', 'SupportTicket', ticket.id, '', request)
            messages.success(request, 'Ответ отправлен.')
            return redirect('dashboard_ticket_detail', ticket_id=ticket.id)

        if action == 'update':
            ticket.status = request.POST.get('status', ticket.status)
            ticket.priority = request.POST.get('priority', ticket.priority)
            ticket.category = request.POST.get('category', ticket.category)
            assign = request.POST.get('assigned_to', '')
            if assign == 'me':
                ticket.assigned_to = request.user
            elif assign == 'none':
                ticket.assigned_to = None
            if ticket.status in ('resolved', 'closed') and not ticket.closed_at:
                ticket.closed_at = timezone.now()
            ticket.save()
            if ticket.status in ('resolved', 'closed'):
                create_notification(
                    ticket.user,
                    f'Тикет #{ticket.id} {ticket.get_status_display().lower()}',
                    ticket.subject,
                    'support',
                    f'/support/tickets/{ticket.id}/',
                )
            log_admin_action(
                request.user, 'ticket_update', 'SupportTicket', ticket.id,
                f'status={ticket.status}', request,
            )
            messages.success(request, 'Тикет обновлён.')
            return redirect('dashboard_ticket_detail', ticket_id=ticket.id)

    return render(request, 'dashboard/ticket_detail.html', {
        'ticket': ticket,
        'ticket_messages': ticket_messages,
        'statuses': SupportTicket.STATUS_CHOICES,
        'priorities': SupportTicket.PRIORITY_CHOICES,
        'categories': SupportTicket.CATEGORY_CHOICES,
    })


# ─────────────────────────────────────────────
# REPORTS
# ─────────────────────────────────────────────

@login_required
@user_passes_test(is_admin)
def dashboard_reports_view(request):
    status = request.GET.get('status', 'pending')
    reports = UserReport.objects.select_related('reporter', 'reported_user', 'handled_by')
    if status:
        reports = reports.filter(status=status)
    return render(request, 'dashboard/reports.html', {
        'reports': reports.order_by('-created_at')[:150],
        'status': status,
        'statuses': UserReport.STATUS_CHOICES,
    })


@login_required
@user_passes_test(is_admin)
def dashboard_report_detail(request, report_id):
    report = get_object_or_404(
        UserReport.objects.select_related('reporter', 'reported_user'),
        id=report_id,
    )
    if request.method == 'POST':
        action = request.POST.get('action')
        note = request.POST.get('admin_note', '').strip()
        report.admin_note = note
        report.handled_by = request.user
        report.resolved_at = timezone.now()

        if action == 'dismiss':
            report.status = 'dismissed'
            report.save()
            create_notification(
                report.reporter, 'Жалоба рассмотрена',
                f'Жалоба #{report.id} отклонена.', 'system', '/support/',
            )
            messages.info(request, 'Жалоба отклонена.')
        elif action == 'action':
            report.status = 'action_taken'
            report.save()
            if report.reported_user and request.POST.get('ban_user') == 'on':
                UserBan.objects.create(
                    user=report.reported_user,
                    banned_by=request.user,
                    ban_type=request.POST.get('ban_type', 'community'),
                    reason=f'По жалобе #{report.id}: {report.get_reason_display()}',
                    ends_at=(
                        timezone.now() + timedelta(days=int(request.POST['days']))
                        if request.POST.get('days', '').isdigit() else None
                    ),
                )
                if request.POST.get('ban_type') in ('full', 'temp'):
                    report.reported_user.is_active = False
                    report.reported_user.save(update_fields=['is_active'])
            create_notification(
                report.reporter, 'Жалоба рассмотрена',
                f'По жалобе #{report.id} приняты меры.', 'system', '/support/',
            )
            messages.success(request, 'Меры приняты.')
        elif action == 'reviewing':
            report.status = 'reviewing'
            report.resolved_at = None
            report.save()
            messages.info(request, 'Статус: проверяется.')

        log_admin_action(
            request.user, f'report_{action}', 'UserReport', report.id, note, request,
        )
        return redirect('dashboard_reports')

    return render(request, 'dashboard/report_detail.html', {
        'report': report,
        'ban_types': UserBan.BAN_TYPE_CHOICES,
    })


# ─────────────────────────────────────────────
# BANS
# ─────────────────────────────────────────────

@login_required
@user_passes_test(is_admin)
def dashboard_bans_view(request):
    active_only = request.GET.get('active', '1') == '1'
    bans = UserBan.objects.select_related('user', 'banned_by').order_by('-created_at')
    if active_only:
        bans = bans.filter(is_active=True)
    return render(request, 'dashboard/bans.html', {
        'bans': bans[:200],
        'active_only': active_only,
    })


@login_required
@user_passes_test(is_admin)
@require_POST
def dashboard_ban_lift(request, ban_id):
    ban = get_object_or_404(UserBan, id=ban_id)
    ban.lift()
    if ban.ban_type in ('full', 'temp'):
        if not UserBan.objects.filter(
            user=ban.user, is_active=True, ban_type__in=('full', 'temp'),
        ).exists():
            ban.user.is_active = True
            ban.user.save(update_fields=['is_active'])
    log_admin_action(request.user, 'lift_ban', 'UserBan', ban.id, ban.user.username, request)
    messages.success(request, f'Бан #{ban.id} снят.')
    return redirect('dashboard_bans')


# ─────────────────────────────────────────────
# REFUNDS
# ─────────────────────────────────────────────

@login_required
@user_passes_test(is_admin)
def dashboard_refunds_view(request):
    status = request.GET.get('status', 'pending')
    refunds = RefundRequest.objects.select_related(
        'user', 'purchase', 'purchase__game', 'handled_by',
    )
    if status:
        refunds = refunds.filter(status=status)
    return render(request, 'dashboard/refunds.html', {
        'refunds': refunds.order_by('-created_at')[:150],
        'status': status,
    })


@login_required
@user_passes_test(is_admin)
@require_POST
def dashboard_refund_action(request, refund_id):
    refund = get_object_or_404(
        RefundRequest.objects.select_related('user', 'user__profile', 'purchase', 'purchase__game'),
        id=refund_id,
    )
    if refund.status != 'pending':
        messages.error(request, 'Заявка уже обработана.')
        return redirect('dashboard_refunds')

    action = request.POST.get('action')
    note = request.POST.get('admin_note', '').strip()
    refund.admin_note = note
    refund.handled_by = request.user
    refund.processed_at = timezone.now()

    game_title = refund.game_title or (
        refund.purchase.game.title if refund.purchase_id else 'игра'
    )
    amount = refund.amount or (refund.purchase.price_paid if refund.purchase_id else Decimal('0'))

    if action == 'approve':
        purchase_id = refund.purchase_id
        with transaction.atomic():
            refund.status = 'approved'
            refund.amount = amount
            refund.game_title = game_title
            refund.save()
            profile = refund.user.profile
            profile.balance += amount
            profile.save(update_fields=['balance'])
            if purchase_id:
                Purchase.objects.filter(pk=purchase_id).delete()
        create_notification(
            refund.user,
            'Возврат одобрен',
            f'Возврат за «{game_title}»: +{amount}',
            'wallet',
            '/wallet/',
        )
        log_admin_action(
            request.user, 'approve_refund', 'RefundRequest', refund.id, note, request,
        )
        messages.success(request, 'Возврат одобрен, средства возвращены.')
    else:
        refund.status = 'declined'
        refund.save()
        create_notification(
            refund.user,
            'Возврат отклонён',
            f'Заявка на возврат «{game_title}» отклонена. {note}',
            'wallet',
            '/support/refunds/',
        )
        log_admin_action(
            request.user, 'decline_refund', 'RefundRequest', refund.id, note, request,
        )
        messages.info(request, 'Возврат отклонён.')

    return redirect('dashboard_refunds')


# ─────────────────────────────────────────────
# REVIEWS MODERATION
# ─────────────────────────────────────────────

@login_required
@user_passes_test(is_admin)
def dashboard_reviews_view(request):
    q = request.GET.get('q', '').strip()
    reviews = Review.objects.select_related('user', 'game').order_by('-created_at')
    if q:
        reviews = reviews.filter(
            Q(text__icontains=q) | Q(user__username__icontains=q) | Q(game__title__icontains=q)
        )
    return render(request, 'dashboard/reviews.html', {
        'reviews': reviews[:200],
        'q': q,
    })


@login_required
@user_passes_test(is_admin)
@require_POST
def dashboard_review_delete(request, review_id):
    review = get_object_or_404(Review, id=review_id)
    log_admin_action(
        request.user, 'delete_review', 'Review', review.id,
        f'{review.user.username} / {review.game.title}', request,
    )
    review.delete()
    messages.success(request, 'Отзыв удалён.')
    return redirect('dashboard_reviews')


# ─────────────────────────────────────────────
# PROMO CODES
# ─────────────────────────────────────────────

@login_required
@user_passes_test(is_admin)
def dashboard_promos_view(request):
    promos = PromoCode.objects.select_related('game', 'created_by').order_by('-created_at')

    if request.method == 'POST':
        code = request.POST.get('code', '').strip().upper()
        reward_type = request.POST.get('reward_type', 'balance')
        try:
            reward_value = Decimal(request.POST.get('reward_value', '0') or '0')
            max_uses = int(request.POST.get('max_uses', '1') or '1')
        except (InvalidOperation, ValueError):
            messages.error(request, 'Неверные значения.')
            return redirect('dashboard_promos')

        if not code:
            messages.error(request, 'Укажите код.')
            return redirect('dashboard_promos')
        if PromoCode.objects.filter(code=code).exists():
            messages.error(request, 'Такой код уже есть.')
            return redirect('dashboard_promos')

        game = None
        game_id = request.POST.get('game_id')
        if game_id:
            game = Game.objects.filter(id=game_id).first()

        PromoCode.objects.create(
            code=code,
            description=request.POST.get('description', '')[:200],
            reward_type=reward_type if reward_type in dict(PromoCode.REWARD_CHOICES) else 'balance',
            reward_value=reward_value,
            game=game,
            max_uses=max(1, max_uses),
            created_by=request.user,
            is_active=True,
        )
        log_admin_action(request.user, 'create_promo', 'PromoCode', code, str(reward_value), request)
        messages.success(request, f'Промокод {code} создан.')
        return redirect('dashboard_promos')

    return render(request, 'dashboard/promos.html', {
        'promos': promos[:100],
        'reward_types': PromoCode.REWARD_CHOICES,
        'games': Game.objects.filter(is_active=True).order_by('title')[:200],
    })


@login_required
@user_passes_test(is_admin)
@require_POST
def dashboard_promo_toggle(request, promo_id):
    promo = get_object_or_404(PromoCode, id=promo_id)
    promo.is_active = not promo.is_active
    promo.save(update_fields=['is_active'])
    messages.info(request, f'Промокод {promo.code}: active={promo.is_active}')
    return redirect('dashboard_promos')


# ─────────────────────────────────────────────
# BROADCAST / NOTIFICATIONS
# ─────────────────────────────────────────────

@login_required
@user_passes_test(is_admin)
def dashboard_broadcast_view(request):
    history = BroadcastMessage.objects.select_related('created_by')[:30]

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        message = request.POST.get('message', '').strip()
        target = request.POST.get('target', 'all')
        if not title or not message:
            messages.error(request, 'Заполните заголовок и текст.')
            return redirect('dashboard_broadcast')

        if target == 'staff':
            users = User.objects.filter(is_staff=True, is_active=True)
        elif target == 'active':
            since = timezone.now() - timedelta(days=30)
            users = User.objects.filter(is_active=True, last_login__gte=since)
        else:
            users = User.objects.filter(is_active=True)
            target = 'all'

        count = 0
        for u in users.iterator():
            create_notification(u, title, message, 'system', '/')
            count += 1

        BroadcastMessage.objects.create(
            title=title,
            message=message,
            target=target,
            created_by=request.user,
            sent_count=count,
        )
        log_admin_action(
            request.user, 'broadcast', 'BroadcastMessage', '',
            f'{target}: {count} users — {title}', request,
        )
        messages.success(request, f'Рассылка отправлена {count} пользователям.')
        return redirect('dashboard_broadcast')

    return render(request, 'dashboard/broadcast.html', {
        'history': history,
        'targets': BroadcastMessage.TARGET_CHOICES,
    })


# ─────────────────────────────────────────────
# SALES / NEWS
# ─────────────────────────────────────────────

@login_required
@user_passes_test(is_admin)
def dashboard_sales_view(request):
    sales = SaleEvent.objects.order_by('-starts_at')

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        if not title:
            messages.error(request, 'Укажите название.')
            return redirect('dashboard_sales')
        try:
            starts = request.POST.get('starts_at')
            ends = request.POST.get('ends_at')
            extra = int(request.POST.get('extra_discount', '0') or '0')
            starts_at = timezone.datetime.fromisoformat(starts)
            ends_at = timezone.datetime.fromisoformat(ends)
            if timezone.is_naive(starts_at):
                starts_at = timezone.make_aware(starts_at)
            if timezone.is_naive(ends_at):
                ends_at = timezone.make_aware(ends_at)
        except (ValueError, TypeError):
            messages.error(request, 'Неверный формат дат (YYYY-MM-DDTHH:MM).')
            return redirect('dashboard_sales')

        SaleEvent.objects.create(
            title=title,
            subtitle=request.POST.get('subtitle', '')[:200],
            starts_at=starts_at,
            ends_at=ends_at,
            banner_color=request.POST.get('banner_color', '#1a9fff')[:20],
            extra_discount=max(0, min(90, extra)),
            is_active=request.POST.get('is_active') == 'on',
        )
        log_admin_action(request.user, 'create_sale', 'SaleEvent', title, '', request)
        messages.success(request, f'Распродажа «{title}» создана.')
        return redirect('dashboard_sales')

    return render(request, 'dashboard/sales.html', {'sales': sales[:50]})


@login_required
@user_passes_test(is_admin)
@require_POST
def dashboard_sale_toggle(request, sale_id):
    sale = get_object_or_404(SaleEvent, id=sale_id)
    sale.is_active = not sale.is_active
    sale.save(update_fields=['is_active'])
    messages.info(request, f'«{sale.title}»: active={sale.is_active}')
    return redirect('dashboard_sales')


@login_required
@user_passes_test(is_admin)
def dashboard_news_view(request):
    news = GameNews.objects.select_related('game').order_by('-created_at')[:100]
    games = Game.objects.filter(is_active=True).order_by('title')

    if request.method == 'POST':
        game_id = request.POST.get('game_id')
        title = request.POST.get('title', '').strip()
        body = request.POST.get('body', '').strip()
        game = Game.objects.filter(id=game_id).first()
        if not game or not title or not body:
            messages.error(request, 'Заполните все поля.')
            return redirect('dashboard_news')
        GameNews.objects.create(
            game=game,
            title=title[:200],
            body=body,
            is_update=request.POST.get('is_update') == 'on',
        )
        log_admin_action(request.user, 'create_news', 'GameNews', title, game.title, request)
        messages.success(request, 'Новость опубликована.')
        return redirect('dashboard_news')

    return render(request, 'dashboard/news.html', {'news': news, 'games': games})


# ─────────────────────────────────────────────
# FAQ admin
# ─────────────────────────────────────────────

@login_required
@user_passes_test(is_admin)
def dashboard_faq_view(request):
    categories = FAQCategory.objects.prefetch_related('articles').all()
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'category':
            name = request.POST.get('name', '').strip()
            if name:
                slug = slugify(name, allow_unicode=True) or f'cat-{timezone.now().timestamp():.0f}'
                FAQCategory.objects.get_or_create(slug=slug, defaults={'name': name})
                messages.success(request, f'Категория «{name}» создана.')
        elif action == 'article':
            cat_id = request.POST.get('category_id')
            title = request.POST.get('title', '').strip()
            body = request.POST.get('body', '').strip()
            cat = FAQCategory.objects.filter(id=cat_id).first()
            if cat and title and body:
                slug = slugify(title, allow_unicode=True) or f'faq-{timezone.now().timestamp():.0f}'
                base = slug
                n = 1
                while FAQArticle.objects.filter(slug=slug).exists():
                    slug = f'{base}-{n}'
                    n += 1
                FAQArticle.objects.create(category=cat, title=title, slug=slug, body=body)
                messages.success(request, f'Статья «{title}» создана.')
        return redirect('dashboard_faq')

    return render(request, 'dashboard/faq.html', {'categories': categories})


@login_required
@user_passes_test(is_admin)
@require_POST
def dashboard_faq_delete(request, article_id):
    article = get_object_or_404(FAQArticle, id=article_id)
    article.delete()
    messages.success(request, 'Статья удалена.')
    return redirect('dashboard_faq')


# ─────────────────────────────────────────────
# ITEMS
# ─────────────────────────────────────────────

@login_required
@user_passes_test(is_admin)
def dashboard_items_view(request):
    items = Item.objects.select_related('game').annotate(
        owners=Count('inventory_entries'),
    ).order_by('name')
    games = Game.objects.filter(is_active=True).order_by('title')

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        game_id = request.POST.get('game_id')
        rarity = request.POST.get('rarity', 'common')
        game = Game.objects.filter(id=game_id).first()
        if not name or not game:
            messages.error(request, 'Укажите название и игру.')
            return redirect('dashboard_items')
        item = Item.objects.create(
            name=name[:200],
            game=game,
            description=request.POST.get('description', ''),
            rarity=rarity if rarity in dict(Item.RARITY_CHOICES) else 'common',
        )
        if request.FILES.get('image'):
            item.image = request.FILES['image']
            item.save()
        log_admin_action(request.user, 'create_item', 'Item', item.id, name, request)
        messages.success(request, f'Предмет «{name}» создан.')
        return redirect('dashboard_items')

    return render(request, 'dashboard/items.html', {
        'items': items[:200],
        'games': games,
        'rarities': Item.RARITY_CHOICES,
    })


# ─────────────────────────────────────────────
# AUDIT LOG / DEVICES
# ─────────────────────────────────────────────

@login_required
@user_passes_test(is_admin)
def dashboard_audit_view(request):
    logs = AdminAuditLog.objects.select_related('admin').order_by('-created_at')[:300]
    q = request.GET.get('q', '').strip()
    if q:
        logs = AdminAuditLog.objects.select_related('admin').filter(
            Q(action__icontains=q) | Q(details__icontains=q) | Q(admin__username__icontains=q)
        ).order_by('-created_at')[:300]
    return render(request, 'dashboard/audit.html', {'logs': logs, 'q': q})


@login_required
@user_passes_test(is_admin)
def dashboard_devices_view(request):
    devices = UserDevice.objects.select_related('user').order_by('-last_activity')[:200]
    q = request.GET.get('q', '').strip()
    if q:
        devices = UserDevice.objects.select_related('user').filter(
            Q(user__username__icontains=q) | Q(ip_address__icontains=q) | Q(country__icontains=q)
        ).order_by('-last_activity')[:200]
    return render(request, 'dashboard/devices.html', {'devices': devices, 'q': q})


# ─────────────────────────────────────────────
# STATS PAGE
# ─────────────────────────────────────────────

@login_required
@user_passes_test(is_admin)
def dashboard_stats_view(request):
    now = timezone.now()
    top_games = (
        Game.objects.annotate(sales=Count('purchase_set'))
        .order_by('-sales')[:10]
    )
    top_users = (
        User.objects.annotate(buys=Count('purchases'))
        .order_by('-buys')[:10]
    )
    by_category = (
        Category.objects.annotate(games=Count('game_set'), sales=Count('game_set__purchase_set'))
        .order_by('-sales')
    )
    ticket_by_cat = (
        SupportTicket.objects.values('category')
        .annotate(c=Count('id'))
        .order_by('-c')
    )
    daily = (
        Purchase.objects.filter(purchased_at__gte=now - timedelta(days=30))
        .annotate(day=TruncDate('purchased_at'))
        .values('day')
        .annotate(count=Count('id'), revenue=Sum('price_paid'))
        .order_by('day')
    )
    return render(request, 'dashboard/stats.html', {
        'top_games': top_games,
        'top_users': top_users,
        'by_category': by_category,
        'ticket_by_cat': ticket_by_cat,
        'daily': list(daily),
        'category_labels': dict(SupportTicket.CATEGORY_CHOICES),
    })
