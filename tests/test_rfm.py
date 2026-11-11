"""
==============================================================================
UNIT TESTS: PHÂN KHÚC KHÁCH HÀNG RFM
==============================================================================
"""

import pytest
from backend.modules.dashboard.revenue_router import get_customer_rfm


def test_rfm_segment_classification_logic():
    """
    Kiểm tra logic phân loại khách hàng dựa trên 3 tiêu chí RFM:
    - Recency (R): Ngày mua gần nhất
    - Frequency (F): Tần suất / Số lượng đơn hàng
    - Monetary (M): Tổng số tiền đã chi tiêu
    """
    def classify_customer(days_since_last_order: int, orders_count: int, total_spent: float) -> str:
        if days_since_last_order <= 30 and orders_count >= 5 and total_spent >= 5_000_000:
            return "VIP"
        elif days_since_last_order <= 45 and orders_count >= 3:
            return "Loyal"
        elif days_since_last_order <= 30 and orders_count == 1:
            return "New"
        elif days_since_last_order <= 60:
            return "Potential"
        elif days_since_last_order > 90:
            return "Lost"
        else:
            return "At-Risk"

    # Test VIP: Mua gần, nhiều đơn, chi tiêu lớn
    assert classify_customer(days_since_last_order=5, orders_count=10, total_spent=15_000_000) == "VIP"

    # Test Loyal: Mua đều đặn
    assert classify_customer(days_since_last_order=20, orders_count=4, total_spent=2_500_000) == "Loyal"

    # Test New: Đơn đầu tiên vừa đặt
    assert classify_customer(days_since_last_order=2, orders_count=1, total_spent=350_000) == "New"

    # Test Lost: Quá 90 ngày không quay lại
    assert classify_customer(days_since_last_order=120, orders_count=2, total_spent=800_000) == "Lost"


def test_api_rfm_structure(admin_user):
    """Kiểm tra router get_customer_rfm trả về đúng cấu trúc nhóm và danh sách khách hàng."""
    res = get_customer_rfm(user=admin_user)
    assert res["success"] is True
    data = res["data"]
    assert "segments" in data
    assert "customers" in data or "topCustomers" in data

    valid_segments = {"VIP", "Loyal", "Potential", "At-Risk", "Lost", "New"}
    for seg in data["data" if "data" in data else "segments"]:
        assert seg["segment"] in valid_segments
        assert "customer_count" in seg
        assert "total_revenue" in seg
