from rest_framework import serializers

from apps.tickets.models import (
    Attachment,
    Category,
    Comment,
    Priority,
    Ticket,
    TicketHistory,
)


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "description"]


class PrioritySerializer(serializers.ModelSerializer):
    class Meta:
        model = Priority
        fields = ["id", "name", "level_weight", "color"]


class AttachmentSerializer(serializers.ModelSerializer):
    uploaded_by = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Attachment
        fields = [
            "id",
            "ticket",
            "comment",
            "file",
            "file_name",
            "file_size",
            "uploaded_by",
            "created_at",
        ]
        read_only_fields = ["id", "file_name", "file_size", "uploaded_by", "created_at"]


class CommentSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    user_id = serializers.IntegerField(source="user.id", read_only=True)
    attachments = AttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = Comment
        fields = [
            "id",
            "ticket",
            "user",
            "user_id",
            "content",
            "is_internal",
            "created_at",
            "updated_at",
            "attachments",
        ]
        read_only_fields = [
            "id",
            "ticket",
            "user",
            "created_at",
            "updated_at",
            "attachments",
        ]

    def validate_content(self, value):
        if not value.strip():
            raise serializers.ValidationError("Nội dung bình luận không được để trống.")
        return value.strip()


class TicketHistorySerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = TicketHistory
        fields = [
            "id",
            "ticket",
            "user",
            "action",
            "old_value",
            "new_value",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "ticket",
            "user",
            "action",
            "old_value",
            "new_value",
            "created_at",
        ]


class TicketSerializer(serializers.ModelSerializer):
    customer = serializers.StringRelatedField(read_only=True)
    customer_id = serializers.IntegerField(source="customer.id", read_only=True)
    assigned_to_name = serializers.CharField(
        source="assigned_to.username", read_only=True
    )
    category_name = serializers.CharField(source="category.name", read_only=True)
    priority_name = serializers.CharField(source="priority.name", read_only=True)
    priority_color = serializers.CharField(source="priority.color", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Ticket
        fields = [
            "id",
            "title",
            "description",
            "status",
            "status_display",
            "category",
            "category_name",
            "priority",
            "priority_name",
            "priority_color",
            "customer",
            "customer_id",
            "assigned_to",
            "assigned_to_name",
            "due_date",
            "resolved_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "status",
            "customer",
            "customer_id",
            "assigned_to",
            "resolved_at",
            "created_at",
            "updated_at",
        ]

    def validate_title(self, value: str) -> str:
        val = value.strip()
        if len(val) < 5:
            raise serializers.ValidationError("Tiêu đề tối thiểu 5 ký tự.")
        return val


class TicketAssignSerializer(serializers.Serializer):
    agent_id = serializers.IntegerField(required=True)


class TicketStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Ticket.Status.choices, required=True)


class DashboardStatsSerializer(serializers.Serializer):
    summary = serializers.DictField()
    status_breakdown = serializers.ListField(child=serializers.DictField())
    agent_performance = serializers.ListField(child=serializers.DictField())
