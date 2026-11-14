import json
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

from fastapi import APIRouter, HTTPException, Query, Depends, Header, Request
from pydantic import BaseModel
from typing import List, Optional
from backend.modules.ai.gemini_service import GeminiService
from backend.modules.auth.auth_router import require_roles, get_current_user, decode_access_token
from backend.modules.dashboard.analytics_service import AnalyticsService

router = APIRouter(prefix="/api/ai", tags=["AI Business Consultant"])


class CopilotChatRequest(BaseModel):
    message: str
    history: Optional[List[dict]] = []


class RevenuePlanRequest(BaseModel):
    target_revenue: float
    days: Optional[int] = 30


def get_optional_user(request: Request, authorization: Optional[str] = Header(None)) -> Optional[dict]:
    token = request.cookies.get("dacn_token")
    if not token and authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1]
    if not token:
        return None
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
        from backend.modules.dashboard.analytics_service import AnalyticsService
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


class MarketingCampaignRequest(BaseModel):
    product_id: Optional[int] = None
    product_name: str
    category: Optional[str] = "Bán lẻ"
    price: Optional[float] = 0
    target_audience: Optional[str] = None
    campaign_goal: Optional[str] = "sales_boost"
    tone: Optional[str] = "trendy"


@router.post("/marketing-campaign")
def generate_marketing_campaign(req: MarketingCampaignRequest, user: dict = Depends(require_roles("admin", "manager", "sales", "user"))):
    try:
        product_data = {
            "id": req.product_id,
            "name": req.product_name,
            "category": req.category,
            "price": req.price,
            "description": ""
        }
        if req.product_id:
            try:
                from backend.config.db import get_db_connection
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute("SELECT name, category, price, stock_quantity, description FROM products WHERE id = ?", (req.product_id,))
                row = cur.fetchone()
                if row:
                    product_data["name"] = row[0] or req.product_name
                    product_data["category"] = row[1] or req.category
                    product_data["price"] = float(row[2]) if row[2] else req.price
                    product_data["stock_quantity"] = row[3] or 0
                    product_data["description"] = row[4] or ""
                conn.close()
            except Exception:
                pass

        result = GeminiService.generate_marketing_campaign(
            product_data=product_data,
            target_audience=req.target_audience,
            campaign_goal=req.campaign_goal,
            tone=req.tone
        )

        # Lưu lịch sử chiến dịch vào CSDL
        try:
            from backend.config.db import get_db_connection
            conn = get_db_connection()
            cur = conn.cursor()
            user_id = int(user.get("sub", 1))
            title = result.get("campaign_title") or f"Chiến dịch {req.product_name}"
            metrics_context = json.dumps({
                "product_name": req.product_name,
                "price": req.price,
                "category": req.category,
                "goal": req.campaign_goal,
                "tone": req.tone
            }, ensure_ascii=False)
            ai_resp_str = json.dumps(result, ensure_ascii=False)
            cur.execute("""
                INSERT INTO ai_strategy_logs (title, strategy_type, user_prompt, ai_response, metrics_context, created_by)
                VALUES (?, 'marketing_studio', ?, ?, ?, ?)
            """, (title, req.product_name, ai_resp_str, metrics_context, user_id))
            conn.commit()
            conn.close()
        except Exception as log_err:
            print(f"⚠️ [Marketing History] Lỗi lưu CSDL: {log_err}")

        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/marketing-history")
def get_marketing_history(limit: int = Query(10, ge=1, le=50), user: dict = Depends(require_roles("admin", "manager", "sales", "user"))):
    try:
        from backend.config.db import DB_TYPE, get_db_connection
        conn = get_db_connection()
        cur = conn.cursor()
        user_role = (user.get("role") or "").lower()
        created_at_clause = "strftime('%Y-%m-%d %H:%M:%S', created_at) as created_at" if DB_TYPE != "mssql" else "CONVERT(VARCHAR(19), created_at, 120) as created_at"
        if user_role in ["admin", "manager"]:
            cur.execute(f"""
                SELECT id, title, user_prompt, ai_response, metrics_context, {created_at_clause}
                FROM ai_strategy_logs
                WHERE strategy_type = 'marketing_studio'
                ORDER BY id DESC
                {('LIMIT ? OFFSET 0' if DB_TYPE != 'mssql' else 'OFFSET 0 ROWS FETCH NEXT ? ROWS ONLY')}
            """, (limit,))
        else:
            uid = int(user.get("sub", 1))
            cur.execute(f"""
                SELECT id, title, user_prompt, ai_response, metrics_context, {created_at_clause}
                FROM ai_strategy_logs
                WHERE strategy_type = 'marketing_studio' AND created_by = ?
                ORDER BY id DESC
                {('LIMIT ? OFFSET 0' if DB_TYPE != 'mssql' else 'OFFSET 0 ROWS FETCH NEXT ? ROWS ONLY')}
            """, (uid, limit))
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        for r in rows:
            if isinstance(r.get("ai_response"), str):
                try:
                    r["ai_response"] = json.loads(r["ai_response"])
                except Exception:
                    pass
            if isinstance(r.get("metrics_context"), str):
                try:
                    r["metrics_context"] = json.loads(r["metrics_context"])
                except Exception:
                    pass
        return {"success": True, "data": rows}
    except Exception as e:
        print(f"⚠️ [Marketing History Error]: {e}")
        return {"success": True, "data": []}


@router.delete("/marketing-history/{history_id}")
def delete_marketing_history(history_id: int, user: dict = Depends(require_roles("admin", "manager", "sales", "user"))):
    try:
        from backend.config.db import get_db_connection
        conn = get_db_connection()
        cur = conn.cursor()
        user_role = (user.get("role") or "").lower()
        if user_role in ["admin", "manager"]:
            cur.execute("DELETE FROM ai_strategy_logs WHERE id = ? AND strategy_type = 'marketing_studio'", (history_id,))
        else:
            uid = int(user.get("sub", 1))
            cur.execute("DELETE FROM ai_strategy_logs WHERE id = ? AND strategy_type = 'marketing_studio' AND created_by = ?", (history_id, uid))
        conn.commit()
        conn.close()
        return {"success": True, "message": "Đã xóa bản ghi lịch sử."}
    except Exception as e:
        return {"success": False, "message": str(e)}

