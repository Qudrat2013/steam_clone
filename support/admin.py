from django.contrib import admin

from .models import (
    AdminAuditLog,
    BroadcastMessage,
    FAQArticle,
    FAQCategory,
    PromoCode,
    PromoRedemption,
    RefundRequest,
    SupportTicket,
    TicketMessage,
    UserBan,
    UserReport,
)


class TicketMessageInline(admin.TabularInline):
    model = TicketMessage
    extra = 0
    readonly_fields = ('author', 'created_at', 'is_staff_reply')


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ('id', 'subject', 'user', 'category', 'status', 'priority', 'assigned_to', 'updated_at')
    list_filter = ('status', 'category', 'priority')
    search_fields = ('subject', 'user__username')
    inlines = [TicketMessageInline]


@admin.register(UserReport)
class UserReportAdmin(admin.ModelAdmin):
    list_display = ('id', 'reporter', 'reported_user', 'reason', 'status', 'created_at')
    list_filter = ('status', 'reason', 'target_type')


@admin.register(UserBan)
class UserBanAdmin(admin.ModelAdmin):
    list_display = ('user', 'ban_type', 'is_active', 'starts_at', 'ends_at', 'banned_by')
    list_filter = ('ban_type', 'is_active')
    search_fields = ('user__username', 'reason')


@admin.register(FAQCategory)
class FAQCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'order')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(FAQArticle)
class FAQArticleAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'is_published', 'views', 'order')
    list_filter = ('is_published', 'category')
    prepopulated_fields = {'slug': ('title',)}
    search_fields = ('title', 'body')


@admin.register(PromoCode)
class PromoCodeAdmin(admin.ModelAdmin):
    list_display = ('code', 'reward_type', 'reward_value', 'used_count', 'max_uses', 'is_active')
    list_filter = ('reward_type', 'is_active')
    search_fields = ('code',)


@admin.register(PromoRedemption)
class PromoRedemptionAdmin(admin.ModelAdmin):
    list_display = ('promo', 'user', 'created_at')


@admin.register(RefundRequest)
class RefundRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'purchase', 'status', 'created_at')
    list_filter = ('status',)


@admin.register(AdminAuditLog)
class AdminAuditLogAdmin(admin.ModelAdmin):
    list_display = ('admin', 'action', 'target_type', 'target_id', 'created_at')
    list_filter = ('action',)
    search_fields = ('admin__username', 'details', 'action')
    readonly_fields = ('admin', 'action', 'target_type', 'target_id', 'details', 'ip_address', 'created_at')


@admin.register(BroadcastMessage)
class BroadcastMessageAdmin(admin.ModelAdmin):
    list_display = ('title', 'target', 'sent_count', 'created_by', 'created_at')
