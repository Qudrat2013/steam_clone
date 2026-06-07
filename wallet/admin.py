from django.contrib import admin, messages
from django.utils import timezone

from notifications.utils import create_notification
from .models import BalanceRequest


@admin.register(BalanceRequest)
class BalanceRequestAdmin(admin.ModelAdmin):
    # Добавил отображение 'click_paydoc_id' в список, чтобы видеть ID транзакции Click
    list_display = ('id', 'user', 'amount', 'status', 'click_paydoc_id', 'created_at', 'processed_at')
    list_filter = ('status', 'created_at')
    search_fields = ('user__username', 'click_paydoc_id')
    
    # Теперь все поля делаем readonly, так как платежи проходят автоматически через API Click
    readonly_fields = ('user', 'amount', 'status', 'click_paydoc_id', 'created_at', 'processed_at')

    def has_add_permission(self, request):
        # Запрещаем создавать заявки вручную из админки, только через сайт
        return False

    def save_model(self, request, obj, form, change):
        old_obj = None

        if change:
            old_obj = BalanceRequest.objects.filter(id=obj.id).first()

        # Логика ручного одобрения новой заявки (если вдруг понадобится через код)
        if not change and obj.status == 'approved':
            profile = obj.user.profile
            profile.balance += obj.amount
            profile.save()
            obj.processed_at = timezone.now()

            create_notification(
                obj.user,
                'Баланс пополнен',
                f'Ваша заявка на {obj.amount} UZS одобрена.',
                'wallet',
                '/wallet/'
            )

        # Логика перевода из ожидания в одобрено
        elif old_obj and old_obj.status == 'pending' and obj.status == 'approved':
            profile = obj.user.profile
            profile.balance += obj.amount
            profile.save()
            obj.processed_at = timezone.now()

            create_notification(
                obj.user,
                'Баланс пополнен',
                f'Ваша заявка на {obj.amount} UZS одобрена.',
                'wallet',
                '/wallet/'
            )

        # Логика перевода из ожидания в отклонено
        elif old_obj and old_obj.status == 'pending' and obj.status == 'declined':
            obj.processed_at = timezone.now()

            create_notification(
                obj.user,
                'Заявка отклонена',
                f'Ваша заявка на {obj.amount} UZS отклонена.',
                'wallet',
                '/wallet/'
            )

        super().save_model(request, obj, form, change)