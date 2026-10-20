"""
==============================================================================
ROUTER QUẢN LÝ SẢN PHẨM & DANH MỤC (PRODUCT ROUTER - FASTAPI)
==============================================================================
"""

from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
from typing import Optional
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


@router.get("/")
def get_products(authorization: Optional[str] = Header(None)):
    user_role = "sales"
    if authorization and authorization.startswith("Bearer "):
        try:
            token = authorization.split(" ")[1]
            payload = decode_access_token(token)
            user_role = payload.get("role", "sales")
        except Exception:
            pass

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.*, c.name as category_name
        FROM products p
        LEFT JOIN categories c ON p.category_id = c.id
        ORDER BY p.id DESC
    """)
    products = [dict(r) for r in cursor.fetchall()]
    conn.close()

    # Nếu là Sales hoặc User thường: ẩn hoàn toàn giá vốn nhập hàng (Bảo mật tài chính doanh nghiệp)
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
def create_product(req: CreateProductRequest, user: dict = Depends(require_roles("admin", "manager"))):
    """Chỉ Admin và Manager mới có quyền thêm sản phẩm mới vào kho."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO products (sku, name, category_id, cost_price, selling_price, stock_quantity, image_url)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (req.sku, req.name, req.categoryId, req.costPrice, req.sellingPrice, req.stockQuantity, req.imageUrl))
        conn.commit()
        product_id = cursor.lastrowid
        conn.close()
        return {"success": True, "message": "Thêm sản phẩm thành công!", "id": product_id}
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=400, detail=f"Lỗi khi thêm sản phẩm: {str(e)}")

