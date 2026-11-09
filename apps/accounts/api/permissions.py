from rest_framework.permissions import BasePermission

from apps.accounts.models import User


class IsManager(BasePermission):
    """Chỉ cho phép Manager truy cập."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == User.Role.MANAGER
        )


class IsAgentOrManager(BasePermission):
    """Cho phép Support Agent hoặc Manager truy cập."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in (User.Role.AGENT, User.Role.MANAGER)
        )
