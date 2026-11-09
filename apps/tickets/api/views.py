import io
from datetime import timedelta

import openpyxl
from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.tickets.models import (
    Category,
    Comment,
    Priority,
    Ticket,
    TicketHistory,
)
from apps.tickets.services import TicketClosedError, assign_ticket

from .permissions import (
    CanAssignTicket,
    CanUpdateTicketStatus,
    IsManager,
    IsStaffOrOwnerReadOnly,
)
from .serializers import (
    AttachmentSerializer,
    CategorySerializer,
    CommentSerializer,
    DashboardStatsSerializer,
    PrioritySerializer,
    TicketAssignSerializer,
    TicketHistorySerializer,
    TicketSerializer,
    TicketStatusUpdateSerializer,
)


class CategoryListView(generics.ListAPIView):
    """Metadata: Lấy danh sách các danh mục hỗ trợ."""

    queryset = Category.objects.all().order_by("name")
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None


class PriorityListView(generics.ListAPIView):
    """Metadata: Lấy danh sách các mức độ ưu tiên."""

    queryset = Priority.objects.all().order_by("level_weight")
    serializer_class = PrioritySerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None


class TicketViewSet(viewsets.ModelViewSet):
    """
    US03, US04, US06, US07, US08, US14:
    Quản lý Ticket (Tạo mới, xem danh sách, chi tiết, sửa, gán, đổi trạng thái).
    """

    serializer_class = TicketSerializer
    permission_classes = [permissions.IsAuthenticated, IsStaffOrOwnerReadOnly]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["status", "priority", "category"]
    search_fields = ["title", "description"]
    ordering_fields = ["created_at", "updated_at", "priority__level_weight", "due_date"]
    ordering = ["-created_at"]

    queryset = Ticket.objects.all()

    def get_queryset(self):
        if (
            getattr(self, "swagger_fake_view", False)
            or not self.request.user.is_authenticated
        ):
            return Ticket.objects.none()
        user = self.request.user
        qs = Ticket.objects.select_related(
            "category", "priority", "assigned_to", "customer"
        )
        if user.role == User.Role.CUSTOMER:
            qs = qs.filter(customer=user)
        elif user.role == User.Role.AGENT:
            # Agent thấy ticket được gán cho mình hoặc chưa ai nhận
            qs = qs.filter(Q(assigned_to=user) | Q(assigned_to__isnull=True))
        # Manager thấy toàn bộ ticket
        return qs

    def perform_create(self, serializer):
        ticket = serializer.save(customer=self.request.user)
        TicketHistory.objects.create(
            ticket=ticket,
            user=self.request.user,
            action="Tạo ticket mới",
            new_value=f"Tiêu đề: {ticket.title}",
        )

    def perform_update(self, serializer):
        updated_ticket = serializer.save()
        TicketHistory.objects.create(
            ticket=updated_ticket,
            user=self.request.user,
            action="Cập nhật thông tin ticket",
        )

    @action(
        detail=True,
        methods=["patch"],
        permission_classes=[CanAssignTicket],
        serializer_class=TicketAssignSerializer,
    )
    def assign(self, request, pk=None):
        """PATCH /api/v1/tickets/{id}/assign : Phân công hoặc chuyển ticket cho agent."""
        ticket = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        agent_id = serializer.validated_data["agent_id"]

        agent = get_object_or_404(
            User, pk=agent_id, role__in=[User.Role.AGENT, User.Role.MANAGER]
        )
        try:
            ticket = assign_ticket(ticket.pk, agent)
            TicketHistory.objects.create(
                ticket=ticket,
                user=request.user,
                action="Phân công ticket",
                new_value=f"Gán cho: {agent.username}",
            )
        except TicketClosedError as exc:
            return Response(
                {"detail": str(exc), "code": "ticket_closed"},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(TicketSerializer(ticket).data, status=status.HTTP_200_OK)

    @action(
        detail=True,
        methods=["patch"],
        permission_classes=[CanUpdateTicketStatus],
        serializer_class=TicketStatusUpdateSerializer,
    )
    def status(self, request, pk=None):
        """PATCH /api/v1/tickets/{id}/status : Cập nhật trạng thái ticket."""
        ticket = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_status = serializer.validated_data["status"]

        old_status = ticket.status
        ticket.status = new_status
        ticket.save()

        TicketHistory.objects.create(
            ticket=ticket,
            user=request.user,
            action="Đổi trạng thái",
            old_value=old_status,
            new_value=new_status,
        )
        return Response(TicketSerializer(ticket).data, status=status.HTTP_200_OK)


class TicketCommentListCreateView(generics.ListCreateAPIView):
    """US05: Danh sách và tạo bình luận trong ticket."""

    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Comment.objects.all()

    def get_ticket(self):
        ticket_id = self.kwargs.get("ticket_id")
        user = self.request.user
        qs = Ticket.objects.all()
        if user.role == User.Role.CUSTOMER:
            qs = qs.filter(customer=user)
        return get_object_or_404(qs, pk=ticket_id)

    def get_queryset(self):
        if (
            getattr(self, "swagger_fake_view", False)
            or not self.request.user.is_authenticated
        ):
            return Comment.objects.none()
        ticket = self.get_ticket()
        comments = ticket.comments.select_related("user").prefetch_related(
            "attachments"
        )
        if self.request.user.role == User.Role.CUSTOMER:
            comments = comments.filter(is_internal=False)
        return comments

    def perform_create(self, serializer):
        ticket = self.get_ticket()
        is_internal = serializer.validated_data.get("is_internal", False)
        # Chỉ agent/manager mới được tạo bình luận nội bộ
        if self.request.user.role == User.Role.CUSTOMER:
            is_internal = False

        serializer.save(ticket=ticket, user=self.request.user, is_internal=is_internal)
        TicketHistory.objects.create(
            ticket=ticket,
            user=self.request.user,
            action="Thêm bình luận" + (" (Nội bộ)" if is_internal else ""),
        )


class AttachmentUploadView(generics.CreateAPIView):
    """US05: Upload tệp đính kèm cho ticket hoặc comment."""

    serializer_class = AttachmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def perform_create(self, serializer):
        serializer.save(uploaded_by=self.request.user)


class TicketHistoryListView(generics.ListAPIView):
    """US09: Xem lịch sử thay đổi của một ticket."""

    serializer_class = TicketHistorySerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = TicketHistory.objects.all()

    def get_queryset(self):
        if (
            getattr(self, "swagger_fake_view", False)
            or not self.request.user.is_authenticated
        ):
            return TicketHistory.objects.none()
        ticket_id = self.kwargs.get("ticket_id")
        user = self.request.user
        qs = Ticket.objects.all()
        if user.role == User.Role.CUSTOMER:
            qs = qs.filter(customer=user)
        ticket = get_object_or_404(qs, pk=ticket_id)
        return ticket.histories.select_related("user").order_by("-created_at")


# US11, US12, US13: Dashboard, SLA, Export
class DashboardStatsView(generics.GenericAPIView):
    """US11: Lấy số liệu thống kê ticket theo trạng thái, nhân viên, thời gian (MANAGER)."""

    permission_classes = [IsManager]
    serializer_class = DashboardStatsSerializer

    def get(self, request):
        status_counts_raw = Ticket.objects.values("status").annotate(total=Count("id"))
        status_dict = {item["status"]: item["total"] for item in status_counts_raw}

        status_breakdown = [
            {
                "status": choice_val,
                "label": choice_label,
                "count": status_dict.get(choice_val, 0),
            }
            for choice_val, choice_label in Ticket.Status.choices
        ]

        summary = Ticket.objects.aggregate(
            total_tickets=Count("id"),
            open_tickets=Count("id", filter=~Q(status=Ticket.Status.CLOSED)),
            resolved_tickets=Count(
                "id",
                filter=Q(status__in=[Ticket.Status.RESOLVED, Ticket.Status.CLOSED]),
            ),
        )
        total = summary["total_tickets"] or 0
        resolved = summary["resolved_tickets"] or 0
        resolution_rate = round((resolved / total * 100), 1) if total > 0 else 0

        # Thống kê agent
        agents_data = []
        agents = User.objects.filter(role=User.Role.AGENT).annotate(
            total_assigned=Count("assigned_tickets"),
            open_count=Count(
                "assigned_tickets",
                filter=~Q(assigned_tickets__status=Ticket.Status.CLOSED),
            ),
        )
        for ag in agents:
            agents_data.append(
                {
                    "id": ag.id,
                    "username": ag.username,
                    "total_assigned": ag.total_assigned,
                    "open_count": ag.open_count,
                }
            )

        return Response(
            {
                "summary": {
                    "total_tickets": total,
                    "open_tickets": summary["open_tickets"] or 0,
                    "resolved_tickets": resolved,
                    "resolution_rate": f"{resolution_rate}%",
                },
                "status_breakdown": status_breakdown,
                "agent_performance": agents_data,
            }
        )


class SLAWarningsView(generics.ListAPIView):
    """US12: Theo dõi danh sách ticket có nguy cơ hoặc đã quá hạn SLA (MANAGER)."""

    serializer_class = TicketSerializer
    permission_classes = [IsManager]
    queryset = Ticket.objects.all()

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Ticket.objects.none()
        now = timezone.now()
        warning_window = now + timedelta(hours=24)
        return (
            Ticket.objects.select_related(
                "category", "priority", "assigned_to", "customer"
            )
            .filter(
                ~Q(status=Ticket.Status.CLOSED),
                due_date__isnull=False,
                due_date__lte=warning_window,
            )
            .order_by("due_date")
        )


class TicketExportExcelView(APIView):
    """US13: Xuất báo cáo thống kê ticket ra file Excel (.xlsx) (MANAGER)."""

    permission_classes = [IsManager]

    @extend_schema(
        responses={
            (
                200,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ): bytes
        }
    )
    def get(self, request):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Tickets Report"

        headers = [
            "ID",
            "Tiêu đề",
            "Trạng thái",
            "Độ ưu tiên",
            "Danh mục",
            "Khách hàng",
            "Người xử lý",
            "Ngày tạo",
            "Hạn SLA",
        ]
        ws.append(headers)

        tickets = (
            Ticket.objects.select_related(
                "category", "priority", "assigned_to", "customer"
            )
            .all()
            .order_by("-created_at")
        )
        for t in tickets:
            ws.append(
                [
                    t.id,
                    t.title,
                    t.get_status_display(),
                    t.priority.name if t.priority else "",
                    t.category.name if t.category else "",
                    t.customer.username if t.customer else "",
                    t.assigned_to.username if t.assigned_to else "Chưa phân công",
                    t.created_at.strftime("%Y-%m-%d %H:%M:%S") if t.created_at else "",
                    t.due_date.strftime("%Y-%m-%d %H:%M:%S") if t.due_date else "",
                ]
            )

        output = io.BytesIO()
        wb.save(output)
        output.seek(0)

        response = HttpResponse(
            output.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = 'attachment; filename="tickets_report.xlsx"'
        return response
