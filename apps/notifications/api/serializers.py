from rest_framework import serializers

from apps.notifications.models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            "id",
            "ticket",
            "title",
            "content",
            "is_sent",
            "is_read",
            "created_at",
        ]
        read_only_fields = ["id", "ticket", "title", "content", "is_sent", "created_at"]


class NotificationReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ["is_read"]
