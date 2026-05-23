from django.db import models
from django.contrib.auth.models import User
from inventory.models import InventoryItem


class MarketListing(models.Model):
    STATUS_CHOICES = [
        ('active', 'Активен'),
        ('sold', 'Продан'),
        ('cancelled', 'Отменён'),
    ]

    seller = models.ForeignKey(User, on_delete=models.CASCADE, related_name='market_listings')
    buyer = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='market_purchases')
    inventory_item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE, related_name='market_listings')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    sold_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Лот маркета'
        verbose_name_plural = 'Лоты маркета'

    def __str__(self):
        return f'{self.inventory_item.item.name} — ${self.price}'
    