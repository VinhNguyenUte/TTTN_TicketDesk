from django.contrib import admin

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "ticket", "title", "is_sent", "is_read", "created_at"]
    list_filter = ["is_sent", "is_read", "created_at"]
    search_fields = ["title", "content", "user__username"]
    autocomplete_fields = ["user", "ticket"]
