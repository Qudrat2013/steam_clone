from django.contrib import admin
from .models import ChatMessage, Sticker, StickerPack


class StickerInline(admin.TabularInline):
    model = Sticker
    extra = 3
    fields = ('name', 'image', 'emoji', 'order')


@admin.register(StickerPack)
class StickerPackAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'sticker_count', 'created_at')
    inlines = [StickerInline]

    def sticker_count(self, obj):
        return obj.stickers.count()
    sticker_count.short_description = 'Стикеров'


@admin.register(Sticker)
class StickerAdmin(admin.ModelAdmin):
    list_display = ('name', 'pack', 'emoji', 'order')
    list_filter = ('pack',)
    list_editable = ('order',)


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'receiver', 'message_type', 'is_read', 'created_at')
    list_filter = ('message_type', 'is_read')