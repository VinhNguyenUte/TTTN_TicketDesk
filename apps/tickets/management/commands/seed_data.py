from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.notifications.models import Notification
from apps.tickets.models import Category, Comment, Priority, Ticket, TicketHistory

User = get_user_model()


class Command(BaseCommand):
    help = "Tạo dữ liệu mẫu (seed data) cho hệ thống TicketDesk"

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Bắt đầu khởi tạo dữ liệu mẫu..."))

        # 1. Tạo Người dùng (Users)
        users_data = [
            {
                "username": "admin",
                "email": "admin@ticketdesk.local",
                "role": User.Role.MANAGER,
                "first_name": "Quản trị",
                "last_name": "Hệ thống",
                "is_staff": True,
                "is_superuser": True,
            },
            {
                "username": "agent_an",
                "email": "an.nguyen@ticketdesk.local",
                "role": User.Role.AGENT,
                "first_name": "An",
                "last_name": "Nguyễn Văn",
                "is_staff": True,
                "is_superuser": False,
            },
            {
                "username": "agent_binh",
                "email": "binh.le@ticketdesk.local",
                "role": User.Role.AGENT,
                "first_name": "Bình",
                "last_name": "Lê Thị",
                "is_staff": True,
                "is_superuser": False,
            },
            {
                "username": "customer_dung",
                "email": "dung.tran@example.com",
                "role": User.Role.CUSTOMER,
                "first_name": "Dũng",
                "last_name": "Trần Tuấn",
                "is_staff": False,
                "is_superuser": False,
            },
            {
                "username": "customer_hoa",
                "email": "hoa.pham@example.com",
                "role": User.Role.CUSTOMER,
                "first_name": "Hoa",
                "last_name": "Phạm Mai",
                "is_staff": False,
                "is_superuser": False,
            },
        ]

        created_users = {}
        for u in users_data:
            user, created = User.objects.get_or_create(
                username=u["username"],
                defaults={
                    "email": u["email"],
                    "role": u["role"],
                    "first_name": u["first_name"],
                    "last_name": u["last_name"],
                    "is_staff": u["is_staff"],
                    "is_superuser": u["is_superuser"],
                },
            )
            # Thiết lập mật khẩu mặc định: admin123 cho admin, 123456 cho các user khác
            password = "admin123" if u["username"] == "admin" else "123456"
            user.set_password(password)
            user.role = u["role"]
            user.is_staff = u["is_staff"]
            user.is_superuser = u["is_superuser"]
            user.save()
            created_users[u["username"]] = user

        self.stdout.write(
            self.style.SUCCESS(f"-> Đã tạo/cập nhật {len(created_users)} người dùng.")
        )

        # 2. Tạo Danh mục (Categories)
        categories_data = [
            (
                "Phần cứng",
                "Các sự cố liên quan đến máy tính, chuột, bàn phím, màn hình, máy in",
            ),
            (
                "Phần mềm",
                "Lỗi cài đặt hệ điều hành, Office, phần mềm kế toán, phần mềm nội bộ",
            ),
            ("Mạng & Kết nối", "Mất kết nối mạng LAN, Wi-Fi chập chờn, VPN công ty"),
            (
                "Tài khoản & Phân quyền",
                "Cấp mới tài khoản, reset mật khẩu, mở khóa truy cập hệ thống",
            ),
        ]
        created_cats = {}
        for name, desc in categories_data:
            cat, _ = Category.objects.get_or_create(
                name=name, defaults={"description": desc}
            )
            created_cats[name] = cat

        self.stdout.write(
            self.style.SUCCESS(f"-> Đã tạo {len(created_cats)} danh mục.")
        )

        # 3. Tạo Độ ưu tiên (Priorities)
        priorities_data = [
            ("Thấp", 1, "#64748b"),
            ("Trung bình", 2, "#3b82f6"),
            ("Cao", 3, "#f59e0b"),
            ("Khẩn cấp", 4, "#ef4444"),
        ]
        created_priorities = {}
        for name, weight, color in priorities_data:
            prio, _ = Priority.objects.get_or_create(
                name=name, defaults={"level_weight": weight, "color": color}
            )
            prio.level_weight = weight
            prio.color = color
            prio.save()
            created_priorities[name] = prio

        self.stdout.write(
            self.style.SUCCESS(f"-> Đã tạo {len(created_priorities)} mức ưu tiên.")
        )

        # 4. Tạo Tickets mẫu
        now = timezone.now()
        tickets_data = [
            {
                "title": "Màn hình Dell phòng Kế toán không lên nguồn",
                "description": "Sáng nay khi khởi động máy thì màn hình không có tín hiệu, đèn nguồn nhấp nháy màu cam.",
                "status": Ticket.Status.NEW,
                "customer": created_users["customer_dung"],
                "assigned_to": None,
                "category": created_cats["Phần cứng"],
                "priority": created_priorities["Cao"],
                "due_date": now + timedelta(hours=4),
            },
            {
                "title": "Không truy cập được mạng nội bộ VPN từ xa",
                "description": "Nhân viên làm việc WFH báo lỗi 'Error 800: Unable to establish VPN connection'.",
                "status": Ticket.Status.IN_PROGRESS,
                "customer": created_users["customer_hoa"],
                "assigned_to": created_users["agent_an"],
                "category": created_cats["Mạng & Kết nối"],
                "priority": created_priorities["Khẩn cấp"],
                "due_date": now + timedelta(hours=2),
            },
            {
                "title": "Cần cấp quyền truy cập thư mục Shared Drive Dự án A",
                "description": "Nhân viên mới cần được cấp quyền Read/Write vào Google Drive của dự án A.",
                "status": Ticket.Status.RESOLVED,
                "customer": created_users["customer_dung"],
                "assigned_to": created_users["agent_binh"],
                "category": created_cats["Tài khoản & Phân quyền"],
                "priority": created_priorities["Trung bình"],
                "due_date": now + timedelta(days=1),
                "resolved_at": now - timedelta(hours=1),
            },
            {
                "title": "Lỗi font chữ khi in hóa đơn trên Excel",
                "description": "Khi xuất file PDF từ Excel bảng lương bị lỗi dấu tiếng Việt và vỡ bảng.",
                "status": Ticket.Status.CLOSED,
                "customer": created_users["customer_hoa"],
                "assigned_to": created_users["agent_an"],
                "category": created_cats["Phần mềm"],
                "priority": created_priorities["Thấp"],
                "due_date": now - timedelta(days=1),
                "resolved_at": now - timedelta(days=1, hours=3),
            },
        ]

        created_tickets = []
        for t_data in tickets_data:
            resolved_at = t_data.pop("resolved_at", None)
            ticket, created = Ticket.objects.get_or_create(
                title=t_data["title"],
                defaults=t_data,
            )
            if resolved_at:
                ticket.resolved_at = resolved_at
                ticket.status = t_data["status"]
                ticket.save()
            created_tickets.append(ticket)

        self.stdout.write(
            self.style.SUCCESS(f"-> Đã tạo {len(created_tickets)} tickets mẫu.")
        )

        # 5. Tạo Bình luận (Comments) & Lịch sử (Histories)
        ticket_vpn = created_tickets[1]
        Comment.objects.get_or_create(
            ticket=ticket_vpn,
            user=created_users["customer_hoa"],
            content="Tôi đã thử khởi động lại modem mạng nhà nhưng vẫn không vào được VPN.",
            defaults={"is_internal": False},
        )
        Comment.objects.get_or_create(
            ticket=ticket_vpn,
            user=created_users["agent_an"],
            content="Đang kiểm tra chứng chỉ SSL gateway phía Firewall.",
            defaults={"is_internal": True},
        )
        Comment.objects.get_or_create(
            ticket=ticket_vpn,
            user=created_users["agent_an"],
            content="Chào bạn Hoa, bạn vui lòng ngắt kết nối và đăng nhập lại bằng tài khoản mới được reset nhé.",
            defaults={"is_internal": False},
        )

        TicketHistory.objects.get_or_create(
            ticket=ticket_vpn,
            user=created_users["agent_an"],
            action="Tiếp nhận ticket",
            old_value="Chưa phân công",
            new_value="agent_an",
        )
        TicketHistory.objects.get_or_create(
            ticket=ticket_vpn,
            user=created_users["agent_an"],
            action="Đổi trạng thái",
            old_value="Mới",
            new_value="Đang xử lý",
        )

        # 6. Tạo Thông báo (Notifications)
        Notification.objects.get_or_create(
            user=created_users["customer_hoa"],
            ticket=ticket_vpn,
            title="Ticket #2 đã được cập nhật",
            content="Nhân viên An đã phản hồi ticket của bạn.",
            defaults={"is_sent": True, "is_read": False},
        )
        Notification.objects.get_or_create(
            user=created_users["agent_an"],
            ticket=ticket_vpn,
            title="Ticket mới được gán cho bạn",
            content="Bạn được phân công xử lý ticket: Không truy cập được mạng nội bộ VPN",
            defaults={"is_sent": True, "is_read": True},
        )

        self.stdout.write(
            self.style.SUCCESS(
                "-> Đã tạo các comments, lịch sử ticket và thông báo mẫu."
            )
        )
        self.stdout.write(self.style.SUCCESS("=== KHỞI TẠO DỮ LIỆU THÀNH CÔNG ==="))
