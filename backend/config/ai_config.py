"""
==============================================================================
FILE CẤU HÌNH & KHỞI TẠO GOOGLE GEMINI AI API (PYTHON)
==============================================================================
Chức năng chính:
- Đọc an toàn GEMINI_API_KEY từ file .env (thông qua python-dotenv).
- Khởi tạo client Google GenAI chính thức (google-genai SDK).
- Đảm bảo an toàn: File .env đã được cấu hình trong .gitignore,
  khi push code lên GitHub, key không bao giờ bị lộ ra ngoài.
- Tự động kiểm tra trạng thái cấu hình và cung cấp chế độ phản hồi dự phòng (Fallback)
  để bảo vệ buổi thuyết trình đồ án không bị crash khi chưa kịp gán API key.
==============================================================================
"""

import os
import sys
import re
from pathlib import Path
from dotenv import load_dotenv

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Tìm và nạp file .env từ thư mục gốc
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(ROOT_DIR / ".env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
raw_model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash").strip()
# Tự động thay thế nếu dùng model cũ đã ngừng hỗ trợ (như gemini-2.5-flash)
if raw_model in ("gemini-2.5-flash", "gemini-1.5-flash", ""):
    GEMINI_MODEL = "gemini-3.5-flash"
else:
    GEMINI_MODEL = raw_model

client = None
is_ai_ready = False

# Kiểm tra xem API Key đã được người dùng gán hay chưa
if GEMINI_API_KEY and GEMINI_API_KEY != "YOUR_GEMINI_API_KEY_HERE":
    try:
        from google import genai
        client = genai.Client(api_key=GEMINI_API_KEY)
        is_ai_ready = True
        print(f"✨ [AI Config] Khởi tạo Google Gemini Client thành công! (Model: {GEMINI_MODEL})")
    except Exception as e:
        print(f"⚠️ [AI Config] Lỗi khi khởi tạo Google GenAI Client: {e}", file=sys.stderr)
else:
    print("\n" + "=" * 68)
    print("⚠️  CẢNH BÁO: CHƯA CẤU HÌNH GEMINI_API_KEY TRONG FILE .env!")
    print("👉 Hãy mở file .env và điền API Key lấy miễn phí tại: https://aistudio.google.com/")
    print("👉 Hệ thống sẽ tạm dùng Mock AI Consultant để đảm bảo bạn vẫn test được giao diện.")
    print("=" * 68 + "\n")


def clean_ai_text(text: str) -> str:
    """Xóa bỏ các dấu tiêu đề ###, ####, ##, # khỏi kết quả do AI sinh ra."""
    if not text:
        return ""
    # Xóa các dấu ###, ####, ##, # ở đầu dòng hoặc trước tiêu đề
    cleaned = re.sub(r'#{1,6}\s*', '', text)
    return cleaned.strip()


def generate_ai_response(prompt: str, system_instruction: str = "") -> str:
    """
    Gọi API Gemini để phân tích dữ liệu và đề xuất chiến lược kinh doanh.
    Có cơ chế tự động thử model dự phòng (Fallback) nếu model chính gặp lỗi (404/503/quá tải).
    """
    if is_ai_ready and client is not None:
        # Danh sách model theo thứ tự ưu tiên
        candidate_models = [GEMINI_MODEL]
        for fallback in ["gemini-3.5-flash", "gemini-3.1-flash-lite"]:
            if fallback not in candidate_models:
                candidate_models.append(fallback)

        last_error = None
        for model_name in candidate_models:
            try:
                config = {}
                if system_instruction:
                    config["system_instruction"] = system_instruction
                    
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=config if config else None
                )
                if response and response.text:
                    return clean_ai_text(response.text)
            except Exception as e:
                last_error = e
                print(f"⚠️ [Gemini Model Fallback] Model '{model_name}' gặp lỗi: {e}. Đang thử model tiếp theo...", file=sys.stderr)
                continue

        print(f"❌ [Gemini API Error - Tất cả model thất bại]: {last_error}", file=sys.stderr)
        raise RuntimeError(f"Lỗi khi gọi Google Gemini API: {str(last_error)}")

    # Phản hồi mô phỏng thông minh cho đồ án (khi chưa gán key)
    return (
        "💡 [PHÂN TÍCH MẪU TỪ HỆ THỐNG - Vui lòng nhập GEMINI_API_KEY vào .env để kích hoạt AI trực tiếp]:\n\n"
        "1. **Đánh giá hiệu suất:** Kênh TikTok Shop và Shopee đang dẫn đầu doanh số với hơn 65% thị phần. "
        "Tỷ lệ hoàn/hủy đơn đạt 2.8% (mức rất an toàn).\n"
        "2. **Cảnh báo tồn kho:** Nhóm hàng 'Thời trang' có tốc độ quay vòng tốt, trong khi nhóm 'Đồ gia dụng' "
        "đang có 3 sản phẩm tồn kho vượt quá 45 ngày.\n"
        "3. **Đề xuất chiến lược tối ưu:**\n"
        "   - Tạo Combo: Ghép Nồi chiên không dầu + Máy xay sinh tố với mức chiết khấu 12% để kích cầu xả hàng.\n"
        "   - Chiến lược giá: Áp dụng chương trình Flash Sale vào khung giờ 19h - 22h cuối tuần trên TikTok Live."
    )
