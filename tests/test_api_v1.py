import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.tickets.models import Category, Comment, Priority, Ticket


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def customer_user(db):
    return User.objects.create_user(
        username="khach01",
        password="password123",
        email="khach01@example.com",
        role=User.Role.CUSTOMER,
    )


@pytest.fixture
def other_customer(db):
    return User.objects.create_user(
        username="khach02",
        password="password123",
        email="khach02@example.com",
        role=User.Role.CUSTOMER,
    )


@pytest.fixture
def agent_user(db):
    return User.objects.create_user(
        username="agent01",
        password="password123",
        email="agent01@example.com",
        role=User.Role.AGENT,
    )


@pytest.fixture
def manager_user(db):
    return User.objects.create_user(
        username="manager01",
        password="password123",
        email="manager01@example.com",
        role=User.Role.MANAGER,
    )


@pytest.fixture
def category(db):
    return Category.objects.create(name="Phần cứng", description="Lỗi phần cứng")


@pytest.fixture
def priority(db):
    return Priority.objects.create(name="Cao", level_weight=3, color="#ef4444")


@pytest.mark.django_db
class TestAuthenticationAPI:
    """Kiểm tra US01: Register, Login JWT, Logout."""

    def test_register_success(self, api_client):
        url = "/api/v1/auth/register"
        data = {
            "username": "newuser",
            "password": "strongpassword123",
            "password_confirm": "strongpassword123",
            "email": "newuser@example.com",
            "first_name": "Nguyen",
            "last_name": "Van A",
        }
        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_201_CREATED
        user = User.objects.get(username="newuser")
        assert user.role == User.Role.CUSTOMER

    def test_login_jwt(self, api_client, customer_user):
        url = "/api/v1/auth/login"
        response = api_client.post(
            url, {"username": "khach01", "password": "password123"}
        )
        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data
        assert "refresh" in response.data

    def test_logout(self, api_client, customer_user):
        login_res = api_client.post(
            "/api/v1/auth/login", {"username": "khach01", "password": "password123"}
        )
        access_token = login_res.data["access"]
        refresh_token = login_res.data["refresh"]

        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        logout_res = api_client.post("/api/v1/auth/logout", {"refresh": refresh_token})
        assert logout_res.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestUserManagementAPI:
    """Kiểm tra US02: Quản lý người dùng và phân quyền (MANAGER)."""

    def test_manager_can_list_users(self, api_client, manager_user, customer_user):
        api_client.force_authenticate(user=manager_user)
        response = api_client.get("/api/v1/users")
        assert response.status_code == status.HTTP_200_OK

    def test_customer_cannot_list_users(self, api_client, customer_user):
        api_client.force_authenticate(user=customer_user)
        response = api_client.get("/api/v1/users")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_manager_can_change_role(self, api_client, manager_user, customer_user):
        api_client.force_authenticate(user=manager_user)
        response = api_client.put(
            f"/api/v1/users/{customer_user.id}/role", {"role": User.Role.AGENT}
        )
        assert response.status_code == status.HTTP_200_OK
        customer_user.refresh_from_db()
        assert customer_user.role == User.Role.AGENT

    def test_manager_can_toggle_user_status(
        self, api_client, manager_user, customer_user
    ):
        api_client.force_authenticate(user=manager_user)
        response = api_client.patch(
            f"/api/v1/users/{customer_user.id}/status", {"is_active": False}
        )
        assert response.status_code == status.HTTP_200_OK
        customer_user.refresh_from_db()
        assert customer_user.is_active is False


@pytest.mark.django_db
class TestTicketAPIAndIDOR:
    """Kiểm tra US03, US04, US06, US07, US08, US14 và bảo mật chống IDOR."""

    def test_customer_can_create_ticket(
        self, api_client, customer_user, category, priority
    ):
        api_client.force_authenticate(user=customer_user)
        payload = {
            "title": "Hỏng màn hình máy tính Dell",
            "description": "Màn hình bị chớp tắt liên tục",
            "category": category.id,
            "priority": priority.id,
        }
        response = api_client.post("/api/v1/tickets", payload)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["title"] == payload["title"]
        assert response.data["customer_id"] == customer_user.id

    def test_customer_only_sees_own_tickets(
        self, api_client, customer_user, other_customer, category, priority
    ):
        t1 = Ticket.objects.create(
            title="Ticket cua Khach 1",
            customer=customer_user,
            category=category,
            priority=priority,
        )
        t2 = Ticket.objects.create(
            title="Ticket cua Khach 2",
            customer=other_customer,
            category=category,
            priority=priority,
        )

        api_client.force_authenticate(user=customer_user)
        response = api_client.get("/api/v1/tickets")
        assert response.status_code == status.HTTP_200_OK
        results = (
            response.data["results"] if "results" in response.data else response.data
        )
        ticket_ids = [item["id"] for item in results]
        assert t1.id in ticket_ids
        assert t2.id not in ticket_ids

    def test_idor_protection_customer_cannot_view_other_ticket(
        self, api_client, customer_user, other_customer, category, priority
    ):
        t2 = Ticket.objects.create(
            title="Ticket bi mat cua Khach 2",
            customer=other_customer,
            category=category,
            priority=priority,
        )

        # khach01 cố gắng đọc ticket của khach02 -> phải nhận 404 Not Found
        api_client.force_authenticate(user=customer_user)
        response = api_client.get(f"/api/v1/tickets/{t2.id}")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_agent_assign_and_status_update(
        self, api_client, agent_user, customer_user, category, priority
    ):
        ticket = Ticket.objects.create(
            title="Lỗi bàn phím gõ không ăn",
            customer=customer_user,
            category=category,
            priority=priority,
        )

        api_client.force_authenticate(user=agent_user)
        # Gán ticket
        assign_res = api_client.patch(
            f"/api/v1/tickets/{ticket.id}/assign", {"agent_id": agent_user.id}
        )
        assert assign_res.status_code == status.HTTP_200_OK
        ticket.refresh_from_db()
        assert ticket.assigned_to == agent_user
        assert ticket.status == Ticket.Status.IN_PROGRESS

        # Cập nhật trạng thái
        status_res = api_client.patch(
            f"/api/v1/tickets/{ticket.id}/status", {"status": Ticket.Status.RESOLVED}
        )
        assert status_res.status_code == status.HTTP_200_OK
        ticket.refresh_from_db()
        assert ticket.status == Ticket.Status.RESOLVED


@pytest.mark.django_db
class TestCommentsAndInternalBadge:
    """Kiểm tra US05: Bình luận và quyền xem ghi chú nội bộ."""

    def test_internal_comment_visibility(
        self, api_client, customer_user, agent_user, category, priority
    ):
        ticket = Ticket.objects.create(
            title="Sự cố mạng",
            customer=customer_user,
            category=category,
            priority=priority,
        )
        # Agent tạo 1 cmt nội bộ và 1 cmt công khai
        Comment.objects.create(
            ticket=ticket,
            user=agent_user,
            content="Ghi chú nội bộ cho kỹ thuật",
            is_internal=True,
        )
        Comment.objects.create(
            ticket=ticket,
            user=agent_user,
            content="Chào bạn, mình đang kiểm tra",
            is_internal=False,
        )

        # Khách hàng xem: chỉ thấy 1 bình luận công khai
        api_client.force_authenticate(user=customer_user)
        res_customer = api_client.get(f"/api/v1/tickets/{ticket.id}/comments")
        assert res_customer.status_code == status.HTTP_200_OK
        customer_comments = (
            res_customer.data["results"]
            if "results" in res_customer.data
            else res_customer.data
        )
        assert len(customer_comments) == 1
        assert customer_comments[0]["is_internal"] is False

        # Agent xem: thấy cả 2 bình luận
        api_client.force_authenticate(user=agent_user)
        res_agent = api_client.get(f"/api/v1/tickets/{ticket.id}/comments")
        assert res_agent.status_code == status.HTTP_200_OK
        agent_comments = (
            res_agent.data["results"] if "results" in res_agent.data else res_agent.data
        )
        assert len(agent_comments) == 2


@pytest.mark.django_db
class TestDashboardAndReport:
    """Kiểm tra US11, US12, US13: Dashboard, SLA, Export."""

    def test_manager_dashboard_and_export(
        self, api_client, manager_user, customer_user, category, priority
    ):
        Ticket.objects.create(
            title="Ticket test 1",
            customer=customer_user,
            category=category,
            priority=priority,
        )

        api_client.force_authenticate(user=manager_user)
        # Dashboard stats
        stats_res = api_client.get("/api/v1/dashboard/stats")
        assert stats_res.status_code == status.HTTP_200_OK
        assert "summary" in stats_res.data
        assert stats_res.data["summary"]["total_tickets"] >= 1

        # SLA Warnings
        sla_res = api_client.get("/api/v1/dashboard/sla-warnings")
        assert sla_res.status_code == status.HTTP_200_OK

        # Export Excel
        export_res = api_client.get("/api/v1/reports/tickets/export")
        assert export_res.status_code == status.HTTP_200_OK
        assert (
            export_res["Content-Type"]
            == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
