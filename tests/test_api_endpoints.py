"""
==============================================================================
INTEGRATION TESTS: CÁC ROUTER DOANH THU & BẢO MẬT GIÁ VỐN
==============================================================================
"""

import pytest
from backend.modules.dashboard.revenue_router import (
    get_kpis,
    get_channels,
    get_top_products
)
from backend.modules.products.product_router import get_products


def test_api_revenue_kpis(admin_user):
    """Kiểm tra router KPIs trả về đầy đủ các chỉ số tài chính trọng yếu."""
    res = get_kpis(days=180, view_user_id=None, user=admin_user)
    assert res["success"] is True

    kpis = res["data"]
    assert "totalRevenue" in kpis
    assert "grossProfit" in kpis
    assert "profitMargin" in kpis
    assert "totalOrders" in kpis
    assert "completedOrders" in kpis
    assert "aov" in kpis
    assert "cancelRate" in kpis

    # Doanh thu và lợi nhuận gộp phải là số không âm
    assert kpis["totalRevenue"] >= 0
    assert kpis["totalOrders"] >= 0


def test_api_products_cost_price_masking(sales_token, admin_token):
    """
    Kiểm tra tính năng bảo mật giá vốn:
    - Tài khoản Sales khi gọi get_products bị ẩn hoàn toàn trường cost_price.
    - Tài khoản Admin/Manager khi gọi get_products nhìn thấy đầy đủ cost_price.
    """
    # 1. Kiểm tra đối với Sales: cost_price phải bị ẩn (None hoặc 0)
    res_sales = get_products(authorization=f"Bearer {sales_token}")
    assert res_sales["success"] is True
    sales_products = res_sales.get("data", [])
    assert len(sales_products) > 0
    for p in sales_products:
        assert p.get("cost_price") in (None, 0.0, 0)

    # 2. Kiểm tra đối với Admin: cost_price hiển thị giá trị thật (> 0)
    res_admin = get_products(authorization=f"Bearer {admin_token}")
    assert res_admin["success"] is True
    admin_products = res_admin.get("data", [])
    assert len(admin_products) > 0
    has_cost = any(p.get("cost_price", 0) > 0 for p in admin_products)
    assert has_cost is True, "Admin phải xem được giá vốn cost_price > 0 của sản phẩm!"


def test_api_revenue_channels(admin_user):
    """Kiểm tra router phân bổ tỷ trọng theo 4 kênh bán lẻ (Shopee, TikTok, Cửa hàng, Web)."""
    res = get_channels(days=180, view_user_id=None, user=admin_user)
    assert res["success"] is True
    channels = res["data"]
    assert isinstance(channels, list)
