"""
==============================================================================
BỘ KHỞI TẠO DỮ LIỆU MẪU ĐỒ ÁN (DATABASE SEEDER - PYTHON)
==============================================================================
Tự động nạp:
1. 3 Tài khoản mẫu (Admin, Manager, Sales) với mật khẩu mặc định: 123456
2. 5 Danh mục & 16 sản phẩm kinh doanh thực tế
3. 12 Khách hàng đa dạng phân khúc RFM
4. Hơn 150 đơn hàng trải dài 6 tháng qua trên 4 kênh bán lẻ
5. Lịch sử phân tích chiến lược AI ban đầu
==============================================================================
"""

import sys
import random
from datetime import datetime, timedelta
from pathlib import Path
import bcrypt

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Thêm thư mục gốc vào PYTHONPATH
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

from config.db import get_db_connection, init_db


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def seed_database():
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()

    # Kiểm tra nếu đã có users thì không seed lại
    cursor.execute("SELECT id FROM users LIMIT 1")
    if cursor.fetchone():
        print("ℹ️ CSDL đã có dữ liệu mẫu. Bỏ qua bước seed.")
        conn.close()
        return

    print("🌱 Đang bắt đầu nạp dữ liệu mẫu vào CSDL SQLite...")

    hashed_pw = hash_password("123456")

    # 1. Seed Users
    users_data = [
        ("Quản Trị Viên (Admin)", "admin@dacn.vn", hashed_pw, "admin"),
        ("Giám Đốc Kinh Doanh (Manager)", "manager@dacn.vn", hashed_pw, "manager"),
        ("Nhân Viên Bán Hàng (Sales)", "sales@dacn.vn", hashed_pw, "sales"),
    ]
    cursor.executemany(
        "INSERT INTO users (full_name, email, password_hash, role) VALUES (?, ?, ?, ?)",
        users_data
    )
    print("✅ Đã tạo 3 tài khoản mẫu: admin@dacn.vn, manager@dacn.vn, sales@dacn.vn (Pass: 123456)")

    # 2. Seed Categories
    categories = [
        ("Thời trang nam nữ", "Quần áo, áo khoác, phụ kiện thời trang dạo phố và công sở"),
        ("Thiết bị điện tử", "Tai nghe chống ồn, bàn phím cơ, phụ kiện công nghệ cao cấp"),
        ("Đồ gia dụng tiện ích", "Nồi chiên không dầu, máy xay sinh tố mini, đồ bếp hiện đại"),
        ("Mỹ phẩm & Chăm sóc da", "Kem chống nắng, serum phục hồi, sữa rửa mặt dịu nhẹ"),
        ("Thể thao & Dã ngoại", "Giày chạy bộ đệm khí, bình nước giữ nhiệt thể thao"),
    ]
    cursor.executemany(
        "INSERT INTO categories (name, description) VALUES (?, ?)",
        categories
    )

    # 3. Seed Products (SKU, Tên, CategoryId, Giá vốn COGS, Giá bán, Tồn kho)
    products = [
        ("SKU-001", "Áo thun Polo Cotton Compact", 1, 95000, 249000, 185),
        ("SKU-002", "Quần Tây âu Slimfit Co giãn", 1, 140000, 389000, 110),
        ("SKU-003", "Áo khoác gió chống nước 2 lớp", 1, 160000, 420000, 42),
        ("SKU-004", "Váy lụa hoa nhí Vintage", 1, 120000, 350000, 28),
        ("SKU-005", "Tai nghe không dây Bluetooth Pro ANC", 2, 280000, 690000, 95),
        ("SKU-006", "Bàn phím cơ không dây RGB 87 phím", 2, 420000, 890000, 35),
        ("SKU-007", "Chuột gaming không dây Ergonomic", 2, 180000, 450000, 60),
        ("SKU-008", "Củ sạc nhanh GaN 65W 3 cổng", 2, 130000, 320000, 140),
        ("SKU-009", "Nồi chiên không dầu điện tử 6L", 3, 580000, 1290000, 19),
        ("SKU-010", "Máy xay sinh tố cầm tay sạc USB", 3, 110000, 269000, 88),
        ("SKU-011", "Bình đun siêu tốc inox 304", 3, 90000, 219000, 52),
        ("SKU-012", "Serum phục hồi da Vitamin B5 & HA", 4, 150000, 360000, 120),
        ("SKU-013", "Kem chống nắng quang phổ rộng SPF50+", 4, 130000, 310000, 95),
        ("SKU-014", "Sữa rửa mặt tạo bọt dịu nhẹ 150ml", 4, 75000, 189000, 160),
        ("SKU-015", "Giày chạy bộ đệm khí Air Cushion", 5, 290000, 750000, 34),
        ("SKU-016", "Bình nước thể thao giữ nhiệt 1000ml", 5, 65000, 179000, 210),
    ]
    cursor.executemany(
        """INSERT INTO products (sku, name, category_id, cost_price, selling_price, stock_quantity)
           VALUES (?, ?, ?, ?, ?, ?)""",
        products
    )
    print(f"✅ Đã nạp {len(products)} sản phẩm với giá vốn, giá bán và tồn kho chuẩn.")

    # 4. Seed Customers
    customers = [
        ("Nguyễn Văn An", "nguyenvanan@gmail.com", "0901234567", "Hà Nội", "VIP"),
        ("Trần Thị Mai", "tranmai89@gmail.com", "0912345678", "TP. Hồ Chí Minh", "VIP"),
        ("Lê Hoàng Long", "lehoanglong@outlook.com", "0987654321", "Đà Nẵng", "Loyal"),
        ("Phạm Thu Hương", "thuhuong.pham@gmail.com", "0933221100", "Hà Nội", "Loyal"),
        ("Vũ Đình Khoa", "khoavd@fpt.edu.vn", "0944556677", "Cần Thơ", "Potential"),
        ("Đặng Minh Tuấn", "tuan.dang@gmail.com", "0977889900", "Hải Phòng", "Potential"),
        ("Bùi Phương Thảo", "thaobui@gmail.com", "0966112233", "TP. Hồ Chí Minh", "At-Risk"),
        ("Hoàng Gia Bảo", "giabao.hoang@gmail.com", "0922334455", "Nha Trang", "At-Risk"),
        ("Ngô Bích Ngọc", "ngocngo@gmail.com", "0911223344", "Huế", "New"),
        ("Đỗ Anh Dũng", "dungdo@gmail.com", "0988776655", "Bình Dương", "New"),
        ("Trịnh Kim Chi", "chitrinh@gmail.com", "0944112233", "Hà Nội", "Loyal"),
        ("Lý Quốc Toản", "toanly@gmail.com", "0933445566", "TP. Hồ Chí Minh", "VIP"),
    ]
    cursor.executemany(
        "INSERT INTO customers (name, email, phone, city, segment) VALUES (?, ?, ?, ?, ?)",
        customers
    )

    # 5. Seed Orders & Order Items (Khoảng 180 đơn trải dài 6 tháng qua)
    channels = ["Shopee", "TikTok Shop", "Cửa hàng trực tiếp", "Website"]
    statuses = ["completed", "completed", "completed", "completed", "shipping", "cancelled"]
    payment_methods = ["COD", "Chuyển khoản QR", "Thẻ tín dụng", "Ví MoMo"]

    now = datetime.now()
    order_counter = 1001

    for day_offset in range(180, 0, -2):
        order_date = now - timedelta(days=day_offset, hours=random.randint(1, 10))
        daily_orders = random.randint(1, 3)

        for _ in range(daily_orders):
            customer_id = random.randint(1, len(customers))
            channel = random.choice(channels)
            status = random.choice(statuses)
            pay_method = random.choice(payment_methods)
            order_code = f"ORD-{order_counter}"
            order_counter += 1

            # Chọn ngẫu nhiên 1 - 3 mặt hàng
            num_items = random.randint(1, 3)
            order_total = 0.0
            items_to_insert = []

            for _ in range(num_items):
                p_idx = random.randint(0, len(products) - 1)
                p = products[p_idx]
                product_id = p_idx + 1
                qty = random.randint(1, 2)
                cost_price = p[3]
                unit_price = p[4]
                item_total = unit_price * qty
                order_total += item_total
                items_to_insert.append((product_id, qty, unit_price, cost_price, item_total))

            # Giảm giá 0 - 8%
            discount = round(order_total * 0.08) if random.random() > 0.6 else 0.0
            net_total = order_total - discount
            date_str = order_date.strftime("%Y-%m-%d %H:%M:%S")

            cursor.execute("""
                INSERT INTO orders (order_code, customer_id, channel, total_amount, discount_amount, net_amount, payment_method, status, order_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (order_code, customer_id, channel, order_total, discount, net_total, pay_method, status, date_str))

            order_id = cursor.lastrowid

            for item in items_to_insert:
                cursor.execute("""
                    INSERT INTO order_items (order_id, product_id, quantity, unit_price, cost_price, total_price)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (order_id, item[0], item[1], item[2], item[3], item[4]))

    # Cập nhật tổng chi tiêu của khách hàng
    cursor.execute("""
        UPDATE customers 
        SET total_spent = (
            SELECT COALESCE(SUM(net_amount), 0) 
            FROM orders 
            WHERE orders.customer_id = customers.id AND orders.status = 'completed'
        ),
        orders_count = (
            SELECT COUNT(id) 
            FROM orders 
            WHERE orders.customer_id = customers.id AND orders.status = 'completed'
        )
    """)

    # 6. Seed AI Strategy log ban đầu
    cursor.execute("""
        INSERT INTO ai_strategy_logs (title, strategy_type, user_prompt, ai_response, metrics_context)
        VALUES (
            'Báo cáo Tối ưu Chiến lược Bán hàng Tháng 10 (Python Gemini)',
            'summary',
            'Phân tích doanh thu và đề xuất tăng trưởng quý 4',
            'Hệ thống ghi nhận doanh thu tăng trưởng ấn tượng trên kênh TikTok Shop (+22%) và Shopee (+15%). Tỷ suất lợi nhuận gộp đạt 47.8%. Đề xuất: Đẩy mạnh combo Thời trang + Phụ kiện công nghệ và kích hoạt chiến dịch Remarketing cho 4 khách hàng thuộc nhóm At-Risk.',
            '{"total_revenue": 168400000, "profit_margin": "47.8%", "top_channel": "TikTok Shop"}'
        )
    """)

    conn.commit()
    conn.close()
    print(f"🎉 Đã nạp thành công {order_counter - 1001} đơn hàng vào CSDL SQLite!")


if __name__ == "__main__":
    seed_database()
