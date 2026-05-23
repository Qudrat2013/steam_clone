from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from achievements.utils import give_achievement
from inventory.models import InventoryItem
from notifications.utils import create_notification
from trades.models import TradeOfferItem
from .models import MarketListing


@login_required
def market_list_view(request):
    listings = MarketListing.objects.filter(status='active').select_related(
        'seller',
        'inventory_item',
        'inventory_item__item',
        'inventory_item__item__game',
    )

    query = request.GET.get('q', '').strip()

    if query:
        listings = listings.filter(inventory_item__item__name__icontains=query)

    return render(request, 'marketplace/market_list.html', {
        'listings': listings,
        'query': query,
    })


@login_required
def sell_item_view(request, inventory_item_id):
    inventory_item = get_object_or_404(
        InventoryItem,
        id=inventory_item_id,
        owner=request.user,
        is_tradable=True
    )

    if MarketListing.objects.filter(inventory_item=inventory_item, status='active').exists():
        messages.error(request, 'Этот предмет уже выставлен на маркет.')
        return redirect('my_market_listings')

    if TradeOfferItem.objects.filter(inventory_item=inventory_item, trade__status='pending').exists():
        messages.error(request, 'Этот предмет уже участвует в активном трейде.')
        return redirect('inventory')

    if request.method == 'POST':
        price = request.POST.get('price', '').strip()

        try:
            price = Decimal(price)
        except:
            messages.error(request, 'Введите правильную цену.')
            return redirect('sell_item', inventory_item_id=inventory_item.id)

        if price <= 0:
            messages.error(request, 'Цена должна быть больше нуля.')
            return redirect('sell_item', inventory_item_id=inventory_item.id)

        MarketListing.objects.create(
            seller=request.user,
            inventory_item=inventory_item,
            price=price
        )

        messages.success(request, 'Предмет выставлен на маркет.')
        return redirect('market_list')

    return render(request, 'marketplace/sell_item.html', {
        'inventory_item': inventory_item,
    })


@login_required
@require_POST
@transaction.atomic
def buy_item_view(request, listing_id):
    listing = get_object_or_404(
        MarketListing.objects.select_related(
            'seller',
            'inventory_item',
            'inventory_item__owner',
            'inventory_item__item',
        ),
        id=listing_id,
        status='active'
    )

    if listing.seller == request.user:
        messages.error(request, 'Нельзя купить свой предмет.')
        return redirect('market_list')

    if listing.inventory_item.owner != listing.seller:
        listing.status = 'cancelled'
        listing.save()
        messages.error(request, 'Предмет больше недоступен.')
        return redirect('market_list')

    buyer_profile = request.user.profile
    seller_profile = listing.seller.profile

    if buyer_profile.balance < listing.price:
        messages.error(request, 'Недостаточно средств на балансе.')
        return redirect('market_list')

    buyer_profile.balance -= listing.price
    buyer_profile.save()

    seller_profile.balance += listing.price
    seller_profile.save()

    listing.inventory_item.owner = request.user
    listing.inventory_item.save()

    listing.buyer = request.user
    listing.status = 'sold'
    listing.sold_at = timezone.now()
    listing.save()

    request.user.profile.add_xp(10)
    listing.seller.profile.add_xp(10)

    give_achievement(request.user, 'Первая покупка на маркете', 'Купите первый предмет на маркете.')
    give_achievement(listing.seller, 'Первая продажа', 'Продайте первый предмет на маркете.')

    create_notification(
        listing.seller,
        'Предмет продан',
        f'{request.user.username} купил ваш предмет «{listing.inventory_item.item.name}» за ${listing.price}.',
        'market',
        '/market/my/'
    )

    create_notification(
        request.user,
        'Предмет куплен',
        f'Вы купили предмет «{listing.inventory_item.item.name}» за ${listing.price}.',
        'market',
        '/inventory/'
    )

    messages.success(request, 'Предмет куплен и добавлен в инвентарь.')
    return redirect('inventory')


@login_required
def my_market_listings_view(request):
    active_listings = request.user.market_listings.filter(status='active').select_related(
        'inventory_item',
        'inventory_item__item',
        'inventory_item__item__game',
    )

    sold_listings = request.user.market_listings.filter(status='sold').select_related(
        'inventory_item',
        'inventory_item__item',
        'inventory_item__item__game',
        'buyer',
    )

    cancelled_listings = request.user.market_listings.filter(status='cancelled').select_related(
        'inventory_item',
        'inventory_item__item',
        'inventory_item__item__game',
    )

    return render(request, 'marketplace/my_listings.html', {
        'active_listings': active_listings,
        'sold_listings': sold_listings,
        'cancelled_listings': cancelled_listings,
    })


@login_required
@require_POST
def cancel_listing_view(request, listing_id):
    listing = get_object_or_404(
        MarketListing,
        id=listing_id,
        seller=request.user,
        status='active'
    )

    listing.status = 'cancelled'
    listing.save()

    messages.success(request, 'Лот снят с продажи.')
    return redirect('my_market_listings')