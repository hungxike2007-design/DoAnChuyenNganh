from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.modules.auth.auth_router import get_current_user
from backend.modules.dashboard import revenue_router


def test_kpi_endpoint_returns_expected_fields(monkeypatch):
    monkeypatch.setattr(revenue_router.AnalyticsService, "get_kpis", lambda days, user_id=None: {
        "totalRevenue": 100, "grossProfit": 40, "aov": 50, "cancelRate": 0
    })
    app = FastAPI()
    app.include_router(revenue_router.router)
    app.dependency_overrides[get_current_user] = lambda: {"sub": "1", "role": "admin"}

    response = TestClient(app).get("/api/revenue/kpis")
    assert response.status_code == 200
    assert {"totalRevenue", "grossProfit", "aov", "cancelRate"} <= response.json()["data"].keys()


def test_sales_role_cannot_open_admin_only_audit_api():
    from backend.modules.audit.audit_router import router as audit_router

    app = FastAPI()
    app.include_router(audit_router)
    app.dependency_overrides[get_current_user] = lambda: {"sub": "2", "role": "sales"}
    response = TestClient(app).get("/api/audit/logs")
    assert response.status_code == 403
