"""
==============================================================================
DỊCH VỤ NHẬT KÝ KIỂM TOÁN HOẠT ĐỘNG (AUDIT LOG SERVICE)
==============================================================================
Chức năng:
- Tự động ghi lại các hành vi nhạy cảm: sửa giá B2B, cập nhật OPEX, đổi quyền người dùng, nạp file.
- Lưu trữ old_value và new_value dạng JSON để so sánh diff trực quan.
- Truy vấn danh sách và chi tiết log có lọc theo hành động, tìm kiếm email và ngày tháng.
==============================================================================
"""

import json
from datetime import datetime
from typing import Optional, Dict, Any, List
try:
    from backend.config.db import get_db_connection
except ImportError:
    from config.db import get_db_connection


class AuditService:
    @staticmethod
    def record_audit(
        action: str,
        target_table: str,
        target_id: Optional[str] = "",
        user_id: Optional[int] = None,
        user_email: Optional[str] = "",
        user_role: Optional[str] = "",
        old_value: Optional[Any] = None,
        new_value: Optional[Any] = None,
        ip_address: Optional[str] = ""
    ) -> bool:
        """
        Ghi một bản ghi kiểm toán vào CSDL.
        Bọc trong khối try/except an toàn để không bao giờ làm gián đoạn luồng nghiệp vụ chính.
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            old_str = json.dumps(old_value, ensure_ascii=False) if isinstance(old_value, (dict, list)) else (str(old_value) if old_value is not None else "")
            new_str = json.dumps(new_value, ensure_ascii=False) if isinstance(new_value, (dict, list)) else (str(new_value) if new_value is not None else "")

            sql = """
                INSERT INTO audit_logs (
                    user_id, user_email, user_role, action, target_table,
                    target_id, old_value, new_value, ip_address
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            cursor.execute(sql, (
                user_id,
                user_email or "",
                user_role or "",
                action,
                target_table,
                str(target_id) if target_id is not None else "",
                old_str,
                new_str,
                ip_address or ""
            ))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"⚠️ [AuditService] Lỗi khi ghi nhật ký kiểm toán: {e}")
            return False

    @staticmethod
    def get_audit_logs(
        limit: int = 50,
        action: Optional[str] = None,
        search: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Lấy danh sách nhật ký kiểm toán có phân trang và bộ lọc."""
        conn = get_db_connection()
        cursor = conn.cursor()

        sql = """
            SELECT id, user_id, user_email, user_role, action, target_table,
                   target_id, old_value, new_value, ip_address, created_at
            FROM audit_logs
            WHERE 1=1
        """
        params = []

        if action and action.upper() != "ALL":
            sql += " AND action = ?"
            params.append(action)

        if search:
            sql += " AND (user_email LIKE ? OR target_id LIKE ?)"
            term = f"%{search.strip()}%"
            params.extend([term, term])

        if from_date:
            sql += " AND created_at >= ?"
            params.append(f"{from_date} 00:00:00")

        if to_date:
            sql += " AND created_at <= ?"
            params.append(f"{to_date} 23:59:59")

        sql += " ORDER BY id DESC"

        # Tương thích LIMIT / OFFSET
        import os
        if os.getenv("DB_TYPE", "mssql").strip().lower() == "mssql":
            sql += " OFFSET 0 ROWS FETCH NEXT ? ROWS ONLY"
        else:
            sql += " LIMIT ?"
        params.append(limit)

        cursor.execute(sql, tuple(params))
        rows = cursor.fetchall()
        conn.close()

        result = []
        for r in rows:
            item = dict(r)
            # Thử parse JSON preview
            try:
                item["old_value_parsed"] = json.loads(item["old_value"]) if item.get("old_value") else None
            except Exception:
                item["old_value_parsed"] = item.get("old_value")

            try:
                item["new_value_parsed"] = json.loads(item["new_value"]) if item.get("new_value") else None
            except Exception:
                item["new_value_parsed"] = item.get("new_value")

            result.append(item)

        return result

    @staticmethod
    def get_audit_log_detail(log_id: int) -> Optional[Dict[str, Any]]:
        """Lấy chi tiết 1 bản ghi kiểm toán kèm parsed JSON."""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, user_id, user_email, user_role, action, target_table,
                   target_id, old_value, new_value, ip_address, created_at
            FROM audit_logs
            WHERE id = ?
        """, (log_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        data = dict(row)
        try:
            data["old_value_parsed"] = json.loads(data["old_value"]) if data.get("old_value") else None
        except Exception:
            data["old_value_parsed"] = data.get("old_value")

        try:
            data["new_value_parsed"] = json.loads(data["new_value"]) if data.get("new_value") else None
        except Exception:
            data["new_value_parsed"] = data.get("new_value")

        return data
