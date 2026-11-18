"""
Bộ kiểm thử toàn diện toàn bộ các chức năng từ cũ đến mới (End-to-End API Test Suite)
Kiểm tra từng phân hệ: Auth, Dashboard, Products, Orders, RFM, Financial, Pivot, AI, Planner, Audit, Import.
"""
import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def get_auth_client(email, password="123456"):
    c = TestClient(app)
    res = c.post("/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, f"Login failed for {email}: {res.text}"
    return c

class TestHealthAndStatic:
    def test_health_check(self):
        res = client.get("/api/health")
        assert res.status_code == 200
        assert res.json()["status"] == "healthy"

    def test_root_redirect(self):
        res = client.get("/", follow_redirects=False)
        assert res.status_code in (301, 302, 307, 308)
        assert "/frontend/index.html" in res.headers["location"]

    def test_legacy_static_redirect(self):
        res = client.get("/static/dashboard.html", follow_redirects=False)
        assert res.status_code in (301, 302, 307, 308)
        assert "dashboard.html" in res.headers["location"]


class TestAuthModule:
    def test_admin_login_success(self):
        res = client.post("/api/auth/login", json={"email": "admin@dacn.vn", "password": "123456"})
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["data"]["user"]["role"] == "admin"
        assert "dacn_token" in res.cookies

    def test_manager_login_success(self):
        res = client.post("/api/auth/login", json={"email": "manager@dacn.vn", "password": "123456"})
        assert res.status_code == 200
        assert res.json()["data"]["user"]["role"] == "manager"

    def test_login_invalid_password(self):
        res = client.post("/api/auth/login", json={"email": "admin@dacn.vn", "password": "wrongpassword"})
        assert res.status_code == 401

    def test_get_me_with_cookie(self):
        c = get_auth_client("admin@dacn.vn")
        res = c.get("/api/auth/me")
        assert res.status_code == 200
        assert res.json()["data"]["email"] == "admin@dacn.vn"

    def test_get_me_unauthorized(self):
        c = TestClient(app)
        res = c.get("/api/auth/me")
        assert res.status_code == 401

    def test_admin_get_users_list(self):
        c = get_auth_client("admin@dacn.vn")
        res = c.get("/api/auth/users")
        assert res.status_code == 200
        assert len(res.json()["data"]) > 0

    def test_user_cannot_get_users_list(self):
        c_user = get_auth_client("user@dacn.vn")
        res = c_user.get("/api/auth/users")
        assert res.status_code == 403

    def test_update_user_role(self):
        c = get_auth_client("admin@dacn.vn")
        res = c.put("/api/auth/users/5/role", json={"role": "user"})
        assert res.status_code == 200
        assert res.json()["success"] is True

    def test_forgot_password_flow(self):
        res = client.post("/api/auth/forgot-password", json={"email": "admin@dacn.vn"})
        assert res.status_code == 200
        assert res.json()["success"] is True

    def test_logout(self):
        c = get_auth_client("admin@dacn.vn")
        res = c.post("/api/auth/logout")
        assert res.status_code == 200
        # Cookie should be cleared
        res_me = c.get("/api/auth/me")
        assert res_me.status_code == 401


class TestDashboardAndRevenueModule:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.admin = get_auth_client("admin@dacn.vn")

    def test_kpis(self):
        res = self.admin.get("/api/revenue/kpis?days=180")
        assert res.status_code == 200
        data = res.json()["data"]
        assert "totalRevenue" in data
        assert "grossProfit" in data
        assert "aov" in data

    def test_timeline(self):
        res = self.admin.get("/api/revenue/timeline?days=30")
        assert res.status_code == 200
        data = res.json()["data"]
        assert isinstance(data, list) or "timeline" in data

    def test_channels(self):
        res = self.admin.get("/api/revenue/channels?days=180")
        assert res.status_code == 200
        data = res.json()["data"]
        assert isinstance(data, list) or "channels" in data

    def test_top_products(self):
        res = self.admin.get("/api/revenue/top-products?limit=8")
        assert res.status_code == 200
        assert isinstance(res.json()["data"], list)

    def test_inventory_alerts(self):
        res = self.admin.get("/api/revenue/inventory-alerts?threshold=40")
        assert res.status_code == 200
        assert isinstance(res.json()["data"], list)

    def test_rfm(self):
        res = self.admin.get("/api/revenue/rfm")
        assert res.status_code == 200
        data = res.json()["data"]
        assert isinstance(data, list) or "customers" in data or "segments" in data

    def test_user_rankings(self):
        res = self.admin.get("/api/revenue/user-rankings")
        assert res.status_code == 200
        assert isinstance(res.json()["data"], list)

    def test_get_orders(self):
        res = self.admin.get("/api/revenue/orders?limit=20")
        assert res.status_code == 200
        assert isinstance(res.json()["data"], list)
        assert len(res.json()["data"]) > 0

    def test_create_order_existing_product(self):
        payload = {
            "channel": "Website",
            "customerId": 1,
            "paymentMethod": "COD",
            "items": [{"productId": 1, "quantity": 1, "unitPrice": 249000}]
        }
        res = self.admin.post("/api/revenue/orders", json=payload)
        assert res.status_code == 200
        assert res.json()["success"] is True
        assert "order_id" in res.json()["data"]

    def test_create_order_custom_product(self):
        payload = {
            "channel": "Shopee",
            "customerId": 1,
            "paymentMethod": "Chuyển khoản QR",
            "items": [{"productName": "Sản phẩm Tùy biến E2E", "quantity": 2, "unitPrice": 150000}]
        }
        res = self.admin.post("/api/revenue/orders", json=payload)
        assert res.status_code == 200
        assert res.json()["success"] is True


class TestProductsModule:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.admin = get_auth_client("admin@dacn.vn")

    def test_get_products(self):
        res = self.admin.get("/api/products/")
        assert res.status_code == 200
        assert len(res.json()["data"]) > 0

    def test_get_categories(self):
        res = self.admin.get("/api/products/categories")
        assert res.status_code == 200
        assert len(res.json()["data"]) > 0

    def test_create_product(self):
        import random
        sku = f"SKU-E2E-{random.randint(10000, 99999)}"
        payload = {
            "sku": sku,
            "name": "Sản phẩm Kiểm thử E2E",
            "categoryId": 1,
            "costPrice": 50000,
            "sellingPrice": 120000,
            "stockQuantity": 80
        }
        res = self.admin.post("/api/products/", json=payload)
        assert res.status_code == 200
        assert res.json()["success"] is True

    def test_get_custom_prices(self):
        res = self.admin.get("/api/products/custom-prices")
        assert res.status_code == 200

    def test_set_and_delete_custom_price(self):
        # Thiết lập giá riêng
        res = self.admin.post("/api/products/custom-price", json={
            "userId": 5,
            "productId": 1,
            "customPrice": 220000,
            "note": "Giá sỉ đại lý E2E"
        })
        assert res.status_code == 200
        assert res.json()["success"] is True

        # Tìm ID của giá riêng vừa tạo để xóa
        res_list = self.admin.get("/api/products/custom-prices")
        assert res_list.status_code == 200
        matching = [item for item in res_list.json()["data"] if item["user_id"] == 5 and item["product_id"] == 1]
        assert len(matching) > 0
        price_id = matching[0]["id"]

        # Hủy giá riêng
        res_del = self.admin.delete(f"/api/products/custom-price/{price_id}")
        assert res_del.status_code == 200
        assert res_del.json()["success"] is True


class TestFinancialModule:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.admin = get_auth_client("admin@dacn.vn")

    def test_pnl_report(self):
        res = self.admin.get("/api/financial/pnl-report")
        assert res.status_code == 200
        data = res.json()["data"]
        assert "summary" in data
        assert "statement" in data

    def test_get_expenses(self):
        res = self.admin.get("/api/financial/expenses")
        assert res.status_code == 200

    def test_upsert_expense(self):
        payload = {
            "month_year": "2026-11",
            "channel": "All",
            "rent_expense": 15000000,
            "salary_expense": 25000000,
            "marketing_expense": 15000000,
            "utilities_expense": 5000000,
            "other_expense": 0,
            "note": "Chi phí kiểm thử tự động"
        }
        res = self.admin.post("/api/financial/expenses", json=payload)
        assert res.status_code == 200
        assert res.json()["success"] is True


class TestPivotModule:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.admin = get_auth_client("admin@dacn.vn")

    def test_pivot_metadata(self):
        res = self.admin.get("/api/analytics/pivot/metadata")
        assert res.status_code == 200
        data = res.json()["data"]
        assert "dimensions" in data
        assert "metrics" in data

    def test_pivot_matrix(self):
        payload = {
            "row_dim": "channel",
            "col_dim": "category",
            "val_metric": "net_amount",
            "agg_func": "sum"
        }
        res = self.admin.post("/api/analytics/pivot/matrix", json=payload)
        assert res.status_code == 200
        data = res.json()["data"]
        assert "matrix" in data
        assert "row_headers" in data


class TestAIAndPlannerModule:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.admin = get_auth_client("admin@dacn.vn")

    def test_planner_baseline(self):
        res = self.admin.get("/api/planner/baseline?days=30")
        assert res.status_code == 200
        assert "baselineRevenue" in res.json()["data"]

    def test_planner_history(self):
        res = self.admin.get("/api/planner/history")
        assert res.status_code == 200

    def test_copilot_history(self):
        res = self.admin.get("/api/ai/copilot/history")
        assert res.status_code == 200

    def test_marketing_history(self):
        res = self.admin.get("/api/ai/marketing-history")
        assert res.status_code == 200


class TestAuditModule:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.admin = get_auth_client("admin@dacn.vn")

    def test_get_audit_logs(self):
        res = self.admin.get("/api/audit/logs")
        assert res.status_code == 200
        assert isinstance(res.json()["data"], list)


class TestImportModule:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.admin = get_auth_client("admin@dacn.vn")

    def test_download_orders_template(self):
        res = self.admin.get("/api/import/template/orders")
        assert res.status_code == 200

    def test_download_products_template(self):
        res = self.admin.get("/api/import/template/products")
        assert res.status_code == 200

    def test_import_orders_csv(self):
        # Tải template và nạp lại
        tmpl = self.admin.get("/api/import/template/orders").text
        files = {"file": ("test_orders.csv", tmpl.encode("utf-8"), "text/csv")}
        res = self.admin.post("/api/import/orders", files=files)
        assert res.status_code == 200
        assert res.json()["success"] is True

    def test_import_products_csv(self):
        tmpl = self.admin.get("/api/import/template/products").text
        files = {"file": ("test_products.csv", tmpl.encode("utf-8"), "text/csv")}
        res = self.admin.post("/api/import/products", files=files)
        assert res.status_code == 200
        assert res.json()["success"] is True
