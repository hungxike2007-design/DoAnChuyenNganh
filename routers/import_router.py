"""
==============================================================================
ROUTER NHẬP DỮ LIỆU TỪ FILE EXCEL / CSV (IMPORT ROUTER - FASTAPI)
==============================================================================
Các Endpoint:
- POST /api/import/orders: Nhập file danh sách đơn hàng đa kênh (.csv, .xlsx, .xls)
- POST /api/import/products: Nhập file danh sách sản phẩm & tồn kho (.csv, .xlsx, .xls)
- GET  /api/import/template/orders: Tải file mẫu CSV đơn hàng chuẩn tiếng Việt
- GET  /api/import/template/products: Tải file mẫu CSV sản phẩm chuẩn tiếng Việt
==============================================================================
"""

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Response
from typing import Optional
from routers.auth_router import get_current_user, require_roles
from services.import_service import ImportService

router = APIRouter(prefix="/api/import", tags=["Data Import (Excel & CSV)"])


@router.post("/orders")
async def import_orders(
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user)
):
    """
    Nạp danh sách đơn hàng từ file CSV hoặc Excel:
    - Gán chặt chẽ dữ liệu với tài khoản cửa hàng đang đăng nhập (user_id).
    - Tự động nhận diện các cột: Mã đơn, Kênh, Khách hàng, Sản phẩm, Đơn giá, v.v.
    """
    try:
        user_id = None if user.get("role") == "admin" else int(user.get("sub", 0))
        contents = await file.read()
        if len(contents) == 0:
            raise HTTPException(status_code=400, detail="File tải lên hoàn toàn rỗng!")

        result = ImportService.import_orders_from_file(contents, file.filename, user_id=user_id)
        return result
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi xử lý file đơn hàng: {str(e)}")


@router.post("/products")
async def import_products(
    file: UploadFile = File(...),
    user: dict = Depends(require_roles("admin", "manager"))
):
    """
    Nạp danh mục sản phẩm và số lượng tồn kho từ file CSV hoặc Excel:
    - Chỉ dành cho Quản Lý (Manager) hoặc Quản Trị Viên (Admin).
    - Tự động cập nhật sản phẩm nếu trùng SKU, thêm mới nếu chưa có.
    """
    try:
        user_id = None if user.get("role") == "admin" else int(user.get("sub", 0))
        contents = await file.read()
        if len(contents) == 0:
            raise HTTPException(status_code=400, detail="File tải lên hoàn toàn rỗng!")

        result = ImportService.import_products_from_file(contents, file.filename, user_id=user_id)
        return result
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi xử lý file sản phẩm: {str(e)}")


@router.get("/template/orders")
def download_order_template():
    """Tải file mẫu CSV danh sách đơn hàng đa kênh với mã hóa UTF-8 BOM chuẩn hiển thị tốt trên Excel tiếng Việt."""
    csv_bytes = ImportService.get_order_template_csv()
    return Response(
        content=csv_bytes,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": "attachment; filename=mau_import_don_hang.csv"
        }
    )


@router.get("/template/products")
def download_product_template():
    """Tải file mẫu CSV danh mục sản phẩm với mã hóa UTF-8 BOM chuẩn hiển thị tốt trên Excel tiếng Việt."""
    csv_bytes = ImportService.get_product_template_csv()
    return Response(
        content=csv_bytes,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": "attachment; filename=mau_import_san_pham.csv"
        }
    )
