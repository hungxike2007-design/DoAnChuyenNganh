"""
==============================================================================
ROUTER PHÂN TÍCH DOANH THU & BIỂU ĐỒ (REVENUE ROUTER - FASTAPI)
==============================================================================
Các Endpoint:
- GET /api/revenue/kpis: Thẻ chỉ số tổng quan (Doanh thu, Lợi nhuận, AOV...)
- GET /api/revenue/timeline: Doanh thu theo chuỗi thời gian
- GET /api/revenue/channels: Tỷ lệ doanh thu theo Shopee, TikTok Shop, Cửa hàng, Web
- GET /api/revenue/top-products: Danh sách sản phẩm bán chạy nhất
- GET /api/revenue/inventory-alerts: Sản phẩm sắp hết hàng hoặc tồn kho lâu
- GET /api/revenue/rfm: Phân khúc khách hàng theo giá trị chi tiêu
==============================================================================
"""

from fastapi import APIRouter, Query
from services.analytics_service import AnalyticsService

router = APIRouter(prefix="/api/revenue", tags=["Revenue & Analytics"])


@router.get("/kpis")
def get_kpis(days: int = Query(180, ge=1, le=720)):
    data = AnalyticsService.get_kpis(days)
    return {"success": True, "data": data}


@router.get("/timeline")
def get_timeline(days: int = Query(30, ge=1, le=180)):
    data = AnalyticsService.get_revenue_timeline(days)
    return {"success": True, "data": data}


@router.get("/channels")
def get_channels(days: int = Query(180, ge=1, le=720)):
    data = AnalyticsService.get_channel_breakdown(days)
    return {"success": True, "data": data}


@router.get("/top-products")
def get_top_products(limit: int = Query(8, ge=1, le=50)):
    data = AnalyticsService.get_top_products(limit)
    return {"success": True, "data": data}


@router.get("/inventory-alerts")
def get_inventory_alerts(threshold: int = Query(40, ge=1, le=500)):
    data = AnalyticsService.get_inventory_alerts(threshold)
    return {"success": True, "data": data}


@router.get("/rfm")
def get_customer_rfm():
    data = AnalyticsService.get_customer_segments()
    return {"success": True, "data": data}


@router.get("/orders")
def get_orders(limit: int = Query(50, ge=1, le=200), channel: str = Query("All"), status: str = Query("All")):
    from config.db import get_db_connection
    conn = get_db_connection()
    cursor = conn.cursor()
    query = """
        SELECT o.id, o.order_code, o.channel, o.total_amount, o.discount_amount, o.net_amount,
               o.payment_method, o.status, CONVERT(VARCHAR(19), o.order_date, 120) as order_date,
               c.name as customer_name, c.phone as customer_phone
        FROM orders o
        LEFT JOIN customers c ON o.customer_id = c.id
        WHERE 1=1
    """
    params = []
    if channel and channel != "All":
        query += " AND o.channel = ?"
        params.append(channel)
    if status and status != "All":
        query += " AND o.status = ?"
        params.append(status)
    query += " ORDER BY o.id DESC OFFSET 0 ROWS FETCH NEXT ? ROWS ONLY"
    params.append(limit)

    cursor.execute(query, tuple(params))
    orders = cursor.fetchall()
    conn.close()

    for o in orders:
        o["total_amount"] = float(o.get("total_amount", 0.0) or 0.0)
        o["net_amount"] = float(o.get("net_amount", 0.0) or 0.0)
        o["discount_amount"] = float(o.get("discount_amount", 0.0) or 0.0)

    return {"success": True, "data": orders}

