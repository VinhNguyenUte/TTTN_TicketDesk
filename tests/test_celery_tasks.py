import os
from datetime import timedelta

import pytest
from django.core import mail
from django.utils import timezone

from apps.accounts.models import User
from apps.tickets.models import Ticket
from apps.tickets.services import assign_ticket
from apps.tickets.tasks import (
    export_tickets_excel_task,
    notify_status_changed,
    remind_overdue_tickets,
)
from apps.tickets.tests.factories import TicketFactory, UserFactory

pytestmark = pytest.mark.django_db


class TestCeleryTasks:
    def test_notify_status_changed_sends_email(self):
        """Test task notify_status_changed gửi email đến khách hàng và người phụ trách."""
        customer = UserFactory(email="khach01@example.com")
        agent = UserFactory(role=User.Role.AGENT, email="agent01@example.com")
        ticket = TicketFactory(
            customer=customer, assigned_to=agent, status=Ticket.Status.IN_PROGRESS
        )

        mail.outbox.clear()
        notify_status_changed(ticket.pk)

        assert len(mail.outbox) == 1
        sent_mail = mail.outbox[0]
        assert f"#{ticket.pk}" in sent_mail.subject
        assert "Đang xử lý" in sent_mail.subject
        assert "khach01@example.com" in sent_mail.to
        assert "agent01@example.com" in sent_mail.to

    def test_assign_ticket_service_calls_notify_task(self, monkeypatch):
        """Test gán ticket gọi notify_status_changed task."""
        customer = UserFactory(email="khach02@example.com")
        agent = UserFactory(role=User.Role.AGENT, email="agent02@example.com")
        ticket = TicketFactory(customer=customer, status=Ticket.Status.NEW)

        called_ticket_ids = []
        monkeypatch.setattr(
            "apps.tickets.tasks.notify_status_changed.delay",
            lambda tid: called_ticket_ids.append(tid),
        )

        with pytest.MonkeyPatch().context() as m:
            from django.db import transaction

            m.setattr(transaction, "on_commit", lambda func: func())
            assign_ticket(ticket.pk, agent)

        assert ticket.pk in called_ticket_ids

    def test_remind_overdue_tickets_beat_task(self):
        """Test Celery Beat task tìm các ticket quá hạn SLA và gửi cảnh báo."""
        agent = UserFactory(role=User.Role.AGENT, email="agent_overdue@example.com")
        past_time = timezone.now() - timedelta(hours=2)

        # Ticket quá hạn
        TicketFactory(
            assigned_to=agent, due_date=past_time, status=Ticket.Status.IN_PROGRESS
        )
        # Ticket đã giải quyết (không gửi)
        TicketFactory(
            assigned_to=agent, due_date=past_time, status=Ticket.Status.RESOLVED
        )

        mail.outbox.clear()
        count = remind_overdue_tickets()

        assert count >= 1
        assert any("quá hạn SLA" in m.subject for m in mail.outbox)

    def test_export_tickets_excel_task_generates_file(self):
        """Test task xuất báo cáo Excel chạy nền và tạo file hợp lệ."""
        TicketFactory.create_batch(2)
        mail.outbox.clear()

        filepath = export_tickets_excel_task(user_email="manager@example.com")

        assert filepath.endswith(".xlsx")
        assert os.path.exists(filepath)
        assert os.path.getsize(filepath) > 0
        assert len(mail.outbox) == 1
        assert "Báo cáo Excel đã sẵn sàng" in mail.outbox[0].subject
