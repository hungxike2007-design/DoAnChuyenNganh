import sqlite3

from backend.modules.audit import audit_service


def test_audit_log_persists_and_filters(monkeypatch, tmp_path):
    db_path = tmp_path / "audit.sqlite"

    def connect():
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn

    monkeypatch.setattr(audit_service, "get_db_connection", connect)
    monkeypatch.setattr(audit_service, "DB_TYPE", "sqlite")
    saved = audit_service.AuditService.record_audit(
        "UPDATE_PRICE", "user_product_prices", "user:2,product:7", 1,
        "admin@example.com", "admin", {"price": 250000}, {"price": 210000},
        "127.0.0.1", "pytest"
    )

    assert saved
    logs = audit_service.AuditService.get_audit_logs(action="UPDATE_PRICE", search="admin@example.com")
    assert len(logs) == 1
    assert logs[0]["user_agent"] == "pytest"
    detail = audit_service.AuditService.get_audit_log_detail(logs[0]["id"])
    assert detail["old_value"] == '{"price": 250000}'
    assert detail["new_value"] == '{"price": 210000}'
