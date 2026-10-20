"""
==============================================================================
HỆ THỐNG PHÂN TÍCH DOANH THU & TỐI ƯU CHIẾN LƯỢC BÁN HÀNG TÍCH HỢP GEMINI AI
ENTRY POINT CHÍNH (FASTAPI MAIN APPLICATION)
==============================================================================
- Chạy với: python main.py hoặc uvicorn main:app --reload
- Tự động nạp CSDL SQLite và dữ liệu mẫu nếu chưa có
- Cung cấp toàn bộ RESTful APIs cho Auth, Analytics, Gemini AI
- Phục vụ giao diện Frontend tĩnh trực tiếp tại http://127.0.0.1:8000
==============================================================================
"""

import os
import sys
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from dotenv import load_dotenv

# Thiết lập UTF-8 cho Windows console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

ROOT_DIR = Path(__file__).resolve().parent
load_dotenv(ROOT_DIR / ".env")

from config.db import test_connection
from routers.auth_router import router as auth_router
from routers.revenue_router import router as revenue_router
from routers.ai_router import router as ai_router
from routers.product_router import router as product_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Khởi động: Kiểm tra kết nối tới Microsoft SQL Server (SSMS)
    print("🚀 [System] Đang khởi động hệ thống...", flush=True)
    is_connected = test_connection()
    if is_connected:
        print("✨ [System] Hệ thống đã sẵn sàng phục vụ tại http://127.0.0.1:8000", flush=True)
    else:
        print("⚠️ [System] Cảnh báo: Chưa kết nối được SQL Server!", flush=True)
    yield
    print("🛑 [System] Đang dừng hệ thống...", flush=True)


app = FastAPI(
    title="Hệ Thống Phân Tích Doanh Thu & Tối Ưu Chiến Lược Bán Hàng - Gemini AI",
    description="Đồ Án Chuyên Ngành: Phân tích kinh doanh, trực quan hóa doanh thu và tích hợp Google Gemini AI",
    version="1.0.0",
    lifespan=lifespan
)

# Cấu hình CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Đăng ký các Router tính năng
app.include_router(auth_router)
app.include_router(revenue_router)
app.include_router(ai_router)
app.include_router(product_router)

# Phục vụ thư mục static (Giao diện Frontend)
static_dir = ROOT_DIR / "static"
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/")
def root():
    """Chuyển hướng trang chủ về giao diện chính."""
    return RedirectResponse(url="/static/index.html")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "127.0.0.1")
    print(f"🔥 Khởi chạy máy chủ tại: http://{host}:{port}")
    uvicorn.run("main:app", host=host, port=port, reload=True)
