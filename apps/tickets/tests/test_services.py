import pytest
from django.db import IntegrityError
from django.utils import timezone

from apps.accounts.models import User
from apps.tickets.models import Ticket
from apps.tickets.services import TicketClosedError, assign_ticket

from .factories import (
    CategoryFactory,
    CommentFactory,
    PriorityFactory,
    TicketFactory,
    UserFactory,
)

pytestmark = pytest.mark.django_db


# ==============================================================================
# 1. UNIT TEST MODELS (Arrange - Act - Assert)
# ==============================================================================


class TestTicketModel:
    def test_create_ticket_successful(self):
        # Arrange & Act
        ticket = TicketFactory(title="Sự cố mạng văn phòng tầng 3")

        # Assert
        assert ticket.pk is not None
        assert ticket.status == Ticket.Status.NEW
        assert str(ticket) == f"#{ticket.pk} Sự cố mạng văn phòng tầng 3"

    def test_ticket_auto_set_resolved_at_when_resolved(self):
        # Arrange
        ticket = TicketFactory(status=Ticket.Status.NEW)
        assert ticket.resolved_at is None

        # Act
        ticket.status = Ticket.Status.RESOLVED
        ticket.save()

        # Assert
        assert ticket.resolved_at is not None
        assert ticket.resolved_at <= timezone.now()

    def test_ticket_created_by_and_assignee_alias_properties(self):
        # Arrange
        customer = UserFactory()
        agent = UserFactory(role=User.Role.AGENT)

        # Act
        ticket = TicketFactory(customer=customer)
        ticket.assignee = agent

        # Assert
        assert ticket.created_by == customer
        assert ticket.assignee == agent
        assert ticket.assigned_to == agent

    def test_ticket_empty_title_constraint_fails(self):
        # Arrange & Act & Assert (Vi phạm CheckConstraint ticket_title_not_empty)
        with pytest.raises(IntegrityError):
            TicketFactory(title="")


class TestCategoryAndPriorityModel:
    def test_category_str(self):
        category = CategoryFactory(name="Phần cứng")
        assert str(category) == "Phần cứng"

    def test_priority_str(self):
        priority = PriorityFactory(name="Khẩn cấp", level_weight=4)
        assert str(priority) == "Khẩn cấp"
        assert priority.level_weight == 4


class TestCommentModel:
    def test_create_comment(self):
        comment = CommentFactory(content="Đã xử lý xong cáp mạng")
        assert comment.pk is not None
        assert "Bình luận của" in str(comment)


# ==============================================================================
# 2. UNIT TEST SERVICE LAYER (assign_ticket) (Arrange - Act - Assert)
# ==============================================================================


class TestAssignTicketService:
    def test_assign_ticket_sets_agent_and_status(self):
        # Arrange
        ticket = TicketFactory(status=Ticket.Status.NEW)
        agent = UserFactory(role=User.Role.AGENT)

        # Act
        result = assign_ticket(ticket.pk, agent)

        # Assert
        assert result.assigned_to == agent
        assert result.status == Ticket.Status.IN_PROGRESS
        # Kiểm tra dữ liệu được lưu thật vào database
        ticket.refresh_from_db()
        assert ticket.assigned_to == agent
        assert ticket.status == Ticket.Status.IN_PROGRESS

    def test_cannot_assign_closed_ticket_raises_error(self):
        # Arrange
        ticket = TicketFactory(status=Ticket.Status.CLOSED)
        agent = UserFactory(role=User.Role.AGENT)

        # Act & Assert
        with pytest.raises(TicketClosedError) as exc_info:
            assign_ticket(ticket.pk, agent)

        assert "Ticket đã đóng, không thể phân công lại." in str(exc_info.value)
