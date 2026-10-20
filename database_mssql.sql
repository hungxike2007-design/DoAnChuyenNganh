-- ==============================================================================
-- KỊCH BẢN TẠO CƠ SỞ DỮ LIỆU MICROSOFT SQL SERVER (SSMS)
-- ĐỀ TÀI: HỆ THỐNG PHÂN TÍCH DOANH THU & TỐI ƯU CHIẾN LƯỢC BÁN HÀNG TÍCH HỢP AI
-- Hướng dẫn: Mở file này trong SQL Server Management Studio (SSMS) và nhấn F5 (Execute)
-- ==============================================================================

-- 1. Tạo Database nếu chưa tồn tại
IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = N'RevenueSystemDB')
BEGIN
    CREATE DATABASE RevenueSystemDB;
    PRINT N'✅ Đã tạo cơ sở dữ liệu RevenueSystemDB thành công!';
END
GO

USE RevenueSystemDB;
GO

-- 2. Xóa các bảng cũ nếu cần thiết lập lại từ đầu (Thứ tự xóa theo khóa ngoại)
IF OBJECT_ID('ai_strategy_logs', 'U') IS NOT NULL DROP TABLE ai_strategy_logs;
IF OBJECT_ID('order_items', 'U') IS NOT NULL DROP TABLE order_items;
IF OBJECT_ID('orders', 'U') IS NOT NULL DROP TABLE orders;
IF OBJECT_ID('customers', 'U') IS NOT NULL DROP TABLE customers;
IF OBJECT_ID('products', 'U') IS NOT NULL DROP TABLE products;
IF OBJECT_ID('categories', 'U') IS NOT NULL DROP TABLE categories;
IF OBJECT_ID('password_resets', 'U') IS NOT NULL DROP TABLE password_resets;
IF OBJECT_ID('users', 'U') IS NOT NULL DROP TABLE users;
GO

-- 3. Tạo Bảng users (Tài khoản, Role)
CREATE TABLE users (
    id INT IDENTITY(1,1) PRIMARY KEY,
    full_name NVARCHAR(150) NOT NULL,
    email NVARCHAR(150) UNIQUE NOT NULL,
    password_hash NVARCHAR(255) NOT NULL,
    role NVARCHAR(20) DEFAULT 'user' CHECK(role IN ('admin', 'manager', 'sales', 'user')),
    avatar_url NVARCHAR(500) DEFAULT '',
    created_at DATETIME2 DEFAULT GETDATE(),
    updated_at DATETIME2 DEFAULT GETDATE()
);
GO

-- 4. Tạo Bảng password_resets (Quên mật khẩu, OTP 6 số)
CREATE TABLE password_resets (
    id INT IDENTITY(1,1) PRIMARY KEY,
    email NVARCHAR(150) NOT NULL,
    otp_code NVARCHAR(10) NOT NULL,
    expires_at DATETIME2 NOT NULL,
    is_used INT DEFAULT 0,
    created_at DATETIME2 DEFAULT GETDATE()
);
GO

-- 5. Tạo Bảng categories (Danh mục sản phẩm)
CREATE TABLE categories (
    id INT IDENTITY(1,1) PRIMARY KEY,
    name NVARCHAR(150) UNIQUE NOT NULL,
    description NVARCHAR(500) DEFAULT '',
    created_at DATETIME2 DEFAULT GETDATE()
);
GO

-- 6. Tạo Bảng products (Sản phẩm, giá vốn COGS, giá bán, tồn kho)
CREATE TABLE products (
    id INT IDENTITY(1,1) PRIMARY KEY,
    sku NVARCHAR(50) UNIQUE NOT NULL,
    name NVARCHAR(255) NOT NULL,
    category_id INT FOREIGN KEY REFERENCES categories(id) ON DELETE SET NULL,
    cost_price DECIMAL(18,2) NOT NULL,
    selling_price DECIMAL(18,2) NOT NULL,
    stock_quantity INT NOT NULL DEFAULT 0,
    image_url NVARCHAR(500) DEFAULT '',
    is_active INT DEFAULT 1,
    created_at DATETIME2 DEFAULT GETDATE()
);
GO

-- 7. Tạo Bảng customers (Khách hàng & Phân khúc RFM)
CREATE TABLE customers (
    id INT IDENTITY(1,1) PRIMARY KEY,
    name NVARCHAR(150) NOT NULL,
    email NVARCHAR(150) UNIQUE NOT NULL,
    phone NVARCHAR(20),
    city NVARCHAR(100),
    segment NVARCHAR(50) DEFAULT 'New' CHECK(segment IN ('VIP', 'Loyal', 'Potential', 'At-Risk', 'Lost', 'New')),
    total_spent DECIMAL(18,2) DEFAULT 0,
    orders_count INT DEFAULT 0,
    last_order_date DATETIME2,
    created_at DATETIME2 DEFAULT GETDATE()
);
GO

-- 8. Tạo Bảng orders (Đơn hàng & Kênh bán đa sàn)
CREATE TABLE orders (
    id INT IDENTITY(1,1) PRIMARY KEY,
    order_code NVARCHAR(50) UNIQUE NOT NULL,
    customer_id INT FOREIGN KEY REFERENCES customers(id) ON DELETE SET NULL,
    channel NVARCHAR(50) NOT NULL CHECK(channel IN ('Shopee', 'TikTok Shop', N'Cửa hàng trực tiếp', 'Website', 'Facebook')),
    total_amount DECIMAL(18,2) NOT NULL,
    discount_amount DECIMAL(18,2) DEFAULT 0,
    net_amount DECIMAL(18,2) NOT NULL,
    payment_method NVARCHAR(50) DEFAULT 'COD',
    status NVARCHAR(50) DEFAULT 'completed' CHECK(status IN ('completed', 'processing', 'shipping', 'cancelled', 'refunded')),
    order_date DATETIME2 DEFAULT GETDATE(),
    created_at DATETIME2 DEFAULT GETDATE()
);
GO

-- 9. Tạo Bảng order_items (Chi tiết món hàng trong đơn)
CREATE TABLE order_items (
    id INT IDENTITY(1,1) PRIMARY KEY,
    order_id INT NOT NULL FOREIGN KEY REFERENCES orders(id) ON DELETE CASCADE,
    product_id INT NOT NULL FOREIGN KEY REFERENCES products(id),
    quantity INT NOT NULL,
    unit_price DECIMAL(18,2) NOT NULL,
    cost_price DECIMAL(18,2) NOT NULL,
    total_price DECIMAL(18,2) NOT NULL
);
GO

-- 10. Tạo Bảng ai_strategy_logs (Lịch sử khuyến nghị chiến lược Gemini AI)
CREATE TABLE ai_strategy_logs (
    id INT IDENTITY(1,1) PRIMARY KEY,
    title NVARCHAR(255) NOT NULL,
    strategy_type NVARCHAR(50) NOT NULL,
    user_prompt NVARCHAR(MAX),
    ai_response NVARCHAR(MAX) NOT NULL,
    metrics_context NVARCHAR(MAX),
    created_by INT FOREIGN KEY REFERENCES users(id) ON DELETE SET NULL,
    created_at DATETIME2 DEFAULT GETDATE()
);
GO

PRINT N'✅ Đã khởi tạo cấu trúc toàn bộ 8 bảng thành công trong SQL Server!';
GO
