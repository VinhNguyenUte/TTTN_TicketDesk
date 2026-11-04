import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.models import User
from apps.tickets.models import Category, Priority, Ticket


class Command(BaseCommand):
    help = "Tạo số lượng lớn dữ liệu mẫu (seed tickets) phục vụ kiểm thử hiệu năng và tối ưu truy vấn"

    def add_arguments(self, parser):
        parser.add_argument(
            "--count",
            type=int,
            default=10_000,
            help="Số lượng ticket cần tạo (mặc định: 10,000)",
        )

    def handle(self, *args, count, **options):
        self.stdout.write(f"Bắt đầu khởi tạo {count:,} ticket mẫu...")

        # 1. Đảm bảo có Categories
        cats = [
            Category.objects.get_or_create(name=n)[0]
            for n in [
                "Phần cứng",
                "Phần mềm",
                "Mạng & Kết nối",
                "Tài khoản & Phân quyền",
            ]
        ]

        # 2. Đảm bảo có Priorities
        priorities = [
            Priority.objects.get_or_create(
                name=n, defaults={"level_weight": w, "color": c}
            )[0]
            for n, w, c in [
                ("Thấp", 1, "#64748b"),
                ("Trung bình", 2, "#3b82f6"),
                ("Cao", 3, "#f59e0b"),
                ("Khẩn cấp", 4, "#ef4444"),
            ]
        ]

        # 3. Lấy users
        customers = list(User.objects.filter(role=User.Role.CUSTOMER))
        if not customers:
            # Tạo ít nhất 1 customer nếu chưa có
            customers = [
                User.objects.create_user(
                    username="customer_seed",
                    password="password123",
                    role=User.Role.CUSTOMER,
                )
            ]

        agents = list(User.objects.filter(role=User.Role.AGENT))
        all_assignees = agents + [None]

        sample_titles = [
            "Màn hình bị nháy",
            "Không vào được hệ thống ERP",
            "Mất kết nối WiFi tầng 3",
            "Cần cài đặt phần mềm Photoshop",
            "Lỗi máy in văn phòng",
            "Quên mật khẩu tài khoản email",
            "Mạng chập chờn khi họp video",
            "Không mở được file Excel dung lượng lớn",
            "Yêu cầu cấp chuột và bàn phím mới",
            "Lỗi đồng bộ dữ liệu cloud",
        ]

        now = timezone.now()
        statuses = [s[0] for s in Ticket.Status.choices]

        tickets_to_create = []
        batch_size = 1000

        for i in range(1, count + 1):
            status = random.choice(statuses)
            created_offset = random.randint(0, 30)  # tạo trong vòng 30 ngày qua
            created_at = now - timedelta(
                days=created_offset, hours=random.randint(0, 23)
            )
            due_date = created_at + timedelta(days=random.randint(1, 5))
            resolved_at = (
                created_at + timedelta(hours=random.randint(2, 48))
                if status in [Ticket.Status.RESOLVED, Ticket.Status.CLOSED]
                else None
            )

            title = f"{random.choice(sample_titles)} #{i}"
            ticket = Ticket(
                title=title,
                description=f"Chi tiết mô tả cho {title}. Cần hỗ trợ xử lý kỹ thuật.",
                status=status,
                customer=random.choice(customers),
                assigned_to=random.choice(all_assignees),
                category=random.choice(cats),
                priority=random.choice(priorities),
                due_date=due_date,
                resolved_at=resolved_at,
            )
            tickets_to_create.append(ticket)

            if len(tickets_to_create) >= batch_size:
                Ticket.objects.bulk_create(tickets_to_create, batch_size=batch_size)
                self.stdout.write(f"  -> Đã tạo {i:,}/{count:,} tickets...")
                tickets_to_create.clear()

        if tickets_to_create:
            Ticket.objects.bulk_create(tickets_to_create, batch_size=batch_size)

        self.stdout.write(
            self.style.SUCCESS(f"Hoàn thành! Đã tạo thành công {count:,} ticket.")
        )
