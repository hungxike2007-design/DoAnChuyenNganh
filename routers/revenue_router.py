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

from fastapi import APIRouter, Query, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from services.analytics_service import AnalyticsService
from routers.auth_router import require_roles, get_current_user

router = APIRouter(prefix="/api/revenue", tags=["Revenue & Analytics"])


@router.get("/kpis")
def get_kpis(days: int = Query(180, ge=1, le=720), user: dict = Depends(require_roles("admin", "manager"))):
    """Chỉ Admin và Manager mới có quyền xem toàn bộ KPI doanh thu & lợi nhuận gộp."""
    data = AnalyticsService.get_kpis(days)
    return {"success": True, "data": data}


@router.get("/timeline")
def get_timeline(days: int = Query(30, ge=1, le=180), user: dict = Depends(require_roles("admin", "manager"))):
    """Chỉ Admin và Manager mới có quyền xem chuỗi thời gian doanh thu toàn công ty."""
    data = AnalyticsService.get_revenue_timeline(days)
    return {"success": True, "data": data}


@router.get("/channels")
def get_channels(days: int = Query(180, ge=1, le=720), user: dict = Depends(require_roles("admin", "manager"))):
    data = AnalyticsService.get_channel_breakdown(days)
    return {"success": True, "data": data}


@router.get("/top-products")
def get_top_products(limit: int = Query(8, ge=1, le=50), user: dict = Depends(get_current_user)):
    data = AnalyticsService.get_top_products(limit)
    # Nếu là Sales hoặc User thông thường, ẩn hoàn toàn thông tin lợi nhuận (cost_price & profit)
    if user.get("role") in ["sales", "user"]:
        for p in data:
            p.pop("cost_price", None)
            p.pop("total_profit", None)
    return {"success": True, "data": data}


@router.get("/inventory-alerts")
def get_inventory_alerts(threshold: int = Query(40, ge=1, le=500), user: dict = Depends(get_current_user)):
    data = AnalyticsService.get_inventory_alerts(threshold)
    if user.get("role") in ["sales", "user"]:
        for p in data:
            p.pop("cost_price", None)
    return {"success": True, "data": data}


@router.get("/rfm")
def get_customer_rfm(user: dict = Depends(require_roles("admin", "manager"))):
    """Chỉ Admin và Manager mới có quyền phân tích phân khúc tài chính khách hàng."""
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


class OrderItemInput(BaseModel):
    productId: int
    quantity: int = 1


class CreateOrderRequest(BaseModel):
    channel: str
    customerId: Optional[int] = 1
    paymentMethod: Optional[str] = "COD"
    items: List[OrderItemInput]


@router.post("/orders")
def create_order(req: CreateOrderRequest, user: dict = Depends(get_current_user)):
    """Tạo đơn hàng mới (Nhập trực tiếp từ Web hoặc đẩy từ Webhook Shopee, TikTok Shop)."""
    if not req.items:
        raise HTTPException(status_code=400, detail="Đơn hàng phải có ít nhất 1 sản phẩm!")

    import random
    from datetime import datetime
    from config.db import get_db_connection

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Lấy thông tin các sản phẩm trong đơn để tính tổng tiền và giá vốn
        product_ids = [item.productId for item in req.items]
        placeholders = ",".join("?" * len(product_ids))
        cursor.execute(f"SELECT id, selling_price, cost_price, stock_quantity, name FROM products WHERE id IN ({placeholders})", tuple(product_ids))
        prod_map = {p["id"]: p for p in cursor.fetchall()}

        total_amount = 0.0
        items_data = []

        for item in req.items:
            prod = prod_map.get(item.productId)
            if not prod:
                raise HTTPException(status_code=404, detail=f"Không tìm thấy sản phẩm có ID {item.productId}")
            
            unit_price = float(prod["selling_price"])
            cost_price = float(prod["cost_price"])
            total_price = unit_price * item.quantity
            total_amount += total_price

            items_data.append({
                "product_id": item.productId,
                "quantity": item.quantity,
                "unit_price": unit_price,
                "cost_price": cost_price,
                "total_price": total_price
            })

        order_code = f"ORD-{datetime.now().strftime('%Y%m%d%H%M')}-{random.randint(100, 999)}"
        net_amount = total_amount

        # 1. Thêm vào bảng orders và lấy ngay order_id bằng OUTPUT INSERTED.id
        cursor.execute("""
            INSERT INTO orders (order_code, customer_id, channel, total_amount, discount_amount, net_amount, payment_method, status, order_date)
            OUTPUT INSERTED.id
            VALUES (?, ?, ?, ?, 0, ?, ?, 'completed', GETDATE())
        """, (order_code, req.customerId, req.channel, total_amount, net_amount, req.paymentMethod))

        row = cursor.fetchone()
        order_id = row["id"] if row else None

        # 2. Thêm vào bảng order_items và trừ tồn kho
        for it in items_data:
            cursor.execute("""
                INSERT INTO order_items (order_id, product_id, quantity, unit_price, cost_price, total_price)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (order_id, it["product_id"], it["quantity"], it["unit_price"], it["cost_price"], it["total_price"]))

            cursor.execute("""
                UPDATE products 
                SET stock_quantity = CASE WHEN stock_quantity >= ? THEN stock_quantity - ? ELSE 0 END
                WHERE id = ?
            """, (it["quantity"], it["quantity"], it["product_id"]))

        # 3. Cập nhật chi tiêu khách hàng
        if req.customerId:
            cursor.execute("""
                UPDATE customers 
                SET total_spent = total_spent + ?,
                    orders_count = orders_count + 1,
                    last_order_date = GETDATE()
                WHERE id = ?
            """, (net_amount, req.customerId))

        conn.commit()
        conn.close()

        return {
            "success": True,
            "message": f"Tạo đơn hàng {order_code} thành công qua kênh '{req.channel}'!",
            "data": {
                "order_id": order_id,
                "order_code": order_code,
                "total_amount": total_amount,
                "channel": req.channel
            }
        }
    except HTTPException:
        conn.close()
        raise
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=f"Lỗi khi tạo đơn hàng: {str(e)}")


