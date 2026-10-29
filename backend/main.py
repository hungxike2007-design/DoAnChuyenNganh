"""
==============================================================================
HỆ THỐNG PHÂN TÍCH DOANH THU & TỐI ƯU CHIẾN LƯỢC BÁN HÀNG TÍCH HỢP GEMINI AI
BACKEND APPLICATION ENTRY POINT (FASTAPI)
==============================================================================
Kiến trúc Module hóa theo tính năng (Feature-Based Modular Architecture):
- backend/config/          : Cấu hình kết nối CSDL SQL Server và Google Gemini AI
- backend/modules/auth/    : Xác thực, JWT, Đăng ký/Đăng nhập, Phân quyền RBAC
- backend/modules/dashboard: Thống kê doanh thu, KPIs, Biểu đồ đa kênh
- backend/modules/orders/   : Quản lý đơn hàng, Import file Excel/CSV chống lỗi
- backend/modules/products/ : Danh mục & Kho hàng, Bảo mật giá vốn
- backend/modules/ai/       : Cố vấn kinh doanh Gemini AI & DSS Lập Kế Hoạch Doanh Thu
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

# Thư mục gốc dự án
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

load_dotenv(BASE_DIR / ".env")

from backend.config.db import test_connection
from backend.modules.auth.auth_router import router as auth_router
from backend.modules.dashboard.revenue_router import router as revenue_router
from backend.modules.ai.ai_router import router as ai_router
from backend.modules.products.product_router import router as product_router
from backend.modules.ai.planner_router import router as planner_router
from backend.modules.orders.import_router import router as import_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 [Backend] Đang khởi động hệ thống Backend Modular...", flush=True)
    is_connected = test_connection()
    if is_connected:
        print("✨ [Backend] Kết nối SQL Server thành công! Sẵn sàng phục vụ tại http://127.0.0.1:8000", flush=True)
    else:
        print("⚠️ [Backend] Cảnh báo: Chưa kết nối được Microsoft SQL Server!", flush=True)
    yield
    print("🛑 [Backend] Đang dừng hệ thống...", flush=True)


app = FastAPI(
    title="Hệ Thống Phân Tích Doanh Thu & Tối Ưu Bán Hàng - Gemini AI",
    description="Backend Module Hóa (Feature-Based Architecture) - FastAPI + Microsoft SQL Server + Gemini AI",
    version="2.0.0",
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
app.include_router(planner_router)
app.include_router(import_router)

# Phục vụ thư mục frontend (Cấu trúc phân hệ mới)
frontend_dir = BASE_DIR / "frontend"
frontend_dir.mkdir(parents=True, exist_ok=True)
app.mount("/frontend", StaticFiles(directory=str(frontend_dir)), name="frontend")

# Phục vụ thư mục static (Hỗ trợ tương thích ngược 100%)
static_dir = BASE_DIR / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/")
def root():
    """Chuyển hướng trang chủ về giao diện chính của frontend."""
    return RedirectResponse(url="/frontend/index.html")


@app.get("/api/health")
def health_check():
    """Kiểm tra tình trạng hoạt động của toàn bộ dịch vụ backend."""
    return {
        "status": "healthy",
        "database": "MSSQL (RevenueSystemDB)",
        "architecture": "modular (frontend/ & backend/)",
        "version": "2.0.0"
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "127.0.0.1")
    print(f"🔥 Khởi chạy máy chủ tại: http://{host}:{port}")
    uvicorn.run("backend.main:app", host=host, port=port, reload=True)

