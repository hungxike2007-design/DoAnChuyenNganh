# Hệ Thống Phân Tích Doanh Thu & Quản Trị Tài Chính AI - Constitution

## Core Principles

### I. Kiến Trúc Phân Lớp Mô-đun (Modular & Clean Architecture)
- Tách biệt rõ ràng giữa Backend (FastAPI modular routers/services) và Frontend (Vanilla JS + CSS hệ thống thiết kế chuẩn).
- Mỗi phân hệ (Auth, Dashboard, Revenue, Orders, Products, Customers RFM, AI, Financial P&L) có service và router độc lập.
- Không ghép nối chặt chẽ (loose coupling), dữ liệu lưu trữ tập trung trên Microsoft SQL Server (`RevenueSystemDB`).

### II. Tính Toàn Vẹn & Chính Xác Tài Chính (Financial Data Integrity)
- Mọi phép tính tài chính (Doanh thu thuần, COGS, OPEX, EBITDA/Lợi nhuận ròng, Tỷ suất lợi nhuận) phải đảm bảo độ chính xác số học tuyệt đối.
- Sử dụng kiểu dữ liệu `DECIMAL(18,2)` trong SQL Server cho tiền tệ, format VND thống nhất.
- Bắt buộc kiểm tra dữ liệu đầu vào tại trust boundaries (Pydantic models, validation middleware).

### III. Bảo Mật & Phân Quyền Đa Tầng (Role-Based Access Control - RBAC)
- 4 phân quyền cốt lõi: `Admin`, `Manager`, `Sales`, `User` (Khách hàng).
- Tuyệt đối bảo mật dữ liệu nhạy cảm: Người dùng vai trò `User` hoặc `Sales` không được phép thấy giá vốn kho (COGS) hoặc biên lợi nhuận kinh doanh.
- Xác thực JWT token bắt buộc cho mọi API nghiệp vụ quan trọng.

### IV. Quy Trình Spec-Driven Development (SDD)
- Mọi tính năng lớn hoặc thay đổi kiến trúc đều đi qua quy trình:
  1. `specify`: Định nghĩa mục tiêu, kịch bản người dùng, acceptance criteria.
  2. `plan`: Thiết kế API, schema bảng SQL Server, layout UI.
  3. `tasks`: Chia nhỏ danh sách công việc theo thứ tự phụ thuộc.
  4. `implement`: Code từng task, test ngay khi hoàn tất.
  5. `converge`: Đối soát mã nguồn với spec để đảm bảo không sót yêu cầu.

### V. Giao Diện Nhất Quán & Trải Nghiệm Tối Ưu (UI/UX Clean Light Theme)
- Chuẩn phong cách Clean Light Business Theme (nền sáng, card phẳng, đường viền 1px crisp).
- Màu chữ tương phản cao: `#0f172a` (Slate 900) cho chữ chính, `#475569` (Slate 600) cho chữ phụ, `#2563eb` cho hành động chính.
- Hỗ trợ responsive đa màn hình, có cache-busting cho assets.

## Tech Stack Constraints
- **Backend**: Python 3.10+ / 3.14, FastAPI, Uvicorn, PyODBC / SQLAlchemy.
- **Database**: Microsoft SQL Server 2019/2022 (`TOM\SQLEXPRESS`, Database `RevenueSystemDB`).
- **AI Core**: Google Gemini SDK (`google-genai`), mô hình `gemini-3.5-flash` / `gemini-2.5-flash`.
- **Frontend**: HTML5, CSS3 Variables, JavaScript thuần (ES6+), Chart.js.

## Governance
- Bản hiến pháp này định hướng toàn bộ quá trình phát triển và bảo trì hệ thống.
- Bất kỳ thay đổi cấu trúc dữ liệu hoặc quyền hạn đều phải cập nhật spec và schema trong `database_mssql.sql`.

**Version**: 1.0.0 | **Ratified**: 2026-11-03
