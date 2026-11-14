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
import re
import sys
import threading
from pathlib import Path
from dotenv import load_dotenv

try:
    import pyodbc
    # SQLAlchemy's QueuePool is the single pool for MSSQL connections.
    pyodbc.pooling = False
except ImportError:
    pyodbc = None

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(ROOT_DIR / ".env")

DB_TYPE = os.getenv("DB_TYPE", "sqlite").strip().lower()
DB_SERVER = os.getenv("DB_SERVER", "localhost").strip()
DB_DATABASE = os.getenv("DB_DATABASE", "RevenueSystemDB").strip()
DB_TRUSTED = os.getenv("DB_TRUSTED_CONNECTION", "yes").strip()
DB_USER = os.getenv("DB_USER", "").strip()
DB_PASSWORD = os.getenv("DB_PASSWORD", "").strip()
DB_POOL_SIZE = max(1, int(os.getenv("DB_POOL_SIZE", "10")))
DB_POOL_TIMEOUT = max(1, int(os.getenv("DB_POOL_TIMEOUT", "30")))
_MSSQL_ENGINES = {}
_MSSQL_ENGINES_LOCK = threading.Lock()


class DictCursorWrapper:
    """Wrapper cho cursor pyodbc để fetchone() và fetchall() trả về dict giống sqlite3.Row."""
    def __init__(self, cursor):
        self.cursor = cursor
        self._last_id = None

    def execute(self, sql, params=()):
        self._last_id = None
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
        # MSSQL identity IDs are captured by OUTPUT INSERTED.id in the INSERT batch.
        return self._last_id

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
            from sqlalchemy import create_engine
            from sqlalchemy.engine import URL

            if pyodbc is None:
                raise RuntimeError("pyodbc is required when DB_TYPE=mssql")
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
                        conn_str = f"Driver={{{driver}}};Server={srv};Database={DB_DATABASE};Trusted_Connection=yes;TrustServerCertificate=yes;APP=RevenueSystemAPI;"
                    else:
                        conn_str = f"Driver={{{driver}}};Server={srv};Database={DB_DATABASE};UID={DB_USER};PWD={DB_PASSWORD};TrustServerCertificate=yes;APP=RevenueSystemAPI;"

                    engine_key = (srv, DB_DATABASE, driver, DB_TRUSTED.lower(), DB_USER)
                    with _MSSQL_ENGINES_LOCK:
                        engine = _MSSQL_ENGINES.get(engine_key)
                        if engine is None:
                            engine = create_engine(
                                URL.create("mssql+pyodbc", query={"odbc_connect": conn_str}),
                                pool_size=DB_POOL_SIZE,
                                max_overflow=0,
                                pool_timeout=DB_POOL_TIMEOUT,
                                pool_recycle=1800,
                                pool_pre_ping=True,
                                connect_args={"timeout": 3, "autocommit": False},
                            )
                            _MSSQL_ENGINES[engine_key] = engine
                    raw_conn = engine.raw_connection()
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
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    # Row factory trả về dict thuần nhất quán 100% với MSSQL DictCursorWrapper
    conn.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
    return conn


def execute_insert_and_get_id(cursor, sql: str, params=()):
    """Execute an INSERT and return its identity without a second-scope lookup."""
    db_name = getattr(cursor.connection, "__class__", type(cursor)).__name__.lower() if hasattr(cursor, "connection") else ""
    is_sqlite_cursor = "sqlite3" in db_name or "sqlite" in db_name or "sqlite" in str(type(cursor)).lower()
    if DB_TYPE != "mssql" or is_sqlite_cursor:
        cursor.execute(sql, params)
        return cursor.lastrowid

    statement = sql.strip().rstrip(";")
    if not re.match(r"INSERT\s+INTO\b", statement, flags=re.IGNORECASE):
        raise ValueError("execute_insert_and_get_id expects an INSERT INTO statement")

    if not re.search(r"\bOUTPUT\s+INSERTED\.id\b", statement, flags=re.IGNORECASE):
        values_match = re.search(r"\bVALUES\b", statement, flags=re.IGNORECASE)
        if not values_match:
            raise ValueError("MSSQL identity inserts must use VALUES or specify OUTPUT INSERTED.id")
        statement = (
            statement[:values_match.start()]
            + "OUTPUT INSERTED.id AS id\n"
            + statement[values_match.start():]
        )

    cursor.execute(statement, params)
    row = cursor.fetchone()
    if not row:
        return None
    value = row.get("id") if isinstance(row, dict) else row[0]
    value = int(value) if value is not None else None
    if hasattr(cursor, "_last_id"):
        cursor._last_id = value
    return value


def dispose_connection_pools():
    """Close idle pooled MSSQL connections during application shutdown."""
    with _MSSQL_ENGINES_LOCK:
        engines = list(_MSSQL_ENGINES.values())
        _MSSQL_ENGINES.clear()
    for engine in engines:
        engine.dispose()


def sql_date_group(column_name: str, period: str = "day") -> str:
    """Trả về biểu thức trích xuất ngày/tháng tương thích cả MSSQL & SQLite."""
    if DB_TYPE == "mssql":
        if period == "month":
            return f"CONVERT(VARCHAR(7), {column_name}, 120)"
        return f"CONVERT(VARCHAR(10), {column_name}, 120)"
    else:
        if period == "month":
            return f"strftime('%Y-%m', {column_name})"
        return f"strftime('%Y-%m-%d', {column_name})"


def sql_paginate(limit: int, offset: int = 0) -> str:
    """Trả về mệnh đề phân trang tương thích cả MSSQL & SQLite."""
    if DB_TYPE == "mssql":
        return f"OFFSET {offset} ROWS FETCH NEXT {limit} ROWS ONLY"
    return f"LIMIT {limit} OFFSET {offset}"


def sql_group_concat(expression: str, separator: str = ", ") -> str:
    """Trả về biểu thức gom chuỗi tương thích với MSSQL hoặc SQLite."""
    if DB_TYPE == "mssql":
        return f"STRING_AGG({expression}, '{separator}')"
    return f"GROUP_CONCAT({expression}, '{separator}')"


def sql_top_limit(limit: int) -> str:
    """Trả về mệnh đề lấy N bản ghi đầu tiên tương thích cả MSSQL & SQLite."""
    if DB_TYPE == "mssql":
        return f"TOP ({limit})"
    return f"LIMIT {limit}"


def sql_limit_offset(limit: int, offset: int = 0) -> str:
    """Alias giữ tương thích với các module đang import tên cũ."""
    return sql_paginate(limit, offset)


def init_db():
    """Khởi tạo cấu trúc các bảng cho SQLite khi chạy chế độ DB_TYPE=sqlite."""
    if DB_TYPE != "sqlite":
        return
    conn = get_db_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT, full_name TEXT NOT NULL, email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL, role TEXT DEFAULT 'user', avatar_url TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP, updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS password_resets (
            id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT NOT NULL, otp_code TEXT NOT NULL,
            expires_at TEXT NOT NULL, is_used INTEGER DEFAULT 0, created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE NOT NULL, description TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT, sku TEXT UNIQUE NOT NULL, name TEXT NOT NULL,
            category_id INTEGER, cost_price REAL NOT NULL, selling_price REAL NOT NULL,
            stock_quantity INTEGER NOT NULL DEFAULT 0, image_url TEXT DEFAULT '', is_active INTEGER DEFAULT 1,
            user_id INTEGER, created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, email TEXT UNIQUE NOT NULL,
            phone TEXT, city TEXT, segment TEXT DEFAULT 'New', total_spent REAL DEFAULT 0,
            orders_count INTEGER DEFAULT 0, last_order_date TEXT, user_id INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT, order_code TEXT UNIQUE NOT NULL, customer_id INTEGER,
            channel TEXT NOT NULL, total_amount REAL NOT NULL, discount_amount REAL DEFAULT 0,
            net_amount REAL NOT NULL, payment_method TEXT DEFAULT 'COD', status TEXT DEFAULT 'completed',
            order_date TEXT DEFAULT CURRENT_TIMESTAMP, created_at TEXT DEFAULT CURRENT_TIMESTAMP, user_id INTEGER
        );
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT, order_id INTEGER NOT NULL, product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL, unit_price REAL NOT NULL, cost_price REAL NOT NULL, total_price REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS financial_expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT, month_year TEXT NOT NULL, channel TEXT DEFAULT 'All',
            rent_expense REAL DEFAULT 0, salary_expense REAL DEFAULT 0, marketing_expense REAL DEFAULT 0,
            utilities_expense REAL DEFAULT 0, other_expense REAL DEFAULT 0, note TEXT DEFAULT '',
            updated_by INTEGER, updated_at TEXT DEFAULT CURRENT_TIMESTAMP, UNIQUE(month_year, channel)
        );
        CREATE TABLE IF NOT EXISTS user_product_prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, product_id INTEGER NOT NULL,
            custom_price REAL NOT NULL, note TEXT DEFAULT '', updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, product_id)
        );
        CREATE TABLE IF NOT EXISTS ai_strategy_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, strategy_type TEXT NOT NULL,
            user_prompt TEXT, ai_response TEXT NOT NULL, metrics_context TEXT, created_by INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS ai_chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, sender TEXT NOT NULL,
            message TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, user_email TEXT NOT NULL DEFAULT '',
            user_role TEXT NOT NULL DEFAULT '', action TEXT NOT NULL, target_table TEXT NOT NULL,
            target_id TEXT NOT NULL DEFAULT '', old_value TEXT NOT NULL DEFAULT '',
            new_value TEXT NOT NULL DEFAULT '', ip_address TEXT NOT NULL DEFAULT '',
            user_agent TEXT NOT NULL DEFAULT '', created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    conn.close()


def test_connection():
    """Kiểm tra kết nối tới cơ sở dữ liệu SQL Server hoặc SQLite."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        if DB_TYPE == "mssql":
            cursor.execute("SELECT @@VERSION")
            print(f"✅ [Database] Kết nối thành công tới Microsoft SQL Server (Database: {DB_DATABASE})!", flush=True)
        else:
            init_db()
            cursor.execute("SELECT 1")
            print("✅ [Database] Kết nối thành công tới SQLite (Cơ chế cục bộ / Docker)!", flush=True)
        conn.close()
        return True
    except Exception as e:
        print(f"⚠️ [Database] Kiểm tra kết nối CSDL thất bại: {e}", flush=True)
        return False


if __name__ == "__main__":
    test_connection()
