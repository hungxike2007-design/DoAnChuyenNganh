"""
==============================================================================
ROUTER CỐ VẤN KINH DOANH GEMINI AI (AI ROUTER - FASTAPI)
==============================================================================
Các Endpoint:
- POST /api/ai/executive-summary: AI tóm tắt hiệu suất & phát hiện bất thường
- POST /api/ai/strategy: AI gợi ý chiến lược giá động & Combo sản phẩm
- POST /api/ai/copilot: Khung chat hỏi đáp AI theo thời gian thực
- GET  /api/ai/history: Xem lại lịch sử các báo cáo và khuyến nghị AI
==============================================================================
"""

from fastapi import APIRouter, HTTPException, Query, Depends, Header
from pydantic import BaseModel
from typing import List, Optional
from services.gemini_service import GeminiService
from routers.auth_router import require_roles, get_current_user, decode_access_token

router = APIRouter(prefix="/api/ai", tags=["AI Business Consultant"])


class CopilotChatRequest(BaseModel):
    message: str
    history: Optional[List[dict]] = []


class RevenuePlanRequest(BaseModel):
    target_revenue: float
    days: Optional[int] = 30


def get_optional_user(authorization: Optional[str] = Header(None)) -> Optional[dict]:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.split(" ")[1]
    try:
        return decode_access_token(token)
    except Exception:
        return None


@router.post("/executive-summary")
def get_executive_summary(user: dict = Depends(require_roles("admin", "manager", "sales"))):
    try:
        target_user_id = None if user.get("role") == "admin" else int(user["sub"])
        result = GeminiService.generate_executive_summary(user_id=target_user_id)
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/strategy")
def get_strategy(user: dict = Depends(require_roles("admin", "manager", "sales"))):
    try:
        target_user_id = None if user.get("role") == "admin" else int(user["sub"])
        result = GeminiService.generate_pricing_and_bundle_strategy(user_id=target_user_id)
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/planning-baseline")
def get_planning_baseline(days: int = Query(30, ge=7, le=180), user: dict = Depends(require_roles("admin", "manager", "sales"))):
    try:
        from services.analytics_service import AnalyticsService
        target_user_id = None if user.get("role") == "admin" else int(user["sub"])
        data = AnalyticsService.get_planning_baseline(days, user_id=target_user_id)
        return {"success": True, "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/revenue-plan")
def get_revenue_plan(req: RevenuePlanRequest, user: dict = Depends(require_roles("admin", "manager", "sales"))):
    try:
        if req.target_revenue <= 0:
            raise HTTPException(status_code=400, detail="Mục tiêu doanh thu phải lớn hơn 0 VNĐ.")
        target_user_id = None if user.get("role") == "admin" else int(user["sub"])
        result = GeminiService.generate_revenue_goal_plan(
            target_revenue=req.target_revenue,
            days=req.days or 30,
            user_id=target_user_id
        )
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/copilot")
def chat_with_copilot(req: CopilotChatRequest, user: Optional[dict] = Depends(get_optional_user)):
    try:
        if not req.message.strip():
            raise HTTPException(status_code=400, detail="Vui lòng nhập nội dung câu hỏi.")
        
        chat_user_id = None
        analytics_user_id = None
        if user and "sub" in user:
            chat_user_id = int(user["sub"])
            # Admin phân tích số liệu toàn hệ thống (None), Sales phân tích số liệu của riêng họ
            analytics_user_id = None if user.get("role") == "admin" else chat_user_id

        result = GeminiService.chat_copilot(
            user_query=req.message,
            history=req.history,
            analytics_user_id=analytics_user_id,
            chat_user_id=chat_user_id
        )
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/copilot/history")
def get_copilot_history(user: dict = Depends(get_current_user)):
    try:
        user_id = int(user["sub"])
        history = GeminiService.get_chat_history(user_id=user_id)
        return {"success": True, "data": history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/copilot/history")
def clear_copilot_history(user: dict = Depends(get_current_user)):
    try:
        user_id = int(user["sub"])
        GeminiService.clear_chat_history(user_id=user_id)
        return {"success": True, "message": "Đã xóa toàn bộ lịch sử chat."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
def get_ai_history(limit: int = Query(10, ge=1, le=50), user: Optional[dict] = Depends(get_optional_user)):
    target_user_id = None
    if user and "sub" in user:
        target_user_id = None if user.get("role") == "admin" else int(user["sub"])
    data = GeminiService.get_strategy_history(limit, user_id=target_user_id)
    return {"success": True, "data": data}
