"""
==============================================================================
ROUTER LẬP KẾ HOẠCH PHÂN BỔ MỤC TIÊU DOANH THU (PLANNER ROUTER - FASTAPI)
==============================================================================
Tách riêng các endpoint API cho bài toán Lập Kế Hoạch Kinh Doanh:
- GET  /api/planner/baseline: Lấy số liệu năng lực cơ sở 30-60 ngày
- POST /api/planner/generate: Phân rã mục tiêu doanh thu bằng Gemini AI
- GET  /api/planner/history: Xem lại các bản kế hoạch đã lập
==============================================================================
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field
from typing import Optional
try:
    from backend.modules.ai.planner_service import PlannerService
    from backend.modules.auth.auth_router import require_roles
except ImportError:
    from services.planner_service import PlannerService
    from routers.auth_router import require_roles

router = APIRouter(prefix="/api/planner", tags=["Revenue Goal Planner"])


class GeneratePlanRequest(BaseModel):
    target_revenue: float = Field(..., gt=0, description="Mục tiêu doanh thu (VNĐ)")
    days: Optional[int] = Field(30, ge=7, le=180, description="Chu kỳ kế hoạch (số ngày)")


@router.get("/baseline")
def get_planning_baseline(
    days: int = Query(30, ge=7, le=180),
    user: dict = Depends(require_roles("admin", "manager"))
):
    """Lấy số liệu thực tế từ cơ sở dữ liệu làm mốc cơ sở (baseline) để lập kế hoạch."""
    try:
        target_user_id = None if user.get("role") == "admin" else int(user["sub"])
        data = PlannerService.get_baseline_data(days, user_id=target_user_id)
        return {"success": True, "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi trích xuất số liệu cơ sở: {str(e)}")


@router.post("/generate")
def generate_revenue_plan(
    req: GeneratePlanRequest,
    user: dict = Depends(require_roles("admin", "manager"))
):
    """Kích hoạt mô hình phân rã mục tiêu và gọi Gemini AI lập lộ trình hành động 4 tuần."""
    try:
        target_user_id = None if user.get("role") == "admin" else int(user["sub"])
        result = PlannerService.generate_goal_plan(
            target_revenue=req.target_revenue,
            days=req.days or 30,
            user_id=target_user_id
        )
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi lập kế hoạch mục tiêu: {str(e)}")


@router.get("/history")
def get_plan_history(
    limit: int = Query(10, ge=1, le=50),
    user: dict = Depends(require_roles("admin", "manager"))
):
    """Xem lại danh sách các bản kế hoạch doanh thu đã lưu."""
    try:
        target_user_id = None if user.get("role") == "admin" else int(user["sub"])
        data = PlannerService.get_plan_history(limit, user_id=target_user_id)
        return {"success": True, "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi tải lịch sử kế hoạch: {str(e)}")
