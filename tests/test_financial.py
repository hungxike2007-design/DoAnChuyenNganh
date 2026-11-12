import sqlite3

import pytest

from backend.modules.financial import financial_service


def make_financial_db(revenue=100_000_000, cogs=60_000_000, expenses=(10_000_000, 15_000_000, 5_000_000)):
    conn = sqlite3.connect(":memory:")
    conn.row_factory = lambda cur, row: dict(zip([col[0] for col in cur.description], row))
    conn.executescript("""
        CREATE TABLE orders (id INTEGER, status TEXT, total_amount REAL, discount_amount REAL,
            net_amount REAL, created_at TEXT, channel TEXT);
        CREATE TABLE order_items (order_id INTEGER, quantity INTEGER, cost_price REAL);
        CREATE TABLE financial_expenses (month_year TEXT, channel TEXT, rent_expense REAL,
            salary_expense REAL, marketing_expense REAL, utilities_expense REAL,
            other_expense REAL, note TEXT);
    """)
    if revenue:
        conn.execute("INSERT INTO orders VALUES (1, 'completed', ?, 0, ?, '2026-10-12 10:00:00', 'Shopee')", (revenue, revenue))
        conn.execute("INSERT INTO order_items VALUES (1, 1, ?)", (cogs,))
    if any(expenses):
        conn.execute("INSERT INTO financial_expenses VALUES ('2026-10', 'All', ?, ?, ?, 0, 0, '')", expenses)
    return conn


def report_with_db(monkeypatch, **kwargs):
    conn = make_financial_db(**kwargs)
    monkeypatch.setattr(financial_service, "get_db_connection", lambda: conn)
    monkeypatch.setattr(financial_service, "DB_TYPE", "sqlite")
    return financial_service.FinancialService.get_pnl_report(10, 2026)


def test_gross_profit_and_ebitda_calculation(monkeypatch):
    report = report_with_db(monkeypatch)
    assert report["summary"]["gross_profit"] == 40_000_000
    assert report["summary"]["gross_margin"] == 40.0
    assert report["summary"]["ebitda"] == 10_000_000
    assert report["summary"]["net_margin"] == 10.0


def test_zero_revenue_has_zero_margins(monkeypatch):
    report = report_with_db(monkeypatch, revenue=0, expenses=(0, 0, 0))
    assert report["summary"]["net_revenue"] == 0
    assert report["summary"]["gross_margin"] == 0
    assert report["summary"]["net_margin"] == 0


@pytest.mark.parametrize(("current", "previous", "expected"), [(110, 100, 10.0), (0, 0, 0.0), (50, 0, 100.0)])
def test_month_over_month_edge_cases(current, previous, expected):
    assert financial_service.calc_mom(current, previous) == expected
