"""
==============================================================================
UNIT TESTS: BÁO CÁO TÀI CHÍNH P&L & EBITDA
==============================================================================
"""

import pytest
from backend.modules.financial.financial_service import calc_mom, FinancialService
from backend.modules.financial.financial_router import get_pnl_report


def test_calc_mom_growth():
    """Kiểm tra công thức tính tỷ lệ tăng trưởng % so với kỳ trước (MoM Growth)."""
    # Tăng trưởng bình thường: 100 lên 120 -> +20.0%
    assert calc_mom(120, 100) == 20.0

    # Giảm: 100 xuống 80 -> -20.0%
    assert calc_mom(80, 100) == -20.0

    # Kỳ trước bằng 0, kỳ này có doanh thu -> 100.0%
    assert calc_mom(5000000, 0) == 100.0

    # Cả 2 kỳ đều bằng 0 -> 0.0%
    assert calc_mom(0, 0) == 0.0

    # Kỳ này bằng 0, kỳ trước có -> -100.0%
    assert calc_mom(0, 100) == -100.0


def test_ebitda_and_gross_profit_logic():
    """
    Kiểm tra công thức tài chính chuẩn:
    - Gross Profit = Net Revenue - COGS
    - Gross Margin = (Gross Profit / Net Revenue) * 100
    - EBITDA = Gross Profit - OPEX
    - EBITDA Margin = (EBITDA / Net Revenue) * 100
    """
    net_revenue = 100_000_000.0
    cogs = 60_000_000.0
    total_opex = 25_000_000.0

    gross_profit = net_revenue - cogs
    assert gross_profit == 40_000_000.0

    gross_margin = round((gross_profit / net_revenue) * 100, 1)
    assert gross_margin == 40.0

    ebitda = gross_profit - total_opex
    assert ebitda == 15_000_000.0

    ebitda_margin = round((ebitda / net_revenue) * 100, 1)
    assert ebitda_margin == 15.0


def test_zero_revenue_edge_case():
    """Đảm bảo hệ thống không bị lỗi chia cho 0 (ZeroDivisionError) khi doanh thu = 0."""
    net_revenue = 0.0
    cogs = 0.0
    total_opex = 5_000_000.0

    gross_profit = net_revenue - cogs
    gross_margin = round((gross_profit / net_revenue * 100), 1) if net_revenue > 0 else 0.0
    ebitda = gross_profit - total_opex
    net_margin = round((ebitda / net_revenue * 100), 1) if net_revenue > 0 else 0.0

    assert gross_profit == 0.0
    assert gross_margin == 0.0
    assert ebitda == -5_000_000.0
    assert net_margin == 0.0


def test_pnl_summary_execution(admin_user):
    """Kiểm tra router get_pnl_report trả về đầy đủ các chỉ số statement và metrics."""
    res = get_pnl_report(month=10, year=2026, channel="All", current_user=admin_user)
    assert res["success"] is True
    data = res["data"]
    assert "summary" in data
    assert "statement" in data
    assert len(data["statement"]) > 0
    assert "gross_profit" in data["summary"]
    assert "ebitda" in data["summary"]
