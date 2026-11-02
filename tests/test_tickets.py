import pytest
from django.contrib.auth import get_user_model

from apps.tickets.models import Category, Priority, Ticket

User = get_user_model()


@pytest.mark.django_db
def test_create_category():
    category = Category.objects.create(
        name="Phần cứng", description="Lỗi máy tính, bàn phím..."
    )
    assert category.name == "Phần cứng"
    assert str(category) == "Phần cứng"


@pytest.mark.django_db
def test_create_priority():
    priority = Priority.objects.create(name="Khẩn cấp", level_weight=4, color="#ef4444")
    assert priority.name == "Khẩn cấp"
    assert priority.level_weight == 4


@pytest.mark.django_db
def test_create_ticket():
    user = User.objects.create_user(username="testuser", password="password123")
    category = Category.objects.create(name="Mạng", description="Lỗi mạng nội bộ")
    priority = Priority.objects.create(name="Bình thường", level_weight=2)

    ticket = Ticket.objects.create(
        title="Mất mạng internet",
        description="Không vào được mạng từ sáng",
        customer=user,
        category=category,
        priority=priority,
    )
    assert ticket.pk is not None
    assert ticket.status == Ticket.Status.NEW
    assert str(ticket) == f"#{ticket.pk} Mất mạng internet"
