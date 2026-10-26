from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        CUSTOMER = "customer", "Khách hàng"
        AGENT = "agent", "Nhân viên hỗ trợ"
        MANAGER = "manager", "Quản lý"

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.CUSTOMER,
        verbose_name="Vai trò",
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Ngày cập nhật")

    def __str__(self) -> str:
        return f"{self.username} ({self.get_role_display()})"
