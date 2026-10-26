from django.contrib import admin

from .models import Attachment, Category, Comment, Priority, Ticket, TicketHistory


class CommentInline(admin.TabularInline):
    model = Comment
    extra = 1
    fields = ["user", "content", "is_internal", "created_at"]
    readonly_fields = ["created_at"]


class AttachmentInline(admin.TabularInline):
    model = Attachment
    extra = 1
    fields = ["file", "file_name", "file_size", "uploaded_by", "created_at"]
    readonly_fields = ["file_name", "file_size", "created_at"]


class TicketHistoryInline(admin.TabularInline):
    model = TicketHistory
    extra = 0
    can_delete = False
    readonly_fields = ["user", "action", "old_value", "new_value", "created_at"]


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "description"]
    search_fields = ["name"]


@admin.register(Priority)
class PriorityAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "level_weight", "color"]
    search_fields = ["name"]
    ordering = ["level_weight"]


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "title",
        "status",
        "priority",
        "category",
        "customer",
        "assigned_to",
        "due_date",
        "created_at",
    ]
    list_filter = ["status", "priority", "category", "created_at"]
    search_fields = [
        "title",
        "description",
        "customer__username",
        "assigned_to__username",
    ]
    autocomplete_fields = ["customer", "assigned_to", "category", "priority"]
    inlines = [CommentInline, AttachmentInline, TicketHistoryInline]


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ["id", "ticket", "user", "is_internal", "created_at"]
    list_filter = ["is_internal", "created_at"]
    search_fields = ["content", "user__username", "ticket__title"]
    autocomplete_fields = ["ticket", "user"]


@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "file_name",
        "ticket",
        "comment",
        "file_size",
        "uploaded_by",
        "created_at",
    ]
    list_filter = ["created_at"]
    search_fields = ["file_name", "ticket__title", "uploaded_by__username"]
    autocomplete_fields = ["ticket", "comment", "uploaded_by"]


@admin.register(TicketHistory)
class TicketHistoryAdmin(admin.ModelAdmin):
    list_display = ["id", "ticket", "user", "action", "created_at"]
    list_filter = ["action", "created_at"]
    search_fields = ["action", "old_value", "new_value", "ticket__title"]
    autocomplete_fields = ["ticket", "user"]
