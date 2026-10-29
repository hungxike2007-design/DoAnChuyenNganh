"""
==============================================================================
DỊCH VỤ LẬP KẾ HOẠCH & PHÂN BỔ MỤC TIÊU DOANH THU (PLANNER SERVICE - PYTHON)
==============================================================================
Tách riêng module xử lý nghiệp vụ Lập Kế Hoạch Kinh Doanh:
1. Trích xuất năng lực cơ sở thực tế từ CSDL SQL (Run-rate, AOV, Kênh bán, Tồn kho).
2. Mô hình hóa phân rã toán học (Goal Decomposition): Hạn mức 4 kênh & Số đơn cần đạt.
3. Prompt Engineering nâng cao cho Google Gemini AI đóng vai Giám đốc Chiến lược (CRO).
4. Lưu vết lịch sử kế hoạch phục vụ đối soát và báo cáo Ban Giám đốc.
==============================================================================
"""

import json
from datetime import datetime
try:
    from backend.config.db import get_db_connection
    from backend.config.ai_config import generate_ai_response, is_ai_ready, GEMINI_MODEL
    from backend.modules.dashboard.analytics_service import AnalyticsService
except ImportError:
    from config.db import get_db_connection
    from config.ai_config import generate_ai_response, is_ai_ready, GEMINI_MODEL
    from services.analytics_service import AnalyticsService


class PlannerService:
    @staticmethod
    def get_baseline_data(days: int = 30, user_id: int = None) -> dict:
        """Lấy dữ liệu cơ sở thực tế của doanh nghiệp phục vụ bài toán lập kế hoạch."""
        return AnalyticsService.get_planning_baseline(days, user_id=user_id)

    @staticmethod
    def generate_goal_plan(target_revenue: float, days: int = 30, user_id: int = None) -> dict:
        """
        Phân rã mục tiêu doanh thu bằng mô hình toán kinh tế kết hợp tư vấn chiến lược từ Gemini AI.
        """
        baseline = AnalyticsService.get_planning_baseline(days, user_id=user_id)
        baseline_rev = float(baseline.get("baselineRevenue", 0.0))
        current_aov = float(baseline.get("baselineAov", 0.0)) or 350000.0
        channels = baseline.get("channels", [])
        top_products = baseline.get("topProducts", [])
        inventory_alerts = baseline.get("inventoryAlerts", [])

        # 1. Tính toán định lượng cơ bản
        growth_rate = round(((target_revenue - baseline_rev) / baseline_rev) * 100, 1) if baseline_rev > 0 else 0.0
        target_aov = round(current_aov * 1.05)  # Kỳ vọng tăng 5% AOV qua kỹ thuật bán kèm combo
        required_orders = round(target_revenue / target_aov) if target_aov > 0 else 0
        daily_target = round(target_revenue / days) if days > 0 else 0

        # 2. Phân bổ hạn mức (Quota) cho 4 kênh bán lẻ dựa trên tỷ trọng lịch sử
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

        # 3. Xây dựng ngữ cảnh Prompt Engineering chuyên sâu
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

        # 4. Lưu lại vào CSDL để quản lý
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
    def get_plan_history(limit: int = 10, user_id: int = None) -> list:
        """Lấy danh sách các kế hoạch doanh thu đã lập gần đây."""
        conn = get_db_connection()
        cursor = conn.cursor()
        if user_id:
            cursor.execute("""
                SELECT id, title, strategy_type, ai_response, metrics_context, created_at
                FROM ai_strategy_logs
                WHERE strategy_type = 'goal_plan' AND created_by = ?
                ORDER BY id DESC
                OFFSET 0 ROWS FETCH NEXT ? ROWS ONLY
            """, (user_id, limit))
        else:
            cursor.execute("""
                SELECT id, title, strategy_type, ai_response, metrics_context, created_at
                FROM ai_strategy_logs
                WHERE strategy_type = 'goal_plan'
                ORDER BY id DESC
                OFFSET 0 ROWS FETCH NEXT ? ROWS ONLY
            """, (limit,))
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()

        for r in rows:
            if r.get("metrics_context"):
                try:
                    r["metrics_context"] = json.loads(r["metrics_context"])
                except Exception:
                    pass
        return rows
