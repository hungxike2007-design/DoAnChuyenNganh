"""
==============================================================================
DỊCH VỤ PHÂN TÍCH DOANH THU ĐA CHIỀU (PIVOT TABLE SERVICE - PYTHON)
==============================================================================
Thực hiện xoay ma trận đa chiều (Dynamic OLAP / Pivot Table):
- Ghép nối tự do 2 chiều (Row Dimension & Column Dimension).
- Hỗ trợ các chỉ số đo: Doanh thu, Lợi nhuận gộp, Số đơn hàng, Sản phẩm bán ra, AOV.
- Tự động tính tổng hàng, tổng cột và tổng toàn bộ ma trận (Marginal & Grand Totals).
- Hỗ trợ phân quyền Multi-tenant cách ly dữ liệu theo user_id.
- Tích hợp Gemini AI giải mã các điểm nóng/điểm trũng trong ma trận.
==============================================================================
"""

import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from backend.config.db import get_db_connection, sql_date_group
from backend.config.ai_config import generate_ai_response, is_ai_ready, GEMINI_MODEL


def get_dimensions_map() -> Dict[str, Dict[str, str]]:
    """Trả về cấu hình các chiều phân tích tương thích cả MSSQL & SQLite."""
    return {
        "channel": {
            "field": "COALESCE(o.channel, 'Khác')",
            "label": "Kênh Bán Hàng"
        },
        "category": {
            "field": "COALESCE(c.name, 'Chưa phân loại')",
            "label": "Danh Mục Sản Phẩm"
        },
        "city": {
            "field": "COALESCE(cust.city, 'Khác')",
            "label": "Tỉnh / Thành Phố"
        },
        "month_period": {
            "field": sql_date_group("o.order_date", "month"),
            "label": "Thời Gian (Tháng)"
        }
    }

# 3 Chỉ số đo lường tài chính quan trọng nhất
METRICS_MAP = {
    "total_revenue": {
        "expr": "COALESCE(SUM(oi.total_price), 0)",
        "label": "Tổng Doanh Thu",
        "unit": "₫"
    },
    "gross_profit": {
        "expr": "COALESCE(SUM((oi.unit_price - oi.cost_price) * oi.quantity), 0)",
        "label": "Lợi Nhuận Gộp",
        "unit": "₫"
    },
    "order_count": {
        "expr": "COUNT(DISTINCT o.id)",
        "label": "Số Đơn Hàng",
        "unit": "đơn"
    }
}


class PivotService:

    @staticmethod
    def get_supported_metadata() -> Dict[str, Any]:
        """Trả về danh sách các chiều và chỉ số hỗ trợ cho giao diện frontend."""
        dimensions = get_dimensions_map()
        return {
            "dimensions": [{"key": k, "label": v["label"]} for k, v in dimensions.items()],
            "metrics": [{"key": k, "label": v["label"], "unit": v["unit"]} for k, v in METRICS_MAP.items()]
        }

    @staticmethod
    def generate_pivot_matrix(
        row_dim: str = "channel",
        col_dim: str = "category",
        metric: str = "total_revenue",
        days: int = 90,
        status: str = "completed",
        user_id: Optional[int] = None,
        role: str = "admin"
    ) -> Dict[str, Any]:
        """Tạo ma trận Pivot 2 chiều từ CSDL SQL Server hoặc SQLite."""
        dimensions = get_dimensions_map()
        if row_dim not in dimensions:
            row_dim = "channel"
        if col_dim not in dimensions:
            col_dim = "category"
        if metric not in METRICS_MAP:
            metric = "total_revenue"

        row_cfg = dimensions[row_dim]
        col_cfg = dimensions[col_dim]
        metric_cfg = METRICS_MAP[metric]

        conn = get_db_connection()
        cursor = conn.cursor()

        date_limit = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")

        where_clauses = ["o.order_date >= ?"]
        params = [date_limit]

        if status and status.lower() != "all":
            where_clauses.append("o.status = ?")
            params.append(status.lower())

        # Cách ly dữ liệu cho role không phải admin/manager
        if role.lower() in ("sales", "user") and user_id is not None:
            where_clauses.append("o.user_id = ?")
            params.append(user_id)

        where_sql = " AND ".join(where_clauses)

        sql = f"""
            SELECT 
                {row_cfg['field']} AS row_val,
                {col_cfg['field']} AS col_val,
                {metric_cfg['expr']} AS metric_val
            FROM orders o
            JOIN order_items oi ON o.id = oi.order_id
            JOIN products p ON oi.product_id = p.id
            LEFT JOIN categories c ON p.category_id = c.id
            LEFT JOIN customers cust ON o.customer_id = cust.id
            LEFT JOIN users u ON o.user_id = u.id
            WHERE {where_sql}
            GROUP BY {row_cfg['field']}, {col_cfg['field']}
        """

        try:
            cursor.execute(sql, tuple(params))
            rows_data = cursor.fetchall()
        finally:
            conn.close()

        # Thu thập các giá trị duy nhất cho Hàng và Cột
        row_keys_set = set()
        col_keys_set = set()
        matrix_lookup: Dict[str, Dict[str, float]] = {}

        for r in rows_data:
            r_val = str(r["row_val"] or "Khác").strip()
            c_val = str(r["col_val"] or "Khác").strip()
            m_val = float(r["metric_val"] or 0.0)

            row_keys_set.add(r_val)
            col_keys_set.add(c_val)

            if r_val not in matrix_lookup:
                matrix_lookup[r_val] = {}
            matrix_lookup[r_val][c_val] = m_val

        # Sắp xếp danh sách hàng và cột chuẩn
        row_headers = sorted(list(row_keys_set))
        col_headers = sorted(list(col_keys_set))

        # Khởi tạo ma trận và tính toán tổng biên
        matrix: List[List[float]] = []
        row_totals: List[float] = []
        col_totals: List[float] = [0.0] * len(col_headers)
        grand_total: float = 0.0
        min_val: float = float("inf")
        max_val: float = 0.0

        for r_idx, r_key in enumerate(row_headers):
            row_list: List[float] = []
            r_sum: float = 0.0
            for c_idx, c_key in enumerate(col_headers):
                cell_val = matrix_lookup.get(r_key, {}).get(c_key, 0.0)
                cell_val = round(cell_val, 2)
                row_list.append(cell_val)
                r_sum += cell_val
                col_totals[c_idx] += cell_val

                if cell_val > 0:
                    if cell_val < min_val:
                        min_val = cell_val
                    if cell_val > max_val:
                        max_val = cell_val

            matrix.append(row_list)
            r_sum = round(r_sum, 2)
            row_totals.append(r_sum)
            grand_total += r_sum

        col_totals = [round(c, 2) for c in col_totals]
        grand_total = round(grand_total, 2)
        if min_val == float("inf"):
            min_val = 0.0

        return {
            "row_dimension": row_dim,
            "row_dimension_label": row_cfg["label"],
            "col_dimension": col_dim,
            "col_dimension_label": col_cfg["label"],
            "metric": metric,
            "metric_label": metric_cfg["label"],
            "metric_unit": metric_cfg["unit"],
            "days": days,
            "row_headers": row_headers,
            "col_headers": col_headers,
            "matrix": matrix,
            "row_totals": row_totals,
            "col_totals": col_totals,
            "grand_total": grand_total,
            "min_val": min_val,
            "max_val": max_val
        }

    @staticmethod
    def get_ai_insight(pivot_data: Dict[str, Any]) -> Dict[str, Any]:
        """Sử dụng Gemini AI để phân tích ma trận Pivot và đưa ra nhận xét chiến lược."""
        row_label = pivot_data.get("row_dimension_label", "Hàng")
        col_label = pivot_data.get("col_dimension_label", "Cột")
        metric_label = pivot_data.get("metric_label", "Chỉ số")
        metric_unit = pivot_data.get("metric_unit", "")
        row_headers = pivot_data.get("row_headers", [])
        col_headers = pivot_data.get("col_headers", [])
        matrix = pivot_data.get("matrix", [])
        grand_total = pivot_data.get("grand_total", 0)

        # Trích xuất top 3 ô có giá trị lớn nhất và 3 ô có giá trị thấp nhất
        cells = []
        for r_idx, r_name in enumerate(row_headers):
            for c_idx, c_name in enumerate(col_headers):
                val = matrix[r_idx][c_idx]
                if val > 0:
                    cells.append({"row": r_name, "col": c_name, "value": val})

        cells.sort(key=lambda x: x["value"], reverse=True)
        top_cells = cells[:3]
        bottom_cells = [c for c in cells if c["value"] > 0][-3:]

        system_instruction = (
            "Bạn là Chuyên gia Phân tích Dữ liệu Kinh doanh Cấp cao (Chief Revenue Data Analyst). "
            "Nhiệm vụ: Phân tích ma trận giao thoa 2 chiều, chỉ ra các điểm sáng doanh thu, ngách tiềm năng và đưa ra 3 khuyến nghị hành động ngắn gọn bằng Tiếng Việt với Markdown."
        )

        prompt = f"""
Dưới đây là ma trận phân tích dữ liệu kinh doanh 2 chiều:
- Trục dòng: {row_label}
- Trục cột: {col_label}
- Chỉ số đo lường: {metric_label} ({metric_unit})
- Tổng toàn bộ ma trận: {grand_total:,.2f} {metric_unit}

Top điểm giao thoa đạt giá trị cao nhất:
{json.dumps(top_cells, ensure_ascii=False, indent=2)}

Điểm giao thoa có giá trị thấp nhất:
{json.dumps(bottom_cells, ensure_ascii=False, indent=2)}

Hãy đưa ra nhận định chiến lược súc tích theo cấu trúc:
1. 🌟 **Điểm Vàng Doanh Thu (Key Drivers):** Cặp giao thoa nào đang gánh vác doanh số chính? Chiếm bao nhiêu %?
2. 💡 **Ngách Tiềm Năng & Bất Thường:** Sự kết hợp nào thú vị hoặc kênh nào đang bán rất tốt một danh mục cụ thể?
3. ⚠️ **Vùng Trũng Cần Khắc Phục:** Cặp giao thoa nào đang yếu kém và nguyên nhân có thể là gì?
4. 🚀 **Hành Động Khuyến Nghị Cụ Thể:** 2 hành động cụ thể cho đội ngũ kinh doanh trong tuần tới.
"""

        ai_reply = generate_ai_response(prompt, system_instruction=system_instruction)

        return {
            "insight_text": ai_reply,
            "isLiveAI": is_ai_ready,
            "model": GEMINI_MODEL
        }

