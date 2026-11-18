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
from fastapi import FastAPI, HTTPException, Request
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

from backend.config.db import dispose_connection_pools, test_connection
from backend.modules.auth.auth_router import router as auth_router
from backend.modules.dashboard.revenue_router import router as revenue_router
from backend.modules.ai.ai_router import router as ai_router
from backend.modules.products.product_router import router as product_router
from backend.modules.ai.planner_router import router as planner_router
from backend.modules.orders.import_router import router as import_router
from backend.modules.financial.financial_router import router as financial_router
from backend.modules.audit.audit_router import router as audit_router
from backend.modules.dashboard.pivot_router import router as pivot_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 [Backend] Đang khởi động hệ thống Backend Modular...", flush=True)
    is_connected = test_connection()
    if is_connected:
        print("✨ [Backend] Kết nối SQL Server thành công! Sẵn sàng phục vụ tại http://127.0.0.1:8000", flush=True)
    else:
        print("⚠️ [Backend] Cảnh báo: Chưa kết nối được Microsoft SQL Server!", flush=True)
    try:
        yield
    finally:
        dispose_connection_pools()
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
app.include_router(financial_router)
app.include_router(audit_router)
app.include_router(pivot_router)

# Phục vụ thư mục frontend (Cấu trúc phân hệ mới)
frontend_dir = BASE_DIR / "frontend"
frontend_dir.mkdir(parents=True, exist_ok=True)
app.mount("/frontend", StaticFiles(directory=str(frontend_dir)), name="frontend")

# Chuyển các URL static cũ sang frontend chuẩn, không phục vụ bản sao mã nguồn.
LEGACY_STATIC_REDIRECTS = {
    "index.html": "index.html",
    "login.html": "auth/login.html",
    "register.html": "auth/register.html",
    "forgot-password.html": "auth/forgot-password.html",
    "dashboard.html": "dashboard/dashboard.html",
    "pivot-table.html": "dashboard/pivot-table.html",
    "orders.html": "orders/orders.html",
    "products.html": "products/products.html",
    "customer-rfm.html": "customers/customer-rfm.html",
    "pnl-report.html": "financial/pnl-report.html",
    "revenue-planner.html": "ai/revenue-planner.html",
    "ai-strategy.html": "ai/ai-strategy.html",
    "ai-copilot.html": "ai/ai-copilot.html",
    "marketing-studio.html": "ai/marketing-studio.html",
    "users.html": "users/users.html",
    "css/main.css": "assets/css/main.css",
    "css/auth.css": "auth/auth.css",
    "css/dashboard.css": "dashboard/dashboard.css",
    "css/ai.css": "ai/ai.css",
    "css/planner.css": "ai/planner.css",
    "js/api.js": "assets/js/api.js",
    "js/auth.js": "auth/auth.js",
    "js/copilot.js": "ai/copilot.js",
    "js/dashboard.js": "dashboard/dashboard.js",
    "js/import_helper.js": "orders/import_helper.js",
    "js/marketing-studio.js": "ai/marketing-studio.js",
    "js/orders.js": "orders/orders.js",
    "js/pivot-table.js": "dashboard/pivot-table.js",
    "js/planner.js": "ai/planner.js",
    "js/pnl-report.js": "financial/pnl-report.js",
    "js/products.js": "products/products.js",
    "js/rfm.js": "customers/rfm.js",
    "js/strategy.js": "ai/strategy.js",
    "js/users.js": "users/users.js",
}


@app.get("/static")
def redirect_legacy_static_root():
    return RedirectResponse(url="/frontend/index.html", status_code=308)


@app.get("/static/{resource_path:path}")
def redirect_legacy_static(resource_path: str, request: Request):
    target = LEGACY_STATIC_REDIRECTS.get(resource_path or "index.html")
    if not target:
        raise HTTPException(status_code=404, detail="Tài nguyên cũ không tồn tại.")
    url = f"/frontend/{target}"
    if request.url.query:
        url = f"{url}?{request.url.query}"
    return RedirectResponse(url=url, status_code=308)


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
    free_port(port)
    reload_flag = os.getenv("RELOAD", "false").lower() == "true"
    print(f"🔥 Khởi chạy máy chủ tại: http://{host}:{port}")
    uvicorn.run("backend.main:app", host=host, port=port, reload=reload_flag)

