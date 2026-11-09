from rest_framework import generics, permissions

from apps.notifications.models import Notification

from .serializers import NotificationReadSerializer, NotificationSerializer


class NotificationListView(generics.ListAPIView):
    """US10: Lấy danh sách thông báo của người dùng hiện tại."""

    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Notification.objects.all()

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Notification.objects.none()
        return Notification.objects.filter(user=self.request.user).order_by(
            "-created_at"
        )


class NotificationMarkReadView(generics.UpdateAPIView):
    """US10: Đánh dấu thông báo đã đọc (PATCH)."""

    serializer_class = NotificationReadSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["patch"]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

    def perform_update(self, serializer):
        serializer.save(is_read=True)
