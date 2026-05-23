from django.contrib import admin, messages
from django.utils import timezone

from notifications.utils import create_notification
from .models import BalanceRequest


@admin.action(description='Одобрить заявки и начислить баланс')
def approve_requests(modeladmin, request, queryset):
    count = 0

    for balance_request in queryset.filter(status='pending'):
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

        count += 1

    messages.success(request, f'Одобрено заявок: {count}')


@admin.action(description='Отклонить заявки')
def decline_requests(modeladmin, request, queryset):
    count = 0

    for balance_request in queryset.filter(status='pending'):
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

        count += 1

    messages.info(request, f'Отклонено заявок: {count}')


@admin.register(BalanceRequest)
class BalanceRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'amount', 'status', 'created_at', 'processed_at')
    list_filter = ('status', 'created_at')
    search_fields = ('user__username',)
    actions = [approve_requests, decline_requests]
    readonly_fields = ('processed_at',)

    def save_model(self, request, obj, form, change):
        old_obj = None

        if change:
            old_obj = BalanceRequest.objects.filter(id=obj.id).first()

        if not change and obj.status == 'approved':
            profile = obj.user.profile
            profile.balance += obj.amount
            profile.save()
            obj.processed_at = timezone.now()

            create_notification(
                obj.user,
                'Баланс пополнен',
                f'Ваша заявка на ${obj.amount} одобрена.',
                'wallet',
                '/wallet/'
            )

        elif old_obj and old_obj.status == 'pending' and obj.status == 'approved':
            profile = obj.user.profile
            profile.balance += obj.amount
            profile.save()
            obj.processed_at = timezone.now()

            create_notification(
                obj.user,
                'Баланс пополнен',
                f'Ваша заявка на ${obj.amount} одобрена.',
                'wallet',
                '/wallet/'
            )

        elif old_obj and old_obj.status == 'pending' and obj.status == 'declined':
            obj.processed_at = timezone.now()

            create_notification(
                obj.user,
                'Заявка отклонена',
                f'Ваша заявка на ${obj.amount} отклонена.',
                'wallet',
                '/wallet/'
            )

        super().save_model(request, obj, form, change)