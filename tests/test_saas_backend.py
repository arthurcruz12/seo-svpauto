from datetime import date
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def unique_email(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:8]}@example.com"


def register(email: str, password: str = "Password123", role: str = "admin"):
    return client.post("/api/v1/auth/register", json={"email": email, "password": password, "role": role})


def login(email: str, password: str = "Password123"):
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return response.json()


def auth_headers(token: str):
    return {"Authorization": f"Bearer {token}"}


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_readiness_and_liveness_endpoints():
    live = client.get("/live")
    ready = client.get("/ready")
    assert live.status_code == 200
    assert ready.status_code == 200


def test_metrics_endpoint():
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "seo_http_requests_total" in response.text


def test_auth_login_and_refresh_flow():
    email = unique_email("auth-test")
    response = register(email)
    assert response.status_code == 201

    tokens = login(email)
    assert "access_token" in tokens
    assert "refresh_token" in tokens

    refresh = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refresh.status_code == 200
    assert "access_token" in refresh.json()


def test_company_document_dashboard_and_audit_flow():
    email = unique_email("admin-flow")
    register(email)
    token = login(email)["access_token"]
    headers = auth_headers(token)

    company = client.post("/api/v1/companies", headers=headers, json={"name": "Empresa Teste", "tax_id": f"PT{uuid4().hex[:9]}", "country": "PT"})
    assert company.status_code == 201
    company_id = company.json()["id"]

    companies = client.get("/api/v1/companies", headers=headers)
    assert companies.status_code == 200
    assert any(item["id"] == company_id for item in companies.json())

    document = client.post(
        "/api/v1/documents",
        headers=headers,
        json={
            "company_id": company_id,
            "document_type": "invoice",
            "supplier": "Fornecedor Teste",
            "amount": "120.50",
            "vat_amount": "27.72",
            "currency": "EUR",
            "issue_date": str(date.today()),
            "description": "serviço de consultoria",
        },
    )
    assert document.status_code == 201
    document_id = document.json()["document"]["id"]

    process = client.post(f"/api/v1/documents/{document_id}/process", headers=headers)
    assert process.status_code == 200

    process_again = client.post(f"/api/v1/documents/{document_id}/process", headers=headers)
    assert process_again.status_code == 409

    dashboard = client.get(f"/api/v1/dashboard/{company_id}", headers=headers)
    assert dashboard.status_code == 200
    assert dashboard.json()["company_id"] == company_id

    audit = client.get("/api/v1/audit-logs", headers=headers)
    assert audit.status_code == 200
    assert isinstance(audit.json(), list)


def test_rbac_blocks_employee_from_audit_logs():
    email = unique_email("employee-rbac")
    register(email, role="employee")
    token = login(email)["access_token"]

    response = client.get("/api/v1/audit-logs", headers=auth_headers(token))
    assert response.status_code == 403


def test_unauthenticated_access_is_blocked():
    response = client.get("/api/v1/companies")
    assert response.status_code == 401


def test_tenant_isolation_between_users():
    email_a = unique_email("tenant-a")
    email_b = unique_email("tenant-b")
    register(email_a)
    register(email_b)
    token_a = login(email_a)["access_token"]
    token_b = login(email_b)["access_token"]

    create_a = client.post("/api/v1/companies", headers=auth_headers(token_a), json={"name": "Tenant A", "tax_id": f"A{uuid4().hex[:8]}", "country": "PT"})
    assert create_a.status_code == 201

    list_a = client.get("/api/v1/companies", headers=auth_headers(token_a))
    list_b = client.get("/api/v1/companies", headers=auth_headers(token_b))

    assert list_a.status_code == 200
    assert list_b.status_code == 200
    names_b = [company["name"] for company in list_b.json()]
    assert "Tenant A" not in names_b
