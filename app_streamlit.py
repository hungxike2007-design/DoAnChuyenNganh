"""
==============================================================================
ỨNG DỤNG PHÂN TÍCH DOANH THU & TỐI ƯU CHIẾN LƯỢC BÁN HÀNG TÍCH HỢP GEMINI AI
GIAO DIỆN 100% PYTHON THUẦN (STREAMLIT & PLOTLY)
==============================================================================
- Không sử dụng bất kỳ một dòng code JavaScript nào!
- Toàn bộ giao diện, biểu đồ, bảng dữ liệu, chatbox AI đều viết bằng Python.
- Kết nối trực tiếp tới Microsoft SQL Server (Server: TOM, Database: RevenueSystemDB).
- Chạy với lệnh: streamlit run app_streamlit.py
==============================================================================
"""

import sys
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

ROOT_DIR = Path(__file__).resolve().parent
load_dotenv(ROOT_DIR / ".env")

from services.auth_service import AuthService
from services.analytics_service import AnalyticsService
from services.gemini_service import GeminiService
from config.ai_config import is_ai_ready, GEMINI_MODEL

# Cấu hình trang Streamlit
st.set_page_config(
    page_title="Hệ Thống Phân Tích Doanh Thu AI",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Khởi tạo Session State cho Authentication & Chat
if "user" not in st.session_state:
    st.session_state.user = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = [
        {"sender": "assistant", "message": "Xin chào! Tôi là **AI Business Copilot** kết nối trực tiếp với CSDL SQL Server của bạn. Bạn có thể hỏi tôi bất kỳ câu hỏi nào về doanh thu, kênh bán hoặc chiến lược tăng trưởng!"}
    ]
if "auth_mode" not in st.session_state:
    st.session_state.auth_mode = "login"


def format_vnd(amount):
    """Định dạng tiền tệ VNĐ."""
    try:
        return f"{amount:,.0f} ₫".replace(",", ".")
    except Exception:
        return "0 ₫"


# ==============================================================================
# 1. GIAO DIỆN XÁC THỰC (ĐĂNG NHẬP, ĐĂNG KÝ, QUÊN MẬT KHẨU)
# ==============================================================================
def render_auth_page():
    col1, col2, col3 = st.columns([1, 1.8, 1])
    with col2:
        st.markdown("<h2 style='text-align: center; color: #6366f1;'>📈 REVENUE AI SYSTEM</h2>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #888;'>Hệ Thống Phân Tích Doanh Thu & Cố Vấn Bán Hàng Thông Minh</p>", unsafe_allow_html=True)
        st.divider()

        # Chọn chế độ: Đăng nhập / Đăng ký / Quên mật khẩu
        tabs = st.tabs(["🔑 Đăng Nhập", "📝 Đăng Ký Tài Khoản", "❓ Quên Mật Khẩu"])

        # TAB 1: ĐĂNG NHẬP
        with tabs[0]:
            st.subheader("Đăng Nhập Hệ Thống")
            email = st.text_input("Email", placeholder="admin@dacn.vn", key="login_email")
            password = st.text_input("Mật khẩu", type="password", key="login_pass")

            col_btn, col_demo = st.columns([1, 2])
            with col_btn:
                if st.button("Đăng Nhập", type="primary", use_container_width=True):
                    try:
                        res = AuthService.login_user(email, password)
                        st.session_state.user = res["user"]
                        st.success("Đăng nhập thành công!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Lỗi: {e}")

            with col_demo:
                st.caption("💡 Tài khoản mẫu thử nhanh (Pass: 123456):")
                sub1, sub2, sub3 = st.columns(3)
                if sub1.button("Admin", use_container_width=True):
                    res = AuthService.login_user("admin@dacn.vn", "123456")
                    st.session_state.user = res["user"]
                    st.rerun()
                if sub2.button("Manager", use_container_width=True):
                    res = AuthService.login_user("manager@dacn.vn", "123456")
                    st.session_state.user = res["user"]
                    st.rerun()
                if sub3.button("Sales", use_container_width=True):
                    res = AuthService.login_user("sales@dacn.vn", "123456")
                    st.session_state.user = res["user"]
                    st.rerun()

        # TAB 2: ĐĂNG KÝ
        with tabs[1]:
            st.subheader("Tạo Tài Khoản Mới")
            reg_name = st.text_input("Họ và Tên", placeholder="Nguyễn Văn A", key="reg_name")
            reg_email = st.text_input("Email", placeholder="user@dacn.vn", key="reg_email")
            reg_role = st.selectbox("Vai trò", ["manager", "sales", "admin"], key="reg_role")
            reg_pass = st.text_input("Mật khẩu (Tối thiểu 6 ký tự)", type="password", key="reg_pass")
            reg_confirm = st.text_input("Xác nhận mật khẩu", type="password", key="reg_confirm")

            if st.button("Tạo Tài Khoản", type="primary", use_container_width=True):
                if reg_pass != reg_confirm:
                    st.warning("Mật khẩu xác nhận không khớp!")
                else:
                    try:
                        res = AuthService.register_user(reg_name, reg_email, reg_pass, reg_role)
                        st.session_state.user = res["user"]
                        st.success("Đăng ký thành công! Đang chuyển vào hệ thống...")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Lỗi: {e}")

        # TAB 3: QUÊN MẬT KHẨU
        with tabs[2]:
            st.subheader("Khôi Phục Mật Khẩu (OTP)")
            f_email = st.text_input("Nhập email đã đăng ký", placeholder="admin@dacn.vn", key="f_email")
            if st.button("Gửi Mã Xác Thực OTP", use_container_width=True):
                try:
                    res = AuthService.request_forgot_password(f_email)
                    st.success(f"Mã OTP đã tạo: **{res['demo_otp']}** (Có hiệu lực trong 15 phút)")
                    st.session_state.temp_otp = res['demo_otp']
                    st.session_state.temp_email = f_email
                except Exception as e:
                    st.error(f"Lỗi: {e}")

            st.markdown("---")
            st.markdown("##### Bước 2: Đặt lại mật khẩu mới")
            reset_email = st.text_input("Email xác nhận", value=st.session_state.get("temp_email", ""), key="r_email")
            reset_otp = st.text_input("Mã OTP (6 số)", value=st.session_state.get("temp_otp", ""), key="r_otp")
            new_pass = st.text_input("Mật khẩu mới", type="password", key="r_pass")
            if st.button("Xác Nhận Đổi Mật Khẩu", type="primary", use_container_width=True):
                try:
                    AuthService.reset_password(reset_email, reset_otp, new_pass)
                    st.success("Đổi mật khẩu thành công! Bạn có thể đăng nhập ngay.")
                except Exception as e:
                    st.error(f"Lỗi: {e}")


# ==============================================================================
# 2. BẢNG ĐIỀU KHIỂN DOANH THU (EXECUTIVE DASHBOARD)
# ==============================================================================
def render_dashboard():
    st.title("📊 Bảng Điều Khiển Doanh Thu & Hiệu Suất Đa Kênh")
    st.caption("Dữ liệu trực tiếp từ Microsoft SQL Server (Server: TOM • Database: RevenueSystemDB)")

    # Bộ lọc thời gian
    col_filter, col_time = st.columns([1, 3])
    with col_filter:
        days = st.selectbox("Khoảng thời gian phân tích:", [7, 30, 90, 180], index=3, format_func=lambda d: f"{d} Ngày gần nhất")

    # Lấy số liệu từ Analytics Service
    kpis = AnalyticsService.get_kpis(days)
    timeline_data = AnalyticsService.get_revenue_timeline(30 if days > 30 else days)
    channel_data = AnalyticsService.get_channel_breakdown(days)
    top_products = AnalyticsService.get_top_products(8)
    inventory_alerts = AnalyticsService.get_inventory_alerts(40)

    # 4 Thẻ KPI chính
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("💰 Doanh Thu Thuần", format_vnd(kpis["totalRevenue"]), f"{kpis['completedOrders']} đơn thành công")
    m2.metric("📈 Lợi Nhuận Gộp", format_vnd(kpis["grossProfit"]), f"Biên lợi nhuận: {kpis['profitMargin']}%")
    m3.metric("📦 Tổng Đơn Hàng", f"{kpis['totalOrders']:,}", f"Hủy: {kpis['cancelRate']}%")
    m4.metric("🎯 Giá Trị Đơn (AOV)", format_vnd(kpis["aov"]), "Trung bình / đơn")

    st.markdown("---")

    # 2 Biểu đồ: Xu hướng doanh thu & Kênh bán
    c1, c2 = st.columns([2, 1.2])

    with c1:
        st.subheader("📈 Xu Hướng Doanh Thu Theo Dòng Thời Gian")
        if timeline_data:
            df_timeline = pd.DataFrame(timeline_data)
            fig_timeline = px.area(
                df_timeline,
                x="date",
                y="revenue",
                title="Doanh thu hàng ngày (VNĐ)",
                labels={"date": "Ngày", "revenue": "Doanh thu (VNĐ)"},
                color_discrete_sequence=["#6366f1"]
            )
            fig_timeline.update_layout(template="plotly_dark", height=350, margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(fig_timeline, use_container_width=True)
        else:
            st.info("Chưa có dữ liệu chuỗi thời gian.")

    with c2:
        st.subheader("🛍️ Tỷ Trọng Theo Kênh Bán Hàng")
        if channel_data:
            df_channel = pd.DataFrame(channel_data)
            fig_channel = px.pie(
                df_channel,
                names="channel",
                values="total_revenue",
                hole=0.6,
                title="Cơ cấu doanh thu",
                color_discrete_sequence=px.colors.qualitative.Prism
            )
            fig_channel.update_layout(template="plotly_dark", height=350, margin=dict(l=10, r=10, t=40, b=10))
            st.plotly_chart(fig_channel, use_container_width=True)

    st.markdown("---")

    # 2 Bảng: Top sản phẩm & Cảnh báo tồn kho
    t1, t2 = st.columns([1.6, 1.2])

    with t1:
        st.subheader("🏆 Top Sản Phẩm Bán Chạy Nhất")
        if top_products:
            df_top = pd.DataFrame(top_products)[["name", "category_name", "total_sold", "total_revenue", "total_profit"]]
            df_top.columns = ["Sản Phẩm", "Danh Mục", "Số Lượng Bán", "Doanh Thu (VNĐ)", "Lợi Nhuận (VNĐ)"]
            df_top["Doanh Thu (VNĐ)"] = df_top["Doanh Thu (VNĐ)"].apply(format_vnd)
            df_top["Lợi Nhuận (VNĐ)"] = df_top["Lợi Nhuận (VNĐ)"].apply(format_vnd)
            st.dataframe(df_top, use_container_width=True, hide_index=True)

    with t2:
        st.subheader("⚠️ Cảnh Báo Tồn Kho Cần Xử Lý")
        if inventory_alerts:
            df_alert = pd.DataFrame(inventory_alerts)[["name", "stock_quantity", "selling_price"]]
            df_alert.columns = ["Sản Phẩm", "Tồn Kho", "Giá Bán (VNĐ)"]
            df_alert["Giá Bán (VNĐ)"] = df_alert["Giá Bán (VNĐ)"].apply(format_vnd)
            st.dataframe(df_alert, use_container_width=True, hide_index=True)


# ==============================================================================
# 3. PHÂN KHÚC KHÁCH HÀNG (RFM)
# ==============================================================================
def render_rfm_page():
    st.title("👥 Phân Tích Phân Khúc Khách Hàng (Mô Hình RFM)")
    st.caption("Phân loại tự động: Recency (Độ mới) - Frequency (Tần suất) - Monetary (Giá trị chi tiêu)")

    data = AnalyticsService.get_customer_segments()
    segments = data["segments"]
    top_customers = data["topCustomers"]

    # Hiển thị các card phân khúc
    st.subheader("Cơ Cấu Phân Khúc")
    cols = st.columns(len(segments))
    for idx, s in enumerate(segments):
        with cols[idx]:
            st.metric(
                label=f"Nhóm {s['segment']}",
                value=f"{s['customer_count']} Khách",
                delta=format_vnd(s['total_revenue'])
            )
            st.caption(f"Chi tiêu TB: {format_vnd(s['avg_spent'])}")

    st.markdown("---")

    # Bảng khách hàng tiêu biểu
    st.subheader("👑 Top 10 Khách Hàng Đóng Góp Doanh Thu Cao Nhất")
    if top_customers:
        df_cust = pd.DataFrame(top_customers)[["name", "email", "city", "segment", "orders_count", "total_spent"]]
        df_cust.columns = ["Tên Khách Hàng", "Email", "Tỉnh/Thành", "Phân Khúc", "Số Đơn Mua", "Tổng Chi Tiêu"]
        df_cust["Tổng Chi Tiêu"] = df_cust["Tổng Chi Tiêu"].apply(format_vnd)
        st.dataframe(df_cust, use_container_width=True, hide_index=True)


# ==============================================================================
# 4. TỐI ƯU CHIẾN LƯỢC BÁN HÀNG TÍCH HỢP GEMINI AI
# ==============================================================================
def render_ai_strategy_page():
    st.title("✨ Cố Vấn Tối Ưu Chiến Lược Bán Hàng (Google Gemini AI)")
    st.caption("AI tự động đào sâu cơ sở dữ liệu SQL Server và đề xuất các quyết sách tối ưu tăng trưởng")

    status_color = "green" if is_ai_ready else "orange"
    status_text = f"Đã kết nối trực tiếp với Google Gemini ({GEMINI_MODEL})" if is_ai_ready else "Chế độ Mô Phỏng Demo (Chưa gán GEMINI_API_KEY trong .env)"
    st.markdown(f":{status_color}[● {status_text}]")

    col_act1, col_act2 = st.columns(2)
    with col_act1:
        if st.button("📊 AI Phân Tích & Tóm Tắt Hiệu Suất Doanh Thu", type="primary", use_container_width=True):
            with st.spinner("Gemini AI đang tổng hợp số liệu SQL và xây dựng báo cáo..."):
                res = GeminiService.generate_executive_summary()
                st.session_state.ai_report = res

    with col_act2:
        if st.button("🏷️ AI Đề Xuất Giá Động (Dynamic Pricing) & Combo Xả Kho", use_container_width=True):
            with st.spinner("Gemini AI đang phân tích giỏ hàng và chu kỳ tồn kho..."):
                res = GeminiService.generate_pricing_and_bundle_strategy()
                st.session_state.ai_report = res

    # Hiển thị báo cáo AI vừa tạo
    if "ai_report" in st.session_state:
        st.markdown("---")
        st.subheader(f"📑 {st.session_state.ai_report['title']}")
        st.markdown(st.session_state.ai_report["content"])

    st.markdown("---")
    st.subheader("🕒 Lịch Sử Các Đề Xuất Chiến Lược Gần Nhất")
    history = GeminiService.get_strategy_history(5)
    for h in history:
        with st.expander(f"📌 {h['title']} ({h['created_at']})"):
            st.markdown(h["ai_response"])


# ==============================================================================
# 5. TRỢ LÝ AI BUSINESS COPILOT (CHAT 100% PYTHON)
# ==============================================================================
def render_copilot_page():
    st.title("💬 AI Business Copilot (Trợ Lý Phân Tích Dữ Liệu)")
    st.caption("Hỏi đáp trực tiếp bằng ngôn ngữ tự nhiên dựa trên số liệu thực tế từ SQL Server TOM")

    # Gợi ý câu hỏi nhanh
    st.markdown("##### 💡 Gợi ý câu hỏi nhanh:")
    g1, g2, g3 = st.columns(3)
    prompt_to_send = None
    if g1.button("Mặt hàng nào có tỷ suất lợi nhuận cao nhất?", use_container_width=True):
        prompt_to_send = "Mặt hàng nào có tỷ suất lợi nhuận cao nhất?"
    if g2.button("Tại sao doanh thu kênh TikTok Shop tăng mạnh?", use_container_width=True):
        prompt_to_send = "Tại sao doanh thu kênh TikTok Shop tăng mạnh?"
    if g3.button("Gợi ý combo xả kho cho hàng tồn lâu ngày?", use_container_width=True):
        prompt_to_send = "Gợi ý combo xả kho cho hàng tồn lâu ngày?"

    # Hiển thị lịch sử chat
    for chat in st.session_state.chat_history:
        with st.chat_message(chat["sender"]):
            st.markdown(chat["message"])

    # Xử lý nhập câu hỏi từ chat input
    user_input = st.chat_input("Hỏi AI về doanh thu, khách hàng, hàng tồn kho...") or prompt_to_send
    if user_input:
        st.session_state.chat_history.append({"sender": "user", "message": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):
            with st.spinner("Gemini AI đang suy luận từ cơ sở dữ liệu SQL..."):
                reply_data = GeminiService.chat_copilot(user_input, st.session_state.chat_history)
                st.markdown(reply_data["reply"])
                st.session_state.chat_history.append({"sender": "assistant", "message": reply_data["reply"]})


# ==============================================================================
# HÀM ĐIỀU HƯỚNG CHÍNH (MAIN APP)
# ==============================================================================
def main():
    if not st.session_state.user:
        render_auth_page()
    else:
        # Sidebar điều hướng
        with st.sidebar:
            st.markdown("### 📈 REVENUE AI")
            st.caption(f"Xin chào, **{st.session_state.user['full_name']}**")
            st.caption(f"Vai trò: `{st.session_state.user['role'].upper()}`")
            st.markdown("---")

            menu = st.radio(
                "Chức năng hệ thống:",
                [
                    "📊 Bảng Điều Khiển Doanh Thu",
                    "👥 Phân Khúc Khách Hàng (RFM)",
                    "✨ Tối Ưu Chiến Lược (Gemini AI)",
                    "💬 AI Business Copilot (Chat)"
                ]
            )

            st.markdown("---")
            if st.button("Đăng Xuất", use_container_width=True):
                st.session_state.user = None
                st.rerun()

        # Hiển thị trang tương ứng
        if menu == "📊 Bảng Điều Khiển Doanh Thu":
            render_dashboard()
        elif menu == "👥 Phân Khúc Khách Hàng (RFM)":
            render_rfm_page()
        elif menu == "✨ Tối Ưu Chiến Lược (Gemini AI)":
            render_ai_strategy_page()
        elif menu == "💬 AI Business Copilot (Chat)":
            render_copilot_page()


if __name__ == "__main__":
    main()
