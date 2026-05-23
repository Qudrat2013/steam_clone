from django.contrib import admin
from .models import MarketListing


@admin.register(MarketListing)
class MarketListingAdmin(admin.ModelAdmin):
    list_display = ('id', 'seller', 'buyer', 'inventory_item', 'price', 'status', 'created_at', 'sold_at')
    list_filter = ('status', 'created_at')
    search_fields = ('seller__username', 'buyer__username', 'inventory_item__item__name')