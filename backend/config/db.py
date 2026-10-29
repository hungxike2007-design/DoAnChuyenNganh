"""
==============================================================================
MODULE KẾT NỐI CƠ SỞ DỮ LIỆU SQL SERVER / SQLITE (DATABASE ADAPTER)
==============================================================================
Chức năng:
- Kết nối trực tiếp tới Microsoft SQL Server (SSMS) qua ODBC Driver 17 / SQL Server.
- Cấu hình linh hoạt qua file .env (Server, Database, Trusted_Connection hoặc User/Password).
- Hỗ trợ Row Factory chuyển đổi kết quả truy vấn thành Dictionary tiện lợi.
- KHÔNG TỰ ĐỘNG RE-CREATE HOẶC SEED LẠI CSDL MỖI KHI CHẠY (Dữ liệu nằm cố định trong SQL).
==============================================================================
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(ROOT_DIR / ".env")

DB_TYPE = os.getenv("DB_TYPE", "mssql").strip().lower()
DB_SERVER = os.getenv("DB_SERVER", "localhost").strip()
DB_DATABASE = os.getenv("DB_DATABASE", "RevenueSystemDB").strip()
DB_TRUSTED = os.getenv("DB_TRUSTED_CONNECTION", "yes").strip()
DB_USER = os.getenv("DB_USER", "").strip()
DB_PASSWORD = os.getenv("DB_PASSWORD", "").strip()


class DictCursorWrapper:
    """Wrapper cho cursor pyodbc để fetchone() và fetchall() trả về dict giống sqlite3.Row."""
    def __init__(self, cursor):
        self.cursor = cursor
        self._last_id = None

    def execute(self, sql, params=()):
        result = self.cursor.execute(sql, params)
        return result

    def executemany(self, sql, seq_of_params):
        return self.cursor.executemany(sql, seq_of_params)

    def fetchone(self):
        row = self.cursor.fetchone()
        if row is None:
            return None
        cols = [c[0] for c in self.cursor.description]
        return dict(zip(cols, row))

    def fetchall(self):
        rows = self.cursor.fetchall()
        if not rows:
            return []
        cols = [c[0] for c in self.cursor.description]
        return [dict(zip(cols, r)) for r in rows]

    @property
    def lastrowid(self):
        try:
            self.cursor.execute("SELECT @@IDENTITY")
            row = self.cursor.fetchone()
            return int(row[0]) if row and row[0] is not None else None
        except Exception:
            return None

    def close(self):
        self.cursor.close()


class DBConnectionWrapper:
    """Wrapper quản lý kết nối và commit tự động."""
    def __init__(self, raw_conn):
        self.raw_conn = raw_conn

    def cursor(self):
        return DictCursorWrapper(self.raw_conn.cursor())

    def commit(self):
        self.raw_conn.commit()

    def rollback(self):
        self.raw_conn.rollback()

    def close(self):
        self.raw_conn.close()


def get_db_connection():
    """Khởi tạo và trả về kết nối tới SQL Server."""
    if DB_TYPE == "mssql":
        try:
            import pyodbc
            drivers = pyodbc.drivers()
            driver = "ODBC Driver 17 for SQL Server" if "ODBC Driver 17 for SQL Server" in drivers else "SQL Server"
            
            # Danh sách server ứng viên (ưu tiên cấu hình trong .env, dự phòng localhost và .)
            candidate_servers = [DB_SERVER]
            for fb in ["localhost", ".", "127.0.0.1"]:
                if fb not in candidate_servers:
                    candidate_servers.append(fb)

            last_error = None
            for srv in candidate_servers:
                try:
                    if DB_TRUSTED.lower() in ("yes", "true", "1"):
                        conn_str = f"Driver={{{driver}}};Server={srv};Database={DB_DATABASE};Trusted_Connection=yes;TrustServerCertificate=yes;"
                    else:
                        conn_str = f"Driver={{{driver}}};Server={srv};Database={DB_DATABASE};UID={DB_USER};PWD={DB_PASSWORD};TrustServerCertificate=yes;"

                    raw_conn = pyodbc.connect(conn_str, autocommit=False, timeout=3)
                    return DBConnectionWrapper(raw_conn)
                except Exception as ex:
                    last_error = ex
                    continue

            print(f"❌ [Database] Không thể kết nối tới SQL Server: {last_error}", file=sys.stderr)
            raise ConnectionError(f"Lỗi kết nối Microsoft SQL Server ({DB_DATABASE}): {str(last_error)}")
        except Exception as e:
            if not isinstance(e, ConnectionError):
                print(f"❌ [Database] Lỗi kết nối CSDL: {e}", file=sys.stderr)
            raise

    # Dự phòng SQLite nếu DB_TYPE = sqlite
    import sqlite3
    db_path = ROOT_DIR / os.getenv("DATABASE_PATH", "data/revenue_system.sqlite")
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def test_connection():
    """Kiểm tra kết nối tới cơ sở dữ liệu SQL Server."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT @@VERSION")
        row = cursor.cursor.fetchone()
        conn.close()
        print(f"✅ [Database] Kết nối thành công tới Microsoft SQL Server (Database: {DB_DATABASE})!", flush=True)
        return True
    except Exception as e:
        print(f"⚠️ [Database] Kiểm tra kết nối SQL Server thất bại: {e}", flush=True)
        return False


if __name__ == "__main__":
    test_connection()
