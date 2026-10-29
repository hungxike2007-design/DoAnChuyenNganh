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
try:
    from backend.config.ai_config import generate_ai_response, is_ai_ready, GEMINI_MODEL
    from backend.config.db import get_db_connection
    from backend.modules.dashboard.analytics_service import AnalyticsService
except ImportError:
    from config.ai_config import generate_ai_response, is_ai_ready, GEMINI_MODEL
    from config.db import get_db_connection
    from services.analytics_service import AnalyticsService


class GeminiService:
    @staticmethod
    def generate_executive_summary(user_id: int = None) -> dict:
        context = AnalyticsService.get_context_for_ai(user_id=user_id)
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
        context = AnalyticsService.get_context_for_ai(user_id=user_id)
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
    def generate_revenue_goal_plan(target_revenue: float, days: int = 30, user_id: int = None) -> dict:
        baseline = AnalyticsService.get_planning_baseline(days, user_id=user_id)

        baseline_rev = float(baseline.get("baselineRevenue", 0.0))
        current_aov = float(baseline.get("baselineAov", 0.0)) or 350000.0
        channels = baseline.get("channels", [])
        top_products = baseline.get("topProducts", [])
        inventory_alerts = baseline.get("inventoryAlerts", [])

        growth_rate = round(((target_revenue - baseline_rev) / baseline_rev) * 100, 1) if baseline_rev > 0 else 0.0
        target_aov = round(current_aov * 1.05)
        required_orders = round(target_revenue / target_aov) if target_aov > 0 else 0
        daily_target = round(target_revenue / days) if days > 0 else 0

        # Phân bổ chỉ tiêu cho từng kênh theo tỷ trọng lịch sử
        channel_quotas = []
        for ch in channels:
            ch_name = ch.get("channel", "Khác")
            share = (ch.get("share_percent", 0.0) or 0.0) / 100.0
            ch_target_rev = round(target_revenue * share)
            ch_aov = ch.get("aov", 0) or target_aov
            ch_target_orders = round(ch_target_rev / ch_aov) if ch_aov > 0 else 0
            channel_quotas.append({
                "channel": ch_name,
                "sharePercent": ch.get("share_percent", 0.0),
                "targetRevenue": ch_target_rev,
                "targetOrders": ch_target_orders,
                "currentAov": ch_aov
            })

        system_instruction = (
            "Bạn là Giám đốc Chiến lược Doanh thu cấp cao (Chief Revenue Officer). "
            "Nhiệm vụ của bạn là lập kế hoạch phân rã mục tiêu doanh thu và xây dựng lộ trình hành động 4 tuần "
            "thực tế, có tính khả thi cao bằng Tiếng Việt với định dạng Markdown chuyên nghiệp."
        )

        prompt = f"""
Dưới đây là bài toán thiết lập mục tiêu kinh doanh cho chu kỳ {days} ngày tới:
- Doanh thu cơ sở (thực tế kỳ trước): {baseline_rev:,.0f} VNĐ
- Doanh thu mục tiêu đề ra: {target_revenue:,.0f} VNĐ (Tăng trưởng: {growth_rate:+.1f}%)
- Giá trị đơn hàng mục tiêu (Target AOV): {target_aov:,.0f} VNĐ (AOV hiện tại: {current_aov:,.0f} VNĐ)
- Tổng số đơn hàng thành công cần đạt: {required_orders:,} đơn (Trung bình: {daily_target:,.0f} VNĐ/ngày)

Phân bổ chỉ tiêu sơ bộ theo 4 kênh bán lẻ:
{json.dumps(channel_quotas, ensure_ascii=False, indent=2)}

Top 3 sản phẩm bán chạy nhất hiện tại:
{json.dumps(top_products[:3], ensure_ascii=False, indent=2)}

Danh sách sản phẩm tồn kho cần đẩy mạnh xả hàng:
{json.dumps(inventory_alerts[:3], ensure_ascii=False, indent=2)}

Hãy xây dựng bản Kế Hoạch Chiến Lược Phân Rã Mục Tiêu Doanh Thu theo cấu trúc sau:
1. 🎯 **Đánh giá Tính Khả Thi & Thách Thức (Feasibility Analysis):** Đánh giá mức tăng trưởng {growth_rate:+.1f}% có khả thi với nguồn lực hiện tại không và 2 thách thức lớn nhất cần giải quyết.
2. 📊 **Chiến Lược Phân Bổ Hạn Mức Kênh (Channel Allocation Strategy):** Hướng dẫn kênh nào nên tập trung tăng ngân sách ads, kênh nào nên dùng để chốt đơn AOV cao.
3. 📦 **Đòn Bẩy Sản Phẩm & Giải Phóng Vốn Tồn Kho (Product & Inventory Leverage):** Chiến lược bán kèm (Cross-sell/Bundle) giữa sản phẩm Best-seller và hàng tồn kho để vừa thu hồi vốn vừa đóng góp vào doanh thu mục tiêu.
4. 🚀 **Lộ Trình Hành Động 4 Tuần (4-Week Step-by-Step Action Roadmap):**
   - **Tuần 1 (Khởi động & Tái kích hoạt):** Hành động với tệp khách cũ RFM và chuẩn bị kho hàng.
   - **Tuần 2 (Tăng tốc & Kích cầu Combo):** Chiến dịch marketing đa kênh và gói combo kích AOV.
   - **Tuần 3 (Đợt sóng Mega Sale giữa kỳ):** Khung giờ vàng Flash sale và đẩy mạnh kênh TikTok/Shopee.
   - **Tuần 4 (Nước rút & Hoàn tất KPI):** Chăm sóc khách VIP, gọi lại giỏ hàng bỏ quên và đánh giá cán đích.
5. 🛡️ **Quản Trị Rủi Ro & Vòng Bảo Vệ An Toàn (Guardrails):** Cảnh báo tỷ lệ hủy đơn và nguyên tắc không giảm giá dưới giá vốn (COGS).
"""

        ai_text = generate_ai_response(prompt, system_instruction)

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO ai_strategy_logs (title, strategy_type, user_prompt, ai_response, metrics_context, created_by)
            VALUES (?, 'goal_plan', ?, ?, ?, ?)
        """, (
            f"Kế Hoạch Phân Bổ Mục Tiêu Doanh Thu: {target_revenue:,.0f} VNĐ",
            f"Mục tiêu {target_revenue:,.0f} VNĐ trong {days} ngày (Tăng trưởng: {growth_rate:+.1f}%)",
            ai_text,
            json.dumps({
                "targetRevenue": target_revenue,
                "baselineRevenue": baseline_rev,
                "growthRate": growth_rate,
                "requiredOrders": required_orders,
                "targetAov": target_aov,
                "dailyTarget": daily_target,
                "channelQuotas": channel_quotas
            }, ensure_ascii=False),
            user_id
        ))
        conn.commit()
        log_id = cursor.lastrowid
        conn.close()

        return {
            "id": log_id,
            "title": f"Kế Hoạch Phân Bổ Mục Tiêu Doanh Thu: {target_revenue:,.0f} VNĐ",
            "targetRevenue": target_revenue,
            "baselineRevenue": baseline_rev,
            "growthRate": growth_rate,
            "requiredOrders": required_orders,
            "targetAov": target_aov,
            "dailyTarget": daily_target,
            "days": days,
            "channelQuotas": channel_quotas,
            "content": ai_text,
            "isLiveAI": is_ai_ready,
            "model": GEMINI_MODEL
        }

    @staticmethod
    def chat_copilot(user_query: str, history: list = None, analytics_user_id: int = None, chat_user_id: int = None, user_id: int = None) -> dict:
        # Tương thích ngược: nếu truyền user_id cũ
        if chat_user_id is None and user_id is not None:
            chat_user_id = user_id
        if analytics_user_id is None and user_id is not None:
            analytics_user_id = user_id
        context = AnalyticsService.get_context_for_ai(user_id=analytics_user_id)
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

        # Lưu tin nhắn vào CSDL theo tài khoản người dùng
        if chat_user_id:
            try:
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute(
                    "INSERT INTO ai_chat_messages (user_id, sender, message) VALUES (?, 'user', ?)",
                    (chat_user_id, user_query)
                )
                cur.execute(
                    "INSERT INTO ai_chat_messages (user_id, sender, message) VALUES (?, 'assistant', ?)",
                    (chat_user_id, ai_text)
                )
                conn.commit()
                conn.close()
            except Exception as e:
                import sys
                print(f"⚠️ [Chat History] Lỗi khi lưu vào CSDL: {e}", file=sys.stderr)

        return {
            "reply": ai_text,
            "isLiveAI": is_ai_ready,
            "model": GEMINI_MODEL
        }

    @staticmethod
    def get_chat_history(user_id: int, limit: int = 100) -> list:
        if not user_id:
            return []
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("""
                SELECT TOP (?) id, sender, message, created_at 
                FROM ai_chat_messages 
                WHERE user_id = ? 
                ORDER BY id ASC
            """, (limit, user_id))
            rows = [dict(r) for r in cur.fetchall()]
            conn.close()
            return rows
        except Exception as e:
            import sys
            print(f"⚠️ [Chat History] Lỗi lấy lịch sử chat: {e}", file=sys.stderr)
            return []

    @staticmethod
    def clear_chat_history(user_id: int) -> bool:
        if not user_id:
            return False
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("DELETE FROM ai_chat_messages WHERE user_id = ?", (user_id,))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            import sys
            print(f"⚠️ [Chat History] Lỗi xóa lịch sử chat: {e}", file=sys.stderr)
            return False

    @staticmethod
    def get_strategy_history(limit: int = 10, user_id: int = None) -> list:
        conn = get_db_connection()
        cursor = conn.cursor()
        if user_id:
            cursor.execute("""
                SELECT id, title, strategy_type, ai_response, created_at 
                FROM ai_strategy_logs 
                WHERE created_by = ?
                ORDER BY id DESC
                OFFSET 0 ROWS FETCH NEXT ? ROWS ONLY
            """, (user_id, limit))
        else:
            cursor.execute("""
                SELECT id, title, strategy_type, ai_response, created_at 
                FROM ai_strategy_logs 
                ORDER BY id DESC
                OFFSET 0 ROWS FETCH NEXT ? ROWS ONLY
            """, (limit,))
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows

