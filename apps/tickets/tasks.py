import os

import openpyxl
from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from apps.tickets.models import Ticket


@shared_task(autoretry_for=(Exception,), retry_backoff=True, max_retries=5)
def notify_status_changed(ticket_id: int) -> None:
    """Task gửi email thông báo khi trạng thái ticket thay đổi."""
    try:
        ticket = Ticket.objects.select_related("customer", "assigned_to").get(
            pk=ticket_id
        )
    except Ticket.DoesNotExist:
        return

    recipients = []
    if ticket.customer and ticket.customer.email:
        recipients.append(ticket.customer.email)
    if (
        ticket.assigned_to
        and ticket.assigned_to.email
        and ticket.assigned_to.email not in recipients
    ):
        recipients.append(ticket.assigned_to.email)

    if recipients:
        send_mail(
            subject=f"[TicketDesk] #{ticket.pk} chuyển sang {ticket.get_status_display()}",
            message=f'Ticket "{ticket.title}" vừa được cập nhật sang trạng thái {ticket.get_status_display()}.\n'
            f"Xem chi tiết tại hệ thống TicketDesk.",
            from_email=getattr(
                settings, "DEFAULT_FROM_EMAIL", "noreply@ticketdesk.local"
            ),
            recipient_list=recipients,
            fail_silently=False,
        )


@shared_task
def remind_overdue_tickets() -> int:
    """Celery Beat task chạy định kỳ nhắc nhở ticket quá hạn SLA."""
    now = timezone.now()
    overdue_tickets = (
        Ticket.objects.select_related("assigned_to")
        .filter(
            due_date__lt=now,
            resolved_at__isnull=True,
        )
        .exclude(status__in=[Ticket.Status.RESOLVED, Ticket.Status.CLOSED])
    )

    reminded_count = 0
    for ticket in overdue_tickets:
        if ticket.assigned_to and ticket.assigned_to.email:
            send_mail(
                subject=f"[TicketDesk CẢNH BÁO] Ticket #{ticket.pk} đã quá hạn SLA!",
                message=f'Ticket "{ticket.title}" đã quá hạn vào lúc {ticket.due_date:%d/%m/%Y %H:%M}.\n'
                f"Vui lòng ưu tiên xử lý ngay.",
                from_email=getattr(
                    settings, "DEFAULT_FROM_EMAIL", "noreply@ticketdesk.local"
                ),
                recipient_list=[ticket.assigned_to.email],
                fail_silently=True,
            )
            reminded_count += 1

    return reminded_count


@shared_task
def export_tickets_excel_task(user_email: str | None = None) -> str:
    """Tác vụ nền tạo báo cáo Excel bằng openpyxl và lưu vào media/reports/."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Tickets Report"

    headers = [
        "ID",
        "Tiêu đề",
        "Trạng thái",
        "Độ ưu tiên",
        "Danh mục",
        "Khách hàng",
        "Người xử lý",
        "Ngày tạo",
        "Hạn SLA",
    ]
    ws.append(headers)

    tickets = (
        Ticket.objects.select_related("category", "priority", "assigned_to", "customer")
        .all()
        .order_by("-created_at")
    )
    for t in tickets:
        ws.append(
            [
                t.id,
                t.title,
                t.get_status_display(),
                t.priority.name if t.priority else "",
                t.category.name if t.category else "",
                t.customer.username if t.customer else "",
                t.assigned_to.username if t.assigned_to else "Chưa phân công",
                t.created_at.strftime("%Y-%m-%d %H:%M:%S") if t.created_at else "",
                t.due_date.strftime("%Y-%m-%d %H:%M:%S") if t.due_date else "",
            ]
        )

    reports_dir = os.path.join(settings.MEDIA_ROOT, "reports")
    os.makedirs(reports_dir, exist_ok=True)
    filename = f"tickets_report_{timezone.now():%Y%m%d_%H%M%S}.xlsx"
    filepath = os.path.join(reports_dir, filename)
    wb.save(filepath)

    if user_email:
        send_mail(
            subject="[TicketDesk] Báo cáo Excel đã sẵn sàng",
            message=f"Báo cáo ticket bạn yêu cầu đã hoàn tất.\nTên file: {filename}",
            from_email=getattr(
                settings, "DEFAULT_FROM_EMAIL", "noreply@ticketdesk.local"
            ),
            recipient_list=[user_email],
            fail_silently=True,
        )

    return filepath
