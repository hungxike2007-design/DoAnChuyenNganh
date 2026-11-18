from datetime import datetime, timedelta, timezone

import jwt

from backend.modules.auth.auth_service import (
    JWT_ALGORITHM,
    JWT_SECRET,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_password_hashing_uses_salt_and_verifies_password():
    first = hash_password("123456")
    second = hash_password("123456")
    assert first != second
    assert verify_password("123456", first)
    assert not verify_password("wrong", first)


def test_jwt_round_trip_and_expiration():
    token = create_access_token({"sub": "7", "email": "admin@example.com", "role": "admin"})
    claims = decode_access_token(token)
    assert (claims["sub"], claims["email"], claims["role"]) == ("7", "admin@example.com", "admin")

    expired = jwt.encode({"sub": "7", "exp": datetime.now(timezone.utc) - timedelta(minutes=1)}, JWT_SECRET, algorithm=JWT_ALGORITHM)
    try:
        decode_access_token(expired)
        assert False, "Expired token should be rejected"
    except ValueError:
        pass


def test_register_blocks_privilege_escalation(monkeypatch, tmp_path):
    import sqlite3
    from backend.modules.auth import auth_service

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT, full_name TEXT, email TEXT UNIQUE,
            password_hash TEXT, role TEXT DEFAULT 'user', created_at TEXT
        );
    """)

    monkeypatch.setattr(auth_service, "get_db_connection", lambda: conn)
    res = auth_service.AuthService.register_user("Attacker", "attacker@evil.com", "secret123", role="admin")
    assert res["user"]["role"] == "user", "Security failure: public registration must not grant admin role!"
