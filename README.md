# HỆ THỐNG PHÂN TÍCH DOANH THU & TỐI ƯU CHIẾN LƯỢC BÁN HÀNG TÍCH HỢP GEMINI AI

> **Đề tài Đồ Án Chuyên Ngành / Tốt Nghiệp Ngành Công Nghệ Thông Tin**  
> **Backend:** Python (FastAPI Framework) — Kiến trúc Feature-Based Modular Architecture  
> **Frontend:** JavaScript (ES6+), HTML5, CSS3 Clean Light Theme (Design System Glassmorphism)  
> **Cơ sở dữ liệu:** Microsoft SQL Server (SSMS) & SQLite (Cơ chế chuyển đổi linh hoạt Dual-Database)  
> **Trí tuệ nhân tạo:** Google Gemini API (`gemini-3.5-flash`) hỗ trợ Cố vấn điều hành, Lập kế hoạch & Sáng tạo kịch bản bán hàng  

---

## 🌟 TỔNG QUAN CÁC PHÂN HỆ NGHIỆP VỤ CỐT LÕI

Hệ thống được thiết kế hướng tới giải quyết trọn vẹn bài toán **Phân tích Doanh thu, Quản trị Hiệu suất Tài chính & Tối ưu Chiến lược Bán lẻ Đa kênh** (Shopee, TikTok Shop, Cửa hàng trực tiếp, Website), bao gồm 8 phân hệ chuyên sâu:

### 1. Phân Hệ Xác Thực & Quản Trị Người Dùng Đa Cấp (Auth & RBAC)
* **Bảo mật chuẩn công nghiệp:** Đăng nhập cấp mã **JWT (JSON Web Token)** thời hạn 24 giờ, mã hóa mật khẩu an toàn bằng thuật toán `bcrypt` có Salt.
* **Quy trình Khôi phục Mật khẩu:** Tính năng Quên mật khẩu xác thực qua **mã OTP 6 chữ số** có hiệu lực 15 phút, chống brute-force.
* **Phân quyền truy cập 4 cấp bậc (RBAC):** `admin` (Toàn quyền), `manager` (Giám đốc kinh doanh), `sales` (Nhân viên bán hàng), `user`.
* **Bộ lọc Drill-Down theo nhân viên:** Admin và Manager có thể chọn xem số liệu doanh thu của từng nhân viên Sales cụ thể hoặc toàn công ty.

### 2. Bảng Điều Khiển Doanh Thu Đa Kênh (Executive Dashboard)
* **Giám sát KPIs thời gian thực:** Doanh thu thuần, Lợi nhuận gộp, Biên lợi nhuận gộp (%), Giá trị đơn trung bình (AOV), Tỷ lệ hủy/hoàn đơn.
* **Biểu đồ chuỗi thời gian (Chart.js):** Theo dõi xu hướng doanh số theo chu kỳ (7 ngày, 30 ngày, 90 ngày, 180 ngày).
* **Phân bổ tỷ trọng kênh bán:** Trực quan hóa doanh thu và số lượng đơn hàng qua 4 kênh chính: Shopee, TikTok Shop, Cửa hàng trực tiếp, Website.
* **Xếp hạng & Cảnh báo:** Top sản phẩm bán chạy nhất kèm tính năng ẩn giá vốn đối với tài khoản Sales; cảnh báo hàng tồn kho thấp chạm ngưỡng an toàn.

### 3. Phân Khúc Khách Hàng RFM (Recency - Frequency - Monetary)
* Tự động chấm điểm và phân loại toàn bộ khách hàng thành 6 nhóm hành vi:
  * **VIP (Khách hàng đặc biệt):** Chi tiêu cao, mua hàng liên tục.
  * **Loyal (Khách trung thành):** Mua hàng đều đặn với giá trị tốt.
  * **Potential (Khách tiềm năng):** Mới mua gần đây với tần suất đang tăng.
  * **At-Risk (Nguy cơ rời bỏ):** Từng mua nhiều nhưng đã lâu không quay lại.
  * **Lost (Khách đã mất) & New (Khách hàng mới).**
* Hiển thị bảng chi tiết khách hàng theo phân khúc, giá trị tích lũy và ngày mua gần nhất.

### 4. Báo Cáo Tài Chính P&L & Hiệu Suất Kinh Doanh (Financial P&L Report)
* **Báo cáo Lãi - Lỗ (Profit & Loss):** Tính toán chi tiết từ Doanh thu thuần $\rightarrow$ Giá vốn hàng bán (COGS) $\rightarrow$ **Lợi nhuận gộp (Gross Profit)**.
* **Quản lý Chi phí Vận hành (OPEX):** Quản lý các khoản mục chi phí theo tháng và theo kênh bán (Chi phí thuê mặt bằng/kho bãi, Lương nhân sự, Chi phí Marketing/Ads, Điện nước & Bao bì, Chi phí khác).
* **Chỉ số Lợi nhuận ròng EBITDA:** Tính toán **EBITDA (Lợi nhuận trước thuế, lãi vay và khấu hao)** và Biên EBITDA (%) thời gian thực.
* Cho phép lọc báo cáo theo từng tháng cụ thể (`YYYY-MM`) và theo từng kênh kinh doanh.

### 5. Lập Kế Hoạch & Phân Bổ Mục Tiêu Doanh Thu (AI Revenue Goal Planner - DSS)
* **Mô hình Hỗ trợ Ra Quyết định (DSS):** Người quản lý nhập chỉ tiêu doanh thu mong muốn hoặc chọn mức tăng trưởng nhanh (+10%, +20%, +30%).
* **Phân rã Quota thông minh:** Gemini AI phân tích dữ liệu lịch sử để tự động chia nhỏ hạn mức doanh thu cho 4 kênh bán lẻ (Shopee, TikTok, Cửa hàng, Web) và ước tính số lượng đơn hàng / giá trị AOV cần đạt.
* **Lộ trình hành động 4 tuần:** Vạch rõ kế hoạch hành động chiến thuật chi tiết theo từng tuần cho bộ phận Kinh doanh và Marketing.

### 6. Chiến Lược Giá Động & Gợi Ý Combo Xả Kho (Dynamic Pricing & Combo Engine)
* **Phát hiện hàng tồn đọng:** Tự động nhận diện các mặt hàng có tốc độ bán chậm, ứ đọng vốn lâu ngày.
* **Đề xuất Giá Động & Combo:** Gemini AI phân tích giá vốn (COGS) và đề xuất phương án giảm giá hoặc đóng gói Combo chéo (Cross-selling) để kích cầu xả hàng mà vẫn đảm bảo lợi nhuận dương.

### 7. Xưởng Sáng Tạo Kịch Bản Marketing & TikTok Ads (AI Marketing Studio)
* **Bố cục 3 cột chuyên nghiệp:** Tự động trích xuất thông tin sản phẩm từ CSDL để tạo nội dung quảng cáo đa nền tảng.
* **Kịch bản Video TikTok 30s:** 4 phân cảnh hoàn chỉnh (Hook 3s giữ chân, Nỗi đau khách hàng, Giải pháp đột phá, Kêu gọi hành động CTA chốt đơn).
* **Bài viết Facebook Ads AIDA:** Chuẩn cấu trúc Thu hút (Attention) - Thích thú (Interest) - Khao khát (Desire) - Hành động (Action).
* **Bộ từ khóa SEO & Hashtag:** Tối ưu hóa lượt tìm kiếm tự nhiên trên mạng xã hội.
* **Lịch sử kịch bản ghim góc phải:** Lưu trữ và quản lý các kịch bản đã tạo, hỗ trợ tải lại và xóa kịch bản bằng modal tùy chỉnh an toàn.

### 8. Trợ Lý AI Doanh Nghiệp Thời Gian Thực (AI Business Copilot)
* Chatbot thông minh hỗ trợ lãnh đạo hỏi đáp trực tiếp về số liệu kinh doanh: *"Doanh thu hôm nay thế nào?"*, *"Mặt hàng nào đang bán chạy nhất?"*, *"Kênh nào có biên lợi nhuận cao nhất?"*.
* Tự động truy xuất bối cảnh số liệu từ CSDL SQL để trả lời chính xác, lưu trữ lịch sử hội thoại riêng biệt theo từng tài khoản người dùng.

---

## 📂 CẤU TRÚC THƯ MỤC DỰ ÁN (FEATURE-BASED ARCHITECTURE)

```text
HeThongDACN/
│
├── .env.example                    # File mẫu cấu hình biến môi trường an toàn đưa lên GitHub
├── .env                            # [BẢO MẬT] File chứa cấu hình CSDL & API Key (chặn bởi .gitignore)
├── requirements.txt                # Danh sách thư viện Python cần thiết
├── README.md                       # Tài liệu hướng dẫn hệ thống
├── main.py                         # File khởi chạy chính FastAPI (Entry Point)
├── database_mssql.sql              # Script tạo bảng & Schema trên Microsoft SQL Server
│
├── backend/                        # TOÀN BỘ MÃ NGUỒN BACKEND MODULAR (FASTAPI)
│   ├── main.py                     # Cấu hình CORS, Static Mount, Lifespan kết nối
│   ├── config/                     # Cấu hình CSDL và AI
│   │   ├── db.py                   # Adapter kết nối SQL Server (SSMS) & SQLite
│   │   └── ai_config.py            # Quản lý Gemini API Key an toàn & Mock Fallback
│   │
│   └── modules/                    # Phân chia theo từng phân hệ nghiệp vụ
│       ├── auth/                   # Xác thực JWT, Bcrypt, OTP, RBAC
│       │   ├── auth_router.py
│       │   └── auth_service.py
│       ├── dashboard/              # Tổng hợp KPI, Chuỗi thời gian, Kênh bán, RFM
│       │   ├── revenue_router.py
│       │   └── analytics_service.py
│       ├── financial/              # Báo cáo P&L, Chi phí OPEX, EBITDA
│       │   ├── financial_router.py
│       │   └── financial_service.py
│       ├── ai/                     # Gemini AI Service, Planner, Copilot, Studio
│       │   ├── ai_router.py
│       │   ├── planner_router.py
│       │   └── gemini_service.py
│       ├── orders/                 # Quản lý đơn hàng & Import Excel/CSV
│       │   └── import_router.py
│       └── products/               # Quản lý danh mục & kho hàng
│           └── product_router.py
│
├── frontend/                       # MÃ NGUỒN GIAO DIỆN PHÁT TRIỂN (HTML/CSS/JS)
│   ├── index.html                  # Trang chuyển hướng trang chủ
│   ├── auth/                       # login.html, register.html, forgot-password.html
│   ├── dashboard/                  # dashboard.html (Executive Dashboard)
│   ├── customers/                  # customer-rfm.html (Phân khúc RFM)
│   ├── financial/                  # pnl-report.html (Báo cáo P&L & OPEX)
│   ├── ai/                         # revenue-planner.html, ai-strategy.html, marketing-studio.html, ai-copilot.html
│   ├── orders/                     # orders.html (Đơn hàng)
│   ├── products/                   # products.html (Sản phẩm & Kho)
│   ├── users/                      # users.html (Quản trị phân quyền)
│   └── assets/                     # css/ (design system clean light) & js/ (api.js, auth.js...)
│
├── static/                         # BẢN GIAO DIỆN ĐỒNG BỘ PRODUCTION (FASTAPI STATIC MOUNT)
│   ├── dashboard.html, pnl-report.html, customer-rfm.html, marketing-studio.html...
│   ├── css/                        # main.css, dashboard.css, ai.css, auth.css...
│   └── js/                         # api.js, dashboard.js, copilot.js, marketing-studio.js...
│
└── data/                           # DỮ LIỆU CSDL & SEEDER
    ├── seed.py                     # Script nạp dữ liệu mẫu 150+ đơn hàng, 16 sản phẩm, 3 tài khoản
    └── revenue_system.sqlite       # Cơ sở dữ liệu SQLite dự phòng
```

---

## 🛠️ HƯỚNG DẪN CÀI ĐẶT & KHỞI CHẠY HỆ THỐNG

### Bước 1: Cài đặt môi trường Python
Mở Terminal hoặc Command Prompt tại thư mục dự án:
```bash
pip install -r requirements.txt
```

### Bước 2: Cấu hình biến môi trường (`.env`)
Tạo file `.env` tại thư mục gốc (hoặc copy từ `.env.example`):
```env
# Cấu hình CSDL: 'mssql' hoặc 'sqlite'
DB_TYPE=mssql
DB_SERVER=localhost
DB_DATABASE=RevenueSystemDB
DB_TRUSTED_CONNECTION=yes

# Cấu hình Google Gemini AI
GEMINI_API_KEY=AIzaSyYourGeminiApiKeyHere
GEMINI_MODEL=gemini-3.5-flash

# Cấu hình JWT Token Secret
JWT_SECRET=your_super_secret_jwt_key_2026
```
*(Nếu chưa có Gemini API Key, hệ thống tự động kích hoạt Mock AI thông minh để kiểm thử và thuyết trình mượt mà không bị gián đoạn).*

---

### Bước 3: Thiết lập Cơ sở dữ liệu (Chọn 1 trong 2 cách)

#### 👉 CÁCH A: Dùng Microsoft SQL Server (SSMS) — Khuyên dùng cho Đồ án
1. Mở **SQL Server Management Studio (SSMS)**.
2. Mở file [`database_mssql.sql`](file:///c:/Users/Public/HeThongDACN/database_mssql.sql) trong dự án.
3. Nhấn **Execute (F5)** để tự động tạo Database `RevenueSystemDB` và toàn bộ 12 bảng dữ liệu.

#### 👉 CÁCH B: Dùng SQLite (Dành cho người clone code về chạy ngay không cài SQL Server)
1. Trong file `.env`, đặt `DB_TYPE=sqlite`.
2. Chạy lệnh nạp dữ liệu mẫu:
```bash
python data/seed.py
```
*(CSDL SQLite sẽ được tự động khởi tạo với đầy đủ tài khoản, danh mục, sản phẩm và hơn 150 đơn hàng).*

---

### Bước 4: Khởi chạy Server Backend
Chạy lệnh duy nhất tại thư mục gốc:
```bash
python main.py
```
Hoặc:
```bash
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```
Truy cập hệ thống tại:  
👉 **http://127.0.0.1:8000**

---

## 🔑 TÀI KHOẢN MẪU ĐỂ CHẤM ĐỒ ÁN / DEMO

Hệ thống đã thiết lập sẵn 3 tài khoản đại diện cho các vai trò trong doanh nghiệp, mật khẩu mặc định đều là `123456`:

| Vai Trò | Email Đăng Nhập | Mật Khẩu | Quyền Hạn |
| :--- | :--- | :--- | :--- |
| **Admin** | `admin@dacn.vn` | `123456` | Toàn quyền quản trị hệ thống, quản lý người dùng, drill-down số liệu |
| **Manager** | `manager@dacn.vn` | `123456` | Xem báo cáo tài chính P&L, xem toàn bộ doanh thu, lập kế hoạch AI |
| **Sales** | `sales@dacn.vn` | `123456` | Quản lý đơn hàng, xem doanh số cá nhân (được ẩn giá vốn COGS) |

*(Tại giao diện Đăng nhập có sẵn các nút bấm chọn nhanh tài khoản để demo tức thì).*

---

## 📡 DANH MỤC API ENDPOINTS CHÍNH (RESTful API)

| Nhóm API | Method | Endpoint | Mô Tả Chức Năng |
| :--- | :---: | :--- | :--- |
| **Xác thực** | `POST` | `/api/auth/login` | Đăng nhập cấp JWT Token |
| | `POST` | `/api/auth/register` | Đăng ký tài khoản mới |
| | `POST` | `/api/auth/forgot-password` | Gửi mã xác nhận OTP 6 số qua email |
| | `POST` | `/api/auth/reset-password` | Đổi mật khẩu mới bằng OTP |
| **Doanh thu** | `GET` | `/api/revenue/kpis` | Lấy các chỉ số tài chính tổng hợp (Doanh thu, Lợi nhuận, AOV) |
| | `GET` | `/api/revenue/timeline` | Chuỗi thời gian doanh thu theo ngày |
| | `GET` | `/api/revenue/channels` | Tỷ trọng doanh thu theo 4 kênh bán lẻ |
| | `GET` | `/api/revenue/top-products` | Danh sách sản phẩm bán chạy nhất |
| | `GET` | `/api/revenue/rfm` | Phân khúc khách hàng theo mô hình RFM |
| **Tài chính P&L** | `GET` | `/api/financial/pnl-summary` | Báo cáo P&L (Doanh thu, COGS, Lợi nhuận gộp, OPEX, EBITDA) |
| | `GET` | `/api/financial/expenses` | Danh sách chi phí vận hành theo tháng & kênh |
| | `POST` | `/api/financial/expenses` | Thêm / Cập nhật chi phí vận hành OPEX |
| **Kế hoạch AI** | `POST` | `/api/ai/planner/generate` | Gemini AI phân rã chỉ tiêu doanh thu & lộ trình 4 tuần |
| | `GET` | `/api/ai/planner/history` | Lấy lịch sử các kế hoạch doanh thu đã lưu |
| **Chiến lược & Copilot** | `POST` | `/api/ai/executive-summary` | Sinh tóm tắt điều hành & cảnh báo bất thường |
| | `POST` | `/api/ai/pricing-strategy` | Đề xuất giá động và gợi ý combo xả kho |
| | `POST` | `/api/ai/copilot/chat` | Trò chuyện trực tiếp với trợ lý AI kinh doanh |
| | `POST` | `/api/ai/marketing/generate` | Sinh kịch bản video TikTok 30s & bài viết Facebook Ads |
| **Đơn hàng & Kho** | `GET` | `/api/products` | Danh sách sản phẩm, tồn kho và danh mục |
| | `POST` | `/api/orders/import` | Import dữ liệu đơn hàng từ file Excel/CSV |

---

## 🔒 BẢO MẬT & QUY TẮC PUSH GITHUB

- File `.gitignore` đã chặn toàn bộ file môi trường `.env`, file cơ sở dữ liệu `*.sqlite`, cache `__pycache__` và các file tạm.
- Không bao giờ commit API Key thật lên repository.
- File cấu hình [`backend/config/ai_config.py`](file:///c:/Users/Public/HeThongDACN/backend/config/ai_config.py) và [`backend/config/db.py`](file:///c:/Users/Public/HeThongDACN/backend/config/db.py) được thiết kế theo nguyên tắc an toàn, tự động nạp từ biến môi trường hoặc chuyển sang chế độ dự phòng an toàn khi thiếu cấu hình.

## Tests and deployment

See [DEVOPS.md](DEVOPS.md) for pytest, Docker Compose, and the non-destructive SQL Server audit migration.
