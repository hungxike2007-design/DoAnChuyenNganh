"""
==============================================================================
DỊCH VỤ XÁC THỰC NGƯỜI DÙNG & BẢO MẬT (AUTH SERVICE - PYTHON)
==============================================================================
Xử lý:
- Mã hóa mật khẩu an toàn với bcrypt.
- Cấp và kiểm tra JWT Token (pyjwt).
- Đăng ký, Đăng nhập, Quên mật khẩu (OTP 6 số), Đặt lại mật khẩu.
==============================================================================
"""

import os
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path
import bcrypt
import jwt
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

from config.db import get_db_connection

JWT_SECRET = os.getenv("JWT_SECRET", "super_secret_jwt_key_dacn_python_2026")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "10080")) # 7 ngày


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise ValueError("Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.")
    except jwt.PyJWTError:
        raise ValueError("Token xác thực không hợp lệ.")


class AuthService:
    @staticmethod
    def register_user(full_name: str, email: str, password: str, role: str = "manager") -> dict:
        email_clean = email.strip().lower()
        if len(password) < 6:
            raise ValueError("Mật khẩu phải có ít nhất 6 ký tự.")

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM users WHERE email = ?", (email_clean,))
        if cursor.fetchone():
            conn.close()
            raise ValueError("Email này đã được sử dụng. Vui lòng chọn email khác.")

        assigned_role = role if role in ["admin", "manager", "sales"] else "manager"
        pw_hash = hash_password(password)

        cursor.execute(
            "INSERT INTO users (full_name, email, password_hash, role) VALUES (?, ?, ?, ?)",
            (full_name.strip(), email_clean, pw_hash, assigned_role)
        )
        user_id = cursor.lastrowid
        conn.commit()

        cursor.execute("SELECT id, full_name, email, role, created_at FROM users WHERE id = ?", (user_id,))
        user_row = dict(cursor.fetchone())
        conn.close()

        token = create_access_token({
            "sub": str(user_row["id"]),
            "email": user_row["email"],
            "role": user_row["role"],
            "name": user_row["full_name"]
        })

        return {
            "token": token,
            "user": user_row
        }

    @staticmethod
    def login_user(email: str, password: str) -> dict:
        email_clean = email.strip().lower()
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE email = ?", (email_clean,))
        user_row = cursor.fetchone()
        conn.close()

        if not user_row:
            raise ValueError("Email hoặc mật khẩu không chính xác.")

        if not verify_password(password, user_row["password_hash"]):
            raise ValueError("Email hoặc mật khẩu không chính xác.")

        user_dict = dict(user_row)
        user_dict.pop("password_hash", None)

        token = create_access_token({
            "sub": str(user_dict["id"]),
            "email": user_dict["email"],
            "role": user_dict["role"],
            "name": user_dict["full_name"]
        })

        return {
            "token": token,
            "user": user_dict
        }

    @staticmethod
    def request_forgot_password(email: str) -> dict:
        email_clean = email.strip().lower()
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT id, full_name FROM users WHERE email = ?", (email_clean,))
        user = cursor.fetchone()
        if not user:
            conn.close()
            raise ValueError("Không tìm thấy tài khoản nào gắn với email này.")

        # Vô hiệu hóa OTP cũ
        cursor.execute("UPDATE password_resets SET is_used = 1 WHERE email = ?", (email_clean,))

        # Tạo mã OTP 6 số
        otp_code = str(random.randint(100000, 999999))
        expires_at = (datetime.now() + timedelta(minutes=15)).strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute(
            "INSERT INTO password_resets (email, otp_code, expires_at, is_used) VALUES (?, ?, ?, 0)",
            (email_clean, otp_code, expires_at)
        )
        conn.commit()
        conn.close()

        print(f"\n🔑 [OTP RESET PASSWORD] Email: {email_clean} | Mã OTP: {otp_code} (Hạn 15 phút)\n")

        return {
            "email": email_clean,
            "demo_otp": otp_code,  # Trả về mã OTP mẫu để bạn test đồ án nhanh
            "expires_in_minutes": 15
        }

    @staticmethod
    def reset_password(email: str, otp_code: str, new_password: str) -> bool:
        if len(new_password) < 6:
            raise ValueError("Mật khẩu mới phải có ít nhất 6 ký tự.")

        email_clean = email.strip().lower()
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT TOP 1 * FROM password_resets 
            WHERE email = ? AND otp_code = ? AND is_used = 0 
            ORDER BY id DESC
        """, (email_clean, otp_code.strip()))
        record = cursor.fetchone()

        if not record:
            conn.close()
            raise ValueError("Mã xác thực OTP không đúng hoặc đã qua sử dụng.")

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if now_str > record["expires_at"]:
            conn.close()
            raise ValueError("Mã xác thực đã hết hạn (chỉ có hiệu lực trong 15 phút).")

        new_hash = hash_password(new_password)
        cursor.execute("UPDATE users SET password_hash = ? WHERE email = ?", (new_hash, email_clean))
        cursor.execute("UPDATE password_resets SET is_used = 1 WHERE id = ?", (record["id"],))
        conn.commit()
        conn.close()
        return True

    @staticmethod
    def get_user_by_id(user_id: int) -> dict:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, full_name, email, role, avatar_url, created_at FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None
