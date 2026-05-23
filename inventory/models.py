from django.db import models
from django.contrib.auth.models import User
from games.models import Game


class Item(models.Model):
    RARITY_CHOICES = [
        ('common', 'Обычный'),
        ('uncommon', 'Необычный'),
        ('rare', 'Редкий'),
        ('epic', 'Эпический'),
        ('legendary', 'Легендарный'),
    ]

    name = models.CharField(max_length=200, verbose_name='Название')
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name='items', verbose_name='Игра')
    description = models.TextField(blank=True, verbose_name='Описание')
    image = models.ImageField(upload_to='items/', blank=True, null=True, verbose_name='Изображение')
    rarity = models.CharField(max_length=20, choices=RARITY_CHOICES, default='common', verbose_name='Редкость')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Предмет'
        verbose_name_plural = 'Предметы'
        ordering = ['name']

    def __str__(self):
        return self.name


class InventoryItem(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='inventory_items', verbose_name='Владелец')
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='inventory_entries', verbose_name='Предмет')
    is_tradable = models.BooleanField(default=True, verbose_name='Можно обменять')
    show_in_profile = models.BooleanField(default=False, verbose_name='Показывать в профиле')
    acquired_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Предмет в инвентаре'
        verbose_name_plural = 'Предметы в инвентаре'
        ordering = ['-acquired_at']

    def __str__(self):
        return f'{self.owner.username} — {self.item.name}'