from rest_framework.permissions import SAFE_METHODS, BasePermission

from apps.accounts.models import User


class IsStaffOrOwnerReadOnly(BasePermission):
    """
    - Manager: Toàn quyền.
    - Agent: Toàn quyền đọc và cập nhật các ticket được gán / trong hệ thống.
    - Customer: Chỉ đọc và cập nhật (nếu là ticket của mình).
    """

    def has_object_permission(self, request, view, obj):
        if request.user.role in (User.Role.AGENT, User.Role.MANAGER):
            return True
        return obj.customer_id == request.user.id and (
            request.method in SAFE_METHODS or request.method in ("PATCH", "PUT")
        )


class CanCreateTicket(BasePermission):
    """Khách hàng hoặc mọi authenticated user được tạo ticket."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)


class CanAssignTicket(BasePermission):
    """Manager và Agent có quyền gán hoặc chuyển ticket."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in (User.Role.AGENT, User.Role.MANAGER)
        )


class CanUpdateTicketStatus(BasePermission):
    """Manager và Agent có quyền cập nhật trạng thái ticket."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in (User.Role.AGENT, User.Role.MANAGER)
        )


class IsManager(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == User.Role.MANAGER
        )
