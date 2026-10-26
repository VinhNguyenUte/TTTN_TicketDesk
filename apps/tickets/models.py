from django.conf import settings
from django.db import models
from django.utils import timezone


class Category(models.Model):
    name = models.CharField("Tên danh mục", max_length=100, unique=True)
    description = models.TextField("Mô tả", blank=True, default="")

    class Meta:
        verbose_name = "Danh mục"
        verbose_name_plural = "Danh mục"

    def __str__(self) -> str:
        return self.name


class Priority(models.Model):
    name = models.CharField("Tên độ ưu tiên", max_length=50, unique=True)
    level_weight = models.IntegerField(
        "Trọng số mức độ",
        default=1,
        help_text="Thứ tự ưu tiên (1: Thấp, 2: Trung bình, 3: Cao, 4: Khẩn cấp)",
    )
    color = models.CharField(
        "Mã màu",
        max_length=20,
        default="#64748b",
        blank=True,
        help_text="Mã màu HEX cho badge (vd: #ef4444)",
    )

    class Meta:
        verbose_name = "Độ ưu tiên"
        verbose_name_plural = "Độ ưu tiên"
        ordering = ["level_weight"]

    def __str__(self) -> str:
        return self.name


class Ticket(models.Model):
    class Status(models.TextChoices):
        NEW = "new", "Mới"
        IN_PROGRESS = "in_progress", "Đang xử lý"
        RESOLVED = "resolved", "Đã xử lý"
        CLOSED = "closed", "Đã đóng"

    title = models.CharField("Tiêu đề", max_length=200)
    description = models.TextField("Mô tả")
    status = models.CharField(
        "Trạng thái", max_length=20, choices=Status.choices, default=Status.NEW
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="customer_tickets",
        verbose_name="Khách hàng",
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_tickets",
        verbose_name="Người xử lý",
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="tickets",
        verbose_name="Danh mục",
    )
    priority = models.ForeignKey(
        Priority,
        on_delete=models.PROTECT,
        related_name="tickets",
        verbose_name="Độ ưu tiên",
    )
    due_date = models.DateTimeField("Hạn xử lý (SLA)", null=True, blank=True)
    resolved_at = models.DateTimeField("Thời điểm giải quyết", null=True, blank=True)
    created_at = models.DateTimeField("Ngày tạo", auto_now_add=True)
    updated_at = models.DateTimeField("Ngày cập nhật", auto_now=True)

    class Meta:
        verbose_name = "Ticket"
        verbose_name_plural = "Tickets"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"#{self.pk} {self.title}"

    @property
    def created_by(self):
        return self.customer

    @property
    def assignee(self):
        return self.assigned_to

    def save(self, *args, **kwargs):
        if (
            self.status in [self.Status.RESOLVED, self.Status.CLOSED]
            and not self.resolved_at
        ):
            self.resolved_at = timezone.now()
        super().save(*args, **kwargs)


class Comment(models.Model):
    ticket = models.ForeignKey(
        Ticket, on_delete=models.CASCADE, related_name="comments", verbose_name="Ticket"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ticket_comments",
        verbose_name="Người bình luận",
    )
    content = models.TextField("Nội dung")
    is_internal = models.BooleanField(
        "Ghi chú nội bộ",
        default=False,
        help_text="Chỉ Agent/Manager mới xem được ghi chú nội bộ này",
    )
    created_at = models.DateTimeField("Ngày tạo", auto_now_add=True)
    updated_at = models.DateTimeField("Ngày cập nhật", auto_now=True)

    class Meta:
        verbose_name = "Bình luận"
        verbose_name_plural = "Bình luận"
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"Bình luận của {self.user.username} trên #{self.ticket_id}"


class Attachment(models.Model):
    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="attachments",
        verbose_name="Ticket",
    )
    comment = models.ForeignKey(
        Comment,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="attachments",
        verbose_name="Bình luận",
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="uploaded_attachments",
        verbose_name="Người tải lên",
    )
    file = models.FileField("Tệp đính kèm", upload_to="attachments/%Y/%m/")
    file_name = models.CharField("Tên tệp", max_length=255, blank=True)
    file_size = models.PositiveIntegerField("Kích thước file (bytes)", default=0)
    created_at = models.DateTimeField("Ngày tải lên", auto_now_add=True)

    class Meta:
        verbose_name = "Tệp đính kèm"
        verbose_name_plural = "Tệp đính kèm"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.file_name or (self.file.name if self.file else "Tệp đính kèm")

    def save(self, *args, **kwargs):
        if self.file:
            if not self.file_name:
                self.file_name = self.file.name.split("/")[-1]
            if hasattr(self.file, "size") and not self.file_size:
                self.file_size = self.file.size
        super().save(*args, **kwargs)


class TicketHistory(models.Model):
    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        related_name="histories",
        verbose_name="Ticket",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ticket_histories",
        verbose_name="Người thực hiện",
    )
    action = models.CharField("Hành động", max_length=100)
    old_value = models.TextField("Giá trị cũ", null=True, blank=True)
    new_value = models.TextField("Giá trị mới", null=True, blank=True)
    created_at = models.DateTimeField("Thời gian", auto_now_add=True)

    class Meta:
        verbose_name = "Lịch sử ticket"
        verbose_name_plural = "Lịch sử ticket"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"#{self.ticket_id} - {self.action} ({self.created_at:%d/%m/%Y %H:%M})"
