import time

import pytest
from django.core.cache import cache

from apps.accounts.models import User
from apps.tickets.models import Ticket
from apps.tickets.services import (
    STATS_CACHE_KEY,
    compute_dashboard_stats,
    get_cached_dashboard_stats,
    invalidate_dashboard_stats,
)
from apps.tickets.tests.factories import TicketFactory, UserFactory

pytestmark = pytest.mark.django_db


class TestDashboardCacheAndPerformance:
    def test_cache_stores_and_returns_data(self):
        """Test get_cached_dashboard_stats lưu kết quả vào cache."""
        cache.clear()
        UserFactory(role=User.Role.MANAGER)
        TicketFactory.create_batch(3, status=Ticket.Status.NEW)

        assert cache.get(STATS_CACHE_KEY) is None

        # Lần 1: Chưa có cache -> tính toán và lưu cache
        data1 = get_cached_dashboard_stats()
        assert data1["summary"]["total_tickets"] >= 3
        assert cache.get(STATS_CACHE_KEY) is not None

        # Lần 2: Lấy trực tiếp từ cache
        data2 = get_cached_dashboard_stats()
        assert data2 == data1

    def test_cache_invalidation_on_ticket_change(self):
        """Test invalidate_dashboard_stats xóa cache khi có ticket mới hoặc đổi trạng thái."""
        cache.clear()
        get_cached_dashboard_stats()
        assert cache.get(STATS_CACHE_KEY) is not None

        invalidate_dashboard_stats()
        assert cache.get(STATS_CACHE_KEY) is None

    def test_cache_improves_response_time(self):
        """Đo thời gian phản hồi: Lần gọi cache nhanh hơn tính toán trực tiếp."""
        TicketFactory.create_batch(10)
        cache.clear()

        # Đo lần tính toán trực tiếp
        t0 = time.perf_counter()
        compute_dashboard_stats()
        compute_duration = time.perf_counter() - t0

        # Lưu cache
        get_cached_dashboard_stats()

        # Đo lần đọc từ cache
        t1 = time.perf_counter()
        get_cached_dashboard_stats()
        cache_duration = time.perf_counter() - t1

        # Lấy từ cache nhanh hơn hoặc bằng tính toán DB
        assert cache_duration <= compute_duration or cache_duration < 0.05
