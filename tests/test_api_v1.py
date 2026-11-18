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
    user = UserFactory(role=User.Role.CUSTOMER, username="khach01")
    user.set_password("matkhau123")
    user.save()
    return user


@pytest.fixture
def other_customer():
    user = UserFactory(role=User.Role.CUSTOMER, username="khach02")
    user.set_password("matkhau123")
    user.save()
    return user


@pytest.fixture
def agent_user():
    user = UserFactory(role=User.Role.AGENT, username="nhanvien01")
    user.set_password("matkhau123")
    user.save()
    return user


@pytest.fixture
def other_agent():
    user = UserFactory(role=User.Role.AGENT, username="nhanvien02")
    user.set_password("matkhau123")
    user.save()
    return user


@pytest.fixture
def manager_user():
    user = UserFactory(role=User.Role.MANAGER, username="quanly01")
    user.set_password("matkhau123")
    user.save()
    return user


@pytest.fixture
def category():
    return CategoryFactory(name="Phần cứng")


@pytest.fixture
def priority():
    return PriorityFactory(name="Cao", level_weight=3, color="#ef4444")


# ==============================================================================
# 1. US01 – ĐĂNG NHẬP, ĐĂNG XUẤT (GIVEN / WHEN / THEN)
# ==============================================================================
class TestUS01Auth:
    def test_kbt1_login_success(self, api_client, customer_user):
        """Kịch bản 1: Đăng nhập thành công -> trả về JWT."""
        res = api_client.post(
            "/api/v1/auth/login",
            {"username": customer_user.username, "password": "matkhau123"},
        )
        assert res.status_code == status.HTTP_200_OK
        assert "access" in res.data
        assert "refresh" in res.data

    def test_kbt2_login_wrong_password(self, api_client, customer_user):
        """Kịch bản 2: Đăng nhập sai mật khẩu -> từ chối cấp token (401)."""
        res = api_client.post(
            "/api/v1/auth/login",
            {"username": customer_user.username, "password": "sai_mat_khau"},
        )
        assert res.status_code == status.HTTP_401_UNAUTHORIZED

    def test_kbt3_login_non_existent_user(self, api_client):
        """Kịch bản 3: Đăng nhập với tài khoản không tồn tại user999 -> 401."""
        res = api_client.post(
            "/api/v1/auth/login",
            {"username": "user999", "password": "any_password"},
        )
        assert res.status_code == status.HTTP_401_UNAUTHORIZED

    def test_kbt4_logout_success(self, api_client, customer_user):
        """Kịch bản 4: Đăng xuất thành công -> Blacklist refresh token."""
        login_res = api_client.post(
            "/api/v1/auth/login",
            {"username": customer_user.username, "password": "matkhau123"},
        )
        refresh_token = login_res.data["refresh"]
        access_token = login_res.data["access"]

        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        logout_res = api_client.post("/api/v1/auth/logout", {"refresh": refresh_token})
        assert logout_res.status_code == status.HTTP_200_OK


# ==============================================================================
# 2. US02 – QUẢN LÝ TÀI KHOẢN VÀ PHÂN QUYỀN
# ==============================================================================
class TestUS02UserManagement:
    def test_kbt1_manager_change_role_agent(
        self, api_client, manager_user, customer_user
    ):
        """Kịch bản 1: Gán vai trò Nhân viên hỗ trợ."""
        api_client.force_authenticate(user=manager_user)
        res = api_client.put(
            f"/api/v1/users/{customer_user.id}/role",
            {"role": User.Role.AGENT},
        )
        assert res.status_code == status.HTTP_200_OK
        customer_user.refresh_from_db()
        assert customer_user.role == User.Role.AGENT

    def test_kbt2_register_duplicate_username_fails(self, api_client, customer_user):
        """Kịch bản 2: Tạo tài khoản với username đã tồn tại -> 400 Bad Request."""
        data = {
            "username": customer_user.username,
            "password": "Password@123",
            "password_confirm": "Password@123",
            "email": "test@example.com",
        }
        res = api_client.post("/api/v1/auth/register", data)
        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert "username" in res.data

    def test_kbt3_agent_cannot_access_user_management(self, api_client, agent_user):
        """Kịch bản 3: Nhân viên truy cập chức năng chỉ dành cho quản lý -> 403."""
        api_client.force_authenticate(user=agent_user)
        res = api_client.get("/api/v1/users")
        assert res.status_code == status.HTTP_403_FORBIDDEN

    def test_kbt4_manager_lock_user_account(self, api_client, manager_user, agent_user):
        """Kịch bản 4: Khóa tài khoản thành công."""
        api_client.force_authenticate(user=manager_user)
        res = api_client.patch(
            f"/api/v1/users/{agent_user.id}/status",
            {"is_active": False},
        )
        assert res.status_code == status.HTTP_200_OK
        agent_user.refresh_from_db()
        assert agent_user.is_active is False


# ==============================================================================
# 3. US03 – TẠO TICKET
# ==============================================================================
class TestUS03TicketCreation:
    def test_kbt1_create_ticket_success(
        self, api_client, customer_user, category, priority
    ):
        """Kịch bản 1: Tạo ticket thành công -> Trạng thái ban đầu là Mới."""
        api_client.force_authenticate(user=customer_user)
        payload = {
            "title": "Hỏng bàn phím cơ văn phòng",
            "description": "Các phím ASDF bị liệt",
            "category": category.id,
            "priority": priority.id,
        }
        res = api_client.post("/api/v1/tickets", payload)
        assert res.status_code == status.HTTP_201_CREATED
        assert res.data["id"] is not None
        assert res.data["status"] == Ticket.Status.NEW

    def test_kbt2_create_ticket_missing_title(
        self, api_client, customer_user, category, priority
    ):
        """Kịch bản 2: Tạo ticket thiếu tiêu đề -> 400."""
        api_client.force_authenticate(user=customer_user)
        payload = {
            "title": "",
            "description": "Không có tiêu đề",
            "category": category.id,
            "priority": priority.id,
        }
        res = api_client.post("/api/v1/tickets", payload)
        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert "title" in res.data

    def test_kbt4_create_ticket_unauthenticated(self, api_client, category, priority):
        """Kịch bản 4: Tạo ticket khi chưa đăng nhập -> 401 Unauthorized."""
        payload = {
            "title": "Cần hỗ trợ gấp",
            "description": "Mô tả",
            "category": category.id,
            "priority": priority.id,
        }
        res = api_client.post("/api/v1/tickets", payload)
        assert res.status_code == status.HTTP_401_UNAUTHORIZED


# ==============================================================================
# 4. US04 & US06 – XEM DANH SÁCH & CHI TIẾT TICKET (PHÂN QUYỀN VÀ IDOR)
# ==============================================================================
class TestUS04AndUS06ViewTickets:
    def test_us04_kbt1_customer_sees_own_tickets(
        self, api_client, customer_user, category, priority
    ):
        """Kịch bản 1: Khách hàng chỉ thấy các ticket do mình tạo."""
        TicketFactory.create_batch(
            3, customer=customer_user, category=category, priority=priority
        )
        api_client.force_authenticate(user=customer_user)

        res = api_client.get("/api/v1/tickets")
        assert res.status_code == status.HTTP_200_OK
        results = res.data["results"] if "results" in res.data else res.data
        assert len(results) == 3

    def test_us04_kbt2_view_ticket_detail(
        self, api_client, customer_user, category, priority
    ):
        """Kịch bản 2: Xem chi tiết ticket của mình."""
        ticket = TicketFactory(
            customer=customer_user, category=category, priority=priority
        )
        api_client.force_authenticate(user=customer_user)

        res = api_client.get(f"/api/v1/tickets/{ticket.id}")
        assert res.status_code == status.HTTP_200_OK
        assert res.data["id"] == ticket.id
        assert res.data["title"] == ticket.title

    def test_us04_kbt3_customer_cannot_view_others_ticket(
        self, api_client, customer_user, other_customer, category, priority
    ):
        """Kịch bản 3: Truy cập ticket của người khác -> 404 (chống IDOR)."""
        other_ticket = TicketFactory(
            customer=other_customer, category=category, priority=priority
        )
        api_client.force_authenticate(user=customer_user)

        res = api_client.get(f"/api/v1/tickets/{other_ticket.id}")
        assert res.status_code == status.HTTP_404_NOT_FOUND

    def test_us04_kbt4_empty_tickets_list(self, api_client, customer_user):
        """Kịch bản 4: Xem danh sách khi chưa có ticket -> Danh sách rỗng."""
        api_client.force_authenticate(user=customer_user)
        res = api_client.get("/api/v1/tickets")
        assert res.status_code == status.HTTP_200_OK
        results = res.data["results"] if "results" in res.data else res.data
        assert len(results) == 0

    def test_us06_agent_view_assigned_and_unassigned_tickets(
        self, api_client, agent_user, other_agent, customer_user, category, priority
    ):
        """US06: Agent thấy ticket được giao cho mình hoặc chưa có người xử lý, không thấy ticket của agent khác."""
        t_assigned = TicketFactory(
            customer=customer_user,
            assigned_to=agent_user,
            category=category,
            priority=priority,
        )
        t_unassigned = TicketFactory(
            customer=customer_user,
            assigned_to=None,
            category=category,
            priority=priority,
        )
        t_other = TicketFactory(
            customer=customer_user,
            assigned_to=other_agent,
            category=category,
            priority=priority,
        )

        api_client.force_authenticate(user=agent_user)
        res = api_client.get("/api/v1/tickets")
        assert res.status_code == status.HTTP_200_OK
        results = res.data["results"] if "results" in res.data else res.data
        ticket_ids = [t["id"] for t in results]

        assert t_assigned.id in ticket_ids
        assert t_unassigned.id in ticket_ids
        assert t_other.id not in ticket_ids


# ==============================================================================
# 5. US05 – BÌNH LUẬN VÀ ĐÍNH KÈM FILE
# ==============================================================================
class TestUS05CommentsAndAttachments:
    def test_kbt1_add_comment_success(
        self, api_client, customer_user, category, priority
    ):
        """Kịch bản 1: Thêm bình luận thành công."""
        ticket = TicketFactory(
            customer=customer_user, category=category, priority=priority
        )
        api_client.force_authenticate(user=customer_user)

        res = api_client.post(
            f"/api/v1/tickets/{ticket.id}/comments",
            {"content": "Tôi đã thử restart nhưng không được"},
        )
        assert res.status_code == status.HTTP_201_CREATED
        assert res.data["content"] == "Tôi đã thử restart nhưng không được"

    def test_kbt2_upload_valid_attachment(
        self, api_client, customer_user, category, priority
    ):
        """Kịch bản 2: Tải file PNG hợp lệ thành công."""
        ticket = TicketFactory(
            customer=customer_user, category=category, priority=priority
        )
        api_client.force_authenticate(user=customer_user)

        png_file = SimpleUploadedFile(
            "screenshot.png", b"\x89PNG\r\n\x1a\nfakeimage", content_type="image/png"
        )
        res = api_client.post(
            "/api/v1/attachments",
            {"ticket": ticket.id, "file": png_file},
            format="multipart",
        )
        assert res.status_code == status.HTTP_201_CREATED
        assert res.data["file_name"] == "screenshot.png"

    def test_kbt3_upload_file_exceeds_size(
        self, api_client, customer_user, category, priority
    ):
        """Kịch bản 3: Tải file vượt quá dung lượng 10MB -> 400 Bad Request."""
        ticket = TicketFactory(
            customer=customer_user, category=category, priority=priority
        )
        api_client.force_authenticate(user=customer_user)

        # Giả lập file > 10MB
        large_content = b"0" * (11 * 1024 * 1024)
        large_file = SimpleUploadedFile(
            "large.pdf", large_content, content_type="application/pdf"
        )
        res = api_client.post(
            "/api/v1/attachments",
            {"ticket": ticket.id, "file": large_file},
            format="multipart",
        )
        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert "file" in res.data

    def test_kbt4_upload_unsupported_file_extension(
        self, api_client, customer_user, category, priority
    ):
        """Kịch bản 4: Tải file .exe không được hỗ trợ -> 400."""
        ticket = TicketFactory(
            customer=customer_user, category=category, priority=priority
        )
        api_client.force_authenticate(user=customer_user)

        exe_file = SimpleUploadedFile(
            "script.exe", b"binary content", content_type="application/octet-stream"
        )
        res = api_client.post(
            "/api/v1/attachments",
            {"ticket": ticket.id, "file": exe_file},
            format="multipart",
        )
        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert "file" in res.data


# ==============================================================================
# 6. US07 – PHÂN CÔNG TICKET
# ==============================================================================
class TestUS07TicketAssignment:
    def test_kbt1_assign_ticket_success(
        self, api_client, manager_user, agent_user, customer_user, category, priority
    ):
        """Kịch bản 1: Gán thành công -> chuyển sang Đang xử lý."""
        ticket = TicketFactory(
            customer=customer_user,
            category=category,
            priority=priority,
            status=Ticket.Status.NEW,
        )
        api_client.force_authenticate(user=manager_user)

        res = api_client.patch(
            f"/api/v1/tickets/{ticket.id}/assign", {"agent_id": agent_user.id}
        )
        assert res.status_code == status.HTTP_200_OK
        ticket.refresh_from_db()
        assert ticket.assigned_to == agent_user
        assert ticket.status == Ticket.Status.IN_PROGRESS

    def test_kbt2_cannot_assign_closed_ticket(
        self, api_client, manager_user, agent_user, customer_user, category, priority
    ):
        """Kịch bản 2: Không gán được ticket đã đóng -> 409 Conflict."""
        ticket = TicketFactory(
            customer=customer_user,
            category=category,
            priority=priority,
            status=Ticket.Status.CLOSED,
        )
        api_client.force_authenticate(user=manager_user)

        res = api_client.patch(
            f"/api/v1/tickets/{ticket.id}/assign", {"agent_id": agent_user.id}
        )
        assert res.status_code == status.HTTP_409_CONFLICT
        assert res.data["code"] == "ticket_closed"

    def test_kbt3_assign_to_non_existent_agent(
        self, api_client, manager_user, customer_user, category, priority
    ):
        """Kịch bản 3: Gán cho nhân viên không tồn tại -> 404."""
        ticket = TicketFactory(
            customer=customer_user, category=category, priority=priority
        )
        api_client.force_authenticate(user=manager_user)

        res = api_client.patch(
            f"/api/v1/tickets/{ticket.id}/assign", {"agent_id": 99999}
        )
        assert res.status_code == status.HTTP_404_NOT_FOUND

    def test_kbt4_cannot_assign_to_locked_agent(
        self, api_client, manager_user, agent_user, customer_user, category, priority
    ):
        """Kịch bản 4: Gán cho tài khoản bị khóa -> Báo lỗi."""
        agent_user.is_active = False
        agent_user.save()

        ticket = TicketFactory(
            customer=customer_user, category=category, priority=priority
        )
        api_client.force_authenticate(user=manager_user)

        res = api_client.patch(
            f"/api/v1/tickets/{ticket.id}/assign", {"agent_id": agent_user.id}
        )
        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_kbt5_customer_cannot_assign_ticket(
        self, api_client, customer_user, agent_user, category, priority
    ):
        """Kịch bản 5: Khách hàng không có quyền phân công -> 403."""
        ticket = TicketFactory(
            customer=customer_user, category=category, priority=priority
        )
        api_client.force_authenticate(user=customer_user)

        res = api_client.patch(
            f"/api/v1/tickets/{ticket.id}/assign", {"agent_id": agent_user.id}
        )
        assert res.status_code == status.HTTP_403_FORBIDDEN


# ==============================================================================
# 7. US08 – CẬP NHẬT TRẠNG THÁI TICKET
# ==============================================================================
class TestUS08TicketStatusUpdate:
    def test_kbt1_update_status_to_in_progress(
        self, api_client, agent_user, customer_user, category, priority
    ):
        """Kịch bản 1: Chuyển sang Đang xử lý thành công."""
        ticket = TicketFactory(
            customer=customer_user,
            category=category,
            priority=priority,
            status=Ticket.Status.NEW,
        )
        api_client.force_authenticate(user=agent_user)

        res = api_client.patch(
            f"/api/v1/tickets/{ticket.id}/status", {"status": Ticket.Status.IN_PROGRESS}
        )
        assert res.status_code == status.HTTP_200_OK
        ticket.refresh_from_db()
        assert ticket.status == Ticket.Status.IN_PROGRESS

    def test_kbt2_update_status_to_resolved(
        self, api_client, agent_user, customer_user, category, priority
    ):
        """Kịch bản 2: Đánh dấu đã giải quyết -> ghi nhận thời điểm resolved_at."""
        ticket = TicketFactory(
            customer=customer_user,
            category=category,
            priority=priority,
            status=Ticket.Status.IN_PROGRESS,
        )
        api_client.force_authenticate(user=agent_user)

        res = api_client.patch(
            f"/api/v1/tickets/{ticket.id}/status", {"status": Ticket.Status.RESOLVED}
        )
        assert res.status_code == status.HTTP_200_OK
        ticket.refresh_from_db()
        assert ticket.status == Ticket.Status.RESOLVED
        assert ticket.resolved_at is not None

    def test_kbt3_cannot_update_closed_ticket_status(
        self, api_client, agent_user, customer_user, category, priority
    ):
        """Kịch bản 3: Ticket đã đóng không thể đổi trạng thái -> 400 Bad Request."""
        ticket = TicketFactory(
            customer=customer_user,
            category=category,
            priority=priority,
            status=Ticket.Status.CLOSED,
        )
        api_client.force_authenticate(user=agent_user)

        res = api_client.patch(
            f"/api/v1/tickets/{ticket.id}/status", {"status": Ticket.Status.IN_PROGRESS}
        )
        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_kbt4_customer_cannot_update_status(
        self, api_client, customer_user, category, priority
    ):
        """Kịch bản 4: Người không có thẩm quyền (Customer) không được đổi status -> 403."""
        ticket = TicketFactory(
            customer=customer_user, category=category, priority=priority
        )
        api_client.force_authenticate(user=customer_user)

        res = api_client.patch(
            f"/api/v1/tickets/{ticket.id}/status", {"status": Ticket.Status.CLOSED}
        )
        assert res.status_code == status.HTTP_403_FORBIDDEN


# ==============================================================================
# 8. US09 – XEM LỊCH SỬ THAY ĐỔI TICKET
# ==============================================================================
class TestUS09TicketHistory:
    def test_kbt1_view_ticket_history_success(
        self, api_client, customer_user, category, priority
    ):
        """Kịch bản 1: Xem lịch sử thành công."""
        ticket = TicketFactory(
            customer=customer_user, category=category, priority=priority
        )
        api_client.force_authenticate(user=customer_user)

        res = api_client.get(f"/api/v1/tickets/{ticket.id}/history")
        assert res.status_code == status.HTTP_200_OK

    def test_kbt3_unauthorized_user_cannot_view_history(
        self, api_client, customer_user, other_customer, category, priority
    ):
        """Kịch bản 3: Người không có quyền không được xem lịch sử ticket người khác -> 404."""
        other_ticket = TicketFactory(
            customer=other_customer, category=category, priority=priority
        )
        api_client.force_authenticate(user=customer_user)

        res = api_client.get(f"/api/v1/tickets/{other_ticket.id}/history")
        assert res.status_code == status.HTTP_404_NOT_FOUND


# ==============================================================================
# 9. US10 – THÔNG BÁO VÀ ĐÁNH DẤU ĐÃ ĐỌC
# ==============================================================================
class TestUS10Notifications:
    def test_view_and_mark_notification_read(self, api_client, customer_user):
        """Kịch bản xem danh sách và đánh dấu thông báo đã đọc."""
        noti = Notification.objects.create(
            user=customer_user, title="Cập nhật", content="Nội dung thông báo"
        )
        api_client.force_authenticate(user=customer_user)

        # Xem danh sách
        res = api_client.get("/api/v1/notifications")
        assert res.status_code == status.HTTP_200_OK

        # Đánh dấu đã đọc
        patch_res = api_client.patch(f"/api/v1/notifications/{noti.id}/read", {})
        assert patch_res.status_code == status.HTTP_200_OK
        noti.refresh_from_db()
        assert noti.is_read is True


# ==============================================================================
# 10. US11, US12, US13 – DASHBOARD, SLA & BÁO CÁO EXCEL
# ==============================================================================
class TestUS11US12US13DashboardAndReports:
    def test_us11_manager_dashboard_stats(
        self, api_client, manager_user, customer_user, category, priority
    ):
        """US11 Kịch bản 1: Quản lý mở dashboard thống kê."""
        TicketFactory.create_batch(
            2,
            customer=customer_user,
            category=category,
            priority=priority,
            status=Ticket.Status.NEW,
        )
        api_client.force_authenticate(user=manager_user)

        res = api_client.get("/api/v1/dashboard/stats")
        assert res.status_code == status.HTTP_200_OK
        assert "summary" in res.data
        assert res.data["summary"]["total_tickets"] >= 2

    def test_us12_sla_warnings_list(self, api_client, manager_user):
        """US12: Quản lý theo dõi danh sách SLA."""
        api_client.force_authenticate(user=manager_user)
        res = api_client.get("/api/v1/dashboard/sla-warnings")
        assert res.status_code == status.HTTP_200_OK

    def test_us13_kbt1_manager_export_excel(
        self, api_client, manager_user, customer_user, category, priority
    ):
        """US13 Kịch bản 1: Xuất báo cáo Excel thành công."""
        TicketFactory(customer=customer_user, category=category, priority=priority)
        api_client.force_authenticate(user=manager_user)

        res = api_client.get("/api/v1/reports/tickets/export")
        assert res.status_code == status.HTTP_200_OK
        assert (
            res["Content-Type"]
            == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    def test_us13_kbt5_agent_cannot_export_excel(self, api_client, agent_user):
        """US13 Kịch bản 5: Nhân viên hỗ trợ không có quyền tải báo cáo -> 403."""
        api_client.force_authenticate(user=agent_user)
        res = api_client.get("/api/v1/reports/tickets/export")
        assert res.status_code == status.HTTP_403_FORBIDDEN


# ==============================================================================
# 11. US14 & US15 – TÌM KIẾM, PHÂN TRANG & REST API JWT
# ==============================================================================
class TestUS14AndUS15SearchPaginationAndAPI:
    def test_us14_search_and_filter_status(
        self, api_client, manager_user, customer_user, category, priority
    ):
        """US14 Kịch bản 1 & 2: Tìm kiếm từ khóa và lọc trạng thái."""
        t1 = TicketFactory(
            title="Máy in Canon lỗi kẹt giấy",
            customer=customer_user,
            category=category,
            priority=priority,
            status=Ticket.Status.NEW,
        )
        TicketFactory(
            title="Mạng wifi tầng 2 chập chờn",
            customer=customer_user,
            category=category,
            priority=priority,
            status=Ticket.Status.IN_PROGRESS,
        )

        api_client.force_authenticate(user=manager_user)
        res = api_client.get("/api/v1/tickets?search=Canon&status=new")
        assert res.status_code == status.HTTP_200_OK
        results = res.data["results"] if "results" in res.data else res.data
        assert len(results) == 1
        assert results[0]["id"] == t1.id

    def test_us15_kbt2_request_without_jwt_fails(self, api_client):
        """US15 Kịch bản 2: Gọi API không có JWT -> 401 Unauthorized."""
        res = api_client.get("/api/v1/tickets")
        assert res.status_code == status.HTTP_401_UNAUTHORIZED
