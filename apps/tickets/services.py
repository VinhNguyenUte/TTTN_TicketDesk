from django.db import transaction

from apps.accounts.models import User
from apps.tickets.models import Ticket


class TicketClosedError(Exception):
    """Lỗi khi cố gắng thao tác trên ticket đã đóng."""

    pass


@transaction.atomic
def assign_ticket(ticket_id: int, agent: User) -> Ticket:
    """
    Phân công ticket cho nhân viên hỗ trợ (Agent) an toàn trong giao dịch.
    Sử dụng select_for_update() để khoá dòng dữ liệu trong PostgreSQL,
    tránh lỗi xung đột (Race Condition) khi 2 người cùng phân công một lúc.
    """
    ticket = Ticket.objects.select_for_update().get(pk=ticket_id)
    if ticket.status == Ticket.Status.CLOSED:
        raise TicketClosedError("Ticket đã đóng, không thể phân công lại.")

    ticket.assigned_to = agent
    ticket.status = Ticket.Status.IN_PROGRESS
    ticket.save(update_fields=["assigned_to", "status", "updated_at"])
    return ticket
