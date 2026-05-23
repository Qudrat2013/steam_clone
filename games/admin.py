from django.contrib import admin
from .models import Game, Category, Tag, Screenshot, Review


class ScreenshotInline(admin.TabularInline):
    model = Screenshot
    extra = 3


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ['title', 'developer', 'price', 'discount', 'is_featured', 'is_active']
    list_filter = ['category', 'is_featured', 'is_active']
    search_fields = ['title', 'developer']
    prepopulated_fields = {'slug': ('title',)}
    inlines = [ScreenshotInline]
    filter_horizontal = ['tags']


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['user', 'game', 'rating', 'created_at']
