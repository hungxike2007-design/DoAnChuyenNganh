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
from backend.modules.dashboard.analytics_service import AnalyticsService
from backend.modules.auth.auth_router import require_roles, get_current_user
from backend.config.db import DB_TYPE, get_db_connection

router = APIRouter(prefix="/api/revenue", tags=["Revenue & Analytics"])


def _normalize_row(row):
    if row is None:
        return None
    if isinstance(row, dict):
        return row
    if hasattr(row, "keys"):
        try:
            return {key: row[key] for key in row.keys()}
        except Exception:
            pass
    if hasattr(row, "_mapping"):
        try:
            return {key: row._mapping[key] for key in row._mapping.keys()}
        except Exception:
            pass
    return dict(row)


def _table_has_columns(cursor, table_name: str, required_columns: List[str]) -> bool:
    try:
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = {column_info[1] for column_info in cursor.fetchall()}
        return all(column in columns for column in required_columns)
    except Exception:
        return False


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

    conn = get_db_connection()
    cursor = conn.cursor()
    last_order_sql = "strftime('%Y-%m-%d', MAX(o.order_date)) as last_order_date" if DB_TYPE != 'mssql' else "CONVERT(VARCHAR(10), MAX(o.order_date), 120) as last_order_date"
    query = f"""
        SELECT 
            u.id, 
            u.full_name, 
            u.email, 
            u.role,
            COUNT(o.id) as total_orders,
            COALESCE(SUM(o.net_amount), 0) as total_revenue,
            COALESCE(AVG(o.net_amount), 0) as avg_order_value,
            {last_order_sql}
        FROM users u
        LEFT JOIN orders o ON u.id = o.user_id AND o.status = 'completed'
        GROUP BY u.id, u.full_name, u.email, u.role
        ORDER BY total_revenue DESC, total_orders DESC
    """
    cursor.execute(query)
    rankings = [_normalize_row(r) for r in cursor.fetchall()]
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
    view_user_id: Optional[int] = Query(None),
    user: dict = Depends(get_current_user)
):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        db_type = DB_TYPE
        order_date_select = "strftime('%Y-%m-%d %H:%M:%S', o.order_date) as order_date" if db_type != 'mssql' else "CONVERT(VARCHAR(19), o.order_date, 120) as order_date"
        order_date_group = "strftime('%Y-%m-%d %H:%M:%S', o.order_date)" if db_type != 'mssql' else "CONVERT(VARCHAR(19), o.order_date, 120)"
        product_summary_expr = "GROUP_CONCAT(p.name || ' (x' || oi.quantity || ')', ', ')" if db_type != 'mssql' else "STRING_AGG(CONCAT(p.name, ' (x', oi.quantity, ')'), ', ')"
        query = f"""
            SELECT o.id, o.order_code, o.channel, o.total_amount, o.discount_amount, o.net_amount,
                   o.payment_method, o.status, {order_date_select},
                   c.name as customer_name, c.phone as customer_phone,
                   COALESCE({product_summary_expr}, 'Sản phẩm đặt hàng') as product_summary
            FROM orders o
            LEFT JOIN customers c ON o.customer_id = c.id
            LEFT JOIN order_items oi ON o.id = oi.order_id
            LEFT JOIN products p ON oi.product_id = p.id
            WHERE 1=1
        """
        params = []
        user_role = (user.get("role") or "").lower()
        if user_role not in ["admin", "manager"]:
            try:
                uid = int(user.get("sub", 0))
                query += " AND o.user_id = ?"
                params.append(uid)
            except Exception:
                pass
        elif view_user_id:
            query += " AND o.user_id = ?"
            params.append(view_user_id)

        if channel and channel != "All":
            query += " AND o.channel = ?"
            params.append(channel)
        if status and status != "All":
            query += " AND o.status = ?"
            params.append(status)
        if db_type == "mssql":
            limit_clause = f"ORDER BY o.id DESC OFFSET 0 ROWS FETCH NEXT {limit} ROWS ONLY"
        else:
            limit_clause = f"ORDER BY o.id DESC LIMIT {limit} OFFSET 0"
        query += f"""
            GROUP BY o.id, o.order_code, o.channel, o.total_amount, o.discount_amount, o.net_amount,
                     o.payment_method, o.status, {order_date_group}, c.name, c.phone
            {limit_clause}
        """

        cursor.execute(query, tuple(params))
        orders = [_normalize_row(o) for o in cursor.fetchall()]
        conn.close()

        for o in orders:
            o["total_amount"] = float(o.get("total_amount", 0.0) or 0.0)
            o["net_amount"] = float(o.get("net_amount", 0.0) or 0.0)
            o["discount_amount"] = float(o.get("discount_amount", 0.0) or 0.0)

        return {"success": True, "data": orders}
    except Exception as e:
        print(f"⚠️ [Orders API Error]: {e}", flush=True)
        raise HTTPException(
            status_code=500,
            detail="Không thể tải danh sách đơn hàng. Vui lòng thử lại hoặc liên hệ quản trị viên."
        ) from e


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

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        user_id = int(user["sub"])
        total_amount = 0.0
        items_data = []

        def _fetch_one(query: str, params=()):
            cursor.execute(query, params)
            row = cursor.fetchone()
            return _normalize_row(row)

        for item in req.items:
            prod_id = item.productId
            quantity = item.quantity if item.quantity > 0 else 1

            if prod_id and prod_id > 0:
                prod = _fetch_one("SELECT id, selling_price, cost_price, name FROM products WHERE id = ?", (prod_id,))
                if not prod:
                    raise HTTPException(status_code=404, detail=f"Không tìm thấy sản phẩm có ID {prod_id}")
                unit_price = float(item.unitPrice if item.unitPrice is not None else prod["selling_price"])
                cost_price = float(prod.get("cost_price") or unit_price * 0.7)
            else:
                prod_name = (item.productName or "Sản phẩm đặt hàng").strip()
                unit_price = float(item.unitPrice if item.unitPrice is not None else 100000.0)
                if unit_price <= 0:
                    unit_price = 100000.0

                existing_sql = "SELECT id, selling_price, cost_price FROM products WHERE name = ? LIMIT 1" if DB_TYPE != "mssql" else "SELECT TOP 1 id, selling_price, cost_price FROM products WHERE name = ?"
                existing = _fetch_one(existing_sql, (prod_name,))
                if existing:
                    prod_id = existing["id"]
                    cost_price = float(existing.get("cost_price") or unit_price * 0.7)
                else:
                    cost_price = round(unit_price * 0.7)
                    sku = f"SKU-{random.randint(1000, 9999)}"
                    product_columns = ["sku", "name", "cost_price", "selling_price", "stock_quantity", "user_id"]
                    product_values = [sku, prod_name, cost_price, unit_price, 100, user_id]
                    if _table_has_columns(cursor, "products", ["category_id"]):
                        product_columns.insert(2, "category_id")
                        product_values.insert(2, 1)

                    cols_sql = ", ".join(product_columns)
                    placeholders = ", ".join(["?"] * len(product_values))
                    insert_sql = f"INSERT INTO products ({cols_sql}) VALUES ({placeholders})"
                    if DB_TYPE == "mssql":
                        insert_sql += " OUTPUT INSERTED.id"
                    cursor.execute(insert_sql, tuple(product_values))
                    if DB_TYPE == "mssql":
                        row_prod = _normalize_row(cursor.fetchone())
                        prod_id = row_prod["id"] if row_prod else None
                    else:
                        prod_id = cursor.lastrowid

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
        date_sql = "datetime('now')" if DB_TYPE != "mssql" else "GETDATE()"

        if DB_TYPE == "mssql":
            cursor.execute("""
                INSERT INTO orders (order_code, customer_id, channel, total_amount, discount_amount, net_amount, payment_method, status, order_date, user_id)
                OUTPUT INSERTED.id
                VALUES (?, ?, ?, ?, 0, ?, ?, 'completed', GETDATE(), ?)
            """, (order_code, req.customerId, req.channel, total_amount, net_amount, req.paymentMethod, user_id))
            row = _normalize_row(cursor.fetchone())
            order_id = row["id"] if row else None
        else:
            cursor.execute("""
                INSERT INTO orders (order_code, customer_id, channel, total_amount, discount_amount, net_amount, payment_method, status, order_date, user_id)
                VALUES (?, ?, ?, ?, 0, ?, ?, 'completed', datetime('now'), ?)
            """, (order_code, req.customerId, req.channel, total_amount, net_amount, req.paymentMethod, user_id))
            order_id = cursor.lastrowid

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

        if req.customerId:
            customer_columns = "total_spent", "orders_count", "last_order_date"
            if _table_has_columns(cursor, "customers", ["total_spent", "orders_count", "last_order_date"]):
                date_expr = "GETDATE()" if DB_TYPE == "mssql" else "datetime('now')"
                cursor.execute(f"""
                    UPDATE customers 
                    SET total_spent = total_spent + ?,
                        orders_count = orders_count + 1,
                        last_order_date = {date_expr}
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