"""
==============================================================================
ROUTER QUẢN LÝ SẢN PHẨM & DANH MỤC (PRODUCT ROUTER - FASTAPI)
==============================================================================
"""

from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel, Field
from typing import Optional
try:
    from backend.config.db import get_db_connection
    from backend.modules.auth.auth_router import get_current_user, require_roles
    from backend.modules.auth.auth_service import decode_access_token
except ImportError:
    from config.db import get_db_connection
    from routers.auth_router import get_current_user, require_roles
    from services.auth_service import decode_access_token

router = APIRouter(prefix="/api/products", tags=["Products & Categories"])


class CreateProductRequest(BaseModel):
    sku: str
    name: str
    categoryId: int
    costPrice: float
    sellingPrice: float
    stockQuantity: int
    imageUrl: Optional[str] = ""


class SetCustomPriceRequest(BaseModel):
    userId: int = Field(..., description="ID của người dùng được gán giá riêng")
    productId: int = Field(..., description="ID của sản phẩm")
    customPrice: float = Field(..., gt=0, description="Mức giá bán riêng (VNĐ)")
    note: Optional[str] = ""


@router.get("/")
def get_products(authorization: Optional[str] = Header(None)):
    user_role = "sales"
    user_id = None
    if authorization and authorization.startswith("Bearer "):
        try:
            token = authorization.split(" ")[1]
            payload = decode_access_token(token)
            user_role = payload.get("role", "sales")
            user_id = int(payload.get("sub")) if payload.get("sub") else None
        except Exception:
            pass

    conn = get_db_connection()
    cursor = conn.cursor()

    if user_id is not None:
        cursor.execute("""
            SELECT p.*, c.name as category_name,
                   upp.custom_price,
                   COALESCE(upp.custom_price, p.selling_price) as effective_price,
                   CASE WHEN upp.custom_price IS NOT NULL THEN 1 ELSE 0 END as has_custom_price
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.id
            LEFT JOIN user_product_prices upp ON p.id = upp.product_id AND upp.user_id = ?
            ORDER BY p.id DESC
        """, (user_id,))
        products = [dict(r) for r in cursor.fetchall()]
        for p in products:
            p["base_price"] = float(p.get("selling_price", 0) or 0)
            p["selling_price"] = float(p.get("effective_price", p["base_price"]))
            p["has_custom_price"] = bool(p.get("has_custom_price", 0))
            p["custom_price"] = float(p["custom_price"]) if p.get("custom_price") is not None else None
    else:
        cursor.execute("""
            SELECT p.*, c.name as category_name
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.id
            ORDER BY p.id DESC
        """)
        products = [dict(r) for r in cursor.fetchall()]
        for p in products:
            p["base_price"] = float(p.get("selling_price", 0) or 0)
            p["has_custom_price"] = False
            p["custom_price"] = None

    conn.close()

    if user_role in ["sales", "user"]:
        for p in products:
            p.pop("cost_price", None)

    return {"success": True, "data": products}


@router.get("/categories")
def get_categories():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM categories ORDER BY id ASC")
    categories = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return {"success": True, "data": categories}


@router.post("/")
def create_product(req: CreateProductRequest, user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        user_id = int(user["sub"])
        cursor.execute("""
            INSERT INTO products (sku, name, category_id, cost_price, selling_price, stock_quantity, image_url, user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (req.sku, req.name, req.categoryId, req.costPrice, req.sellingPrice, req.stockQuantity, req.imageUrl, user_id))
        conn.commit()
        product_id = cursor.lastrowid
        conn.close()
        return {"success": True, "message": "Thêm sản phẩm thành công vào kho của bạn!", "id": product_id}
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=400, detail=f"Lỗi khi thêm sản phẩm: {str(e)}")


@router.post("/custom-price")
def set_custom_price(
    req: SetCustomPriceRequest,
    admin: dict = Depends(require_roles("admin", "manager"))
):
    if req.customPrice <= 0:
        raise HTTPException(status_code=400, detail="Mức giá bán riêng phải lớn hơn 0 VNĐ!")

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT cost_price, selling_price, name FROM products WHERE id = ?", (req.productId,))
        prod = cursor.fetchone()
        if not prod:
            raise HTTPException(status_code=404, detail="Không tìm thấy sản phẩm tương ứng!")

        cost_price = float(prod.get("cost_price", 0) or 0)
        warning = None
        if req.customPrice < cost_price:
            warning = f"Cảnh báo: Mức giá riêng ({req.customPrice:,.0f} đ) thấp hơn giá vốn ({cost_price:,.0f} đ)!"

        cursor.execute("SELECT id FROM user_product_prices WHERE user_id = ? AND product_id = ?", (req.userId, req.productId))
        existing = cursor.fetchone()
        if existing:
            cursor.execute("""
                UPDATE user_product_prices
                SET custom_price = ?, note = ?, updated_at = GETDATE()
                WHERE id = ?
            """, (req.customPrice, req.note or "", existing["id"]))
        else:
            cursor.execute("""
                INSERT INTO user_product_prices (user_id, product_id, custom_price, note)
                VALUES (?, ?, ?, ?)
            """, (req.userId, req.productId, req.customPrice, req.note or ""))

        conn.commit()
        return {
            "success": True,
            "message": f"Đã thiết lập mức giá riêng {req.customPrice:,.0f} đ cho sản phẩm '{prod['name']}'!",
            "warning": warning
        }
    finally:
        conn.close()


@router.get("/custom-prices")
def list_custom_prices(admin: dict = Depends(require_roles("admin", "manager"))):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT upp.id, upp.user_id, u.full_name as user_name, u.email as user_email, u.role as user_role,
                   upp.product_id, p.name as product_name, p.sku as product_sku, p.cost_price, p.selling_price as standard_price,
                   upp.custom_price, upp.note,
                   CONVERT(VARCHAR(19), upp.updated_at, 120) as updated_at
            FROM user_product_prices upp
            JOIN users u ON upp.user_id = u.id
            JOIN products p ON upp.product_id = p.id
            ORDER BY upp.id DESC
        """)
        rows = cursor.fetchall()
        data = []
        for r in rows:
            item = dict(r)
            item["custom_price"] = float(item["custom_price"])
            item["standard_price"] = float(item["standard_price"])
            item["cost_price"] = float(item["cost_price"])
            data.append(item)
        return {"success": True, "data": data}
    finally:
        conn.close()


@router.delete("/custom-price/{price_id}")
def delete_custom_price(price_id: int, admin: dict = Depends(require_roles("admin", "manager"))):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM user_product_prices WHERE id = ?", (price_id,))
        conn.commit()
        return {"success": True, "message": "Đã hủy mức giá riêng này, đưa về giá niêm yết chuẩn!"}
    finally:
        conn.close()
