"""
==============================================================================
DỊCH VỤ CỐ VẤN KINH DOANH GEMINI AI (GEMINI AI SERVICE - PYTHON)
==============================================================================
Tích hợp Google GenAI SDK để thực hiện 3 nghiệp vụ cốt lõi:
1. Tự động tóm tắt hiệu suất kinh doanh (Executive Briefing & Anomaly Detection).
2. Đề xuất chiến lược giá, Combo bán kèm và Flash Sale xả hàng tồn kho.
3. Trợ lý AI Copilot trả lời mọi câu hỏi về tình hình doanh nghiệp.
==============================================================================
"""

import json
from config.ai_config import generate_ai_response, is_ai_ready, GEMINI_MODEL
from config.db import get_db_connection
from services.analytics_service import AnalyticsService


class GeminiService:
    @staticmethod
    def generate_executive_summary(user_id: int = None) -> dict:
        context = AnalyticsService.get_context_for_ai()
        kpis = context["kpis"]
        channels = context["channels"]
        top_products = context["top_products"]

        system_instruction = (
            "Bạn là Giám đốc Phân tích Dữ liệu và Cố vấn Chiến lược Kinh doanh cao cấp. "
            "Hãy đọc báo cáo số liệu thực tế được cung cấp và đưa ra bản tóm tắt chiến lược chuyên nghiệp, "
            "ngắn gọn, mạch lạc bằng Tiếng Việt với định dạng Markdown."
        )

        prompt = f"""
Dưới đây là số liệu kinh doanh thực tế trích xuất từ cơ sở dữ liệu hệ thống:
- Tổng doanh thu (60 ngày qua): {kpis['totalRevenue']:,.0f} VNĐ
- Lợi nhuận gộp: {kpis['grossProfit']:,.0f} VNĐ (Tỷ suất lợi nhuận: {kpis['profitMargin']}%)
- Tổng số đơn hàng: {kpis['totalOrders']} (Số đơn thành công: {kpis['completedOrders']}, Tỷ lệ hủy/hoàn: {kpis['cancelRate']}%)
- Giá trị trung bình đơn (AOV): {kpis['aov']:,.0f} VNĐ

Thống kê theo kênh bán hàng:
{json.dumps(channels, ensure_ascii=False, indent=2)}

Top 5 sản phẩm bán chạy nhất:
{json.dumps(top_products, ensure_ascii=False, indent=2)}

Hãy phân tích theo cấu trúc sau:
1. 🌟 **Điểm sáng kinh doanh:** Những chỉ số hoặc kênh bán hàng hoạt động xuất sắc nhất.
2. ⚠️ **Rủi ro & Điểm nghẽn cần khắc phục:** Cảnh báo về tỷ lệ hủy, sản phẩm biên lợi nhuận thấp hoặc kênh hoạt động kém.
3. 🚀 **3 Hành động cụ thể (Action Items):** Đưa ra 3 khuyến nghị hành động ngay trong tuần tới để tăng 15% doanh thu.
"""

        ai_text = generate_ai_response(prompt, system_instruction)

        # Lưu lại vào DB để tra cứu lịch sử
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO ai_strategy_logs (title, strategy_type, user_prompt, ai_response, metrics_context, created_by)
            VALUES (?, 'summary', ?, ?, ?, ?)
        """, (
            "Báo cáo Đánh giá Hiệu suất Kinh doanh Tổng quan",
            "Yêu cầu AI tóm tắt hiệu suất 60 ngày gần nhất",
            ai_text,
            json.dumps({"kpis": kpis, "channels": channels}, ensure_ascii=False),
            user_id
        ))
        conn.commit()
        log_id = cursor.lastrowid
        conn.close()

        return {
            "id": log_id,
            "title": "Báo cáo Đánh giá Hiệu suất Kinh doanh Tổng quan",
            "content": ai_text,
            "isLiveAI": is_ai_ready,
            "model": GEMINI_MODEL
        }

    @staticmethod
    def generate_pricing_and_bundle_strategy(user_id: int = None) -> dict:
        context = AnalyticsService.get_context_for_ai()
        alerts = context["inventory_alerts"]
        top_products = context["top_products"]

        system_instruction = (
            "Bạn là Chuyên gia Tối ưu Giá (Dynamic Pricing) và Chiến lược Giỏ hàng (Cross-sell/Up-sell). "
            "Mục tiêu là tối đa hóa lợi nhuận và giải phóng hàng tồn kho mà không làm tổn hại hình ảnh thương hiệu."
        )

        prompt = f"""
Dữ liệu kho hàng hiện tại:
- Danh sách sản phẩm tồn kho cần đẩy mạnh xả hàng hoặc đang bán chậm:
{json.dumps(alerts, ensure_ascii=False, indent=2)}

- Danh sách sản phẩm bán chạy nhất (Best-sellers):
{json.dumps(top_products, ensure_ascii=False, indent=2)}

Hãy xây dựng chiến lược tối ưu:
1. 🎯 **Gợi ý 2 gói Combo (Cross-sell Bundles):** Ghép 1 sản phẩm bán chạy với 1 sản phẩm bán chậm, nêu rõ tỷ lệ giảm giá đề xuất (ví dụ: Giảm 12% khi mua combo) và lý do khách hàng sẽ mua.
2. 🏷️ **Chiến lược Dynamic Pricing (Giá linh hoạt):** Đề xuất mức giá khuyến mãi tối ưu cho sản phẩm tồn kho sao cho vẫn giữ được biên lợi nhuận trên giá vốn (COGS).
3. ⏱️ **Kế hoạch Flash Sale:** Khung giờ vàng và kênh bán hàng phù hợp nhất để kích hoạt chương trình.
"""

        ai_text = generate_ai_response(prompt, system_instruction)

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO ai_strategy_logs (title, strategy_type, user_prompt, ai_response, metrics_context, created_by)
            VALUES (?, 'pricing', ?, ?, ?, ?)
        """, (
            "Chiến lược Giá Động & Gợi ý Combo Tối Ưu Tồn Kho",
            "Yêu cầu AI đề xuất Dynamic Pricing và Combo Bundles",
            ai_text,
            json.dumps({"alerts": alerts, "top_products": top_products}, ensure_ascii=False),
            user_id
        ))
        conn.commit()
        log_id = cursor.lastrowid
        conn.close()

        return {
            "id": log_id,
            "title": "Chiến lược Giá Động & Gợi ý Combo Tối Ưu Tồn Kho",
            "content": ai_text,
            "isLiveAI": is_ai_ready,
            "model": GEMINI_MODEL
        }

    @staticmethod
    def chat_copilot(user_query: str, history: list = None, user_id: int = None) -> dict:
        context = AnalyticsService.get_context_for_ai()
        kpis = context["kpis"]

        system_instruction = f"""
Bạn là Trợ lý AI Phân tích Doanh thu & Tối ưu Chiến lược (AI Business Copilot).
Bạn có quyền truy cập trực tiếp vào số liệu thực tế của cửa hàng:
- Tổng doanh thu 60 ngày qua: {kpis['totalRevenue']:,.0f} VNĐ
- Lợi nhuận gộp: {kpis['grossProfit']:,.0f} VNĐ ({kpis['profitMargin']}%)
- Đơn hàng: {kpis['totalOrders']} đơn ({kpis['completedOrders']} thành công)
- AOV: {kpis['aov']:,.0f} VNĐ

Nhiệm vụ: Trả lời ngắn gọn, thực tế, dựa trên số liệu của cửa hàng, xưng hô lịch thiệp, hỗ trợ người quản lý ra quyết định kinh doanh chuẩn xác.
"""

        history_text = ""
        if history:
            for item in history[-4:]:
                history_text += f"{item.get('sender', 'user')}: {item.get('message', '')}\n"

        prompt = f"""
Lịch sử trao đổi gần nhất:
{history_text}

Người dùng hỏi: "{user_query}"
"""

        ai_text = generate_ai_response(prompt, system_instruction)

        return {
            "reply": ai_text,
            "isLiveAI": is_ai_ready,
            "model": GEMINI_MODEL
        }

    @staticmethod
    def get_strategy_history(limit: int = 10) -> list:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, title, strategy_type, ai_response, created_at 
            FROM ai_strategy_logs 
            ORDER BY id DESC
            OFFSET 0 ROWS FETCH NEXT ? ROWS ONLY
        """, (limit,))
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows
