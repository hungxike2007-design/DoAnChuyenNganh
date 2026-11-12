"""
==============================================================================
MODULE NGHIỆP VỤ TÀI CHÍNH & BÁO CÁO KẾT QUẢ KINH DOANH (FINANCIAL P&L SERVICE)
==============================================================================
Chức năng:
- Bóc tách toàn diện P&L: Doanh thu danh nghĩa, Giảm trừ chiết khấu, Doanh thu thuần,
  Giá vốn hàng bán (COGS), Lợi nhuận gộp, Chi phí vận hành (OPEX), EBITDA (Lợi nhuận ròng).
- Phân tích tăng trưởng so với tháng trước (MoM Growth %) và tính toán tỷ trọng trên doanh thu thuần.
- Quản lý cấu hình chi phí vận hành hàng tháng (bảng financial_expenses).
==============================================================================
"""

from typing import Dict, Any, List, Optional
from config.db import get_db_connection, DB_TYPE


def calc_mom(current: float, previous: float) -> float:
    """Tính tỷ lệ tăng trưởng % so với kỳ trước (MoM Growth)."""
    if previous is None or previous == 0:
        return 0.0 if (current is None or current == 0) else 100.0
    return round(((current - previous) / previous) * 100, 1)


class FinancialService:

    @staticmethod
    def get_pnl_report(month: int, year: int, channel: str = "All", user_id: Optional[int] = None, role: str = "admin") -> Dict[str, Any]:
        """Tổng hợp và tính toán báo cáo kết quả hoạt động kinh doanh (P&L) theo tháng và năm."""
        month_str = f"{year:04d}-{month:02d}"
        prev_month = 12 if month == 1 else (month - 1)
        prev_year = (year - 1) if month == 1 else year
        prev_month_str = f"{prev_year:04d}-{prev_month:02d}"

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            # 1. Hàm phụ trợ lấy số liệu đơn hàng theo kỳ
            def fetch_order_metrics(target_month: str):
                channel_filter = ""
                params = [f"{target_month}%"]

                if channel != "All":
                    channel_filter += " AND o.channel = ?"
                    params.append(channel)

                user_filter = ""
                if role in ("sales", "user") and user_id is not None:
                    user_filter = " AND o.user_id = ?"
                    params.append(user_id)

                # Query doanh thu đơn hoàn thành
                if DB_TYPE == "mssql":
                    date_cond = "FORMAT(o.created_at, 'yyyy-MM') = ?"
                else:
                    date_cond = "strftime('%Y-%m', o.created_at) = ?"

                query_orders = f"""
                    SELECT 
                        COUNT(CASE WHEN o.status = 'completed' THEN 1 END) as completed_count,
                        SUM(CASE WHEN o.status = 'completed' THEN o.total_amount ELSE 0 END) as gross_revenue,
                        SUM(CASE WHEN o.status = 'completed' THEN o.discount_amount ELSE 0 END) as discount_deductions,
                        SUM(CASE WHEN o.status = 'completed' THEN o.net_amount ELSE 0 END) as net_revenue,
                        COUNT(CASE WHEN o.status IN ('cancelled', 'refunded') THEN 1 END) as cancelled_count,
                        SUM(CASE WHEN o.status IN ('cancelled', 'refunded') THEN o.total_amount ELSE 0 END) as cancelled_amount
                    FROM orders o
                    WHERE {date_cond} {channel_filter} {user_filter}
                """
                cursor.execute(query_orders, [target_month] + params[1:])
                row_order = cursor.fetchone() or {}

                # Query giá vốn (COGS) từ order_items của các đơn completed
                query_cogs = f"""
                    SELECT SUM(oi.quantity * oi.cost_price) as total_cogs
                    FROM order_items oi
                    JOIN orders o ON oi.order_id = o.id
                    WHERE o.status = 'completed' AND {date_cond} {channel_filter} {user_filter}
                """
                cursor.execute(query_cogs, [target_month] + params[1:])
                row_cogs = cursor.fetchone() or {}

                gross_rev = float(row_order.get("gross_revenue") or 0)
                discounts = float(row_order.get("discount_deductions") or 0)
                net_rev = float(row_order.get("net_revenue") or 0)
                completed_cnt = int(row_order.get("completed_count") or 0)
                canc_cnt = int(row_order.get("cancelled_count") or 0)
                canc_amt = float(row_order.get("cancelled_amount") or 0)
                cogs = float(row_cogs.get("total_cogs") or 0)

                return {
                    "gross_revenue": gross_rev,
                    "discount_deductions": discounts,
                    "net_revenue": net_rev,
                    "completed_count": completed_cnt,
                    "cancelled_count": canc_cnt,
                    "cancelled_amount": canc_amt,
                    "cogs": cogs
                }

            curr_metrics = fetch_order_metrics(month_str)
            prev_metrics = fetch_order_metrics(prev_month_str)

            # 2. Lấy chi phí vận hành (OPEX) từ bảng financial_expenses
            def fetch_opex(target_month: str):
                cursor.execute("""
                    SELECT rent_expense, salary_expense, marketing_expense, utilities_expense, other_expense, note
                    FROM financial_expenses
                    WHERE month_year = ? AND channel = 'All'
                """, (target_month,))
                row = cursor.fetchone() or {}
                rent = float(row.get("rent_expense") or 0)
                sal = float(row.get("salary_expense") or 0)
                mkt = float(row.get("marketing_expense") or 0)
                util = float(row.get("utilities_expense") or 0)
                oth = float(row.get("other_expense") or 0)
                note = row.get("note") or ""
                total = rent + sal + mkt + util + oth
                return {
                    "rent": rent,
                    "salary": sal,
                    "marketing": mkt,
                    "utilities": util,
                    "other": oth,
                    "total": total,
                    "note": note
                }

            curr_opex = fetch_opex(month_str)
            prev_opex = fetch_opex(prev_month_str)

            # 3. Tính toán Lợi nhuận gộp & Lợi nhuận ròng
            curr_gross_profit = curr_metrics["net_revenue"] - curr_metrics["cogs"]
            curr_gross_margin = round((curr_gross_profit / curr_metrics["net_revenue"] * 100), 1) if curr_metrics["net_revenue"] > 0 else 0.0

            curr_ebitda = curr_gross_profit - curr_opex["total"]
            curr_net_margin = round((curr_ebitda / curr_metrics["net_revenue"] * 100), 1) if curr_metrics["net_revenue"] > 0 else 0.0

            prev_gross_profit = prev_metrics["net_revenue"] - prev_metrics["cogs"]
            prev_gross_margin = round((prev_gross_profit / prev_metrics["net_revenue"] * 100), 1) if prev_metrics["net_revenue"] > 0 else 0.0

            prev_ebitda = prev_gross_profit - prev_opex["total"]
            prev_net_margin = round((prev_ebitda / prev_metrics["net_revenue"] * 100), 1) if prev_metrics["net_revenue"] > 0 else 0.0

            net_rev = curr_metrics["net_revenue"]
            calc_share = lambda val: round((val / net_rev * 100), 1) if net_rev > 0 else 0.0

            # 4. Cấu trúc dữ liệu báo cáo chi tiết theo chuẩn kế toán
            statement_items = [
                {
                    "code": "01",
                    "label": "I. Doanh thu bán hàng & cung cấp dịch vụ (Gross Revenue)",
                    "current": curr_metrics["gross_revenue"],
                    "previous": prev_metrics["gross_revenue"],
                    "share_pct": calc_share(curr_metrics["gross_revenue"]),
                    "mom_growth": calc_mom(curr_metrics["gross_revenue"], prev_metrics["gross_revenue"]),
                    "is_header": True
                },
                {
                    "code": "02",
                    "label": "II. Các khoản giảm trừ doanh thu (Chiết khấu & Voucher)",
                    "current": curr_metrics["discount_deductions"],
                    "previous": prev_metrics["discount_deductions"],
                    "share_pct": calc_share(curr_metrics["discount_deductions"]),
                    "mom_growth": calc_mom(curr_metrics["discount_deductions"], prev_metrics["discount_deductions"]),
                    "is_header": False
                },
                {
                    "code": "03",
                    "label": "III. Doanh thu thuần về bán hàng & cung cấp dịch vụ (Net Revenue)",
                    "current": curr_metrics["net_revenue"],
                    "previous": prev_metrics["net_revenue"],
                    "share_pct": 100.0,
                    "mom_growth": calc_mom(curr_metrics["net_revenue"], prev_metrics["net_revenue"]),
                    "is_highlight": True
                },
                {
                    "code": "04",
                    "label": "IV. Giá vốn hàng bán (Cost of Goods Sold - COGS)",
                    "current": curr_metrics["cogs"],
                    "previous": prev_metrics["cogs"],
                    "share_pct": calc_share(curr_metrics["cogs"]),
                    "mom_growth": calc_mom(curr_metrics["cogs"], prev_metrics["cogs"]),
                    "is_header": False
                },
                {
                    "code": "05",
                    "label": "V. Lợi nhuận gộp về bán hàng & cung cấp dịch vụ (Gross Profit)",
                    "current": curr_gross_profit,
                    "previous": prev_gross_profit,
                    "share_pct": curr_gross_margin,
                    "mom_growth": calc_mom(curr_gross_profit, prev_gross_profit),
                    "is_highlight": True
                },
                {
                    "code": "06",
                    "label": "VI. Chi phí vận hành & bán hàng (Operating Expenses - OPEX)",
                    "current": curr_opex["total"],
                    "previous": prev_opex["total"],
                    "share_pct": calc_share(curr_opex["total"]),
                    "mom_growth": calc_mom(curr_opex["total"], prev_opex["total"]),
                    "is_header": True
                },
                {
                    "code": "06.1",
                    "label": "  1. Chi phí thuê mặt bằng kho bãi",
                    "current": curr_opex["rent"],
                    "previous": prev_opex["rent"],
                    "share_pct": calc_share(curr_opex["rent"]),
                    "mom_growth": calc_mom(curr_opex["rent"], prev_opex["rent"]),
                    "is_sub": True
                },
                {
                    "code": "06.2",
                    "label": "  2. Chi phí lương nhân viên & hoa hồng",
                    "current": curr_opex["salary"],
                    "previous": prev_opex["salary"],
                    "share_pct": calc_share(curr_opex["salary"]),
                    "mom_growth": calc_mom(curr_opex["salary"], prev_opex["salary"]),
                    "is_sub": True
                },
                {
                    "code": "06.3",
                    "label": "  3. Chi phí tiếp thị & quảng cáo (Marketing/Ads)",
                    "current": curr_opex["marketing"],
                    "previous": prev_opex["marketing"],
                    "share_pct": calc_share(curr_opex["marketing"]),
                    "mom_growth": calc_mom(curr_opex["marketing"], prev_opex["marketing"]),
                    "is_sub": True
                },
                {
                    "code": "06.4",
                    "label": "  4. Chi phí điện nước, internet, bao bì",
                    "current": curr_opex["utilities"],
                    "previous": prev_opex["utilities"],
                    "share_pct": calc_share(curr_opex["utilities"]),
                    "mom_growth": calc_mom(curr_opex["utilities"], prev_opex["utilities"]),
                    "is_sub": True
                },
                {
                    "code": "06.5",
                    "label": "  5. Chi phí vận hành & quản lý khác",
                    "current": curr_opex["other"],
                    "previous": prev_opex["other"],
                    "share_pct": calc_share(curr_opex["other"]),
                    "mom_growth": calc_mom(curr_opex["other"], prev_opex["other"]),
                    "is_sub": True
                },
                {
                    "code": "07",
                    "label": "VII. Lợi nhuận thuần từ hoạt động kinh doanh (EBITDA / Net Profit)",
                    "current": curr_ebitda,
                    "previous": prev_ebitda,
                    "share_pct": curr_net_margin,
                    "mom_growth": calc_mom(curr_ebitda, prev_ebitda),
                    "is_highlight": True,
                    "is_final": True
                }
            ]

            # 5. Dữ liệu trực quan hóa biểu đồ
            cost_distribution = [
                {"label": "Giá Vốn Hàng Bán (COGS)", "value": curr_metrics["cogs"], "color": "#f97316"},
                {"label": "Lương Nhân Sự", "value": curr_opex["salary"], "color": "#3b82f6"},
                {"label": "Thuê Mặt Bằng", "value": curr_opex["rent"], "color": "#8b5cf6"},
                {"label": "Tiếp Thị & Ads", "value": curr_opex["marketing"], "color": "#ec4899"},
                {"label": "Điện Nước & Khác", "value": curr_opex["utilities"] + curr_opex["other"], "color": "#64748b"}
            ]

            waterfall_data = [
                {"label": "Doanh Thu Thuần", "value": curr_metrics["net_revenue"], "type": "total"},
                {"label": "Giá Vốn (COGS)", "value": -curr_metrics["cogs"], "type": "subtraction"},
                {"label": "Lợi Nhuận Gộp", "value": curr_gross_profit, "type": "subtotal"},
                {"label": "Chi Phí OPEX", "value": -curr_opex["total"], "type": "subtraction"},
                {"label": "Lợi Nhuận Ròng", "value": curr_ebitda, "type": "result"}
            ]

            return {
                "period": {
                    "month": month,
                    "year": year,
                    "month_year": month_str,
                    "prev_month_year": prev_month_str,
                    "channel": channel
                },
                "summary": {
                    "net_revenue": curr_metrics["net_revenue"],
                    "net_revenue_mom": calc_mom(curr_metrics["net_revenue"], prev_metrics["net_revenue"]),
                    "gross_profit": curr_gross_profit,
                    "gross_margin": curr_gross_margin,
                    "gross_profit_mom": calc_mom(curr_gross_profit, prev_gross_profit),
                    "total_opex": curr_opex["total"],
                    "total_opex_mom": calc_mom(curr_opex["total"], prev_opex["total"]),
                    "ebitda": curr_ebitda,
                    "net_margin": curr_net_margin,
                    "ebitda_mom": calc_mom(curr_ebitda, prev_ebitda),
                    "completed_orders": curr_metrics["completed_count"],
                    "cancelled_orders": curr_metrics["cancelled_count"],
                    "cancelled_amount": curr_metrics["cancelled_amount"]
                },
                "statement": statement_items,
                "cost_distribution": cost_distribution,
                "waterfall": waterfall_data,
                "opex_raw": curr_opex
            }

        finally:
            conn.close()

    @staticmethod
    def save_expenses(
        month_year: str,
        channel: str = "All",
        rent: float = 0.0,
        salary: float = 0.0,
        marketing: float = 0.0,
        utilities: float = 0.0,
        other: float = 0.0,
        note: str = "",
        user_id: Optional[int] = None,
        user_email: str = "",
        user_role: str = "",
        ip_address: str = "",
        user_agent: str = ""
    ) -> bool:
        """Lưu hoặc cập nhật chi phí vận hành (OPEX) cho một tháng cụ thể."""
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT rent_expense, salary_expense, marketing_expense, utilities_expense, other_expense FROM financial_expenses WHERE month_year = ? AND channel = ?", (month_year, channel))
            old_expenses = cursor.fetchone()
            if DB_TYPE == "mssql":
                upsert_sql = """
                    IF EXISTS (SELECT 1 FROM financial_expenses WHERE month_year = ? AND channel = ?)
                    BEGIN
                        UPDATE financial_expenses
                        SET rent_expense = ?, salary_expense = ?, marketing_expense = ?,
                            utilities_expense = ?, other_expense = ?, note = ?, updated_by = ?, updated_at = GETDATE()
                        WHERE month_year = ? AND channel = ?
                    END
                    ELSE
                    BEGIN
                        INSERT INTO financial_expenses (month_year, channel, rent_expense, salary_expense, marketing_expense, utilities_expense, other_expense, note, updated_by)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    END
                """
                cursor.execute(upsert_sql, (
                    month_year, channel,
                    rent, salary, marketing, utilities, other, note, user_id,
                    month_year, channel,
                    month_year, channel, rent, salary, marketing, utilities, other, note, user_id
                ))
            else:
                upsert_sql = """
                    INSERT INTO financial_expenses (month_year, channel, rent_expense, salary_expense, marketing_expense, utilities_expense, other_expense, note, updated_by, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(month_year, channel) DO UPDATE SET
                        rent_expense = excluded.rent_expense,
                        salary_expense = excluded.salary_expense,
                        marketing_expense = excluded.marketing_expense,
                        utilities_expense = excluded.utilities_expense,
                        other_expense = excluded.other_expense,
                        note = excluded.note,
                        updated_by = excluded.updated_by,
                        updated_at = CURRENT_TIMESTAMP
                """
                cursor.execute(upsert_sql, (month_year, channel, rent, salary, marketing, utilities, other, note, user_id))

            conn.commit()
            from backend.modules.audit.audit_service import AuditService
            AuditService.record_audit("UPDATE_OPEX", "financial_expenses", f"{month_year}:{channel}", user_id,
                user_email, user_role, dict(old_expenses) if old_expenses else None,
                {"rent": rent, "salary": salary, "marketing": marketing, "utilities": utilities, "other": other, "note": note},
                ip_address, user_agent)
            return True
        finally:
            conn.close()

    @staticmethod
    def get_expenses_history() -> List[Dict[str, Any]]:
        """Lấy danh sách các kỳ đã cấu hình chi phí vận hành."""
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT id, month_year, channel, rent_expense, salary_expense, marketing_expense,
                       utilities_expense, other_expense, note, updated_at
                FROM financial_expenses
                ORDER BY month_year DESC
            """)
            return cursor.fetchall()
        finally:
            conn.close()
