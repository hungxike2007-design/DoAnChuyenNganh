# Kiểm thử, Audit Logs và Docker

## Kiểm thử

```bash
pip install -r requirements-dev.txt
pytest -v
```

## Audit Logs trên SQL Server

Các thao tác qua ứng dụng tạo log trong `audit_logs`. Bảng được tự tạo khi có thao tác audit đầu tiên; nếu muốn cài sẵn cấu trúc và trigger ghi nhận đổi role trực tiếp trong SSMS, chạy `migrations/001_audit_logs.sql` trên database `RevenueSystemDB`. Migration này không xóa dữ liệu. Không chạy lại `database_mssql.sql` trên database đang sử dụng vì file đó khởi tạo lại các bảng.

Để gỡ tính năng lợi nhuận đóng góp theo đơn trên database cũ, migration `migrations/002_remove_order_profit_tables.sql` xóa `dbo.order_fee_status` và `dbo.order_costs` cùng dữ liệu trong hai bảng đó.

## Chạy bằng Docker

```bash
docker compose up --build
```

Mở `http://localhost:8000`. Container dùng SQLite trong `data/revenue_system.sqlite` và tự khởi tạo dữ liệu demo khi database còn trống. Tài khoản demo: `admin@dacn.vn` / `123456`. Dữ liệu được lưu ở thư mục `data` trên máy host.

Thiết lập `JWT_SECRET` và `GEMINI_API_KEY` qua biến môi trường trước khi triển khai ra ngoài môi trường demo. Telegram không được cấu hình hoặc gọi trong các hạng mục này.
