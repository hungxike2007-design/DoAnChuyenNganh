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

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
from services.gemini_service import GeminiService

router = APIRouter(prefix="/api/ai", tags=["AI Business Consultant"])


class CopilotChatRequest(BaseModel):
    message: str
    history: Optional[List[dict]] = []


@router.post("/executive-summary")
def get_executive_summary():
    try:
        result = GeminiService.generate_executive_summary()
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/strategy")
def get_strategy():
    try:
        result = GeminiService.generate_pricing_and_bundle_strategy()
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/copilot")
def chat_with_copilot(req: CopilotChatRequest):
    try:
        if not req.message.strip():
            raise HTTPException(status_code=400, detail="Vui lòng nhập nội dung câu hỏi.")
        result = GeminiService.chat_copilot(req.message, req.history)
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
def get_ai_history(limit: int = Query(10, ge=1, le=50)):
    data = GeminiService.get_strategy_history(limit)
    return {"success": True, "data": data}
