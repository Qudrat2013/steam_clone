import hashlib
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from .models import BalanceRequest

# Данные мерчанта (Твои пароли и токены)
CLICK_SERVICE_ID = "ТВОЙ_SERVICE_ID"
CLICK_MERCHANT_ID = "ТВОЙ_MERCHANT_ID"
CLICK_SECRET_KEY = "ТВОЙ_SECRET_KEY"


@login_required
def create_payment(request):
    user_requests = BalanceRequest.objects.filter(user=request.user).order_by('-created_at')

    if request.method == "POST":
        amount = request.POST.get('amount')

        if not amount:
            return render(request, 'wallet/wallet.html', {'error': 'Вы не ввели сумму', 'requests': user_requests})

        try:
            amount_decimal = Decimal(amount)
            if amount_decimal <= 0:
                return render(request, 'wallet/wallet.html', {'error': 'Сумма должна быть больше нуля', 'requests': user_requests})
        except Exception:
            return render(request, 'wallet/wallet.html', {'error': 'Некорректный формат суммы', 'requests': user_requests})

        balance_request = BalanceRequest.objects.create(
            user=request.user,
            amount=amount_decimal,
            status='pending'
        )

        click_url = (
            f"https://my.click.uz/services/pay"
            f"?service_id={CLICK_SERVICE_ID}"
            f"&merchant_id={CLICK_MERCHANT_ID}"
            f"&amount={amount_decimal}"
            f"&transaction_param={balance_request.id}"
        )

        return redirect(click_url)

    return render(request, 'wallet/wallet.html', {'requests': user_requests})


@csrf_exempt
def click_webhook(request):
    if request.method != 'POST':
        return JsonResponse({'error': '-3', 'error_note': 'Method not allowed'}, status=405)

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

    # Проверка подписи
    raw_string = f"{click_trans_id}{service_id}{CLICK_SECRET_KEY}{merchant_trans_id}{amount}{action}{sign_time}"
    my_sign = hashlib.md5(raw_string.encode('utf-8')).hexdigest()

    if my_sign != sign_string:
        return JsonResponse({'error': '-1', 'error_note': 'Sign string mismatch'})

    try:
        balance_request = BalanceRequest.objects.get(id=merchant_trans_id)
    except BalanceRequest.DoesNotExist:
        return JsonResponse({'error': '-5', 'error_note': 'Transaction not found'})

    # Проверка суммы
    if Decimal(str(balance_request.amount)) != Decimal(str(amount)):
        return JsonResponse({'error': '-2', 'error_note': 'Incorrect amount'})

    # Проверка ошибок от Click
    if int(error) < 0:
        balance_request.status = 'declined'
        balance_request.processed_at = timezone.now()
        balance_request.save()
        return JsonResponse({'error': error, 'error_note': 'Payment failed'})

    if int(action) == 0:
        if balance_request.status == 'pending':
            return JsonResponse({
                'click_trans_id': click_trans_id,
                'merchant_trans_id': merchant_trans_id,
                'error': '0',
                'error_note': 'Success'
            })
        else:
            return JsonResponse({'error': '-4', 'error_note': 'Transaction already processed'})

    elif int(action) == 1:
        if balance_request.status == 'pending':
            balance_request.status = 'approved'
            balance_request.click_paydoc_id = click_paydoc_id
            balance_request.processed_at = timezone.now()
            balance_request.save()

            # Начисляем деньги на баланс
            profile = balance_request.user.profile
            profile.balance += Decimal(str(balance_request.amount))
            profile.save()

            return JsonResponse({
                'click_trans_id': click_trans_id,
                'merchant_trans_id': merchant_trans_id,
                'error': '0',
                'error_note': 'Success'
            })
        elif balance_request.status == 'approved':
            return JsonResponse({'error': '0', 'error_note': 'Already approved'})
        else:
            return JsonResponse({'error': '-9', 'error_note': 'Transaction declined before'})

    return JsonResponse({'error': '-3', 'error_note': 'Action not found'})