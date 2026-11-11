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
from decimal import Decimal


def calc_mom(current: float, previous: float) -> float:
    """Tính tỷ lệ tăng trưởng % so với kỳ trước (MoM Growth)."""
    if previous is None or previous == 0:
        return 0.0 if (current is None or current == 0) else 100.0
    return round(((current - previous) / previous) * 100, 1)


class FinancialService:

    @staticmethod
    def initialize_user_expenses_schema() -> None:
        conn = get_db_connection()
        cursor = conn.cursor()
        if DB_TYPE == "mssql":
            cursor.execute("""
                IF OBJECT_ID('financial_user_expenses', 'U') IS NULL
                CREATE TABLE financial_user_expenses (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    user_id INT NOT NULL FOREIGN KEY REFERENCES users(id) ON DELETE CASCADE,
                    month_year NVARCHAR(7) NOT NULL,
                    channel NVARCHAR(100) NOT NULL DEFAULT 'All',
                    rent_expense DECIMAL(18,2) NOT NULL DEFAULT 0,
                    salary_expense DECIMAL(18,2) NOT NULL DEFAULT 0,
                    marketing_expense DECIMAL(18,2) NOT NULL DEFAULT 0,
                    utilities_expense DECIMAL(18,2) NOT NULL DEFAULT 0,
                    other_expense DECIMAL(18,2) NOT NULL DEFAULT 0,
                    note NVARCHAR(500) NOT NULL DEFAULT '',
                    CONSTRAINT UQ_financial_user_expenses UNIQUE(user_id, month_year, channel)
                )
            """)
        else:
            cursor.execute("""CREATE TABLE IF NOT EXISTS financial_user_expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
                month_year TEXT NOT NULL, channel TEXT NOT NULL DEFAULT 'All',
                rent_expense REAL NOT NULL DEFAULT 0, salary_expense REAL NOT NULL DEFAULT 0,
                marketing_expense REAL NOT NULL DEFAULT 0, utilities_expense REAL NOT NULL DEFAULT 0,
                other_expense REAL NOT NULL DEFAULT 0, note TEXT NOT NULL DEFAULT '',
                UNIQUE(user_id, month_year, channel))""")
        conn.commit()
        conn.close()

    @staticmethod
    def get_pnl_users() -> List[Dict[str, Any]]:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id, full_name, email FROM users ORDER BY full_name, id")
            return cursor.fetchall()
        finally:
            conn.close()

    @staticmethod
    def initialize_order_profit_schema() -> None:
        """Create the additive order-cost tables if they are missing."""
        conn = get_db_connection()
        cursor = conn.cursor()
        if DB_TYPE == "mssql":
            cursor.execute("""
                IF OBJECT_ID('order_costs', 'U') IS NULL
                CREATE TABLE order_costs (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    order_id INT NOT NULL FOREIGN KEY REFERENCES orders(id) ON DELETE CASCADE,
                    cost_type NVARCHAR(40) NOT NULL,
                    amount DECIMAL(18,2) NOT NULL CHECK(amount > 0),
                    source NVARCHAR(40) NOT NULL DEFAULT 'manual',
                    note NVARCHAR(500) NOT NULL DEFAULT '',
                    created_by INT NULL FOREIGN KEY REFERENCES users(id) ON DELETE SET NULL,
                    created_at DATETIME2 NOT NULL DEFAULT GETDATE(),
                    updated_at DATETIME2 NOT NULL DEFAULT GETDATE()
                );
                IF OBJECT_ID('order_fee_status', 'U') IS NULL
                CREATE TABLE order_fee_status (
                    order_id INT PRIMARY KEY FOREIGN KEY REFERENCES orders(id) ON DELETE CASCADE,
                    status NVARCHAR(20) NOT NULL DEFAULT 'unverified' CHECK(status IN ('unverified', 'entered', 'reconciled')),
                    updated_by INT NULL FOREIGN KEY REFERENCES users(id) ON DELETE SET NULL,
                    updated_at DATETIME2 NOT NULL DEFAULT GETDATE()
                );
                IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_order_costs_order_id')
                    CREATE INDEX IX_order_costs_order_id ON order_costs(order_id);
                IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_order_items_order_id')
                    CREATE INDEX IX_order_items_order_id ON order_items(order_id);
            """)
        else:
            cursor.execute("""CREATE TABLE IF NOT EXISTS order_costs (
                id INTEGER PRIMARY KEY AUTOINCREMENT, order_id INTEGER NOT NULL,
                cost_type TEXT NOT NULL, amount REAL NOT NULL CHECK(amount > 0),
                source TEXT NOT NULL DEFAULT 'manual', note TEXT NOT NULL DEFAULT '',
                created_by INTEGER, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )""")
            cursor.execute("""CREATE TABLE IF NOT EXISTS order_fee_status (
                order_id INTEGER PRIMARY KEY, status TEXT NOT NULL DEFAULT 'unverified'
                    CHECK(status IN ('unverified', 'entered', 'reconciled')),
                updated_by INTEGER, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )""")
            cursor.execute("CREATE INDEX IF NOT EXISTS IX_order_costs_order_id ON order_costs(order_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS IX_order_items_order_id ON order_items(order_id)")
        conn.commit()
        conn.close()

    @staticmethod
    def get_order_profit(limit: int = 50, offset: int = 0, channel: str = "All", status: str = "All",
                         fee_status: str = "All", profit_filter: str = "All", from_date: Optional[str] = None,
                         to_date: Optional[str] = None) -> List[Dict[str, Any]]:
        FinancialService.initialize_order_profit_schema()
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = """
            SELECT o.id, o.order_code, o.channel, o.status, o.order_date,
                   o.net_amount AS revenue, COALESCE(i.cogs, 0) AS cogs,
                   COALESCE(c.costs, 0) AS direct_costs, COALESCE(c.cost_count, 0) AS cost_count,
                   COALESCE(s.status, 'unverified') AS fee_status
            FROM orders o
            LEFT JOIN (SELECT order_id, SUM(quantity * cost_price) AS cogs FROM order_items GROUP BY order_id) i ON i.order_id = o.id
            LEFT JOIN (SELECT order_id, SUM(amount) AS costs, COUNT(*) AS cost_count FROM order_costs GROUP BY order_id) c ON c.order_id = o.id
            LEFT JOIN order_fee_status s ON s.order_id = o.id
            WHERE 1=1
        """
        params = []
        if channel != "All":
            sql += " AND o.channel = ?"
            params.append(channel)
        if status != "All":
            sql += " AND o.status = ?"
            params.append(status)
        if fee_status != "All":
            sql += " AND COALESCE(s.status, 'unverified') = ?"
            params.append(fee_status)
        if profit_filter in ("negative", "nonnegative"):
            comparator = "< 0" if profit_filter == "negative" else ">= 0"
            sql += f" AND o.status = 'completed' AND (o.net_amount - COALESCE(i.cogs, 0) - COALESCE(c.costs, 0)) {comparator}"
        if from_date:
            sql += " AND o.order_date >= ?"
            params.append(from_date)
        if to_date:
            sql += " AND o.order_date < ?"
            params.append(to_date)
        sql += " ORDER BY o.order_date DESC, o.id DESC"
        sql += " OFFSET ? ROWS FETCH NEXT ? ROWS ONLY" if DB_TYPE == "mssql" else " LIMIT ? OFFSET ?"
        params.extend([offset, limit] if DB_TYPE == "mssql" else [limit, offset])
        cursor.execute(sql, tuple(params))
        rows = cursor.fetchall()
        conn.close()
        return [FinancialService._order_profit_values(row) for row in rows]

    @staticmethod
    def get_order_profit_detail(order_id: int) -> Optional[Dict[str, Any]]:
        FinancialService.initialize_order_profit_schema()
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT o.id, o.order_code, o.channel, o.status, o.order_date,
                   o.net_amount AS revenue, COALESCE(i.cogs, 0) AS cogs,
                   COALESCE(c.costs, 0) AS direct_costs,
                   COALESCE(s.status, 'unverified') AS fee_status
            FROM orders o
            LEFT JOIN (SELECT order_id, SUM(quantity * cost_price) AS cogs FROM order_items GROUP BY order_id) i ON i.order_id = o.id
            LEFT JOIN (SELECT order_id, SUM(amount) AS costs FROM order_costs GROUP BY order_id) c ON c.order_id = o.id
            LEFT JOIN order_fee_status s ON s.order_id = o.id
            WHERE o.id = ?
        """, (order_id,))
        order = cursor.fetchone()
        if not order:
            conn.close()
            return None
        cursor.execute("SELECT p.name AS product_name, p.sku, oi.quantity, oi.unit_price, oi.cost_price, oi.total_price FROM order_items oi LEFT JOIN products p ON p.id = oi.product_id WHERE oi.order_id = ?", (order_id,))
        items = cursor.fetchall()
        cursor.execute("SELECT id, cost_type, amount, source, note, created_at, updated_at FROM order_costs WHERE order_id = ? ORDER BY id", (order_id,))
        costs = cursor.fetchall()
        conn.close()
        result = FinancialService._order_profit_values(order)
        result.update({"items": items, "costs": costs})
        return result

    @staticmethod
    def _order_profit_values(row: Dict[str, Any]) -> Dict[str, Any]:
        item = dict(row)
        for key in ("revenue", "cogs", "direct_costs"):
            item[key] = float(Decimal(str(item.get(key) or 0)).quantize(Decimal("0.01")))
        if item["status"] == "completed":
            item["contribution_profit"] = float((Decimal(str(item["revenue"])) - Decimal(str(item["cogs"])) - Decimal(str(item["direct_costs"]))).quantize(Decimal("0.01")))
            item["margin_pct"] = round(item["contribution_profit"] / item["revenue"] * 100, 1) if item["revenue"] > 0 else 0.0
        else:
            item["contribution_profit"] = None
            item["margin_pct"] = None
        return item

    @staticmethod
    def add_order_cost(order_id: int, cost_type: str, amount: float, note: str, user_id: int) -> int:
        FinancialService.initialize_order_profit_schema()
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM orders WHERE id = ?", (order_id,))
        if not cursor.fetchone():
            conn.close()
            raise ValueError("Không tìm thấy đơn hàng.")
        cursor.execute("INSERT INTO order_costs (order_id, cost_type, amount, note, created_by) VALUES (?, ?, ?, ?, ?)", (order_id, cost_type, amount, note, user_id))
        cost_id = cursor.lastrowid
        if DB_TYPE == "mssql":
            cost_id = cursor.lastrowid
            cursor.execute("IF EXISTS (SELECT 1 FROM order_fee_status WHERE order_id = ?) UPDATE order_fee_status SET status = 'entered', updated_by = ?, updated_at = GETDATE() WHERE order_id = ? ELSE INSERT INTO order_fee_status (order_id, status, updated_by) VALUES (?, 'entered', ?)", (order_id, user_id, order_id, order_id, user_id))
        else:
            cursor.execute("INSERT INTO order_fee_status (order_id, status, updated_by) VALUES (?, 'entered', ?) ON CONFLICT(order_id) DO UPDATE SET status = 'entered', updated_by = excluded.updated_by, updated_at = CURRENT_TIMESTAMP", (order_id, user_id))
        conn.commit()
        conn.close()
        return cost_id

    @staticmethod
    def update_order_cost(cost_id: int, cost_type: str, amount: float, note: str) -> Dict[str, Any]:
        FinancialService.initialize_order_profit_schema()
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT order_id, cost_type, amount, note FROM order_costs WHERE id = ?", (cost_id,))
        old = cursor.fetchone()
        if not old:
            conn.close()
            raise ValueError("Không tìm thấy khoản phí.")
        old = dict(old)
        old["amount"] = float(old.get("amount") or 0)
        updated_at = "GETDATE()" if DB_TYPE == "mssql" else "CURRENT_TIMESTAMP"
        cursor.execute(f"UPDATE order_costs SET cost_type = ?, amount = ?, note = ?, updated_at = {updated_at} WHERE id = ?", (cost_type, amount, note, cost_id))
        conn.commit()
        conn.close()
        return old

    @staticmethod
    def set_order_fee_status(order_id: int, status: str, user_id: int) -> str:
        FinancialService.initialize_order_profit_schema()
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT status FROM order_fee_status WHERE order_id = ?", (order_id,))
        old = cursor.fetchone()
        old_status = old["status"] if old else "unverified"
        cursor.execute("SELECT id FROM orders WHERE id = ?", (order_id,))
        if not cursor.fetchone():
            conn.close()
            raise ValueError("Không tìm thấy đơn hàng.")
        if DB_TYPE == "mssql":
            cursor.execute("IF EXISTS (SELECT 1 FROM order_fee_status WHERE order_id = ?) UPDATE order_fee_status SET status = ?, updated_by = ?, updated_at = GETDATE() WHERE order_id = ? ELSE INSERT INTO order_fee_status (order_id, status, updated_by) VALUES (?, ?, ?)", (order_id, status, user_id, order_id, order_id, status, user_id))
        else:
            cursor.execute("INSERT INTO order_fee_status (order_id, status, updated_by) VALUES (?, ?, ?) ON CONFLICT(order_id) DO UPDATE SET status = excluded.status, updated_by = excluded.updated_by, updated_at = CURRENT_TIMESTAMP", (order_id, status, user_id))
        conn.commit()
        conn.close()
        return old_status

    @staticmethod
    def get_pnl_report(month: int, year: int, channel: str = "All", user_id: Optional[int] = None, role: str = "admin", report_user_id: Optional[int] = None) -> Dict[str, Any]:
        """Tổng hợp và tính toán báo cáo kết quả hoạt động kinh doanh (P&L) theo tháng và năm."""
        month_str = f"{year:04d}-{month:02d}"
        prev_month = 12 if month == 1 else (month - 1)
        prev_year = (year - 1) if month == 1 else year
        prev_month_str = f"{prev_year:04d}-{prev_month:02d}"

        FinancialService.initialize_user_expenses_schema()
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
                scope_user_id = report_user_id if role in ("admin", "manager") else user_id
                if scope_user_id is not None:
                    user_filter = " AND o.user_id = ?"
                    params.append(scope_user_id)

                # Query doanh thu đơn hoàn thành
                if DB_TYPE == "mssql":
                    date_cond = "FORMAT(o.order_date, 'yyyy-MM') = ?"
                else:
                    date_cond = "strftime('%Y-%m', o.order_date) = ?"

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
                scope_user_id = report_user_id if role in ("admin", "manager") else user_id
                expense_table = "financial_user_expenses" if scope_user_id is not None else "financial_expenses"
                user_column = " AND user_id = ?" if expense_table == "financial_user_expenses" else ""
                channel_condition = "channel = ?" if user_column else "channel = 'All'"
                cursor.execute("""
                    SELECT rent_expense, salary_expense, marketing_expense, utilities_expense, other_expense, note
                    FROM """ + expense_table + " WHERE month_year = ? AND " + channel_condition + user_column,
                    (target_month, channel, scope_user_id) if user_column else (target_month,))
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
        scope_user_id: Optional[int] = None
    ) -> bool:
        """Lưu hoặc cập nhật chi phí vận hành (OPEX) cho một tháng cụ thể."""
        if scope_user_id is not None:
            FinancialService.initialize_user_expenses_schema()
            conn = get_db_connection()
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO financial_user_expenses
                    (user_id, month_year, channel, rent_expense, salary_expense, marketing_expense, utilities_expense, other_expense, note)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(user_id, month_year, channel) DO UPDATE SET
                        rent_expense=excluded.rent_expense, salary_expense=excluded.salary_expense,
                        marketing_expense=excluded.marketing_expense, utilities_expense=excluded.utilities_expense,
                        other_expense=excluded.other_expense, note=excluded.note
                """, (scope_user_id, month_year, channel, rent, salary, marketing, utilities, other, note)) if DB_TYPE != "mssql" else cursor.execute("""
                    IF EXISTS (SELECT 1 FROM financial_user_expenses WHERE user_id=? AND month_year=? AND channel=?)
                        UPDATE financial_user_expenses SET rent_expense=?, salary_expense=?, marketing_expense=?, utilities_expense=?, other_expense=?, note=? WHERE user_id=? AND month_year=? AND channel=?
                    ELSE INSERT INTO financial_user_expenses (user_id, month_year, channel, rent_expense, salary_expense, marketing_expense, utilities_expense, other_expense, note) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (scope_user_id, month_year, channel, rent, salary, marketing, utilities, other, note, scope_user_id, month_year, channel, scope_user_id, month_year, channel, rent, salary, marketing, utilities, other, note))
                conn.commit()
                try:
                    from backend.modules.audit.audit_service import AuditService
                    AuditService.record_audit("UPDATE_USER_OPEX", "financial_user_expenses", f"{scope_user_id}:{month_year}:{channel}", user_id,
                        user_email=user_email, user_role=user_role, ip_address=ip_address,
                        new_value={"rent_expense": rent, "salary_expense": salary, "marketing_expense": marketing,
                                   "utilities_expense": utilities, "other_expense": other, "note": note})
                except Exception:
                    pass
                return True
            finally:
                conn.close()

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT rent_expense, salary_expense, marketing_expense, utilities_expense, other_expense FROM financial_expenses WHERE month_year = ? AND channel = ?", (month_year, channel))
            old_expense = cursor.fetchone()
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
            try:
                from backend.modules.audit.audit_service import AuditService
                AuditService.record_audit("UPDATE_OPEX", "financial_expenses", f"{month_year}:{channel}", user_id,
                    user_email=user_email, user_role=user_role, ip_address=ip_address,
                    old_value=dict(old_expense) if old_expense else None,
                    new_value={"rent_expense": rent, "salary_expense": salary, "marketing_expense": marketing, "utilities_expense": utilities, "other_expense": other, "note": note})
            except Exception:
                pass
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
