from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from cart.models import Purchase
from games.models import Game
from notifications.utils import create_notification

from .models import (
    FAQArticle,
    FAQCategory,
    PromoCode,
    PromoRedemption,
    RefundRequest,
    SupportTicket,
    TicketMessage,
    UserReport,
)


def support_home(request):
    """Центр поддержки — как help.steampowered.com."""
    categories = FAQCategory.objects.prefetch_related('articles').all()
    popular = FAQArticle.objects.filter(is_published=True).order_by('-views')[:8]
    q = request.GET.get('q', '').strip()
    search_results = []
    if q:
        search_results = FAQArticle.objects.filter(
            is_published=True,
        ).filter(Q(title__icontains=q) | Q(body__icontains=q))[:20]

    open_tickets = 0
    if request.user.is_authenticated:
        open_tickets = SupportTicket.objects.filter(
            user=request.user,
        ).exclude(status__in=('resolved', 'closed')).count()

    return render(request, 'support/home.html', {
        'categories': categories,
        'popular': popular,
        'q': q,
        'search_results': search_results,
        'open_tickets': open_tickets,
    })


def faq_article(request, slug):
    article = get_object_or_404(FAQArticle, slug=slug, is_published=True)
    FAQArticle.objects.filter(pk=article.pk).update(views=article.views + 1)
    related = FAQArticle.objects.filter(
        category=article.category, is_published=True,
    ).exclude(pk=article.pk)[:5]
    return render(request, 'support/faq_article.html', {
        'article': article,
        'related': related,
    })


@login_required
def ticket_list(request):
    tickets = SupportTicket.objects.filter(user=request.user).prefetch_related('messages')
    status = request.GET.get('status', '')
    if status == 'open':
        tickets = tickets.exclude(status__in=('resolved', 'closed'))
    elif status == 'closed':
        tickets = tickets.filter(status__in=('resolved', 'closed'))
    return render(request, 'support/ticket_list.html', {
        'tickets': tickets,
        'status': status,
    })


@login_required
def ticket_create(request):
    games = Game.objects.filter(is_active=True).order_by('title')
    if request.method == 'POST':
        subject = request.POST.get('subject', '').strip()
        category = request.POST.get('category', 'other')
        body = request.POST.get('body', '').strip()
        game_id = request.POST.get('game_id', '').strip()

        if not subject or not body:
            messages.error(request, 'Укажите тему и описание проблемы.')
            return redirect('support_ticket_create')

        if category not in dict(SupportTicket.CATEGORY_CHOICES):
            category = 'other'

        related_game = None
        if game_id.isdigit():
            related_game = Game.objects.filter(id=int(game_id)).first()

        ticket = SupportTicket.objects.create(
            user=request.user,
            subject=subject[:200],
            category=category,
            related_game=related_game,
            status='open',
            priority='normal',
        )
        TicketMessage.objects.create(
            ticket=ticket,
            author=request.user,
            body=body,
            is_staff_reply=False,
        )
        messages.success(request, f'Тикет #{ticket.id} создан. Поддержка ответит в ближайшее время.')
        return redirect('support_ticket_detail', ticket_id=ticket.id)

    return render(request, 'support/ticket_create.html', {
        'categories': SupportTicket.CATEGORY_CHOICES,
        'games': games,
    })


@login_required
def ticket_detail(request, ticket_id):
    ticket = get_object_or_404(SupportTicket, id=ticket_id, user=request.user)
    messages_qs = ticket.messages.filter(is_internal=False).select_related('author')

    if request.method == 'POST':
        action = request.POST.get('action', 'reply')
        if action == 'close' and ticket.is_open:
            ticket.mark_closed('closed')
            messages.info(request, 'Тикет закрыт.')
            return redirect('support_ticket_detail', ticket_id=ticket.id)

        if action == 'reopen' and not ticket.is_open:
            ticket.status = 'open'
            ticket.closed_at = None
            ticket.save(update_fields=['status', 'closed_at', 'updated_at'])
            messages.success(request, 'Тикет открыт снова.')
            return redirect('support_ticket_detail', ticket_id=ticket.id)

        body = request.POST.get('body', '').strip()
        if not body:
            messages.error(request, 'Сообщение не может быть пустым.')
            return redirect('support_ticket_detail', ticket_id=ticket.id)

        if not ticket.is_open:
            messages.error(request, 'Тикет закрыт. Откройте его снова, чтобы написать.')
            return redirect('support_ticket_detail', ticket_id=ticket.id)

        TicketMessage.objects.create(
            ticket=ticket,
            author=request.user,
            body=body,
            is_staff_reply=False,
        )
        ticket.status = 'pending'
        ticket.save(update_fields=['status', 'updated_at'])
        messages.success(request, 'Сообщение отправлено.')
        return redirect('support_ticket_detail', ticket_id=ticket.id)

    return render(request, 'support/ticket_detail.html', {
        'ticket': ticket,
        'ticket_messages': messages_qs,
    })


@login_required
def report_user(request, username=None):
    reported = None
    if username:
        reported = get_object_or_404(User, username=username)

    if request.method == 'POST':
        reported_username = request.POST.get('username', '').strip() or (reported.username if reported else '')
        reason = request.POST.get('reason', 'other')
        description = request.POST.get('description', '').strip()
        target_type = request.POST.get('target_type', 'user')
        target_id = request.POST.get('target_id', '').strip()

        reported_user = User.objects.filter(username=reported_username).first()
        if not reported_user and target_type == 'user':
            messages.error(request, 'Пользователь не найден.')
            return redirect('support_report')

        if not description:
            messages.error(request, 'Опишите проблему.')
            return redirect('support_report')

        if reason not in dict(UserReport.REASON_CHOICES):
            reason = 'other'
        if target_type not in dict(UserReport.TARGET_CHOICES):
            target_type = 'user'

        report = UserReport.objects.create(
            reporter=request.user,
            reported_user=reported_user,
            target_type=target_type,
            target_id=int(target_id) if target_id.isdigit() else None,
            reason=reason,
            description=description,
        )
        messages.success(request, f'Жалоба #{report.id} отправлена. Модераторы рассмотрят её.')
        return redirect('support_home')

    return render(request, 'support/report.html', {
        'reported': reported,
        'reasons': UserReport.REASON_CHOICES,
        'target_types': UserReport.TARGET_CHOICES,
    })


@login_required
def refund_list(request):
    refunds = RefundRequest.objects.filter(user=request.user).select_related('purchase', 'purchase__game')
    purchases = Purchase.objects.filter(user=request.user).select_related('game').order_by('-purchased_at')
    already = set(refunds.values_list('purchase_id', flat=True))
    return render(request, 'support/refunds.html', {
        'refunds': refunds,
        'purchases': purchases,
        'already_refunded_ids': already,
    })


@login_required
@require_POST
def refund_create(request):
    purchase_id = request.POST.get('purchase_id')
    reason = request.POST.get('reason', '').strip()
    purchase = get_object_or_404(Purchase, id=purchase_id, user=request.user)

    if not reason:
        messages.error(request, 'Укажите причину возврата.')
        return redirect('support_refunds')

    if RefundRequest.objects.filter(purchase=purchase, status__in=('pending', 'approved')).exists():
        messages.error(request, 'Заявка на возврат уже существует.')
        return redirect('support_refunds')

    # Steam-like: refund within ~14 days
    days = (timezone.now() - purchase.purchased_at).days
    if days > 14:
        messages.warning(request, 'Покупка старше 14 дней. Заявка всё равно создана, но может быть отклонена.')

    refund = RefundRequest.objects.create(
        user=request.user,
        purchase=purchase,
        game_title=purchase.game.title,
        amount=purchase.price_paid,
        reason=reason,
    )
    messages.success(request, f'Заявка на возврат #{refund.id} создана.')
    return redirect('support_refunds')


@login_required
def redeem_promo(request):
    if request.method == 'POST':
        code = request.POST.get('code', '').strip().upper()
        promo = PromoCode.objects.filter(code__iexact=code).first()
        if not promo:
            messages.error(request, 'Промокод не найден.')
            return redirect('support_redeem')

        if not promo.is_valid:
            messages.error(request, 'Промокод недействителен или исчерпан.')
            return redirect('support_redeem')

        if PromoRedemption.objects.filter(promo=promo, user=request.user).exists():
            messages.error(request, 'Вы уже активировали этот промокод.')
            return redirect('support_redeem')

        profile = request.user.profile
        try:
            with transaction.atomic():
                promo = PromoCode.objects.select_for_update().get(pk=promo.pk)
                if not promo.is_valid:
                    messages.error(request, 'Промокод больше недоступен.')
                    return redirect('support_redeem')

                if promo.reward_type == 'balance':
                    profile.balance += Decimal(str(promo.reward_value))
                    profile.save(update_fields=['balance'])
                    reward_msg = f'+{promo.reward_value} на баланс'
                elif promo.reward_type == 'points':
                    profile.steam_points += int(promo.reward_value)
                    profile.save(update_fields=['steam_points'])
                    reward_msg = f'+{int(promo.reward_value)} Steam Points'
                elif promo.reward_type == 'xp':
                    profile.add_xp(int(promo.reward_value))
                    reward_msg = f'+{int(promo.reward_value)} XP'
                elif promo.reward_type == 'game' and promo.game_id:
                    if Purchase.objects.filter(user=request.user, game=promo.game).exists():
                        messages.error(request, 'Игра уже есть в библиотеке.')
                        return redirect('support_redeem')
                    Purchase.objects.create(
                        user=request.user,
                        game=promo.game,
                        price_paid=Decimal('0.00'),
                    )
                    reward_msg = f'Игра «{promo.game.title}»'
                else:
                    reward_msg = f'Награда: {promo.get_reward_type_display()}'

                PromoRedemption.objects.create(promo=promo, user=request.user)
                promo.used_count += 1
                promo.save(update_fields=['used_count'])

            create_notification(
                request.user,
                'Промокод активирован',
                f'Код {promo.code}: {reward_msg}',
                'wallet',
                '/wallet/',
            )
            messages.success(request, f'Промокод активирован! {reward_msg}')
        except (InvalidOperation, ValueError):
            messages.error(request, 'Ошибка при начислении награды.')
        return redirect('support_redeem')

    history = PromoRedemption.objects.filter(user=request.user).select_related('promo')[:20]
    return render(request, 'support/redeem.html', {'history': history})
