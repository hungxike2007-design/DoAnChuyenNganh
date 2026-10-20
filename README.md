# HỆ THỐNG PHÂN TÍCH DOANH THU & TỐI ƯU CHIẾN LƯỢC BÁN HÀNG TÍCH HỢP GEMINI AI

> **Đề tài Đồ Án Chuyên Ngành / Tốt Nghiệp**  
> **Ngôn ngữ:** Python (FastAPI) & JavaScript/HTML5/CSS3 Hiện Đại  
> **Cơ sở dữ liệu:** SQLite (Quan hệ chuẩn SQL)  
> **Trí tuệ nhân tạo:** Google Gemini API (Mô hình: `gemini-2.5-flash`)

---

## 🌟 ĐIỂM NỔI BẬT CỦA HỆ THỐNG

1. **Phân hệ Xác thực & Quản trị Toàn diện:**
   - Đăng ký tài khoản mới với lựa chọn vai trò (Admin, Manager, Sales).
   - Đăng nhập bảo mật cấp JWT Token (JSON Web Token), mã hóa mật khẩu chuẩn `bcrypt`.
   - Quên mật khẩu & Khôi phục mật khẩu thông qua mã xác thực OTP 6 số có thời hạn an toàn (15 phút).
2. **Bảng điều khiển Doanh thu Đa kênh (Executive Dashboard):**
   - Giám sát thời gian thực các chỉ số tài chính: Doanh thu thuần, Lợi nhuận gộp, Biên lợi nhuận, AOV (Giá trị đơn trung bình), Tỷ lệ hoàn/hủy đơn.
   - Biểu đồ đường xu hướng doanh thu và biểu đồ tròn tỷ trọng các kênh (Shopee, TikTok Shop, Cửa hàng trực tiếp, Website).
   - Bảng xếp hạng Top sản phẩm bán chạy nhất và Cảnh báo mức tồn kho thấp.
3. **Phân tích Khách hàng Theo Mô hình RFM (Recency - Frequency - Monetary):**
   - Tự động phân loại tập khách hàng thành: *VIP, Trung thành (Loyal), Tiềm năng (Potential), Nguy cơ rời bỏ (At-Risk), Mới (New)*.
4. **Bộ Não Tối Ưu Chiến Lược Bán Hàng Bằng Gemini AI:**
   - **Tóm tắt điều hành & Phát hiện bất thường:** AI tự động đọc dữ liệu SQL và chỉ ra điểm sáng, rủi ro, và 3 hành động cụ thể cho tuần tới.
   - **Chiến lược Giá Động (Dynamic Pricing) & Gợi ý Combo:** Phân tích hàng bán chậm và đề xuất combo kích cầu xả hàng mà vẫn đảm bảo biên lợi nhuận trên giá vốn (COGS).
   - **AI Business Copilot:** Trợ lý ảo hỏi đáp trực tiếp về số liệu kinh doanh qua ngôn ngữ tự nhiên.
5. **Bảo Mật API Key Tuyệt Đối Khi Đẩy Lên GitHub:**
   - Toàn bộ key và cấu hình nhạy cảm được đặt trong file `.env`.
   - File `.gitignore` đã chặn toàn bộ `.env` và database không bị push lên kho lưu trữ GitHub.
   - File độc lập `config/ai_config.py` đọc key an toàn từ biến môi trường, có chế độ demo dự phòng thông minh giúp hệ thống luôn hoạt động mượt mà.

---

## 📂 CẤU TRÚC PHÂN TÁCH FILE & THƯ MỤC CỦA DỰ ÁN

Hệ thống được tổ chức module hóa chuyên nghiệp, tách bạch rõ ràng giữa Nghiệp vụ, Dữ liệu, Giao diện và Cấu hình AI:

```text
HeThongDACN/
│
├── .gitignore                      # Chặn đẩy file .env, cache, database lên GitHub
├── .env.example                    # File mẫu cấu hình biến môi trường an toàn đưa lên GitHub
├── .env                            # [BẢO MẬT] File chứa API Key thật tại máy cá nhân
├── requirements.txt                # Danh sách thư viện Python cần thiết
├── README.md                       # Hướng dẫn chi tiết dự án
├── main.py                         # File khởi chạy chính FastAPI (Entry Point)
│
├── config/                         # THƯ MỤC CẤU HÌNH HỆ THỐNG
│   ├── ai_config.py                # [FILE RIÊNG BIỆT] Nạp API Key Gemini từ .env an toàn
│   └── db.py                       # Kết nối CSDL SQLite & khởi tạo Schema bảng SQL
│
├── services/                       # TẦNG LOGIC NGHIỆP VỤ & TÍNH TOÁN
│   ├── auth_service.py             # Xử lý hash bcrypt, token JWT, OTP quên mật khẩu
│   ├── analytics_service.py        # Các câu lệnh SQL tổng hợp doanh thu, KPI, RFM
│   └── gemini_service.py           # Prompt Engineering & gọi Google GenAI SDK
│
├── routers/                        # TẦNG ĐIỀU HƯỚNG CÁC ENDPOINT API
│   ├── auth_router.py              # /api/auth (register, login, forgot-password, reset)
│   ├── revenue_router.py           # /api/revenue (kpis, timeline, channels, top-products)
│   ├── ai_router.py                # /api/ai (executive-summary, strategy, copilot)
│   └── product_router.py           # /api/products (CRUD danh mục & sản phẩm)
│
├── data/                           # DỮ LIỆU CSDL & SEEDER
│   ├── seed.py                     # Nạp sẵn 190+ đơn hàng, 16 sản phẩm, 12 khách hàng mẫu
│   └── revenue_system.sqlite       # File cơ sở dữ liệu quan hệ SQLite
│
└── static/                         # GIAO DIỆN NGƯỜI DÙNG (FRONTEND TÁCH FILE RIÊNG BIỆT)
    ├── index.html                  # Trang điều hướng ban đầu
    ├── login.html                  # Giao diện Đăng nhập
    ├── register.html               # Giao diện Đăng ký
    ├── forgot-password.html        # Giao diện Quên mật khẩu & Đặt lại mật khẩu 2 bước
    ├── dashboard.html              # Bảng điều khiển Doanh thu & Biểu đồ Chart.js
    ├── customer-rfm.html           # Giao diện Phân khúc khách hàng RFM
    ├── ai-strategy.html            # Giao diện Tối ưu Chiến lược Gemini AI
    ├── ai-copilot.html             # Giao diện Chatbot Trợ lý Kinh doanh AI
    │
    ├── css/                        # Tách riêng file CSS cho từng chức năng
    │   ├── main.css                # Design system, glassmorphism, sidebar, theme
    │   ├── auth.css                # CSS cho form đăng nhập, đăng ký, quên pass
    │   ├── dashboard.css           # CSS cho biểu đồ, thẻ KPI, bảng thống kê
    │   └── ai.css                  # CSS cho báo cáo AI, spinner, khung chat Copilot
    │
    └── js/                         # Tách riêng logic JavaScript cho từng trang
        ├── api.js                  # Client API chung, xử lý JWT, định dạng VND, Toast
        ├── auth.js                 # Xử lý sự kiện đăng nhập, đăng ký, OTP đổi mật khẩu
        ├── dashboard.js            # Vẽ biểu đồ Chart.js và cập nhật KPI theo bộ lọc
        ├── rfm.js                  # Hiển thị thẻ phân khúc và danh sách khách hàng
        ├── strategy.js             # Gửi yêu cầu sinh chiến lược tới Gemini AI
        └── copilot.js              # Xử lý tin nhắn chat thời gian thực với AI
```

---

## 🚀 HƯỚNG DẪN CÀI ĐẶT & CHẠY HỆ THỐNG

### 1. Cài đặt các thư viện Python:
Mở terminal tại thư mục dự án và chạy:
```bash
pip install -r requirements.txt
```

### 2. Cấu hình Gemini API Key:
1. Lấy API Key miễn phí tại: [Google AI Studio](https://aistudio.google.com/)
2. Mở file `.env` và dán key vào:
```env
GEMINI_API_KEY=AIzaSyD-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
GEMINI_MODEL=gemini-2.5-flash
```
*(Nếu bạn chưa nhập key, hệ thống vẫn có chế độ Mock AI thông minh để bạn thuyết trình demo không bị lỗi!)*

### 3. Khởi chạy Server:
Chạy lệnh duy nhất sau:
```bash
python main.py
```
Hệ thống sẽ tự động khởi tạo CSDL SQLite, nạp dữ liệu mẫu và mở server tại:  
👉 **http://127.0.0.1:8000**

---

## 🔑 TÀI KHOẢN MẪU ĐỂ CHẤM ĐỒ ÁN / KIỂM THỬ

Hệ thống đã chuẩn bị sẵn 3 tài khoản mẫu với mật khẩu mặc định là `123456`:
- **Admin (Toàn quyền):** `admin@dacn.vn`
- **Manager (Giám đốc kinh doanh):** `manager@dacn.vn`
- **Sales (Nhân viên bán hàng):** `sales@dacn.vn`

*(Tại trang đăng nhập có sẵn các nút bấm chọn nhanh tài khoản rất tiện lợi).*

---

## 🛡️ CƠ CHẾ BẢO VỆ API KEY KHI ĐẨY LÊN GITHUB

- File `.gitignore` đã được cấu hình chặt chẽ để **loại trừ vĩnh viễn** file `.env`, file CSDL `*.sqlite`, và các file nhạy cảm.
- Khi đẩy code lên GitHub, bạn chỉ cần commit file `.env.example`. Người khác khi tải dự án về chỉ cần đổi tên thành `.env` và điền key cá nhân của họ mà không ảnh hưởng tới bạn.
- File [config/ai_config.py](file:///c:/Users/Public/HeThongDACN/config/ai_config.py) là nơi duy nhất quản lý việc nạp và gọi Gemini client, không hardcode bất kỳ chuỗi nhạy cảm nào trong mã nguồn.
