"""
==============================================================================
DỊCH VỤ XỬ LÝ NHẬP DỮ LIỆU TỪ FILE EXCEL / CSV (IMPORT SERVICE - PYTHON)
==============================================================================
Chức năng:
- Đọc và phân tích file CSV (hỗ trợ UTF-8, UTF-8-BOM) và Excel (.xlsx, .xls)
- Tự động chuẩn hóa tiêu đề cột linh hoạt (tiếng Việt không dấu / có dấu / tiếng Anh)
- Import danh sách Đơn Hàng đa kênh (gộp các sản phẩm cùng mã đơn)
- Tự động đồng bộ khách hàng và sản phẩm nếu chưa có trong CSDL
- Import danh sách Sản Phẩm & cập nhật tồn kho / giá vốn
- Bảo đảm nguyên tắc Multi-Tenant Data Isolation: gắn chặt user_id của tài khoản
- Cung cấp file template mẫu chuẩn định dạng
==============================================================================
"""

import io
import re
import csv
import random
import unicodedata
from datetime import datetime
from typing import List, Dict, Any, Optional
import pandas as pd
from config.db import get_db_connection


def strip_accents_and_normalize(text: str) -> str:
    """Loại bỏ dấu tiếng Việt (kể cả đ/Đ), ký tự đặc biệt và chuyển về chữ thường để khớp tiêu đề cột."""
    if not text:
        return ""
    text = str(text).strip()
    text = text.replace('đ', 'd').replace('Đ', 'D')
    text = unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('utf-8')
    text = re.sub(r'[^a-zA-Z0-9]', '_', text.lower())
    text = re.sub(r'_+', '_', text).strip('_')
    return text


class ImportService:
    @staticmethod
    def get_order_template_csv() -> bytes:
        """Tạo file CSV mẫu danh sách đơn hàng đa kênh với mã hóa UTF-8 BOM chuẩn cho Excel."""
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Mã đơn hàng", "Kênh bán", "Tên khách hàng", "Số điện thoại", 
            "Tên sản phẩm", "Mã SKU", "Số lượng", "Đơn giá", "Giảm giá", 
            "Ngày đặt", "Phương thức thanh toán", "Trạng thái"
        ])
        writer.writerow([
            "ORD-SP-101", "Shopee", "Nguyễn Thu Hà", "0912345678", 
            "Áo sơ mi lụa công sở", "SKU-SM-01", 2, 350000, 0, 
            datetime.now().strftime("%Y-%m-%d"), "COD", "completed"
        ])
        writer.writerow([
            "ORD-SP-101", "Shopee", "Nguyễn Thu Hà", "0912345678", 
            "Chân váy xếp ly dáng dài", "SKU-CV-02", 1, 280000, 30000, 
            datetime.now().strftime("%Y-%m-%d"), "COD", "completed"
        ])
        writer.writerow([
            "ORD-TK-102", "TikTok Shop", "Trần Quốc Bảo", "0987654321", 
            "Tai nghe Bluetooth chống ồn", "SKU-TN-03", 1, 490000, 50000, 
            datetime.now().strftime("%Y-%m-%d"), "Chuyển khoản", "completed"
        ])
        writer.writerow([
            "ORD-STORE-103", "Cửa hàng trực tiếp", "Lê Minh Tuấn", "0903112233", 
            "Balo laptop chống nước", "SKU-BL-04", 1, 620000, 0, 
            datetime.now().strftime("%Y-%m-%d"), "Thẻ tín dụng", "completed"
        ])
        writer.writerow([
            "ORD-WEB-104", "Website", "Phạm Hương Giang", "0934556677", 
            "Đồng hồ thông minh thể thao", "SKU-DH-05", 1, 850000, 100000, 
            datetime.now().strftime("%Y-%m-%d"), "Chuyển khoản", "completed"
        ])
        # Thêm tiền tố UTF-8 BOM (\xef\xbb\xbf) để Excel hiển thị đúng tiếng Việt
        return '\ufeff'.encode('utf-8') + output.getvalue().encode('utf-8')

    @staticmethod
    def get_product_template_csv() -> bytes:
        """Tạo file CSV mẫu danh mục sản phẩm."""
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Mã SKU", "Tên sản phẩm", "Danh mục", "Giá vốn (COGS)", "Giá bán niêm yết", "Số lượng tồn kho"])
        writer.writerow(["SKU-AO-01", "Áo sơ mi nam Oxford cao cấp", "Thời trang nam nữ", 180000, 390000, 120])
        writer.writerow(["SKU-TN-02", "Tai nghe Gaming chụp tai 7.1", "Thiết bị điện tử", 320000, 650000, 45])
        writer.writerow(["SKU-BL-03", "Bình giữ nhiệt Lock&Lock 800ml", "Đồ gia dụng tiện ích", 150000, 299000, 85])
        writer.writerow(["SKU-SR-04", "Serum dưỡng ẩm chống lão hóa HA", "Mỹ phẩm & Chăm sóc da", 210000, 480000, 60])
        writer.writerow(["SKU-TT-05", "Thảm tập Yoga định tuyến chống trượt", "Thể thao & Dã ngoại", 140000, 290000, 70])
        return '\ufeff'.encode('utf-8') + output.getvalue().encode('utf-8')

    @classmethod
    def _read_dataframe(cls, file_bytes: bytes, filename: str) -> pd.DataFrame:
        """Đọc file bytes thành Pandas DataFrame, hỗ trợ cả CSV và Excel."""
        fname = filename.lower()
        if fname.endswith(".csv"):
            try:
                # Thử đọc UTF-8
                df = pd.read_csv(io.BytesIO(file_bytes), encoding="utf-8")
            except UnicodeDecodeError:
                try:
                    df = pd.read_csv(io.BytesIO(file_bytes), encoding="utf-8-sig")
                except UnicodeDecodeError:
                    df = pd.read_csv(io.BytesIO(file_bytes), encoding="latin1")
        elif fname.endswith((".xlsx", ".xls")):
            df = pd.read_excel(io.BytesIO(file_bytes))
        else:
            raise ValueError("Định dạng file không được hỗ trợ! Vui lòng chọn file .csv hoặc .xlsx / .xls.")
        
        # Xóa các dòng hoàn toàn trống
        df = df.dropna(how="all")
        return df

    @classmethod
    def import_orders_from_file(cls, file_bytes: bytes, filename: str, user_id: Optional[int]) -> dict:
        """
        Phân tích và nạp danh sách đơn hàng vào CSDL:
        - Tự động map cột linh hoạt
        - Gộp các dòng có cùng order_code thành 1 đơn nhiều món
        - Tự động tạo sản phẩm & khách hàng nếu chưa tồn tại
        - Gán chặt chẽ user_id phục vụ Multi-Tenant
        """
        df = cls._read_dataframe(file_bytes, filename)
        if df.empty:
            raise ValueError("File tải lên không có dữ liệu để xử lý.")

        # Map tên cột chuẩn hóa linh hoạt (hỗ trợ nhiều định dạng từ Shopee, TikTok Shop, POS, KiotViet, Sapo)
        col_map = {}
        for col in df.columns:
            norm = strip_accents_and_normalize(col)
            if norm in ["ma_don_hang", "ma_don", "order_code", "order_id", "code", "so_hoa_don", "ma_dh", "so_phieu", "ma_chung_tu"]:
                col_map["order_code"] = col
            elif norm in ["kenh_ban", "kenh", "channel", "san_tmdt", "nguon_don", "nguon", "san"]:
                col_map["channel"] = col
            elif norm in ["ten_khach_hang", "khach_hang", "customer_name", "customer", "ten_kh", "nguoi_mua", "ho_ten", "nguoi_nhan", "ten"]:
                col_map["customer_name"] = col
            elif norm in ["so_dien_thoai", "sdt", "customer_phone", "phone", "dien_thoai", "mobile", "tel"]:
                col_map["customer_phone"] = col
            elif norm in ["ten_san_pham", "san_pham", "product_name", "product", "ten_hang", "mat_hang", "ten_sp", "hang_hoa"]:
                col_map["product_name"] = col
            elif norm in ["ma_sku", "sku", "ma_sp", "ma_hang", "barcode", "ma_vach", "product_code"]:
                col_map["sku"] = col
            elif norm in ["so_luong", "sl", "quantity", "qty", "so_luong_mua"]:
                col_map["quantity"] = col
            elif norm in ["don_gia", "gia_ban", "unit_price", "price", "gia", "don_gia_ban", "gia_le"]:
                col_map["unit_price"] = col
            elif norm in ["thanh_tien", "tong_tien", "total_amount", "total_price", "tong_cong", "tien_hang"]:
                col_map["total_price"] = col
            elif norm in ["giam_gia", "chiet_khau", "discount", "discount_amount", "voucher", "khuyen_mai"]:
                col_map["discount"] = col
            elif norm in ["ngay_dat", "ngay", "order_date", "date", "thoi_gian", "ngay_tao", "created_date", "ngay_mua"]:
                col_map["order_date"] = col
            elif norm in ["phuong_thuc_thanh_toan", "thanh_toan", "payment_method", "payment", "hinh_thuc_thanh_toan", "pttt"]:
                col_map["payment_method"] = col
            elif norm in ["trang_thai", "status", "tinh_trang", "trang_thai_don_hang"]:
                col_map["status"] = col

        # Tự động phát hiện các cột bị thiếu trong file Excel và xây dựng danh sách cảnh báo
        warnings = []
        if "order_code" not in col_map:
            warnings.append("Thiếu cột 'Mã đơn': Hệ thống đã tự động tạo mã đơn (IMP-...)")
        if "product_name" not in col_map and "sku" not in col_map:
            warnings.append("Thiếu cột 'Sản phẩm/SKU': Hệ thống tự động gán 'Sản phẩm bán lẻ'")
        if "unit_price" not in col_map and "total_price" not in col_map:
            warnings.append("Thiếu cột 'Đơn giá/Thành tiền': Hệ thống tự động áp dụng giá mẫu 250.000 đ")
        if "customer_name" not in col_map:
            warnings.append("Thiếu cột 'Khách hàng': Hệ thống tự động gán 'Khách vãng lai'")
        if "channel" not in col_map:
            warnings.append("Thiếu cột 'Kênh bán': Hệ thống tự động gán kênh 'Shopee'")
        if "order_date" not in col_map:
            warnings.append("Thiếu cột 'Ngày đặt': Hệ thống tự động lấy ngày giờ hiện tại")

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            # Lấy danh sách sản phẩm hiện có của shop
            if user_id:
                cursor.execute("SELECT id, sku, name, selling_price, cost_price FROM products WHERE user_id = ?", (user_id,))
            else:
                cursor.execute("SELECT id, sku, name, selling_price, cost_price FROM products")
            existing_products = cursor.fetchall()
            prod_by_sku = {p["sku"].upper(): p for p in existing_products if p.get("sku")}
            prod_by_name = {p["name"].strip().lower(): p for p in existing_products if p.get("name")}

            # Lấy danh sách khách hàng hiện có của shop
            if user_id:
                cursor.execute("SELECT id, name, phone FROM customers WHERE user_id = ?", (user_id,))
            else:
                cursor.execute("SELECT id, name, phone FROM customers")
            existing_customers = cursor.fetchall()
            cust_by_phone = {c["phone"].strip(): c for c in existing_customers if c.get("phone")}
            cust_by_name = {c["name"].strip().lower(): c for c in existing_customers if c.get("name")}

            # Nhóm dữ liệu theo order_code
            grouped_orders: Dict[str, Dict[str, Any]] = {}
            row_idx = 0

            for _, row in df.iterrows():
                row_idx += 1
                raw_code = str(row[col_map["order_code"]]).strip() if "order_code" in col_map and pd.notna(row[col_map["order_code"]]) else f"IMP-{datetime.now().strftime('%Y%m%d%H%M')}-{random.randint(100, 999)}"
                if not raw_code:
                    raw_code = f"IMP-ORD-{row_idx:04d}"

                raw_channel = str(row[col_map["channel"]]).strip() if "channel" in col_map and pd.notna(row[col_map["channel"]]) else "Shopee"
                # Chuẩn hóa tên kênh
                norm_chan = raw_channel.lower()
                if "shopee" in norm_chan:
                    channel = "Shopee"
                elif "tiktok" in norm_chan:
                    channel = "TikTok Shop"
                elif "web" in norm_chan:
                    channel = "Website"
                else:
                    channel = "Cửa hàng trực tiếp"

                cust_name = str(row[col_map["customer_name"]]).strip() if "customer_name" in col_map and pd.notna(row[col_map["customer_name"]]) else "Khách vãng lai"
                cust_phone = str(row[col_map["customer_phone"]]).strip() if "customer_phone" in col_map and pd.notna(row[col_map["customer_phone"]]) else ""
                prod_name = str(row[col_map["product_name"]]).strip() if "product_name" in col_map and pd.notna(row[col_map["product_name"]]) else "Sản phẩm bán lẻ"
                sku_val = str(row[col_map["sku"]]).strip() if "sku" in col_map and pd.notna(row[col_map["sku"]]) else f"SKU-{random.randint(1000, 9999)}"

                try:
                    qty = int(float(row[col_map["quantity"]])) if "quantity" in col_map and pd.notna(row[col_map["quantity"]]) else 1
                    qty = max(1, qty)
                except Exception:
                    qty = 1

                try:
                    if "unit_price" in col_map and pd.notna(row[col_map["unit_price"]]):
                        u_price = float(row[col_map["unit_price"]])
                    elif "total_price" in col_map and pd.notna(row[col_map["total_price"]]):
                        tot_val = float(row[col_map["total_price"]])
                        u_price = tot_val / qty if qty > 0 else tot_val
                    else:
                        u_price = 250000.0
                    u_price = max(0.0, u_price)
                except Exception:
                    u_price = 250000.0

                try:
                    disc = float(row[col_map["discount"]]) if "discount" in col_map and pd.notna(row[col_map["discount"]]) else 0.0
                    disc = max(0.0, disc)
                except Exception:
                    disc = 0.0

                raw_date = row[col_map["order_date"]] if "order_date" in col_map and pd.notna(row[col_map["order_date"]]) else datetime.now()
                if isinstance(raw_date, str):
                    try:
                        order_date_val = pd.to_datetime(raw_date).to_pydatetime()
                    except Exception:
                        order_date_val = datetime.now()
                elif hasattr(raw_date, "to_pydatetime"):
                    order_date_val = raw_date.to_pydatetime()
                else:
                    order_date_val = datetime.now()

                pay_method = str(row[col_map["payment_method"]]).strip() if "payment_method" in col_map and pd.notna(row[col_map["payment_method"]]) else "COD"
                status_val = str(row[col_map["status"]]).strip().lower() if "status" in col_map and pd.notna(row[col_map["status"]]) else "completed"
                if status_val not in ["completed", "shipping", "processing", "cancelled", "refunded"]:
                    status_val = "completed"

                if raw_code not in grouped_orders:
                    grouped_orders[raw_code] = {
                        "order_code": raw_code,
                        "channel": channel,
                        "customer_name": cust_name,
                        "customer_phone": cust_phone,
                        "order_date": order_date_val,
                        "payment_method": pay_method,
                        "status": status_val,
                        "discount_amount": disc,
                        "items": []
                    }

                grouped_orders[raw_code]["items"].append({
                    "product_name": prod_name,
                    "sku": sku_val,
                    "quantity": qty,
                    "unit_price": u_price,
                    "total_price": qty * u_price
                })

            imported_orders_count = 0
            imported_items_count = 0
            total_revenue_imported = 0.0
            new_customers_created = 0
            new_products_created = 0

            # Ghi vào CSDL
            for code, ord_info in grouped_orders.items():
                # 1. Tìm hoặc tạo khách hàng
                c_name = ord_info["customer_name"]
                c_phone = ord_info["customer_phone"]
                cust_id = None

                if c_phone and c_phone in cust_by_phone:
                    cust_id = cust_by_phone[c_phone]["id"]
                elif c_name.lower() in cust_by_name:
                    cust_id = cust_by_name[c_name.lower()]["id"]
                else:
                    # Tạo khách hàng mới
                    cursor.execute("""
                        INSERT INTO customers (name, email, phone, city, segment, total_spent, orders_count, last_order_date, user_id)
                        OUTPUT INSERTED.id
                        VALUES (?, ?, ?, ?, 'New', 0, 0, GETDATE(), ?)
                    """, (c_name, f"cust_{random.randint(10000, 99999)}@import.local", c_phone or None, "Hồ Chí Minh", user_id))
                    cust_row = cursor.fetchone()
                    cust_id = cust_row["id"] if cust_row else None
                    new_customers_created += 1
                    if c_phone:
                        cust_by_phone[c_phone] = {"id": cust_id, "name": c_name, "phone": c_phone}
                    cust_by_name[c_name.lower()] = {"id": cust_id, "name": c_name, "phone": c_phone}

                # 2. Xử lý sản phẩm & chi phí
                tot_amount = sum(it["total_price"] for it in ord_info["items"])
                net_amount = max(0.0, tot_amount - ord_info["discount_amount"])
                order_date_str = ord_info["order_date"].strftime("%Y-%m-%d %H:%M:%S")

                cursor.execute("""
                    INSERT INTO orders (order_code, customer_id, channel, total_amount, discount_amount, net_amount, payment_method, status, order_date, user_id)
                    OUTPUT INSERTED.id
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    ord_info["order_code"], cust_id, ord_info["channel"], tot_amount,
                    ord_info["discount_amount"], net_amount, ord_info["payment_method"],
                    ord_info["status"], order_date_str, user_id
                ))
                order_row = cursor.fetchone()
                order_id = order_row["id"] if order_row else None

                # 3. Ghi chi tiết order_items
                for it in ord_info["items"]:
                    p_name = it["product_name"]
                    p_sku = it["sku"].upper()
                    prod_id = None
                    c_price = it["unit_price"] * 0.6  # Benchmark giá vốn 60%

                    if p_sku in prod_by_sku:
                        p_obj = prod_by_sku[p_sku]
                        prod_id = p_obj["id"]
                        c_price = float(p_obj.get("cost_price", 0) or c_price)
                    elif p_name.lower() in prod_by_name:
                        p_obj = prod_by_name[p_name.lower()]
                        prod_id = p_obj["id"]
                        c_price = float(p_obj.get("cost_price", 0) or c_price)
                    else:
                        # Tự động tạo sản phẩm mới vào kho của shop
                        cursor.execute("""
                            INSERT INTO products (sku, name, category_id, cost_price, selling_price, stock_quantity, user_id)
                            OUTPUT INSERTED.id
                            VALUES (?, ?, 1, ?, ?, 100, ?)
                        """, (p_sku, p_name, c_price, it["unit_price"], user_id))
                        p_row = cursor.fetchone()
                        prod_id = p_row["id"] if p_row else None
                        new_products_created += 1
                        prod_by_sku[p_sku] = {"id": prod_id, "sku": p_sku, "name": p_name, "cost_price": c_price}
                        prod_by_name[p_name.lower()] = prod_by_sku[p_sku]

                    cursor.execute("""
                        INSERT INTO order_items (order_id, product_id, quantity, unit_price, cost_price, total_price)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (order_id, prod_id, it["quantity"], it["unit_price"], c_price, it["total_price"]))
                    imported_items_count += 1

                # Cập nhật chi tiêu khách hàng
                if cust_id:
                    cursor.execute("""
                        UPDATE customers 
                        SET total_spent = total_spent + ?,
                            orders_count = orders_count + 1,
                            last_order_date = ?
                        WHERE id = ?
                    """, (net_amount, order_date_str, cust_id))

                imported_orders_count += 1
                total_revenue_imported += net_amount

            conn.commit()
            conn.close()

            return {
                "success": True,
                "imported_orders_count": imported_orders_count,
                "imported_items_count": imported_items_count,
                "total_revenue": total_revenue_imported,
                "new_products_created": new_products_created,
                "new_customers_created": new_customers_created,
                "warnings": warnings,
                "message": f"Nạp thành công {imported_orders_count} đơn hàng ({imported_items_count} mặt hàng) với tổng doanh thu {total_revenue_imported:,.0f} VNĐ!"
            }

        except Exception as e:
            conn.close()
            raise e

    @classmethod
    def import_products_from_file(cls, file_bytes: bytes, filename: str, user_id: Optional[int]) -> dict:
        """
        Nhập danh sách sản phẩm và tồn kho từ file Excel / CSV:
        - Cột hỗ trợ: sku, name, category, cost_price, selling_price, stock_quantity
        - Cập nhật nếu SKU đã tồn tại trong kho của shop
        - Thêm mới nếu chưa có
        """
        df = cls._read_dataframe(file_bytes, filename)
        if df.empty:
            raise ValueError("File sản phẩm không có dữ liệu.")

        col_map = {}
        for col in df.columns:
            norm = strip_accents_and_normalize(col)
            if norm in ["ma_sku", "sku", "ma_sp", "ma_hang", "barcode", "product_code"]:
                col_map["sku"] = col
            elif norm in ["ten_san_pham", "ten_sp", "name", "san_pham", "ten_hang", "mat_hang", "product_name"]:
                col_map["name"] = col
            elif norm in ["danh_muc", "category", "loai_sp", "nhom_hang", "category_name"]:
                col_map["category"] = col
            elif norm in ["gia_von", "gia_nhap", "cost_price", "cogs", "gia_goc"]:
                col_map["cost_price"] = col
            elif norm in ["gia_ban", "gia_niem_yet", "selling_price", "price", "don_gia", "gia"]:
                col_map["selling_price"] = col
            elif norm in ["so_luong_ton_kho", "ton_kho", "stock_quantity", "so_luong", "stock", "sl_ton"]:
                col_map["stock_quantity"] = col

        # Tự động phát hiện thiếu cột trong file sản phẩm
        warnings = []
        if "name" not in col_map:
            warnings.append("Thiếu cột Tên sản phẩm: Hệ thống tự động đặt tên theo mã SKU")
        if "cost_price" not in col_map and "selling_price" in col_map:
            warnings.append("Thiếu cột Giá vốn: Tự động tính giá vốn bằng 60% giá bán")
        elif "cost_price" not in col_map:
            warnings.append("Thiếu cột Giá vốn: Tự động gán 150.000 đ")
        if "selling_price" not in col_map:
            warnings.append("Thiếu cột Giá bán: Tự động tính giá bán hoặc gán 250.000 đ")
        if "stock_quantity" not in col_map:
            warnings.append("Thiếu cột Tồn kho: Tự động gán 50 cái")

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            # Lấy danh mục
            cursor.execute("SELECT id, name FROM categories")
            categories = {strip_accents_and_normalize(c["name"]): c["id"] for c in cursor.fetchall()}
            default_cat_id = list(categories.values())[0] if categories else 1

            # Lấy sản phẩm hiện có
            if user_id:
                cursor.execute("SELECT id, sku FROM products WHERE user_id = ?", (user_id,))
            else:
                cursor.execute("SELECT id, sku FROM products")
            existing_skus = {p["sku"].upper(): p["id"] for p in cursor.fetchall() if p.get("sku")}

            created_count = 0
            updated_count = 0
            row_idx = 0

            for _, row in df.iterrows():
                row_idx += 1
                sku_val = str(row[col_map["sku"]]).strip().upper() if "sku" in col_map and pd.notna(row[col_map["sku"]]) else f"SKU-{row_idx:04d}"

                if "name" in col_map and pd.notna(row[col_map["name"]]):
                    name_val = str(row[col_map["name"]]).strip()
                else:
                    name_val = f"Sản phẩm {sku_val}"

                cat_name_raw = str(row[col_map["category"]]).strip() if "category" in col_map and pd.notna(row[col_map["category"]]) else ""
                cat_id = categories.get(strip_accents_and_normalize(cat_name_raw), default_cat_id)

                s_price = None
                if "selling_price" in col_map and pd.notna(row[col_map["selling_price"]]):
                    try:
                        s_price = float(row[col_map["selling_price"]])
                    except Exception:
                        s_price = None

                c_price = None
                if "cost_price" in col_map and pd.notna(row[col_map["cost_price"]]):
                    try:
                        c_price = float(row[col_map["cost_price"]])
                    except Exception:
                        c_price = None

                # Tự bù giá bán và giá vốn nếu một trong hai bị thiếu
                if s_price is None and c_price is not None:
                    s_price = round(c_price * 1.5)
                elif s_price is not None and c_price is None:
                    c_price = round(s_price * 0.6)
                elif s_price is None and c_price is None:
                    s_price = 250000.0
                    c_price = 150000.0

                try:
                    stock_val = int(float(row[col_map["stock_quantity"]])) if "stock_quantity" in col_map and pd.notna(row[col_map["stock_quantity"]]) else 50
                except Exception:
                    stock_val = 50

                if sku_val in existing_skus:
                    # Cập nhật sản phẩm
                    cursor.execute("""
                        UPDATE products
                        SET name = ?, category_id = ?, cost_price = ?, selling_price = ?, stock_quantity = ?
                        WHERE id = ?
                    """, (name_val, cat_id, c_price, s_price, stock_val, existing_skus[sku_val]))
                    updated_count += 1
                else:
                    # Tạo sản phẩm mới
                    cursor.execute("""
                        INSERT INTO products (sku, name, category_id, cost_price, selling_price, stock_quantity, user_id)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (sku_val, name_val, cat_id, c_price, s_price, stock_val, user_id))
                    created_count += 1
                    existing_skus[sku_val] = True

            conn.commit()
            conn.close()

            return {
                "success": True,
                "created_count": created_count,
                "updated_count": updated_count,
                "warnings": warnings,
                "message": f"Nạp danh sách sản phẩm thành công! Thêm mới {created_count} sản phẩm, cập nhật {updated_count} sản phẩm."
            }
        except Exception as e:
            conn.close()
            raise e
