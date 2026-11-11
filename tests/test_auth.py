"""
==============================================================================
UNIT TESTS: XÁC THỰC & PHÂN QUYỀN (AUTH & RBAC)
==============================================================================
"""

import pytest
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException
import jwt
from backend.modules.auth.auth_service import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
    JWT_SECRET,
    JWT_ALGORITHM,
)
from backend.modules.auth.auth_router import get_current_user, get_me, require_roles


def test_password_hashing():
    """Kiểm tra mã hóa mật khẩu bcrypt có sinh muối và xác thực chính xác."""
    raw_pass = "SecurePass123"
    hashed = hash_password(raw_pass)

    assert hashed != raw_pass
    assert hashed.startswith("$2b$") or hashed.startswith("$2a$")
    assert verify_password(raw_pass, hashed) is True
    assert verify_password("WrongPass456", hashed) is False


def test_jwt_encode_decode():
    """Kiểm tra tạo token JWT và giải mã trả đúng payload định danh."""
    payload = {"sub": "99", "email": "test@domain.com", "role": "manager"}
    token = create_access_token(payload)

    assert isinstance(token, str)
    decoded = decode_access_token(token)
    assert decoded["sub"] == "99"
    assert decoded["email"] == "test@domain.com"
    assert decoded["role"] == "manager"
    assert "exp" in decoded


def test_jwt_expired_token():
    """Kiểm tra token hết hạn phải ném ra lỗi ValueError rõ ràng."""
    expired_payload = {
        "sub": "1",
        "email": "expired@domain.com",
        "exp": datetime.now(timezone.utc) - timedelta(minutes=5)
    }
    expired_token = jwt.encode(expired_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

    with pytest.raises(ValueError, match="Phiên đăng nhập đã hết hạn"):
        decode_access_token(expired_token)


def test_jwt_invalid_signature():
    """Kiểm tra token bị giả mạo khóa bí mật phải bị từ chối."""
    fake_token = jwt.encode({"sub": "1"}, "wrong_secret_key", algorithm="HS256")
    with pytest.raises(ValueError, match="Token xác thực không hợp lệ"):
        decode_access_token(fake_token)


def test_auth_me_unauthorized():
    """Gọi get_current_user mà không có token phải ném ra HTTPException 401."""
    with pytest.raises(HTTPException) as exc:
        get_current_user(authorization=None)
    assert exc.value.status_code == 401


def test_auth_me_authorized(admin_token):
    """Gọi get_me với token hợp lệ phải lấy được thông tin hồ sơ người dùng."""
    user = get_current_user(authorization=f"Bearer {admin_token}")
    res = get_me(user=user)
    assert res["success"] is True
    assert res["data"]["email"] == "admin@dacn.vn"
    assert res["data"]["role"] == "admin"


def test_require_roles_permission():
    """Kiểm tra RBAC: Role Sales bị chặn khi gọi endpoint yêu cầu Admin."""
    role_checker = require_roles("admin")
    
    # Sales bị chặn 403
    with pytest.raises(HTTPException) as exc:
        role_checker(user={"role": "sales", "sub": "3"})
    assert exc.value.status_code == 403

    # Admin được phép
    allowed = role_checker(user={"role": "admin", "sub": "1"})
    assert allowed["role"] == "admin"
