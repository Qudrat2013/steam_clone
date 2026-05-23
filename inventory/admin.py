from django.contrib import admin
from .models import Item, InventoryItem


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'game', 'rarity', 'created_at')
    list_filter = ('game', 'rarity', 'created_at')
    search_fields = ('name', 'game__title')


@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'owner', 'item', 'is_tradable', 'show_in_profile', 'acquired_at')
    list_filter = ('is_tradable', 'show_in_profile', 'acquired_at', 'item__game')
    search_fields = ('owner__username', 'item__name')