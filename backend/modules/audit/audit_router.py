"""
==============================================================================
ROUTER NHẬT KÝ KIỂM TOÁN (AUDIT ROUTER - FASTAPI)
==============================================================================
Các Endpoint:
- GET  /api/audit/logs: Lấy danh sách nhật ký kiểm toán (Chỉ dành cho Admin)
- GET  /api/audit/logs/{id}: Lấy chi tiết một sự kiện kiểm toán kèm diff JSON
==============================================================================
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from typing import Optional
try:
    from backend.modules.auth.auth_router import require_roles
    from backend.modules.audit.audit_service import AuditService
except ImportError:
    from routers.auth_router import require_roles
    from services.audit_service import AuditService

router = APIRouter(prefix="/api/audit", tags=["Audit Trail & Activity Logs"])


@router.get("/logs")
def list_audit_logs(
    limit: int = Query(50, ge=1, le=200),
    action: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    from_date: Optional[str] = Query(None),
    to_date: Optional[str] = Query(None),
    admin: dict = Depends(require_roles("admin"))
):
    """
    Lấy danh sách các sự kiện kiểm toán hoạt động hệ thống.
    Chỉ duy nhất người dùng có quyền Quản trị viên (Admin) mới được truy cập.
    """
    try:
        logs = AuditService.get_audit_logs(
            limit=limit,
            action=action,
            search=search,
            from_date=from_date,
            to_date=to_date
        )
        return {
            "success": True,
            "total": len(logs),
            "data": logs
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi truy xuất nhật ký kiểm toán: {str(e)}")


@router.get("/logs/{log_id}")
def get_audit_log_detail(
    log_id: int,
    admin: dict = Depends(require_roles("admin"))
):
    """Lấy chi tiết một bản ghi kiểm toán kèm dữ liệu đối chiếu cũ và mới."""
    log = AuditService.get_audit_log_detail(log_id)
    if not log:
        raise HTTPException(status_code=404, detail="Không tìm thấy bản ghi kiểm toán.")
    return {
        "success": True,
        "data": log
    }
