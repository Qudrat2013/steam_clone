import hashlib
import os
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from users.models import Profile
from .models import BalanceRequest

# Click credentials from environment (optional online payments)
CLICK_SERVICE_ID = os.environ.get('CLICK_SERVICE_ID', '')
CLICK_MERCHANT_ID = os.environ.get('CLICK_MERCHANT_ID', '')
CLICK_SECRET_KEY = os.environ.get('CLICK_SECRET_KEY', '')
CLICK_ENABLED = bool(CLICK_SERVICE_ID and CLICK_MERCHANT_ID and CLICK_SECRET_KEY)


@login_required
def create_payment(request):
    """Create a balance top-up request (manual card transfer or optional Click)."""
    user_requests = BalanceRequest.objects.filter(user=request.user).order_by('-created_at')
    profile, _ = Profile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        amount_raw = (request.POST.get('amount') or '').strip()

        if not amount_raw:
            return render(request, 'wallet/wallet.html', {
                'error': 'Вы не ввели сумму',
                'requests': user_requests,
                'balance': profile.balance,
            })

        try:
            amount_decimal = Decimal(amount_raw)
            if amount_decimal <= 0:
                return render(request, 'wallet/wallet.html', {
                    'error': 'Сумма должна быть больше нуля',
                    'requests': user_requests,
                    'balance': profile.balance,
                })
        except (InvalidOperation, ValueError):
            return render(request, 'wallet/wallet.html', {
                'error': 'Некорректный формат суммы',
                'requests': user_requests,
                'balance': profile.balance,
            })

        balance_request = BalanceRequest.objects.create(
            user=request.user,
            amount=amount_decimal,
            status='pending',
        )

        # Optional: redirect to Click if merchant credentials are configured
        if CLICK_ENABLED and request.POST.get('use_click') == '1':
            click_url = (
                f'https://my.click.uz/services/pay'
                f'?service_id={CLICK_SERVICE_ID}'
                f'&merchant_id={CLICK_MERCHANT_ID}'
                f'&amount={amount_decimal}'
                f'&transaction_param={balance_request.id}'
            )
            return redirect(click_url)

        messages.success(
            request,
            f'Заявка на {amount_decimal} UZS создана. Администратор проверит перевод и зачислит баланс.',
        )
        return redirect('wallet:deposit')

    return render(request, 'wallet/wallet.html', {
        'requests': user_requests,
        'balance': profile.balance,
    })


@csrf_exempt
@require_POST
def click_webhook(request):
    """Click.uz payment callback (only works when CLICK_* env vars are set)."""
    if not CLICK_ENABLED:
        return JsonResponse({'error': '-8', 'error_note': 'Click payments disabled'}, status=503)

    data = request.POST

    click_trans_id = data.get('click_trans_id')
    service_id = data.get('service_id')
    click_paydoc_id = data.get('click_paydoc_id')
    merchant_trans_id = data.get('merchant_trans_id')
    amount = data.get('amount')
    action = data.get('action')
    error = data.get('error')
    sign_time = data.get('sign_time')
    sign_string = data.get('sign_string')

    raw_string = (
        f'{click_trans_id}{service_id}{CLICK_SECRET_KEY}'
        f'{merchant_trans_id}{amount}{action}{sign_time}'
    )
    my_sign = hashlib.md5(raw_string.encode('utf-8')).hexdigest()

    if my_sign != sign_string:
        return JsonResponse({'error': '-1', 'error_note': 'Sign string mismatch'})

    try:
        balance_request = BalanceRequest.objects.get(id=merchant_trans_id)
    except BalanceRequest.DoesNotExist:
        return JsonResponse({'error': '-5', 'error_note': 'Transaction not found'})

    if Decimal(str(balance_request.amount)) != Decimal(str(amount)):
        return JsonResponse({'error': '-2', 'error_note': 'Incorrect amount'})

    try:
        error_code = int(error)
        action_code = int(action)
    except (TypeError, ValueError):
        return JsonResponse({'error': '-3', 'error_note': 'Invalid action/error'})

    if error_code < 0:
        balance_request.status = 'declined'
        balance_request.processed_at = timezone.now()
        balance_request.save(update_fields=['status', 'processed_at'])
        return JsonResponse({'error': error, 'error_note': 'Payment failed'})

    if action_code == 0:
        if balance_request.status == 'pending':
            return JsonResponse({
                'click_trans_id': click_trans_id,
                'merchant_trans_id': merchant_trans_id,
                'error': '0',
                'error_note': 'Success',
            })
        return JsonResponse({'error': '-4', 'error_note': 'Transaction already processed'})

    if action_code == 1:
        if balance_request.status == 'pending':
            balance_request.status = 'approved'
            balance_request.click_paydoc_id = click_paydoc_id
            balance_request.processed_at = timezone.now()
            balance_request.save()

            profile, _ = Profile.objects.get_or_create(user=balance_request.user)
            profile.balance += Decimal(str(balance_request.amount))
            profile.save(update_fields=['balance'])

            return JsonResponse({
                'click_trans_id': click_trans_id,
                'merchant_trans_id': merchant_trans_id,
                'error': '0',
                'error_note': 'Success',
            })
        if balance_request.status == 'approved':
            return JsonResponse({'error': '0', 'error_note': 'Already approved'})
        return JsonResponse({'error': '-9', 'error_note': 'Transaction declined before'})

    return JsonResponse({'error': '-3', 'error_note': 'Action not found'})
