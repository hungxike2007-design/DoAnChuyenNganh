"""
==============================================================================
ROUTER BÁO CÁO KẾT QUẢ KINH DOANH P&L (FINANCIAL ROUTER - FASTAPI)
==============================================================================
Các Endpoint:
- GET /api/financial/pnl-report: Trả về Báo cáo Kết quả Kinh doanh (P&L) chi tiết
- POST /api/financial/expenses: Cập nhật chi phí vận hành (OPEX) cho tháng
- GET /api/financial/expenses: Lấy lịch sử cấu hình chi phí vận hành
==============================================================================
"""

from fastapi import APIRouter, Query, Depends, HTTPException, status, Request
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

try:
    from backend.modules.financial.financial_service import FinancialService
    from backend.modules.auth.auth_router import require_roles, get_current_user
except ImportError:
    from services.financial_service import FinancialService
    from routers.auth_router import require_roles, get_current_user

router = APIRouter(prefix="/api/financial", tags=["Financial & P&L"])


class ExpenseUpdateRequest(BaseModel):
    month_year: str
    channel: str = "All"
    rent_expense: float = 0.0
    salary_expense: float = 0.0
    marketing_expense: float = 0.0
    utilities_expense: float = 0.0
    other_expense: float = 0.0
    note: Optional[str] = ""


@router.get("/pnl-report")
def get_pnl_report(
    month: Optional[int] = Query(None, ge=1, le=12, description="Tháng báo cáo (1-12)"),
    year: Optional[int] = Query(None, ge=2020, le=2030, description="Năm báo cáo"),
    channel: str = Query("All", description="Kênh bán hàng lọc"),
    current_user: dict = Depends(require_roles("admin", "manager", "sales", "user"))
):
    """Lấy Báo cáo Kết quả Hoạt động Kinh doanh (P&L) theo tháng và năm."""
    now = datetime.now()
    target_month = month or now.month
    target_year = year or now.year

    user_id = current_user.get("user_id") or current_user.get("sub")
    if user_id is not None:
        try:
            user_id = int(user_id)
        except (ValueError, TypeError):
            user_id = None
            
    role = (current_user.get("role") or "user").lower()

    try:
        report = FinancialService.get_pnl_report(
            month=target_month,
            year=target_year,
            channel=channel,
            user_id=user_id,
            role=role
        )
        return {"success": True, "data": report}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi tổng hợp báo cáo tài chính P&L: {str(e)}"
        )


@router.post("/expenses")
def update_expenses(
    req: ExpenseUpdateRequest,
    request: Request,
    current_user: dict = Depends(require_roles("admin", "manager"))
):
    """Cập nhật chi phí vận hành (OPEX) cho một kỳ kế toán (Chỉ Admin và Manager)."""
    user_id = current_user.get("user_id") or current_user.get("sub")
    if user_id is not None:
        try:
            user_id = int(user_id)
        except (ValueError, TypeError):
            user_id = None

    try:
        ok = FinancialService.save_expenses(
            month_year=req.month_year.strip(),
            channel=req.channel.strip(),
            rent=req.rent_expense,
            salary=req.salary_expense,
            marketing=req.marketing_expense,
            utilities=req.utilities_expense,
            other=req.other_expense,
            note=req.note or "",
            user_id=user_id,
            user_email=current_user.get("email", ""), user_role=current_user.get("role", ""),
            ip_address=request.client.host if request.client else "", user_agent=request.headers.get("user-agent", "")
        )
        return {"success": ok, "message": f"Đã lưu chi phí vận hành cho kỳ {req.month_year} thành công!"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi lưu chi phí vận hành: {str(e)}"
        )


@router.get("/expenses")
def list_expenses_history(
    current_user: dict = Depends(require_roles("admin", "manager", "sales", "user"))
):
    """Lấy danh sách các kỳ đã cấu hình chi phí vận hành."""
    try:
        history = FinancialService.get_expenses_history()
        return {"success": True, "data": history}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi tải lịch sử chi phí: {str(e)}"
        )
