import pytest
from fastapi import HTTPException

from backend.modules.auth.auth_router import require_roles
from backend.modules.dashboard import revenue_router


def test_kpi_endpoint_returns_expected_fields(monkeypatch):
    monkeypatch.setattr(revenue_router.AnalyticsService, "get_kpis", lambda days, user_id=None: {
        "totalRevenue": 100, "grossProfit": 40, "aov": 50, "cancelRate": 0
    })
    result = revenue_router.get_kpis(days=180, view_user_id=None, user={"sub": "1", "role": "admin"})
    assert result["success"] is True
    assert {"totalRevenue", "grossProfit", "aov", "cancelRate"} <= result["data"].keys()


def test_sales_role_cannot_open_admin_only_audit_api():
    checker = require_roles("admin")
    with pytest.raises(HTTPException) as exc_info:
        checker(user={"sub": "2", "role": "sales"})
    assert exc_info.value.status_code == 403


def test_orders_endpoint_works_on_sqlite(monkeypatch):
    import sqlite3
    from backend.modules.dashboard import revenue_router

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            phone TEXT,
            email TEXT,
            city TEXT,
            user_id INTEGER
        );
        CREATE TABLE products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sku TEXT,
            name TEXT,
            selling_price REAL,
            cost_price REAL,
            stock_quantity INTEGER,
            user_id INTEGER
        );
        CREATE TABLE orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_code TEXT,
            customer_id INTEGER,
            channel TEXT,
            total_amount REAL,
            discount_amount REAL,
            net_amount REAL,
            payment_method TEXT,
            status TEXT,
            order_date TEXT,
            user_id INTEGER
        );
        CREATE TABLE order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER,
            product_id INTEGER,
            quantity INTEGER,
            unit_price REAL,
            cost_price REAL,
            total_price REAL
        );
        INSERT INTO customers (name, phone, email, city, user_id) VALUES ('Alice', '0901', 'a@example.com', 'HCM', 1);
        INSERT INTO products (sku, name, selling_price, cost_price, stock_quantity, user_id) VALUES ('SKU-1', 'Laptop', 20, 10, 5, 1);
        INSERT INTO orders (order_code, customer_id, channel, total_amount, discount_amount, net_amount, payment_method, status, order_date, user_id)
        VALUES ('A1001', 1, 'Shopee', 20, 0, 20, 'COD', 'completed', '2026-11-12 09:00:00', 1);
        INSERT INTO order_items (order_id, product_id, quantity, unit_price, cost_price, total_price) VALUES (1, 1, 1, 20, 10, 20);
    """)

    monkeypatch.setattr(revenue_router, "get_db_connection", lambda: conn)
    monkeypatch.setattr(revenue_router, "DB_TYPE", "sqlite")

    result = revenue_router.get_orders(limit=10, channel="All", status="All", user={"sub": "1", "role": "sales"})

    assert result["success"] is True
    assert result["data"] and result["data"][0]["order_code"] == "A1001"


def test_orders_endpoint_hides_orders_from_other_users(monkeypatch):
    import sqlite3
    from backend.modules.dashboard import revenue_router

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            phone TEXT,
            email TEXT,
            city TEXT,
            user_id INTEGER
        );
        CREATE TABLE products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sku TEXT,
            name TEXT,
            selling_price REAL,
            cost_price REAL,
            stock_quantity INTEGER,
            user_id INTEGER
        );
        CREATE TABLE orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_code TEXT,
            customer_id INTEGER,
            channel TEXT,
            total_amount REAL,
            discount_amount REAL,
            net_amount REAL,
            payment_method TEXT,
            status TEXT,
            order_date TEXT,
            user_id INTEGER
        );
        CREATE TABLE order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER,
            product_id INTEGER,
            quantity INTEGER,
            unit_price REAL,
            cost_price REAL,
            total_price REAL
        );
        INSERT INTO customers (name, phone, email, city, user_id) VALUES ('Alice', '0901', 'a@example.com', 'HCM', 1);
        INSERT INTO products (sku, name, selling_price, cost_price, stock_quantity, user_id) VALUES ('SKU-1', 'Laptop', 20, 10, 5, 1);
        INSERT INTO orders (order_code, customer_id, channel, total_amount, discount_amount, net_amount, payment_method, status, order_date, user_id)
        VALUES ('OWN-1', 1, 'Shopee', 20, 0, 20, 'COD', 'completed', '2026-11-12 09:00:00', 42),
               ('OTHER-1', 1, 'Website', 50, 0, 50, 'COD', 'completed', '2026-11-12 10:00:00', 99),
               ('LEGACY-1', 1, 'TikTok Shop', 30, 0, 30, 'COD', 'completed', '2026-11-12 11:00:00', NULL);
        INSERT INTO order_items (order_id, product_id, quantity, unit_price, cost_price, total_price) VALUES (1, 1, 1, 20, 10, 20), (2, 1, 1, 50, 10, 50), (3, 1, 1, 30, 10, 30);
    """)

    monkeypatch.setattr(revenue_router, "get_db_connection", lambda: conn)
    monkeypatch.setattr(revenue_router, "DB_TYPE", "sqlite")

    result = revenue_router.get_orders(limit=10, channel="All", status="All", user={"sub": "42", "role": "sales"})

    assert result["success"] is True
    assert [row["order_code"] for row in result["data"]] == ["OWN-1"]


def test_orders_endpoint_does_not_send_unused_mssql_limit_parameter(monkeypatch):
    class FakeCursor:
        def __init__(self):
            self.query = None
            self.params = None

        def execute(self, query, params):
            self.query = query
            self.params = params

        def fetchall(self):
            return []

    class FakeConnection:
        def __init__(self):
            self.fake_cursor = FakeCursor()

        def cursor(self):
            return self.fake_cursor

        def close(self):
            pass

    conn = FakeConnection()
    monkeypatch.setattr(revenue_router, "get_db_connection", lambda: conn)
    monkeypatch.setattr(revenue_router, "DB_TYPE", "mssql")

    result = revenue_router.get_orders(
        limit=10,
        channel="All",
        status="All",
        view_user_id=None,
        user={"sub": "1", "role": "admin"},
    )

    assert result == {"success": True, "data": []}
    assert "FETCH NEXT 10 ROWS ONLY" in conn.fake_cursor.query
    assert conn.fake_cursor.params == ()
