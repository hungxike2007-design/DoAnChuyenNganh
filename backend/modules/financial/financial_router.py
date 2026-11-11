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
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timedelta, date
from decimal import Decimal

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
    scope_user_id: Optional[int] = None


@router.get("/pnl-report")
def get_pnl_report(
    month: Optional[int] = Query(None, ge=1, le=12, description="Tháng báo cáo (1-12)"),
    year: Optional[int] = Query(None, ge=2020, le=2030, description="Năm báo cáo"),
    channel: str = Query("All", description="Kênh bán hàng lọc"),
    view_user_id: Optional[int] = Query(None, ge=1),
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
            role=role,
            report_user_id=view_user_id
        )

        return {"success": True, "data": report}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"P&L error: {e}")


@router.get("/pnl-users")
def list_pnl_users(current_user: dict = Depends(require_roles("admin", "manager"))):
    try:
        return {"success": True, "data": FinancialService.get_pnl_users()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Không thể tải danh sách người dùng: {e}")


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
            user_email=current_user.get("email", ""),
            user_role=current_user.get("role", ""),
            ip_address=request.client.host if request.client else "",
            scope_user_id=req.scope_user_id
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


class OrderCostRequest(BaseModel):
    cost_type: str = Field(pattern="^(marketplace_fee|payment_fee|shipping_cost|packaging|order_ads|other)$")
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    note: str = Field(default="", max_length=500)


class OrderFeeStatusRequest(BaseModel):
    status: str = Field(pattern="^(unverified|entered|reconciled)$")


@router.get("/order-profit")
def list_order_profit(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    channel: str = Query("All"),
    order_status: str = Query("All"),
    fee_status: str = Query("All", pattern="^(All|unverified|entered|reconciled)$"),
    profit_filter: str = Query("All", pattern="^(All|negative|nonnegative)$"),
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    admin: dict = Depends(require_roles("admin", "manager"))
):
    """Danh sách lợi nhuận đóng góp theo đơn, chỉ dành cho Admin/Manager."""
    try:
        end_date = (to_date + timedelta(days=1)).strftime("%Y-%m-%d") if to_date else None
        data = FinancialService.get_order_profit(
            limit=limit, offset=offset, channel=channel, status=order_status,
            fee_status=fee_status, profit_filter=profit_filter,
            from_date=from_date.strftime("%Y-%m-%d") if from_date else None, to_date=end_date
        )
        return {"success": True, "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi tải phân tích lợi nhuận đơn hàng: {e}")


@router.get("/orders/{order_id}/profit")
def get_order_profit_detail(order_id: int, admin: dict = Depends(require_roles("admin", "manager"))):
    data = FinancialService.get_order_profit_detail(order_id)
    if not data:
        raise HTTPException(status_code=404, detail="Không tìm thấy đơn hàng.")
    return {"success": True, "data": data}


@router.post("/orders/{order_id}/costs")
def add_order_cost(order_id: int, req: OrderCostRequest, request: Request,
                   admin: dict = Depends(require_roles("admin", "manager"))):
    try:
        user_id = int(admin["sub"])
        cost_id = FinancialService.add_order_cost(order_id, req.cost_type, float(req.amount), req.note, user_id)
        from backend.modules.audit.audit_service import AuditService
        AuditService.record_audit("ADD_ORDER_COST", "order_costs", str(cost_id), user_id, admin.get("email"), admin.get("role"),
                                  new_value={"order_id": order_id, "cost_type": req.cost_type, "amount": float(req.amount), "note": req.note},
                                  ip_address=request.client.host if request.client else "")
        return {"success": True, "data": FinancialService.get_order_profit_detail(order_id)}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Không thể thêm khoản phí: {e}")


@router.put("/order-costs/{cost_id}")
def update_order_cost(cost_id: int, req: OrderCostRequest, request: Request,
                      admin: dict = Depends(require_roles("admin", "manager"))):
    try:
        old = FinancialService.update_order_cost(cost_id, req.cost_type, float(req.amount), req.note)
        from backend.modules.audit.audit_service import AuditService
        AuditService.record_audit("UPDATE_ORDER_COST", "order_costs", str(cost_id), int(admin["sub"]), admin.get("email"), admin.get("role"),
                                  old_value=old, new_value={"cost_type": req.cost_type, "amount": float(req.amount), "note": req.note},
                                  ip_address=request.client.host if request.client else "")
        return {"success": True, "data": FinancialService.get_order_profit_detail(old["order_id"])}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Không thể cập nhật khoản phí: {e}")


@router.put("/orders/{order_id}/fee-status")
def update_order_fee_status(order_id: int, req: OrderFeeStatusRequest, request: Request,
                            admin: dict = Depends(require_roles("admin", "manager"))):
    try:
        old_status = FinancialService.set_order_fee_status(order_id, req.status, int(admin["sub"]))
        from backend.modules.audit.audit_service import AuditService
        AuditService.record_audit("RECONCILE_ORDER_FEES", "orders", str(order_id), int(admin["sub"]), admin.get("email"), admin.get("role"),
                                  old_value={"fee_status": old_status}, new_value={"fee_status": req.status},
                                  ip_address=request.client.host if request.client else "")
        return {"success": True, "data": FinancialService.get_order_profit_detail(order_id)}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Không thể cập nhật trạng thái đối soát: {e}")
