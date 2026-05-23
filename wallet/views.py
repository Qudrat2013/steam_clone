from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .models import BalanceRequest


@login_required
def wallet_view(request):
    requests = BalanceRequest.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'wallet/wallet.html', {
        'requests': requests,
    })


@login_required
def create_balance_request(request):
    if request.method == 'POST':
        amount = request.POST.get('amount', '').strip()

        try:
            amount = Decimal(amount)
        except:
            messages.error(request, 'Введите правильную сумму.')
            return redirect('wallet')

        if amount <= 0:
            messages.error(request, 'Сумма должна быть больше нуля.')
            return redirect('wallet')

        BalanceRequest.objects.create(
            user=request.user,
            amount=amount
        )

        messages.success(request, 'Заявка на пополнение отправлена администратору.')
        return redirect('wallet')

    return redirect('wallet')