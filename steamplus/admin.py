from django.contrib import admin
from .models import (
    Playtime, Activity, Gift, GameNews, DiscoverySkip,
    PointsShopItem, PointsPurchase, SaleEvent,
    DailyBonusClaim, GameRecommendation,
)


@admin.register(Playtime)
class PlaytimeAdmin(admin.ModelAdmin):
    list_display = ('user', 'game', 'minutes', 'sessions', 'last_played')
    search_fields = ('user__username', 'game__title')


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ('user', 'activity_type', 'text', 'created_at')
    list_filter = ('activity_type',)


@admin.register(Gift)
class GiftAdmin(admin.ModelAdmin):
    list_display = ('sender', 'receiver', 'game', 'status', 'price_paid', 'created_at')
    list_filter = ('status',)


@admin.register(GameNews)
class GameNewsAdmin(admin.ModelAdmin):
    list_display = ('title', 'game', 'is_update', 'created_at')
    list_filter = ('is_update',)


@admin.register(DiscoverySkip)
class DiscoverySkipAdmin(admin.ModelAdmin):
    list_display = ('user', 'game', 'created_at')


@admin.register(PointsShopItem)
class PointsShopItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'cost', 'reward_type', 'reward_value', 'is_active')


@admin.register(PointsPurchase)
class PointsPurchaseAdmin(admin.ModelAdmin):
    list_display = ('user', 'item', 'cost_paid', 'created_at')


@admin.register(SaleEvent)
class SaleEventAdmin(admin.ModelAdmin):
    list_display = ('title', 'starts_at', 'ends_at', 'is_active', 'extra_discount')


@admin.register(DailyBonusClaim)
class DailyBonusClaimAdmin(admin.ModelAdmin):
    list_display = ('user', 'claim_date', 'points_awarded', 'xp_awarded', 'streak')
    list_filter = ('claim_date',)


@admin.register(GameRecommendation)
class GameRecommendationAdmin(admin.ModelAdmin):
    list_display = ('user', 'game', 'score', 'reason')
