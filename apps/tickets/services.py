from django.core.cache import cache
from django.db import transaction
from django.db.models import Count, Q

from apps.accounts.models import User
from apps.tickets.models import Ticket

STATS_CACHE_KEY = "dashboard:stats"


class TicketClosedError(Exception):
    """Lỗi khi cố gắng thao tác trên ticket đã đóng."""

    pass


class InactiveUserError(Exception):
    """Lỗi khi phân công cho tài khoản bị khóa."""

    pass


def compute_dashboard_stats() -> dict:
    """Hàm tính toán thống kê dashboard (dùng để lưu vào cache)."""
    status_counts_raw = Ticket.objects.values("status").annotate(total=Count("id"))
    status_dict = {item["status"]: item["total"] for item in status_counts_raw}

    status_breakdown = [
        {
            "status": choice_val,
            "label": choice_label,
            "count": status_dict.get(choice_val, 0),
        }
        for choice_val, choice_label in Ticket.Status.choices
    ]

    summary = Ticket.objects.aggregate(
        total_tickets=Count("id"),
        open_tickets=Count("id", filter=~Q(status=Ticket.Status.CLOSED)),
        resolved_tickets=Count(
            "id",
            filter=Q(status__in=[Ticket.Status.RESOLVED, Ticket.Status.CLOSED]),
        ),
    )
    total = summary["total_tickets"] or 0
    resolved = summary["resolved_tickets"] or 0
    resolution_rate = round((resolved / total * 100), 1) if total > 0 else 0

    agents_data = []
    agents = User.objects.filter(role=User.Role.AGENT).annotate(
        total_assigned=Count("assigned_tickets"),
        open_count=Count(
            "assigned_tickets",
            filter=~Q(assigned_tickets__status=Ticket.Status.CLOSED),
        ),
    )
    for ag in agents:
        agents_data.append(
            {
                "id": ag.id,
                "username": ag.username,
                "total_assigned": ag.total_assigned,
                "open_count": ag.open_count,
            }
        )

    return {
        "summary": {
            "total_tickets": total,
            "open_tickets": summary["open_tickets"] or 0,
            "resolved_tickets": resolved,
            "resolution_rate": f"{resolution_rate}%",
        },
        "status_breakdown": status_breakdown,
        "agent_performance": agents_data,
    }


def get_cached_dashboard_stats(timeout: int = 300) -> dict:
    """Lấy dữ liệu thống kê từ cache, nếu chưa có thì tính toán và lưu cache (TTL 300s)."""
    return cache.get_or_set(STATS_CACHE_KEY, compute_dashboard_stats, timeout=timeout)


def invalidate_dashboard_stats() -> None:
    """Xóa cache thống kê khi có thay đổi liên quan đến ticket (tạo, đổi status...)."""
    cache.delete(STATS_CACHE_KEY)


@transaction.atomic
def assign_ticket(ticket_id: int, agent: User) -> Ticket:
    """
    Phân công ticket cho nhân viên hỗ trợ (Agent) an toàn trong giao dịch.
    Sử dụng select_for_update() để khoá dòng dữ liệu trong PostgreSQL,
    tránh lỗi xung đột (Race Condition) khi 2 người cùng phân công một lúc.
    Đồng thời gọi tác vụ nền gửi email sau khi transaction commit thành công.
    """
    if not agent.is_active:
        raise InactiveUserError("Không thể gán ticket cho tài khoản bị khóa.")

    ticket = Ticket.objects.select_for_update().get(pk=ticket_id)
    if ticket.status == Ticket.Status.CLOSED:
        raise TicketClosedError("Ticket đã đóng, không thể phân công lại.")

    ticket.assigned_to = agent
    ticket.status = Ticket.Status.IN_PROGRESS
    ticket.save(update_fields=["assigned_to", "status", "updated_at"])

    # Xóa cache thống kê
    invalidate_dashboard_stats()

    # Gửi email thông báo qua Celery task khi transaction hoàn tất (on_commit)
    from apps.tickets.tasks import notify_status_changed

    transaction.on_commit(lambda: notify_status_changed.delay(ticket.pk))

    return ticket
