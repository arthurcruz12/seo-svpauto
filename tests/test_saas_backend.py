from datetime import date

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


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


def test_auth_login_and_refresh_flow():
    email = "auth-test@example.com"
    response = register(email)
    assert response.status_code in (201, 409)

    tokens = login(email)
    assert "access_token" in tokens
    assert "refresh_token" in tokens

    refresh = client.post("/api/v1/auth/refresh", params={"refresh_token": tokens["refresh_token"]})
    assert refresh.status_code == 200
    assert "access_token" in refresh.json()


def test_company_document_dashboard_and_audit_flow():
    email = "admin-flow@example.com"
    register(email)
    token = login(email)["access_token"]
    headers = auth_headers(token)

    company = client.post("/api/v1/companies", headers=headers, json={"name": "Empresa Teste", "tax_id": "PT123456789", "country": "PT"})
    assert company.status_code in (201, 409)

    companies = client.get("/api/v1/companies", headers=headers)
    assert companies.status_code == 200
    company_id = companies.json()[0]["id"]

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

    dashboard = client.get(f"/api/v1/dashboard/{company_id}", headers=headers)
    assert dashboard.status_code == 200
    assert dashboard.json()["company_id"] == company_id

    audit = client.get("/api/v1/audit-logs", headers=headers)
    assert audit.status_code == 200
    assert isinstance(audit.json(), list)


def test_rbac_blocks_employee_from_audit_logs():
    email = "employee-rbac@example.com"
    register(email, role="employee")
    token = login(email)["access_token"]

    response = client.get("/api/v1/audit-logs", headers=auth_headers(token))
    assert response.status_code == 403


def test_tenant_isolation_between_users():
    register("tenant-a@example.com")
    register("tenant-b@example.com")
    token_a = login("tenant-a@example.com")["access_token"]
    token_b = login("tenant-b@example.com")["access_token"]

    create_a = client.post("/api/v1/companies", headers=auth_headers(token_a), json={"name": "Tenant A", "tax_id": "A123", "country": "PT"})
    assert create_a.status_code in (201, 409)

    list_a = client.get("/api/v1/companies", headers=auth_headers(token_a))
    list_b = client.get("/api/v1/companies", headers=auth_headers(token_b))

    assert list_a.status_code == 200
    assert list_b.status_code == 200
    names_b = [company["name"] for company in list_b.json()]
    assert "Tenant A" not in names_b
