from django.contrib import admin
from .models import TradeOffer, TradeOfferItem


class TradeOfferItemInline(admin.TabularInline):
    model = TradeOfferItem
    extra = 0


@admin.register(TradeOffer)
class TradeOfferAdmin(admin.ModelAdmin):
    list_display = ('id', 'sender', 'receiver', 'status', 'created_at', 'updated_at')
    list_filter = ('status', 'created_at')
    search_fields = ('sender__username', 'receiver__username', 'message')
    inlines = [TradeOfferItemInline]