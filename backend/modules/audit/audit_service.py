import json
from typing import Any, Dict, List, Optional

from backend.config.db import DB_TYPE, get_db_connection


class AuditService:
    @staticmethod
    def ensure_schema() -> None:
        conn = get_db_connection()
        cursor = conn.cursor()
        if DB_TYPE == "mssql":
            cursor.execute("""
                IF OBJECT_ID('dbo.audit_logs', 'U') IS NULL
                CREATE TABLE dbo.audit_logs (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    user_id INT NULL,
                    user_email NVARCHAR(150) NOT NULL DEFAULT '',
                    user_role NVARCHAR(50) NOT NULL DEFAULT '',
                    action NVARCHAR(50) NOT NULL,
                    target_table NVARCHAR(50) NOT NULL,
                    target_id NVARCHAR(100) NOT NULL DEFAULT '',
                    old_value NVARCHAR(MAX) NOT NULL DEFAULT '',
                    new_value NVARCHAR(MAX) NOT NULL DEFAULT '',
                    ip_address NVARCHAR(50) NOT NULL DEFAULT '',
                    user_agent NVARCHAR(500) NOT NULL DEFAULT '',
                    created_at DATETIME2 NOT NULL DEFAULT GETDATE()
                );
                IF COL_LENGTH('dbo.audit_logs', 'user_agent') IS NULL
                    ALTER TABLE dbo.audit_logs ADD user_agent NVARCHAR(500) NOT NULL DEFAULT '';
            """)
        else:
            cursor.execute("""CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, user_email TEXT NOT NULL DEFAULT '',
                user_role TEXT NOT NULL DEFAULT '', action TEXT NOT NULL, target_table TEXT NOT NULL,
                target_id TEXT NOT NULL DEFAULT '', old_value TEXT NOT NULL DEFAULT '',
                new_value TEXT NOT NULL DEFAULT '', ip_address TEXT NOT NULL DEFAULT '',
                user_agent TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )""")
        conn.commit()
        conn.close()

    @staticmethod
    def record_audit(action: str, target_table: str, target_id: str = "", user_id: Optional[int] = None,
                     user_email: str = "", user_role: str = "", old_value: Any = None,
                     new_value: Any = None, ip_address: str = "", user_agent: str = "") -> bool:
        conn = None
        try:
            AuditService.ensure_schema()
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""INSERT INTO audit_logs
                (user_id, user_email, user_role, action, target_table, target_id,
                 old_value, new_value, ip_address, user_agent)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", (
                    user_id, user_email or "", user_role or "", action, target_table,
                    str(target_id or ""),
                    json.dumps(old_value, ensure_ascii=False) if old_value is not None else "",
                    json.dumps(new_value, ensure_ascii=False) if new_value is not None else "",
                    ip_address or "", user_agent or ""
                ))
            conn.commit()
            return True
        except Exception as exc:
            print(f"[AuditService] Không thể ghi audit log: {exc}")
            return False
        finally:
            if conn:
                conn.close()

    @staticmethod
    def get_audit_logs(limit: int = 50, action: Optional[str] = None, search: Optional[str] = None,
                       from_date: Optional[str] = None, to_date: Optional[str] = None) -> List[Dict[str, Any]]:
        AuditService.ensure_schema()
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            sql = "SELECT id, user_id, user_email, user_role, action, target_table, target_id, old_value, new_value, ip_address, user_agent, created_at FROM audit_logs WHERE 1=1"
            params = []
            if action and action.upper() != "ALL":
                sql += " AND action = ?"
                params.append(action)
            if search:
                sql += " AND user_email LIKE ?"
                params.append(f"%{search.strip()}%")
            if from_date:
                sql += " AND created_at >= ?"
                params.append(f"{from_date} 00:00:00")
            if to_date:
                sql += " AND created_at < ?"
                params.append(f"{to_date} 23:59:59.999")
            if DB_TYPE == "mssql":
                sql += " ORDER BY id DESC OFFSET 0 ROWS FETCH NEXT ? ROWS ONLY"
            else:
                sql += " ORDER BY id DESC LIMIT ?"
            params.append(limit)
            cursor.execute(sql, tuple(params))
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    @staticmethod
    def get_audit_log_detail(log_id: int) -> Optional[Dict[str, Any]]:
        AuditService.ensure_schema()
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id, user_id, user_email, user_role, action, target_table, target_id, old_value, new_value, ip_address, user_agent, created_at FROM audit_logs WHERE id = ?", (log_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()
