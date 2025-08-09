from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, UserToken


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('email', 'display_name', 'is_active', 'is_staff', 'is_admin', 'date_joined')
    list_filter = ('is_active', 'is_staff', 'is_admin', 'date_joined')
    search_fields = ('email', 'display_name')
    ordering = ('-date_joined',)
    
    fieldsets = (
        (None, {'fields': ('email', 'display_name')}),
        ('权限', {'fields': ('is_active', 'is_staff', 'is_admin', 'is_superuser', 'groups', 'user_permissions')}),
        ('重要日期', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'display_name', 'is_active', 'is_staff', 'is_admin'),
        }),
    )


@admin.register(UserToken)
class UserTokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'token_preview', 'created_at', 'expires_at', 'is_remember_me', 'is_expired')
    list_filter = ('is_remember_me', 'created_at', 'expires_at')
    search_fields = ('user__email', 'token')
    readonly_fields = ('token', 'created_at')
    
    def token_preview(self, obj):
        return f'{obj.token[:20]}...'
    token_preview.short_description = '令牌预览'
