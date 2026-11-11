"""
==============================================================================
PYTEST FIXTURES & CONFIGURATION
==============================================================================
"""

import os
import sys
from pathlib import Path
import pytest

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))
os.environ["DB_TYPE"] = "sqlite"
os.environ["DATABASE_PATH"] = "data/revenue_system.sqlite"
os.environ["JWT_SECRET"] = "test_super_secret_jwt_key_2026_secure_32bytes"

from backend.modules.auth.auth_service import create_access_token


@pytest.fixture(scope="session")
def admin_user():
    return {"sub": "1", "email": "admin@dacn.vn", "role": "admin"}


@pytest.fixture(scope="session")
def manager_user():
    return {"sub": "2", "email": "manager@dacn.vn", "role": "manager"}


@pytest.fixture(scope="session")
def sales_user():
    return {"sub": "3", "email": "sales@dacn.vn", "role": "sales"}


@pytest.fixture(scope="session")
def admin_token(admin_user):
    return create_access_token(admin_user)


@pytest.fixture(scope="session")
def sales_token(sales_user):
    return create_access_token(sales_user)


@pytest.fixture(scope="session")
def manager_token(manager_user):
    return create_access_token(manager_user)
