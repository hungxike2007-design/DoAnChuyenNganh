import sqlite3

from backend.modules.dashboard import analytics_service


def test_customer_segments_return_expected_groups(monkeypatch):
    conn = sqlite3.connect(":memory:")
    conn.row_factory = lambda cur, row: dict(zip([col[0] for col in cur.description], row))
    conn.create_function("VARCHAR", 1, lambda value: value)
    conn.create_function("CONVERT", 3, lambda _type, value, _style: str(value)[:10] if value else None)
    conn.executescript("""
        CREATE TABLE customers (id INTEGER, name TEXT, email TEXT, phone TEXT, city TEXT,
            segment TEXT, total_spent REAL, orders_count INTEGER, last_order_date TEXT, user_id INTEGER);
        INSERT INTO customers VALUES (1, 'VIP buyer', 'vip@example.com', '', '', 'VIP', 12000000, 5, '2026-11-12', 1);
        INSERT INTO customers VALUES (2, 'At risk', 'risk@example.com', '', '', 'At-Risk', 6000000, 3, '2026-01-01', 1);
        INSERT INTO customers VALUES (3, 'New buyer', 'new@example.com', '', '', 'New', 100000, 1, '2026-11-12', 1);
    """)
    monkeypatch.setattr(analytics_service, "get_db_connection", lambda: conn)

    result = analytics_service.AnalyticsService.get_customer_segments(user_id=1)
    assert {row["segment"]: row["customer_count"] for row in result["segments"]} == {"VIP": 1, "At-Risk": 1, "New": 1}
    assert len(result["topCustomers"]) == 3
