from django.conf import settings
from django.db import models


class Notification(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
        verbose_name="Người nhận",
    )
    ticket = models.ForeignKey(
        "tickets.Ticket",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
        verbose_name="Ticket liên quan",
    )
    title = models.CharField("Tiêu đề", max_length=200)
    content = models.TextField("Nội dung")
    is_sent = models.BooleanField(
        "Đã gửi đi",
        default=False,
        help_text="Đã gửi thông báo qua email/SMS/webhook chưa",
    )
    is_read = models.BooleanField(
        "Đã đọc",
        default=False,
        help_text="Người dùng đã xem thông báo trên hệ thống chưa",
    )
    created_at = models.DateTimeField("Ngày tạo", auto_now_add=True)

    class Meta:
        verbose_name = "Thông báo"
        verbose_name_plural = "Thông báo"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Thông báo tới {self.user.username}: {self.title}"
