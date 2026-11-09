from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, status
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User

from .permissions import IsManager
from .serializers import (
    LogoutSerializer,
    RegisterSerializer,
    UserRoleUpdateSerializer,
    UserSerializer,
    UserStatusUpdateSerializer,
)


class RegisterView(generics.CreateAPIView):
    """US01: Đăng ký tài khoản mới (mặc định role Customer)."""

    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]


class LogoutView(generics.GenericAPIView):
    """US01: Đăng xuất hệ thống, blacklist refresh token."""

    serializer_class = LogoutSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            refresh_token = serializer.validated_data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response(
                {"detail": "Đăng xuất thành công."}, status=status.HTTP_200_OK
            )
        except Exception:
            return Response(
                {"detail": "Refresh token không hợp lệ hoặc đã hết hạn."},
                status=status.HTTP_400_BAD_REQUEST,
            )


class UserListView(generics.ListAPIView):
    """US02: Lấy danh sách toàn bộ người dùng (có phân trang/lọc) dành cho Manager."""

    queryset = User.objects.all().order_by("-id")
    serializer_class = UserSerializer
    permission_classes = [IsManager]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["role", "is_active"]
    search_fields = ["username", "email", "first_name", "last_name"]
    ordering_fields = ["id", "date_joined", "username"]


class UserRoleUpdateView(generics.UpdateAPIView):
    """US02: Cập nhật phân quyền (role) cho người dùng (PUT)."""

    queryset = User.objects.all()
    serializer_class = UserRoleUpdateSerializer
    permission_classes = [IsManager]
    http_method_names = ["put"]


class UserStatusUpdateView(generics.UpdateAPIView):
    """US02: Khóa hoặc mở khóa tài khoản (is_active) (PATCH)."""

    queryset = User.objects.all()
    serializer_class = UserStatusUpdateSerializer
    permission_classes = [IsManager]
    http_method_names = ["patch"]
