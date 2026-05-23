from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from achievements.utils import give_achievement
from friends.models import Friendship
from inventory.models import InventoryItem
from marketplace.models import MarketListing
from notifications.utils import create_notification
from .models import TradeOffer, TradeOfferItem


@login_required
def create_trade_offer_view(request, username):
    receiver = get_object_or_404(User, username=username)

    if receiver == request.user:
        messages.error(request, 'Нельзя отправить трейд самому себе.')
        return redirect('inventory')

    if not Friendship.are_friends(request.user, receiver):
        messages.error(request, 'Отправлять трейды можно только друзьям.')
        return redirect('profile', username=receiver.username)

    sender_items = InventoryItem.objects.filter(
        owner=request.user,
        is_tradable=True
    ).exclude(
        market_listings__status='active'
    ).select_related('item', 'item__game')

    receiver_items = InventoryItem.objects.filter(
        owner=receiver,
        is_tradable=True
    ).exclude(
        market_listings__status='active'
    ).select_related('item', 'item__game')

    if request.method == 'POST':
        sender_item_ids = request.POST.getlist('sender_items')
        receiver_item_ids = request.POST.getlist('receiver_items')
        message = request.POST.get('message', '').strip()

        if not sender_item_ids and not receiver_item_ids:
            messages.error(request, 'Выберите хотя бы один предмет для обмена.')
            return redirect('trade_offer', username=receiver.username)

        selected_item_ids = sender_item_ids + receiver_item_ids

        if TradeOfferItem.objects.filter(
            trade__status='pending',
            inventory_item_id__in=selected_item_ids
        ).exists():
            messages.error(request, 'Один из выбранных предметов уже участвует в активном трейде.')
            return redirect('trade_offer', username=receiver.username)

        if MarketListing.objects.filter(
            status='active',
            inventory_item_id__in=selected_item_ids
        ).exists():
            messages.error(request, 'Один из выбранных предметов выставлен на маркет.')
            return redirect('trade_offer', username=receiver.username)

        valid_sender_items = InventoryItem.objects.filter(
            id__in=sender_item_ids,
            owner=request.user,
            is_tradable=True
        )

        valid_receiver_items = InventoryItem.objects.filter(
            id__in=receiver_item_ids,
            owner=receiver,
            is_tradable=True
        )

        if len(sender_item_ids) != valid_sender_items.count() or len(receiver_item_ids) != valid_receiver_items.count():
            messages.error(request, 'Один из выбранных предметов недоступен.')
            return redirect('trade_offer', username=receiver.username)

        trade = TradeOffer.objects.create(
            sender=request.user,
            receiver=receiver,
            message=message,
        )

        for inv_item in valid_sender_items:
            TradeOfferItem.objects.create(
                trade=trade,
                inventory_item=inv_item,
                from_sender=True
            )

        for inv_item in valid_receiver_items:
            TradeOfferItem.objects.create(
                trade=trade,
                inventory_item=inv_item,
                from_sender=False
            )

        create_notification(
            receiver,
            'Новое предложение обмена',
            f'{request.user.username} отправил вам трейд.',
            'trade',
            f'/trades/{trade.id}/'
        )

        give_achievement(request.user, 'Первый трейд', 'Отправьте своё первое предложение обмена.')

        messages.success(request, 'Предложение обмена отправлено.')
        return redirect('trade_detail', trade_id=trade.id)

    return render(request, 'trades/trade_offer.html', {
        'receiver': receiver,
        'sender_items': sender_items,
        'receiver_items': receiver_items,
    })


@login_required
def trade_detail_view(request, trade_id):
    trade = get_object_or_404(
        TradeOffer.objects.select_related('sender', 'receiver').prefetch_related(
            'trade_items__inventory_item__item',
            'trade_items__inventory_item__owner',
        ),
        id=trade_id
    )

    if request.user != trade.sender and request.user != trade.receiver:
        messages.error(request, 'У вас нет доступа к этому обмену.')
        return redirect('inventory')

    sender_trade_items = trade.trade_items.filter(
        from_sender=True
    ).select_related('inventory_item__item', 'inventory_item__owner')

    receiver_trade_items = trade.trade_items.filter(
        from_sender=False
    ).select_related('inventory_item__item', 'inventory_item__owner')

    return render(request, 'trades/trade_detail.html', {
        'trade': trade,
        'sender_trade_items': sender_trade_items,
        'receiver_trade_items': receiver_trade_items,
    })


@login_required
@require_POST
@transaction.atomic
def accept_trade_view(request, trade_id):
    trade = get_object_or_404(TradeOffer, id=trade_id, receiver=request.user)

    if trade.status != 'pending':
        messages.error(request, 'Этот трейд уже обработан.')
        return redirect('trade_detail', trade_id=trade.id)

    trade_items = trade.trade_items.select_related('inventory_item')

    used_item_ids = list(trade_items.values_list('inventory_item_id', flat=True))

    if MarketListing.objects.filter(status='active', inventory_item_id__in=used_item_ids).exists():
        messages.error(request, 'Один из предметов уже выставлен на маркет.')
        return redirect('trade_detail', trade_id=trade.id)

    for trade_item in trade_items:
        inv_item = trade_item.inventory_item

        if trade_item.from_sender and inv_item.owner != trade.sender:
            messages.error(request, 'Предмет отправителя уже недоступен.')
            return redirect('trade_detail', trade_id=trade.id)

        if not trade_item.from_sender and inv_item.owner != trade.receiver:
            messages.error(request, 'Один из ваших предметов уже недоступен.')
            return redirect('trade_detail', trade_id=trade.id)

    for trade_item in trade_items:
        inv_item = trade_item.inventory_item

        if trade_item.from_sender:
            inv_item.owner = trade.receiver
        else:
            inv_item.owner = trade.sender

        inv_item.save()

    trade.status = 'accepted'
    trade.save()

    TradeOffer.objects.filter(
        status='pending',
        trade_items__inventory_item_id__in=used_item_ids
    ).exclude(id=trade.id).distinct().update(status='cancelled')

    trade.sender.profile.add_xp(20)
    trade.receiver.profile.add_xp(20)

    give_achievement(trade.sender, 'Успешный обмен', 'Завершите первый обмен.')
    give_achievement(trade.receiver, 'Успешный обмен', 'Завершите первый обмен.')

    create_notification(
        trade.sender,
        'Обмен принят',
        f'{trade.receiver.username} принял ваш обмен.',
        'trade',
        f'/trades/{trade.id}/'
    )

    messages.success(request, 'Обмен успешно завершён.')
    return redirect('trade_detail', trade_id=trade.id)


@login_required
@require_POST
def decline_trade_view(request, trade_id):
    trade = get_object_or_404(TradeOffer, id=trade_id, receiver=request.user)

    if trade.status == 'pending':
        trade.status = 'declined'
        trade.save()

        create_notification(
            trade.sender,
            'Обмен отклонён',
            f'{trade.receiver.username} отклонил ваш обмен.',
            'trade',
            f'/trades/{trade.id}/'
        )

        messages.info(request, 'Обмен отклонён.')

    return redirect('trade_detail', trade_id=trade.id)


@login_required
def trade_list_view(request):
    sent_trades = request.user.sent_trade_offers.select_related('receiver')
    received_trades = request.user.received_trade_offers.select_related('sender')

    return render(request, 'trades/trade_list.html', {
        'sent_trades': sent_trades,
        'received_trades': received_trades,
    })