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

# Thiết lập UTF-8 chống lỗi font và emoji trên Windows console (cp1258/cp437)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Đảm bảo đường dẫn gốc nằm trong sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Nạp ứng dụng FastAPI từ backend.main
from backend.main import app


def free_port(port: int):
    """Tự động giải phóng cổng nếu có tiến trình cũ đang chiếm giữ trên Windows."""
    try:
        import subprocess
        out = subprocess.check_output(f'netstat -ano | findstr :{port}', shell=True, text=True, stderr=subprocess.DEVNULL)
        current_pid = os.getpid()
        for line in out.strip().splitlines():
            parts = line.split()
            if len(parts) >= 5 and "LISTENING" in parts:
                pid = int(parts[-1])
                if pid != current_pid and pid > 0:
                    subprocess.call(f'taskkill /PID {pid} /F', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    print(f"🧹 [System] Đã tự động giải phóng cổng {port} (tiến trình cũ PID: {pid})")
    except Exception:
        pass


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "127.0.0.1")
    
    # Giải phóng cổng cũ để chống lỗi WinError 10048 (Address already in use)
    free_port(port)

    # Trên Windows Python 3.14+, multiprocessing reload bị lỗi WinError 2 NamedPipe, chạy trực tiếp để ổn định 100%
    reload_flag = os.getenv("RELOAD", "false").lower() == "true"
    print(f"🔥 [System] Khởi chạy hệ thống tại: http://{host}:{port}")
    uvicorn.run("backend.main:app", host=host, port=port, reload=reload_flag)
