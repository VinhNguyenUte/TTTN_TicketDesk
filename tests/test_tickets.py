import pytest
from django.contrib.auth import get_user_model

from apps.tickets.models import Category, Priority, Ticket
from apps.tickets.services import TicketClosedError, assign_ticket

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


@pytest.mark.django_db
def test_ticket_stats_view(client):
    user = User.objects.create_user(username="statuser", password="password123")
    client.force_login(user)
    response = client.get("/tickets/stats/")
    assert response.status_code == 200
    assert "Báo cáo & Thống kê" in response.content.decode("utf-8")
    assert "status_stats" in response.context
    assert "agent_stats" in response.context


@pytest.mark.django_db
def test_assign_ticket_success():
    customer = User.objects.create_user(username="cust1", password="password123")
    agent = User.objects.create_user(
        username="agent1", password="password123", role=User.Role.AGENT
    )
    cat = Category.objects.create(name="Phần mềm")
    prio = Priority.objects.create(name="Cao", level_weight=3)

    ticket = Ticket.objects.create(
        title="Lỗi Office",
        description="Không kích hoạt được Word",
        customer=customer,
        category=cat,
        priority=prio,
        status=Ticket.Status.NEW,
    )

    updated_ticket = assign_ticket(ticket.pk, agent)
    assert updated_ticket.assigned_to == agent
    assert updated_ticket.status == Ticket.Status.IN_PROGRESS


@pytest.mark.django_db
def test_assign_ticket_closed_raises_error():
    customer = User.objects.create_user(username="cust2", password="password123")
    agent = User.objects.create_user(
        username="agent2", password="password123", role=User.Role.AGENT
    )
    cat = Category.objects.create(name="Mạng")
    prio = Priority.objects.create(name="Thấp", level_weight=1)

    ticket = Ticket.objects.create(
        title="Đổi mật khẩu WiFi",
        description="Đã xử lý xong",
        customer=customer,
        category=cat,
        priority=prio,
        status=Ticket.Status.CLOSED,
    )

    with pytest.raises(TicketClosedError):
        assign_ticket(ticket.pk, agent)


@pytest.mark.django_db
def test_ticket_list_prevents_n_plus_one(client, django_assert_num_queries):
    user = User.objects.create_user(
        username="admin_test", password="password123", role=User.Role.MANAGER
    )
    client.force_login(user)

    cat = Category.objects.create(name="Phần cứng")
    prio = Priority.objects.create(name="Cao", level_weight=3)

    # Tạo 15 tickets với các quan hệ ForeignKey khác nhau
    for i in range(15):
        Ticket.objects.create(
            title=f"Sự cố #{i}",
            description="Mô tả",
            customer=user,
            assigned_to=user,
            category=cat,
            priority=prio,
        )

    # Nhờ select_related(), số query lấy danh sách 15 ticket là hằng số (4 query):
    # 1. Session lookup, 2. Auth user lookup, 3. Paginator COUNT, 4. Single JOIN query for all 15 tickets
    with django_assert_num_queries(4):
        response = client.get("/tickets/")
        assert response.status_code == 200
        assert len(response.context["ticket_list"]) == 15


@pytest.mark.django_db
def test_ticket_detail_view(client):
    user = User.objects.create_user(
        username="detail_user", password="password123", role=User.Role.CUSTOMER
    )
    client.force_login(user)

    cat = Category.objects.create(name="Phần cứng")
    prio = Priority.objects.create(name="Cao", level_weight=3)

    ticket = Ticket.objects.create(
        title="Chi tiết ticket test",
        description="Mô tả chi tiết",
        customer=user,
        category=cat,
        priority=prio,
        status=Ticket.Status.NEW,
    )

    response = client.get(f"/tickets/{ticket.pk}/")
    assert response.status_code == 200
    assert "Chi tiết ticket test" in response.content.decode("utf-8")
