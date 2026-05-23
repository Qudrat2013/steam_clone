from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from wallet.models import BalanceRequest
from marketplace.models import MarketListing
from trades.models import TradeOffer
from inventory.models import InventoryItem, Item
from cart.models import Purchase
from notifications.utils import create_notification


def is_admin(user):
    return user.is_authenticated and user.is_staff


@login_required
@user_passes_test(is_admin)
def dashboard_home(request):
    pending_balance_count = BalanceRequest.objects.filter(status='pending').count()
    users_count = User.objects.count()
    active_market_count = MarketListing.objects.filter(status='active').count()
    pending_trades_count = TradeOffer.objects.filter(status='pending').count()
    purchases_count = Purchase.objects.count()
    items_count = Item.objects.count()

    return render(request, 'dashboard/index.html', {
        'pending_balance_count': pending_balance_count,
        'users_count': users_count,
        'active_market_count': active_market_count,
        'pending_trades_count': pending_trades_count,
        'purchases_count': purchases_count,
        'items_count': items_count,
    })


@login_required
@user_passes_test(is_admin)
def balance_requests_view(request):
    status = request.GET.get('status', 'pending')

    requests = BalanceRequest.objects.select_related('user', 'user__profile')

    if status:
        requests = requests.filter(status=status)

    requests = requests.order_by('-created_at')

    return render(request, 'dashboard/balance_requests.html', {
        'requests': requests,
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
        f'Ваша заявка на ${balance_request.amount} одобрена.',
        'wallet',
        '/wallet/'
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
        f'Ваша заявка на ${balance_request.amount} отклонена.',
        'wallet',
        '/wallet/'
    )

    messages.info(request, 'Заявка отклонена.')
    return redirect('dashboard_balance_requests')


@login_required
@user_passes_test(is_admin)
def dashboard_users_view(request):
    query = request.GET.get('q', '').strip()
    users = User.objects.select_related('profile').order_by('-date_joined')

    if query:
        users = users.filter(username__icontains=query)

    return render(request, 'dashboard/users.html', {
        'users': users,
        'query': query,
    })


@login_required
@user_passes_test(is_admin)
def dashboard_user_detail_view(request, user_id):
    user_obj = get_object_or_404(User.objects.select_related('profile'), id=user_id)

    if request.method == 'POST':
        balance = request.POST.get('balance', '').strip()
        steam_level = request.POST.get('steam_level', '').strip()
        xp = request.POST.get('xp', '').strip()
        is_active = request.POST.get('is_active') == 'on'
        is_staff = request.POST.get('is_staff') == 'on'

        try:
            user_obj.profile.balance = balance
            user_obj.profile.steam_level = int(steam_level)
            user_obj.profile.xp = int(xp)
            user_obj.profile.save()

            user_obj.is_active = is_active
            user_obj.is_staff = is_staff
            user_obj.save()

            messages.success(request, 'Пользователь обновлён.')
            return redirect('dashboard_user_detail', user_id=user_obj.id)
        except Exception:
            messages.error(request, 'Ошибка при сохранении данных.')

    inventory_items = InventoryItem.objects.filter(owner=user_obj).select_related('item', 'item__game')[:20]
    purchases = Purchase.objects.filter(user=user_obj).select_related('game')[:20]

    return render(request, 'dashboard/user_detail.html', {
        'user_obj': user_obj,
        'inventory_items': inventory_items,
        'purchases': purchases,
    })


@login_required
@user_passes_test(is_admin)
def dashboard_market_view(request):
    listings = MarketListing.objects.select_related(
        'seller',
        'buyer',
        'inventory_item',
        'inventory_item__item',
    ).order_by('-created_at')[:100]

    return render(request, 'dashboard/market.html', {
        'listings': listings,
    })


@login_required
@user_passes_test(is_admin)
def dashboard_trades_view(request):
    trades = TradeOffer.objects.select_related('sender', 'receiver').order_by('-created_at')[:100]

    return render(request, 'dashboard/trades.html', {
        'trades': trades,
    })