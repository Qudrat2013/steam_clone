from django.db import models
from django.contrib.auth.models import User
from inventory.models import InventoryItem


class TradeOffer(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Ожидает'),
        ('accepted', 'Принят'),
        ('declined', 'Отклонён'),
        ('cancelled', 'Отменён'),
    ]

    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_trade_offers')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_trade_offers')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    message = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Предложение обмена'
        verbose_name_plural = 'Предложения обмена'
        ordering = ['-created_at']

    def __str__(self):
        return f'Обмен #{self.id}: {self.sender} -> {self.receiver}'


class TradeOfferItem(models.Model):
    trade = models.ForeignKey(TradeOffer, on_delete=models.CASCADE, related_name='trade_items')
    inventory_item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE)
    from_sender = models.BooleanField()

    class Meta:
        verbose_name = 'Предмет обмена'
        verbose_name_plural = 'Предметы обмена'

    def __str__(self):
        side = 'sender' if self.from_sender else 'receiver'
        return f'{self.trade_id} - {self.inventory_item} ({side})'