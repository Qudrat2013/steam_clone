from django.contrib import admin
from .models import Group, GroupMembership, GroupPost, GroupPostComment, GroupChatMessage


class GroupMembershipInline(admin.TabularInline):
    model = GroupMembership
    extra = 0
    fields = ('user', 'role', 'status', 'joined_at')
    readonly_fields = ('joined_at',)


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'tag', 'owner', 'is_public', 'member_count', 'created_at')
    list_filter = ('is_public', 'created_at')
    search_fields = ('name', 'tag', 'owner__username')
    inlines = [GroupMembershipInline]


@admin.register(GroupPost)
class GroupPostAdmin(admin.ModelAdmin):
    list_display = ('title', 'group', 'author', 'pinned', 'created_at')
    list_filter = ('group', 'pinned')
    search_fields = ('title', 'author__username')


@admin.register(GroupMembership)
class GroupMembershipAdmin(admin.ModelAdmin):
    list_display = ('user', 'group', 'role', 'status', 'joined_at')
    list_filter = ('role', 'status')