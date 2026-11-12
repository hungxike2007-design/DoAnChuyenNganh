from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.modules.audit.audit_service import AuditService
from backend.modules.auth.auth_router import require_roles

router = APIRouter(prefix="/api/audit", tags=["Audit Logs"])


@router.get("/logs")
def list_audit_logs(limit: int = Query(50, ge=1, le=200), action: Optional[str] = None,
                    search: Optional[str] = None, from_date: Optional[str] = None,
                    to_date: Optional[str] = None, admin: dict = Depends(require_roles("admin"))):
    try:
        data = AuditService.get_audit_logs(limit, action, search, from_date, to_date)
        return {"success": True, "total": len(data), "data": data}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Không thể tải nhật ký kiểm toán: {exc}")


@router.get("/logs/{log_id}")
def get_audit_log_detail(log_id: int, admin: dict = Depends(require_roles("admin"))):
    data = AuditService.get_audit_log_detail(log_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy nhật ký kiểm toán.")
    return {"success": True, "data": data}
