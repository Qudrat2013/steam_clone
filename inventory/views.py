from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import InventoryItem


@login_required
def inventory_view(request):
    game_id = request.GET.get('game')

    items = request.user.inventory_items.select_related('item', 'item__game')

    if game_id:
        items = items.filter(item__game_id=game_id)

    games = []
    seen = set()

    for inv in request.user.inventory_items.select_related('item__game'):
        if inv.item.game_id not in seen:
            seen.add(inv.item.game_id)
            games.append(inv.item.game)

    selected_item = items.first()

    active_market_item_ids = set(
        request.user.inventory_items.filter(
            market_listings__status='active'
        ).values_list('id', flat=True)
    )

    active_trade_item_ids = set(
        request.user.inventory_items.filter(
            tradeofferitem__trade__status='pending'
        ).values_list('id', flat=True)
    )

    return render(request, 'inventory/inventory.html', {
        'items': items,
        'games': games,
        'selected_item': selected_item,
        'selected_game_id': str(game_id) if game_id else '',
        'active_market_item_ids': active_market_item_ids,
        'active_trade_item_ids': active_trade_item_ids,
    })


@login_required
@require_POST
def toggle_showcase_view(request, item_id):
    inventory_item = get_object_or_404(
        InventoryItem,
        id=item_id,
        owner=request.user
    )

    if not inventory_item.show_in_profile:
        showcase_count = InventoryItem.objects.filter(
            owner=request.user,
            show_in_profile=True
        ).count()

        if showcase_count >= 6:
            messages.error(request, 'В витрине можно показывать максимум 6 предметов.')
            return redirect('inventory')

    inventory_item.show_in_profile = not inventory_item.show_in_profile
    inventory_item.save()

    if inventory_item.show_in_profile:
        messages.success(request, 'Предмет добавлен в витрину профиля.')
    else:
        messages.info(request, 'Предмет убран из витрины профиля.')

    return redirect('inventory')