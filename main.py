"""
==============================================================================
HỆ THỐNG PHÂN TÍCH DOANH THU & TỐI ƯU CHIẾN LƯỢC BÁN HÀNG TÍCH HỢP GEMINI AI
ENTRY POINT RUNNER (FORWARD TO BACKEND.MAIN)
==============================================================================
- Cho phép chạy trực tiếp từ thư mục gốc: python main.py
- Chuyển tiếp toàn bộ cấu hình tới backend/main.py
- Phục vụ frontend/ và backend/ theo chuẩn kiến trúc Feature-Based Modules
==============================================================================
"""

import os
import sys
from pathlib import Path

# Đảm bảo đường dẫn gốc nằm trong sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Nạp ứng dụng FastAPI từ backend.main
from backend.main import app

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "127.0.0.1")
    print(f"🔥 [System] Khởi chạy hệ thống tại: http://{host}:{port}")
    uvicorn.run("backend.main:app", host=host, port=port, reload=True)
