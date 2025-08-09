from django.contrib import admin
from .models import Book, BookDraft


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'ai_check_title', 'ai_check_description', 'adm_check_title', 'adm_check_description', 'created_at', 'updated_at')
    list_filter = ('ai_check_title', 'ai_check_description', 'adm_check_title', 'adm_check_description', 'created_at')
    search_fields = ('title', 'description', 'author__email', 'author__display_name')
    readonly_fields = ('created_at', 'updated_at', 'last_chapter_update')
    
    fieldsets = (
        ('基本信息', {
            'fields': ('author', 'title', 'description')
        }),
        ('待审核内容', {
            'fields': ('title_pending', 'description_pending'),
            'classes': ('collapse',)
        }),
        ('审核状态', {
            'fields': ('ai_check_title', 'ai_check_description', 'adm_check_title', 'adm_check_description')
        }),
        ('拒绝原因', {
            'fields': ('title_reject_reason', 'description_reject_reason'),
            'classes': ('collapse',)
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at', 'last_chapter_update'),
            'classes': ('collapse',)
        }),
    )


@admin.register(BookDraft)
class BookDraftAdmin(admin.ModelAdmin):
    list_display = ('book', 'title', 'updated_at')
    search_fields = ('book__title', 'title', 'description')
    readonly_fields = ('updated_at',)
