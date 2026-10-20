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
from pathlib import Path
from dotenv import load_dotenv

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Tìm và nạp file .env từ thư mục gốc
ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()

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


def generate_ai_response(prompt: str, system_instruction: str = "") -> str:
    """
    Gọi API Gemini để phân tích dữ liệu và đề xuất chiến lược kinh doanh.
    Có cơ chế dự phòng thông minh nếu chưa có API key.
    """
    if is_ai_ready and client is not None:
        try:
            config = {}
            if system_instruction:
                config["system_instruction"] = system_instruction
                
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config=config if config else None
            )
            return response.text
        except Exception as e:
            print(f"❌ [Gemini API Error]: {e}", file=sys.stderr)
            raise RuntimeError(f"Lỗi khi gọi Google Gemini API: {str(e)}")

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
