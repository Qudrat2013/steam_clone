import random

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction  # Для безопасного списания денег

from games.models import Game
from inventory.models import Item, InventoryItem
from achievements.utils import give_achievement
from .models import CartItem, Purchase, Wishlist


def give_random_items_for_game(user, game):
    available_items = list(Item.objects.filter(game=game))

    if not available_items:
        return 0

    count = random.randint(1, min(3, len(available_items)))
    selected_items = random.sample(available_items, count)

    for item in selected_items:
        InventoryItem.objects.create(
            owner=user,
            item=item,
            is_tradable=True
        )

    return count


@login_required
def cart_view(request):
    # ИСПРАВЛЕНО: Добавлено явное указание поля user=
    cart_items = CartItem.objects.filter(user=request.user).select_related('game')
    total = sum(item.game.get_discounted_price() for item in cart_items)
    return render(request, 'cart/cart.html', {'cart_items': cart_items, 'total': total})


@login_required
def add_to_cart(request, game_id):
    game = get_object_or_404(Game, id=game_id)

    if Purchase.objects.filter(user=request.user, game=game).exists():
        messages.info(request, f'Вы уже владеете игрой «{game.title}»')
    else:
        CartItem.objects.get_or_create(user=request.user, game=game)
        messages.success(request, f'«{game.title}» добавлена в корзину')

    return redirect(request.META.get('HTTP_REFERER', 'home'))


@login_required
def remove_from_cart(request, game_id):
    CartItem.objects.filter(user=request.user, game_id=game_id).delete()
    messages.success(request, 'Игра удалена из корзины')
    return redirect('cart')


@login_required
def checkout(request):
    cart_items = CartItem.objects.filter(user=request.user).select_related('game')

    if not cart_items.exists():
        messages.error(request, 'Ваша корзина пуста')
        return redirect('cart')

    # Считаем общую стоимость всех игр в корзине
    total_price = sum(item.game.get_discounted_price() for item in cart_items)

    if request.method == 'POST':
        profile = request.user.profile

        # ПРОВЕРКА: Если денег на балансе кошелька меньше, чем стоит корзина
        if profile.balance < total_price:
            messages.error(request, f'Недостаточно средств! К оплате: {total_price} UZS. Ваш баланс: {profile.balance} UZS.')
            return redirect('cart')

        total_items_given = 0
        new_purchases = 0

        # Оборачиваем в atomic, чтобы транзакция была безопасной
        with transaction.atomic():
            # СПИСЫВАЕМ ДЕНЬГИ С КОШЕЛЬКА профиля
            profile.balance -= total_price
            profile.save()

            for item in cart_items:
                purchase, created = Purchase.objects.get_or_create(
                    user=request.user,
                    game=item.game,
                    defaults={'price_paid': item.game.get_discounted_price()}
                )

                if created:
                    new_purchases += 1
                    total_items_given += give_random_items_for_game(request.user, item.game)

            if new_purchases > 0:
                request.user.profile.add_xp(50 * new_purchases)
                # Steam Points за покупки
                try:
                    p = request.user.profile
                    p.steam_points = (p.steam_points or 0) + (10 * new_purchases)
                    p.save(update_fields=['steam_points'])
                except Exception:
                    pass
                give_achievement(request.user, 'Первая покупка', 'Купите свою первую игру.')

                if new_purchases >= 3:
                    give_achievement(request.user, 'Оптовый покупатель', 'Купите 3 игры за раз.')

                try:
                    from steamplus.utils import log_activity
                    for item in list(cart_items):
                        log_activity(
                            request.user,
                            'purchase',
                            f'купил «{item.game.title}»',
                            game=item.game,
                        )
                except Exception:
                    pass

            # Очищаем корзину после успешной оплаты
            cart_items.delete()

        if total_items_given > 0:
            messages.success(
                request,
                f'Покупка прошла успешно! Списано {total_price} UZS. Вы получили предметов: {total_items_given}.'
            )
        else:
            messages.success(request, f'Покупка прошла успешно! Списано {total_price} UZS. Игры добавлены в библиотеку.')

        return redirect('library')

    return render(request, 'cart/checkout.html', {'cart_items': cart_items, 'total': total_price})


@login_required
def library(request):
    purchases = list(
        Purchase.objects.filter(user=request.user).select_related('game').order_by('-purchased_at')
    )
    try:
        from steamplus.models import Playtime
        pt_map = {
            pt.game_id: pt
            for pt in Playtime.objects.filter(user=request.user)
        }
        for p in purchases:
            p.playtime = pt_map.get(p.game_id)
    except Exception:
        for p in purchases:
            p.playtime = None
    return render(request, 'cart/library.html', {
        'purchases': purchases,
    })


@login_required
def toggle_wishlist(request, game_id):
    game = get_object_or_404(Game, id=game_id)
    obj, created = Wishlist.objects.get_or_create(user=request.user, game=game)

    if not created:
        obj.delete()
        messages.info(request, f'«{game.title}» удалена из списка желаемого')
    else:
        give_achievement(request.user, 'Первое желаемое', 'Добавьте игру в список желаемого.')
        messages.success(request, f'«{game.title}» добавлена в список желаемого')

    return redirect(request.META.get('HTTP_REFERER', 'home'))


@login_required
def wishlist_view(request):
    wishlist = Wishlist.objects.filter(user=request.user).select_related('game')
    return render(request, 'cart/wishlist.html', {'wishlist': wishlist})