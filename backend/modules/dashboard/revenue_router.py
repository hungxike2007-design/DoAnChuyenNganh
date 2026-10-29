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
try:
    from backend.modules.dashboard.analytics_service import AnalyticsService
    from backend.modules.auth.auth_router import require_roles, get_current_user
    from backend.config.db import get_db_connection
except ImportError:
    from services.analytics_service import AnalyticsService
    from routers.auth_router import require_roles, get_current_user
    from config.db import get_db_connection

router = APIRouter(prefix="/api/revenue", tags=["Revenue & Analytics"])

def _resolve_target_user(user: dict, view_user_id: Optional[int] = None) -> Optional[int]:
    role = (user.get("role") or "").lower()
    if role in ["admin", "manager"]:
        return view_user_id
    return int(user["sub"])



@router.get("/kpis")
def get_kpis(days: int = Query(180, ge=1, le=720), view_user_id: Optional[int] = Query(None), user: dict = Depends(get_current_user)):
    target_user_id = _resolve_target_user(user, view_user_id)
    data = AnalyticsService.get_kpis(days, user_id=target_user_id)
    return {"success": True, "data": data}


@router.get("/timeline")
def get_timeline(days: int = Query(30, ge=1, le=180), view_user_id: Optional[int] = Query(None), user: dict = Depends(get_current_user)):
    target_user_id = _resolve_target_user(user, view_user_id)
    data = AnalyticsService.get_revenue_timeline(days, user_id=target_user_id)
    return {"success": True, "data": data}


@router.get("/channels")
def get_channels(days: int = Query(180, ge=1, le=720), view_user_id: Optional[int] = Query(None), user: dict = Depends(get_current_user)):
    target_user_id = _resolve_target_user(user, view_user_id)
    data = AnalyticsService.get_channel_breakdown(days, user_id=target_user_id)
    return {"success": True, "data": data}


@router.get("/top-products")
def get_top_products(limit: int = Query(8, ge=1, le=50), view_user_id: Optional[int] = Query(None), user: dict = Depends(get_current_user)):
    target_user_id = _resolve_target_user(user, view_user_id)
    data = AnalyticsService.get_top_products(limit, user_id=target_user_id)
    if user.get("role") in ["sales", "user"]:
        for p in data:
            p.pop("cost_price", None)
            p.pop("total_profit", None)
    return {"success": True, "data": data}


@router.get("/inventory-alerts")
def get_inventory_alerts(threshold: int = Query(40, ge=1, le=500), view_user_id: Optional[int] = Query(None), user: dict = Depends(get_current_user)):
    target_user_id = _resolve_target_user(user, view_user_id)
    data = AnalyticsService.get_inventory_alerts(threshold, user_id=target_user_id)
    if user.get("role") in ["sales", "user"]:
        for p in data:
            p.pop("cost_price", None)
    return {"success": True, "data": data}


@router.get("/rfm")
def get_customer_rfm(user: dict = Depends(get_current_user)):
    target_user_id = None if user.get("role") == "admin" else int(user["sub"])
    data = AnalyticsService.get_customer_segments(user_id=target_user_id)
    return {"success": True, "data": data}




@router.get("/user-rankings")
def get_user_rankings(user: dict = Depends(get_current_user)):
    """Bảng xếp hạng doanh thu và hiệu suất người dùng (Chỉ dành cho Admin & Manager)."""
    user_role = (user.get("role") or "").lower()
    if user_role not in ["admin", "manager"]:
        raise HTTPException(status_code=403, detail="Chỉ Quản trị viên (Admin) hoặc Quản lý (Manager) mới có quyền xem Bảng xếp hạng người dùng!")

    try:
        from backend.config.db import get_db_connection
    except ImportError:
        from config.db import get_db_connection

    conn = get_db_connection()
    cursor = conn.cursor()
    query = """
        SELECT 
            u.id, 
            u.full_name, 
            u.email, 
            u.role,
            COUNT(o.id) as total_orders,
            COALESCE(SUM(o.net_amount), 0) as total_revenue,
            COALESCE(AVG(o.net_amount), 0) as avg_order_value,
            CONVERT(VARCHAR(10), MAX(o.order_date), 120) as last_order_date
        FROM users u
        LEFT JOIN orders o ON u.id = o.user_id AND o.status = 'completed'
        GROUP BY u.id, u.full_name, u.email, u.role
        ORDER BY total_revenue DESC, total_orders DESC
    """
    cursor.execute(query)
    rankings = cursor.fetchall()
    conn.close()

    for r in rankings:
        r["total_revenue"] = float(r.get("total_revenue", 0.0) or 0.0)
        r["avg_order_value"] = float(r.get("avg_order_value", 0.0) or 0.0)
        r["total_orders"] = int(r.get("total_orders", 0) or 0)

    return {"success": True, "data": rankings}


@router.get("/orders")
def get_orders(
    limit: int = Query(50, ge=1, le=200),
    channel: str = Query("All"),
    status: str = Query("All"),
    user: dict = Depends(get_current_user)
):
    from config.db import get_db_connection
    conn = get_db_connection()
    cursor = conn.cursor()
    query = """
        SELECT o.id, o.order_code, o.channel, o.total_amount, o.discount_amount, o.net_amount,
               o.payment_method, o.status, CONVERT(VARCHAR(19), o.order_date, 120) as order_date,
               c.name as customer_name, c.phone as customer_phone,
               COALESCE(STRING_AGG(CONCAT(p.name, ' (x', oi.quantity, ')'), ', '), N'Sản phẩm đặt hàng') as product_summary
        FROM orders o
        LEFT JOIN customers c ON o.customer_id = c.id
        LEFT JOIN order_items oi ON o.id = oi.order_id
        LEFT JOIN products p ON oi.product_id = p.id
        WHERE 1=1
    """
    params = []
    if user.get("role") != "admin":
        query += " AND o.user_id = ?"
        params.append(int(user["sub"]))

    if channel and channel != "All":
        query += " AND o.channel = ?"
        params.append(channel)
    if status and status != "All":
        query += " AND o.status = ?"
        params.append(status)
    query += """
        GROUP BY o.id, o.order_code, o.channel, o.total_amount, o.discount_amount, o.net_amount,
                 o.payment_method, o.status, CONVERT(VARCHAR(19), o.order_date, 120),
                 c.name, c.phone
        ORDER BY o.id DESC OFFSET 0 ROWS FETCH NEXT ? ROWS ONLY
    """
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
    productId: Optional[int] = None
    productName: Optional[str] = None
    unitPrice: Optional[float] = None
    quantity: int = 1


class CreateOrderRequest(BaseModel):
    channel: str
    customerId: Optional[int] = 1
    paymentMethod: Optional[str] = "COD"
    items: List[OrderItemInput]


@router.post("/orders")
def create_order(req: CreateOrderRequest, user: dict = Depends(get_current_user)):
    """Tạo đơn hàng mới (tự động gắn với tài khoản đang đăng nhập user_id, hỗ trợ cả tự nhập sản phẩm thủ công)."""
    if not req.items:
        raise HTTPException(status_code=400, detail="Đơn hàng phải có ít nhất 1 sản phẩm!")

    import random
    from datetime import datetime
    try:
        from backend.config.db import get_db_connection
    except ImportError:
        from config.db import get_db_connection

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        user_id = int(user["sub"])
        total_amount = 0.0
        items_data = []

        for item in req.items:
            prod_id = item.productId
            quantity = item.quantity if item.quantity > 0 else 1

            if prod_id and prod_id > 0:
                # 1. Chọn từ kho sản phẩm có sẵn
                cursor.execute("SELECT id, selling_price, cost_price, name FROM products WHERE id = ?", (prod_id,))
                prod = cursor.fetchone()
                if not prod:
                    raise HTTPException(status_code=404, detail=f"Không tìm thấy sản phẩm có ID {prod_id}")
                unit_price = float(item.unitPrice if item.unitPrice is not None else prod["selling_price"])
                cost_price = float(prod["cost_price"] or unit_price * 0.7)
            else:
                # 2. Người dùng tự nhập tên sản phẩm và đơn giá
                prod_name = (item.productName or "Sản phẩm đặt hàng").strip()
                unit_price = float(item.unitPrice if item.unitPrice is not None else 100000.0)
                if unit_price <= 0:
                    unit_price = 100000.0

                # Kiểm tra xem sản phẩm đã có trong DB chưa
                cursor.execute("SELECT TOP 1 id, selling_price, cost_price FROM products WHERE name = ?", (prod_name,))
                existing = cursor.fetchone()
                if existing:
                    prod_id = existing["id"]
                    cost_price = float(existing["cost_price"] or unit_price * 0.7)
                else:
                    cost_price = round(unit_price * 0.7)
                    sku = f"SKU-{random.randint(1000, 9999)}"
                    cursor.execute("""
                        INSERT INTO products (sku, name, category_id, cost_price, selling_price, stock_quantity, user_id)
                        OUTPUT INSERTED.id
                        VALUES (?, ?, 1, ?, ?, 100, ?)
                    """, (sku, prod_name, cost_price, unit_price, user_id))
                    row_prod = cursor.fetchone()
                    prod_id = row_prod["id"]

            total_price = unit_price * quantity
            total_amount += total_price

            items_data.append({
                "product_id": prod_id,
                "quantity": quantity,
                "unit_price": unit_price,
                "cost_price": cost_price,
                "total_price": total_price
            })

        order_code = f"ORD-{datetime.now().strftime('%Y%m%d%H%M')}-{random.randint(100, 999)}"
        net_amount = total_amount

        # 1. Thêm vào bảng orders và lấy ngay order_id bằng OUTPUT INSERTED.id
        cursor.execute("""
            INSERT INTO orders (order_code, customer_id, channel, total_amount, discount_amount, net_amount, payment_method, status, order_date, user_id)
            OUTPUT INSERTED.id
            VALUES (?, ?, ?, ?, 0, ?, ?, 'completed', GETDATE(), ?)
        """, (order_code, req.customerId, req.channel, total_amount, net_amount, req.paymentMethod, user_id))

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
