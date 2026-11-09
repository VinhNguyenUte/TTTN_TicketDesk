from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.accounts.api.views import (
    LogoutView,
    RegisterView,
    UserListView,
    UserRoleUpdateView,
    UserStatusUpdateView,
)
from apps.notifications.api.views import (
    NotificationListView,
    NotificationMarkReadView,
)
from apps.tickets.api.views import (
    AttachmentUploadView,
    CategoryListView,
    DashboardStatsView,
    PriorityListView,
    SLAWarningsView,
    TicketCommentListCreateView,
    TicketExportExcelView,
    TicketHistoryListView,
    TicketViewSet,
)

router = DefaultRouter(trailing_slash=False)
router.register(r"tickets", TicketViewSet, basename="ticket")

urlpatterns = [
    # 1. Authentication (US01)
    path("auth/register", RegisterView.as_view(), name="auth-register"),
    path("auth/login", TokenObtainPairView.as_view(), name="auth-login"),
    path("auth/token/refresh", TokenRefreshView.as_view(), name="token-refresh"),
    path("auth/logout", LogoutView.as_view(), name="auth-logout"),
    # 2. User & Role Management (US02)
    path("users", UserListView.as_view(), name="user-list"),
    path("users/<int:pk>/role", UserRoleUpdateView.as_view(), name="user-role-update"),
    path(
        "users/<int:pk>/status",
        UserStatusUpdateView.as_view(),
        name="user-status-update",
    ),
    # 4. Comments & Attachments (US05)
    path(
        "tickets/<int:ticket_id>/comments",
        TicketCommentListCreateView.as_view(),
        name="ticket-comments",
    ),
    path("attachments", AttachmentUploadView.as_view(), name="attachment-upload"),
    # 5. History & Notifications (US09, US10)
    path(
        "tickets/<int:ticket_id>/history",
        TicketHistoryListView.as_view(),
        name="ticket-history",
    ),
    path("notifications", NotificationListView.as_view(), name="notification-list"),
    path(
        "notifications/<int:pk>/read",
        NotificationMarkReadView.as_view(),
        name="notification-read",
    ),
    # 6. Dashboard, SLA & Report (US11, US12, US13)
    path("dashboard/stats", DashboardStatsView.as_view(), name="dashboard-stats"),
    path(
        "dashboard/sla-warnings",
        SLAWarningsView.as_view(),
        name="dashboard-sla-warnings",
    ),
    path(
        "reports/tickets/export",
        TicketExportExcelView.as_view(),
        name="reports-tickets-export",
    ),
    # 7. Metadata Endpoints
    path("categories", CategoryListView.as_view(), name="category-list"),
    path("priorities", PriorityListView.as_view(), name="priority-list"),
    # 3. Router URLs (Tickets CRUD & actions: /tickets, /tickets/{id}, /tickets/{id}/assign, /tickets/{id}/status)
    path("", include(router.urls)),
]
