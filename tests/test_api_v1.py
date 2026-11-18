import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.notifications.models import Notification
from apps.tickets.models import Ticket
from apps.tickets.tests.factories import (
    CategoryFactory,
    PriorityFactory,
    TicketFactory,
    UserFactory,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def customer_user():
    return UserFactory(role=User.Role.CUSTOMER, username="khach01")


@pytest.fixture
def other_customer():
    return UserFactory(role=User.Role.CUSTOMER, username="khach02")


@pytest.fixture
def agent_user():
    return UserFactory(role=User.Role.AGENT, username="agent01")


@pytest.fixture
def manager_user():
    return UserFactory(role=User.Role.MANAGER, username="manager01")


@pytest.fixture
def category():
    return CategoryFactory(name="Phần cứng")


@pytest.fixture
def priority():
    return PriorityFactory(name="Cao", level_weight=3, color="#ef4444")


# ==============================================================================
# 1. TEST AUTHENTICATION & TOKENS (US01)
# ==============================================================================
class TestAuthAPI:
    def test_register_success(self, api_client):
        data = {
            "username": "new_user_1",
            "password": "Password@123",
            "password_confirm": "Password@123",
            "email": "newuser@example.com",
            "first_name": "Van",
            "last_name": "Nguyen",
        }
        res = api_client.post("/api/v1/auth/register", data)
        assert res.status_code == status.HTTP_201_CREATED
        user = User.objects.get(username="new_user_1")
        assert user.role == User.Role.CUSTOMER

    def test_register_password_mismatch_fails(self, api_client):
        data = {
            "username": "mismatch_user",
            "password": "Password@123",
            "password_confirm": "Password@456",
        }
        res = api_client.post("/api/v1/auth/register", data)
        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert "password_confirm" in res.data

    def test_login_jwt_success(self, api_client, customer_user):
        customer_user.set_password("password123")
        customer_user.save()
        res = api_client.post(
            "/api/v1/auth/login",
            {"username": customer_user.username, "password": "password123"},
        )
        assert res.status_code == status.HTTP_200_OK
        assert "access" in res.data
        assert "refresh" in res.data

    def test_login_invalid_credentials_fails(self, api_client):
        res = api_client.post(
            "/api/v1/auth/login", {"username": "fake", "password": "wrong"}
        )
        assert res.status_code == status.HTTP_401_UNAUTHORIZED

    def test_logout_without_token_fails(self, api_client, customer_user):
        api_client.force_authenticate(user=customer_user)
        res = api_client.post("/api/v1/auth/logout", {})
        assert res.status_code == status.HTTP_400_BAD_REQUEST


# ==============================================================================
# 2. TEST USER MANAGEMENT & ROLES (US02)
# ==============================================================================
class TestUserManagementAPI:
    def test_anonymous_cannot_access_users(self, api_client):
        res = api_client.get("/api/v1/users")
        assert res.status_code == status.HTTP_401_UNAUTHORIZED

    def test_agent_cannot_access_user_list(self, api_client, agent_user):
        api_client.force_authenticate(user=agent_user)
        res = api_client.get("/api/v1/users")
        assert res.status_code == status.HTTP_403_FORBIDDEN

    def test_manager_can_list_and_search_users(
        self, api_client, manager_user, customer_user
    ):
        api_client.force_authenticate(user=manager_user)
        res = api_client.get(f"/api/v1/users?search={customer_user.username}")
        assert res.status_code == status.HTTP_200_OK
        results = res.data["results"] if "results" in res.data else res.data
        assert any(u["username"] == customer_user.username for u in results)

    def test_manager_update_role_success(self, api_client, manager_user, customer_user):
        api_client.force_authenticate(user=manager_user)
        res = api_client.put(
            f"/api/v1/users/{customer_user.id}/role", {"role": User.Role.AGENT}
        )
        assert res.status_code == status.HTTP_200_OK
        customer_user.refresh_from_db()
        assert customer_user.role == User.Role.AGENT

    def test_manager_toggle_user_status(self, api_client, manager_user, customer_user):
        api_client.force_authenticate(user=manager_user)
        res = api_client.patch(
            f"/api/v1/users/{customer_user.id}/status", {"is_active": False}
        )
        assert res.status_code == status.HTTP_200_OK
        customer_user.refresh_from_db()
        assert customer_user.is_active is False


# ==============================================================================
# 3. TEST TICKET CRUD & VALIDATION (US03, US04, US06, US07, US08, US14)
# ==============================================================================
class TestTicketAPI:
    def test_create_ticket_validation_short_title(
        self, api_client, customer_user, category, priority
    ):
        api_client.force_authenticate(user=customer_user)
        payload = {
            "title": "abc",  # Tiêu đề < 5 ký tự
            "description": "Nội dung hợp lệ",
            "category": category.id,
            "priority": priority.id,
        }
        res = api_client.post("/api/v1/tickets", payload)
        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert "title" in res.data

    def test_customer_cannot_update_others_ticket(
        self, api_client, customer_user, other_customer, category, priority
    ):
        other_ticket = TicketFactory(
            customer=other_customer, category=category, priority=priority
        )
        api_client.force_authenticate(user=customer_user)
        res = api_client.patch(
            f"/api/v1/tickets/{other_ticket.id}", {"title": "Cố tình sửa tiêu đề"}
        )
        # 404 vì get_queryset filter theo customer -> IDOR safe
        assert res.status_code == status.HTTP_404_NOT_FOUND

    def test_customer_cannot_assign_ticket(
        self, api_client, customer_user, agent_user, category, priority
    ):
        ticket = TicketFactory(
            customer=customer_user, category=category, priority=priority
        )
        api_client.force_authenticate(user=customer_user)
        res = api_client.patch(
            f"/api/v1/tickets/{ticket.id}/assign", {"agent_id": agent_user.id}
        )
        assert res.status_code == status.HTTP_403_FORBIDDEN

    def test_customer_cannot_update_status(
        self, api_client, customer_user, category, priority
    ):
        ticket = TicketFactory(
            customer=customer_user, category=category, priority=priority
        )
        api_client.force_authenticate(user=customer_user)
        res = api_client.patch(
            f"/api/v1/tickets/{ticket.id}/status", {"status": Ticket.Status.CLOSED}
        )
        assert res.status_code == status.HTTP_403_FORBIDDEN

    def test_agent_assign_closed_ticket_conflict(
        self, api_client, agent_user, customer_user, category, priority
    ):
        ticket = TicketFactory(
            customer=customer_user,
            category=category,
            priority=priority,
            status=Ticket.Status.CLOSED,
        )
        api_client.force_authenticate(user=agent_user)
        res = api_client.patch(
            f"/api/v1/tickets/{ticket.id}/assign", {"agent_id": agent_user.id}
        )
        assert res.status_code == status.HTTP_409_CONFLICT
        assert res.data["code"] == "ticket_closed"

    def test_filter_and_search_tickets(
        self, api_client, agent_user, customer_user, category, priority
    ):
        TicketFactory(
            title="Máy in hỏng laser",
            customer=customer_user,
            category=category,
            priority=priority,
            status=Ticket.Status.NEW,
        )
        TicketFactory(
            title="Mạng chập chờn",
            customer=customer_user,
            category=category,
            priority=priority,
            status=Ticket.Status.IN_PROGRESS,
        )

        api_client.force_authenticate(user=agent_user)
        res = api_client.get("/api/v1/tickets?search=laser&status=new")
        assert res.status_code == status.HTTP_200_OK
        results = res.data["results"] if "results" in res.data else res.data
        assert len(results) == 1
        assert "laser" in results[0]["title"]


# ==============================================================================
# 4. TEST COMMENTS & ATTACHMENTS (US05)
# ==============================================================================
class TestCommentsAndAttachmentsAPI:
    def test_create_comment_empty_content_fails(
        self, api_client, customer_user, category, priority
    ):
        ticket = TicketFactory(
            customer=customer_user, category=category, priority=priority
        )
        api_client.force_authenticate(user=customer_user)
        res = api_client.post(
            f"/api/v1/tickets/{ticket.id}/comments", {"content": "   "}
        )
        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_customer_cannot_create_internal_comment(
        self, api_client, customer_user, category, priority
    ):
        ticket = TicketFactory(
            customer=customer_user, category=category, priority=priority
        )
        api_client.force_authenticate(user=customer_user)
        res = api_client.post(
            f"/api/v1/tickets/{ticket.id}/comments",
            {"content": "Bình luận", "is_internal": True},
        )
        assert res.status_code == status.HTTP_201_CREATED
        # Khách hàng bị ép is_internal = False
        assert res.data["is_internal"] is False

    def test_upload_attachment(self, api_client, customer_user, category, priority):
        ticket = TicketFactory(
            customer=customer_user, category=category, priority=priority
        )
        api_client.force_authenticate(user=customer_user)

        fake_file = SimpleUploadedFile(
            "log.txt", b"error log content", content_type="text/plain"
        )
        res = api_client.post(
            "/api/v1/attachments",
            {"ticket": ticket.id, "file": fake_file},
            format="multipart",
        )
        assert res.status_code == status.HTTP_201_CREATED
        assert res.data["file_name"] == "log.txt"


# ==============================================================================
# 5. TEST HISTORY & NOTIFICATIONS (US09, US10)
# ==============================================================================
class TestHistoryAndNotificationsAPI:
    def test_get_ticket_history(self, api_client, customer_user, category, priority):
        ticket = TicketFactory(
            customer=customer_user, category=category, priority=priority
        )
        api_client.force_authenticate(user=customer_user)
        res = api_client.get(f"/api/v1/tickets/{ticket.id}/history")
        assert res.status_code == status.HTTP_200_OK

    def test_notifications_list_and_mark_read(self, api_client, customer_user):
        noti = Notification.objects.create(
            user=customer_user, title="Thông báo mới", content="Ticket đã được nhận"
        )
        api_client.force_authenticate(user=customer_user)

        # Xem danh sách
        res_list = api_client.get("/api/v1/notifications")
        assert res_list.status_code == status.HTTP_200_OK
        results = (
            res_list.data["results"] if "results" in res_list.data else res_list.data
        )
        assert any(n["id"] == noti.id for n in results)

        # Đánh dấu đã đọc
        res_read = api_client.patch(f"/api/v1/notifications/{noti.id}/read", {})
        assert res_read.status_code == status.HTTP_200_OK
        noti.refresh_from_db()
        assert noti.is_read is True


# ==============================================================================
# 6. TEST DASHBOARD & METADATA (US11, US12, US13 & Metadata)
# ==============================================================================
class TestDashboardAndMetadataAPI:
    def test_customer_cannot_access_dashboard_stats(self, api_client, customer_user):
        api_client.force_authenticate(user=customer_user)
        res = api_client.get("/api/v1/dashboard/stats")
        assert res.status_code == status.HTTP_403_FORBIDDEN

    def test_customer_cannot_export_reports(self, api_client, customer_user):
        api_client.force_authenticate(user=customer_user)
        res = api_client.get("/api/v1/reports/tickets/export")
        assert res.status_code == status.HTTP_403_FORBIDDEN

    def test_manager_export_reports_success(
        self, api_client, manager_user, customer_user, category, priority
    ):
        TicketFactory(customer=customer_user, category=category, priority=priority)
        api_client.force_authenticate(user=manager_user)
        res = api_client.get("/api/v1/reports/tickets/export")
        assert res.status_code == status.HTTP_200_OK
        assert (
            res["Content-Type"]
            == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    def test_get_metadata_categories_and_priorities(
        self, api_client, customer_user, category, priority
    ):
        api_client.force_authenticate(user=customer_user)
        res_cat = api_client.get("/api/v1/categories")
        assert res_cat.status_code == status.HTTP_200_OK
        assert len(res_cat.data) >= 1

        res_pri = api_client.get("/api/v1/priorities")
        assert res_pri.status_code == status.HTTP_200_OK
        assert len(res_pri.data) >= 1
