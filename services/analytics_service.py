"""
==============================================================================
DỊCH VỤ PHÂN TÍCH DOANH THU SQL SERVER (ANALYTICS SERVICE - MSSQL)
==============================================================================
Thực hiện các truy vấn T-SQL tối ưu trên Microsoft SQL Server:
- Tổng hợp KPI tài chính (Doanh thu thuần, Lợi nhuận gộp, AOV, Tỷ lệ hủy)
- Chuỗi thời gian doanh thu (CONVERT format 120)
- Tỷ trọng kênh bán lẻ
- Top sản phẩm bán chạy (OFFSET FETCH NEXT)
- Cảnh báo tồn kho & Phân khúc khách hàng RFM
==============================================================================
"""

from datetime import datetime, timedelta
from config.db import get_db_connection


class AnalyticsService:
    @staticmethod
    def get_kpis(days: int = 180) -> dict:
        date_limit = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
        conn = get_db_connection()
        cursor = conn.cursor()

        # 1. Thống kê đơn hàng và doanh thu
        cursor.execute("""
            SELECT 
                COUNT(id) as total_orders,
                COALESCE(SUM(CASE WHEN status = 'completed' THEN net_amount ELSE 0 END), 0) as total_revenue,
                COALESCE(SUM(CASE WHEN status = 'completed' THEN discount_amount ELSE 0 END), 0) as total_discount,
                COALESCE(SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END), 0) as cancelled_orders,
                COALESCE(SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END), 0) as completed_orders
            FROM orders
            WHERE order_date >= ?
        """, (date_limit,))
        order_stats = cursor.fetchone() or {}

        # 2. Lợi nhuận gộp: SUM((unit_price - cost_price) * quantity)
        cursor.execute("""
            SELECT 
                COALESCE(SUM((oi.unit_price - oi.cost_price) * oi.quantity), 0) as gross_profit
            FROM order_items oi
            JOIN orders o ON oi.order_id = o.id
            WHERE o.status = 'completed' AND o.order_date >= ?
        """, (date_limit,))
        profit_row = cursor.fetchone() or {}

        conn.close()

        total_orders = order_stats.get("total_orders", 0) or 0
        completed_orders = order_stats.get("completed_orders", 0) or 0
        total_revenue = float(order_stats.get("total_revenue", 0.0) or 0.0)
        gross_profit = float(profit_row.get("gross_profit", 0.0) or 0.0)

        aov = round(total_revenue / completed_orders) if completed_orders > 0 else 0
        profit_margin = round((gross_profit / total_revenue) * 100, 1) if total_revenue > 0 else 0.0
        cancel_rate = round((order_stats.get("cancelled_orders", 0) / total_orders) * 100, 1) if total_orders > 0 else 0.0

        return {
            "totalRevenue": total_revenue,
            "grossProfit": gross_profit,
            "profitMargin": profit_margin,
            "totalOrders": total_orders,
            "completedOrders": completed_orders,
            "aov": aov,
            "cancelRate": cancel_rate,
            "totalDiscount": float(order_stats.get("total_discount", 0.0) or 0.0),
            "daysAnalyzed": days
        }

    @staticmethod
    def get_revenue_timeline(days: int = 30) -> list:
        date_limit = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
        conn = get_db_connection()
        cursor = conn.cursor()

        # T-SQL dùng CONVERT(VARCHAR(10), order_date, 120) cho định dạng yyyy-MM-dd
        cursor.execute("""
            SELECT 
                CONVERT(VARCHAR(10), order_date, 120) as [date],
                COUNT(id) as order_count,
                COALESCE(SUM(CASE WHEN status = 'completed' THEN net_amount ELSE 0 END), 0) as revenue
            FROM orders
            WHERE order_date >= ?
            GROUP BY CONVERT(VARCHAR(10), order_date, 120)
            ORDER BY [date] ASC
        """, (date_limit,))
        rows = cursor.fetchall()
        conn.close()

        for r in rows:
            r["revenue"] = float(r.get("revenue", 0.0) or 0.0)
        return rows

    @staticmethod
    def get_channel_breakdown(days: int = 180) -> list:
        date_limit = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT 
                channel,
                COUNT(id) as order_count,
                COALESCE(SUM(CASE WHEN status = 'completed' THEN net_amount ELSE 0 END), 0) as total_revenue
            FROM orders
            WHERE order_date >= ?
            GROUP BY channel
            ORDER BY total_revenue DESC
        """, (date_limit,))
        rows = cursor.fetchall()
        conn.close()

        for r in rows:
            r["total_revenue"] = float(r.get("total_revenue", 0.0) or 0.0)
        return rows

    @staticmethod
    def get_top_products(limit: int = 8) -> list:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT 
                p.id,
                p.sku,
                p.name,
                c.name as category_name,
                p.selling_price,
                p.cost_price,
                p.stock_quantity,
                SUM(oi.quantity) as total_sold,
                SUM(oi.total_price) as total_revenue,
                SUM((oi.unit_price - oi.cost_price) * oi.quantity) as total_profit
            FROM order_items oi
            JOIN products p ON oi.product_id = p.id
            LEFT JOIN categories c ON p.category_id = c.id
            JOIN orders o ON oi.order_id = o.id
            WHERE o.status = 'completed'
            GROUP BY p.id, p.sku, p.name, c.name, p.selling_price, p.cost_price, p.stock_quantity
            ORDER BY total_sold DESC
            OFFSET 0 ROWS FETCH NEXT ? ROWS ONLY
        """, (limit,))
        rows = cursor.fetchall()
        conn.close()

        for r in rows:
            r["selling_price"] = float(r.get("selling_price", 0.0) or 0.0)
            r["cost_price"] = float(r.get("cost_price", 0.0) or 0.0)
            r["total_revenue"] = float(r.get("total_revenue", 0.0) or 0.0)
            r["total_profit"] = float(r.get("total_profit", 0.0) or 0.0)
        return rows

    @staticmethod
    def get_inventory_alerts(threshold: int = 40) -> list:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT 
                p.id,
                p.sku,
                p.name,
                c.name as category_name,
                p.selling_price,
                p.cost_price,
                p.stock_quantity
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.id
            WHERE p.stock_quantity <= ?
            ORDER BY p.stock_quantity ASC
        """, (threshold,))
        rows = cursor.fetchall()
        conn.close()

        for r in rows:
            r["selling_price"] = float(r.get("selling_price", 0.0) or 0.0)
            r["cost_price"] = float(r.get("cost_price", 0.0) or 0.0)
        return rows

    @staticmethod
    def get_customer_segments() -> dict:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT 
                segment,
                COUNT(id) as customer_count,
                COALESCE(SUM(total_spent), 0) as total_revenue,
                COALESCE(AVG(total_spent), 0) as avg_spent
            FROM customers
            GROUP BY segment
            ORDER BY total_revenue DESC
        """)
        segments = cursor.fetchall()

        cursor.execute("""
            SELECT 
                id, name, email, phone, city, segment, total_spent, orders_count
            FROM customers
            ORDER BY total_spent DESC
            OFFSET 0 ROWS FETCH NEXT 10 ROWS ONLY
        """)
        top_customers = cursor.fetchall()

        conn.close()

        for s in segments:
            s["total_revenue"] = float(s.get("total_revenue", 0.0) or 0.0)
            s["avg_spent"] = float(s.get("avg_spent", 0.0) or 0.0)

        for c in top_customers:
            c["total_spent"] = float(c.get("total_spent", 0.0) or 0.0)

        return {
            "segments": segments,
            "topCustomers": top_customers
        }

    @staticmethod
    def get_context_for_ai() -> dict:
        kpis = AnalyticsService.get_kpis(60)
        channels = AnalyticsService.get_channel_breakdown(60)
        top_products = AnalyticsService.get_top_products(5)
        inventory_alerts = AnalyticsService.get_inventory_alerts(40)
        segments = AnalyticsService.get_customer_segments()

        return {
            "kpis": kpis,
            "channels": channels,
            "top_products": top_products,
            "inventory_alerts": inventory_alerts,
            "segments": segments["segments"]
        }
