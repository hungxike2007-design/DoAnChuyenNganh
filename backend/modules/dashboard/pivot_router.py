"""
==============================================================================
ROUTER PHÂN TÍCH DOANH THU ĐA CHIỀU (PIVOT TABLE ROUTER - FASTAPI)
==============================================================================
Các Endpoint:
- GET  /api/analytics/pivot/metadata: Lấy danh mục các chiều & chỉ số hỗ trợ
- POST /api/analytics/pivot/matrix: Tạo ma trận Heatmap Pivot 2 chiều động
- POST /api/analytics/pivot/ai-insight: Gọi Gemini AI phân tích ma trận
==============================================================================
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

from backend.modules.dashboard.pivot_service import PivotService
from backend.modules.auth.auth_router import require_roles

router = APIRouter(prefix="/api/analytics/pivot", tags=["Dynamic Pivot Analytics"])


class PivotMatrixRequest(BaseModel):
    row_dimension: str = Field("channel", description="Mã chiều trục dòng")
    col_dimension: str = Field("category", description="Mã chiều trục cột")
    metric: str = Field("total_revenue", description="Chỉ số đo lường")
    days: Optional[int] = Field(90, ge=1, le=720, description="Khoảng thời gian phân tích (ngày)")
    status_filter: Optional[str] = Field("completed", description="Trạng thái đơn hàng (completed / all)")


class PivotAiInsightRequest(BaseModel):
    pivot_data: Dict[str, Any]


@router.get("/metadata")
def get_pivot_metadata(
    current_user: dict = Depends(require_roles("admin", "manager", "sales", "user"))
):
    """Lấy danh sách các chiều dữ liệu và chỉ số đo lường hỗ trợ xoay ma trận."""
    return {
        "success": True,
        "data": PivotService.get_supported_metadata()
    }


@router.post("/matrix")
def generate_pivot_matrix(
    req: PivotMatrixRequest,
    current_user: dict = Depends(require_roles("admin", "manager", "sales", "user"))
):
    """
    Tạo ma trận Pivot 2 chiều kết hợp tính tổng hàng, tổng cột và min/max heatmap.
    Hỗ trợ mọi vai trò người dùng (Admin, Manager, Sales, User).
    """
    if req.row_dimension == req.col_dimension:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Trục dòng và trục cột không được trùng nhau để đảm bảo phân tích ma trận 2 chiều chính xác."
        )

    try:
        user_id = current_user.get("user_id") or current_user.get("sub")
        if user_id is not None:
            try:
                user_id = int(user_id)
            except (ValueError, TypeError):
                user_id = None

        role = (current_user.get("role") or "user").lower()

        data = PivotService.generate_pivot_matrix(
            row_dim=req.row_dimension,
            col_dim=req.col_dimension,
            metric=req.metric,
            days=req.days or 90,
            status=req.status_filter or "completed",
            user_id=user_id,
            role=role
        )
        return {"success": True, "data": data}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi xử lý ma trận đa chiều: {str(e)}"
        )


@router.post("/ai-insight")
def get_ai_insight(
    req: PivotAiInsightRequest,
    current_user: dict = Depends(require_roles("admin", "manager", "sales", "user"))
):
    """Gửi bảng dữ liệu ma trận sang Google Gemini AI để tự động phát hiện quy luật và đề xuất chiến lược."""
    try:
        insight = PivotService.get_ai_insight(req.pivot_data)
        return {"success": True, "data": insight}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi Gemini AI phân tích ma trận: {str(e)}"
        )

