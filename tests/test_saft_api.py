from uuid import uuid4

from fastapi.testclient import TestClient

from app.main_saft import app

client = TestClient(app)

VALID_SAFT = b'''<?xml version="1.0" encoding="UTF-8"?>
<AuditFile xmlns="urn:OECD:StandardAuditFile-Tax:PT_1.04_01">
  <Header>
    <AuditFileVersion>1.04_01</AuditFileVersion>
    <CompanyID>SVP</CompanyID>
    <TaxRegistrationNumber>500000000</TaxRegistrationNumber>
    <CompanyName>SVP Auto</CompanyName>
    <FiscalYear>2026</FiscalYear>
    <StartDate>2026-01-01</StartDate>
    <EndDate>2026-12-31</EndDate>
    <CurrencyCode>EUR</CurrencyCode>
  </Header>
  <SourceDocuments>
    <SalesInvoices>
      <Invoice>
        <InvoiceNo>FT 2026/100</InvoiceNo>
        <InvoiceStatus>N</InvoiceStatus>
        <InvoiceDate>2026-08-19</InvoiceDate>
        <InvoiceType>FT</InvoiceType>
        <CustomerID>C1</CustomerID>
        <DocumentTotals>
          <TaxPayable>23.00</TaxPayable>
          <NetTotal>100.00</NetTotal>
          <GrossTotal>123.00</GrossTotal>
        </DocumentTotals>
      </Invoice>
    </SalesInvoices>
  </SourceDocuments>
</AuditFile>'''


def _email(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:10]}@example.com"


def _register_and_login(prefix: str) -> dict[str, str]:
    email = _email(prefix)
    register = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Password123", "role": "admin"},
    )
    assert register.status_code == 201
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "Password123"},
    )
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_saft_import_stays_out_of_operational_documents(monkeypatch):
    monkeypatch.setenv("SAFT_INTEGRATION_ENABLED", "true")
    headers = _register_and_login("saft-isolation")

    company = client.post(
        "/api/v1/companies",
        headers=headers,
        json={"name": "SVP Auto", "tax_id": "500000000", "country": "PT"},
    )
    assert company.status_code == 201

    imported = client.post(
        "/api/v1/saft/import",
        headers=headers,
        params={"company_id": company.json()["id"]},
        files={"file": ("saft.xml", VALID_SAFT, "application/xml")},
    )
    assert imported.status_code == 201
    body = imported.json()
    assert body["status"] == "staged"
    assert body["safety"]["isolated_ai_database"] is True
    assert body["safety"]["operational_database_unchanged"] is True
    assert body["safety"]["financial_documents_unchanged"] is True
    assert body["safety"]["snc_execution_enabled"] is False

    # Nothing from SAF-T is copied into the existing operational documents table.
    documents = client.get("/api/v1/documents", headers=headers)
    assert documents.status_code == 200
    assert documents.json() == []

    preview = client.get(f"/api/v1/saft/imports/{body['id']}/preview", headers=headers)
    assert preview.status_code == 200
    assert preview.json()["storage"] == "isolated_ai_database"
    assert preview.json()["documents"][0]["document_number"] == "FT 2026/100"


def test_saft_staging_is_tenant_isolated(monkeypatch):
    monkeypatch.setenv("SAFT_INTEGRATION_ENABLED", "true")
    owner_headers = _register_and_login("saft-owner")
    other_headers = _register_and_login("saft-other")

    company = client.post(
        "/api/v1/companies",
        headers=owner_headers,
        json={"name": "SVP Auto", "tax_id": "500000000", "country": "PT"},
    )
    imported = client.post(
        "/api/v1/saft/import",
        headers=owner_headers,
        params={"company_id": company.json()["id"]},
        files={"file": ("saft.xml", VALID_SAFT.replace(b"FT 2026/100", f"FT 2026/{uuid4().hex[:6]}".encode()), "application/xml")},
    )
    assert imported.status_code == 201

    forbidden_by_isolation = client.get(
        f"/api/v1/saft/imports/{imported.json()['id']}",
        headers=other_headers,
    )
    assert forbidden_by_isolation.status_code == 404


def test_saft_feature_flag_blocks_import(monkeypatch):
    monkeypatch.setenv("SAFT_INTEGRATION_ENABLED", "false")
    headers = _register_and_login("saft-disabled")
    company = client.post(
        "/api/v1/companies",
        headers=headers,
        json={"name": "SVP Auto", "tax_id": "500000000", "country": "PT"},
    )
    response = client.post(
        "/api/v1/saft/import",
        headers=headers,
        params={"company_id": company.json()["id"]},
        files={"file": ("saft.xml", VALID_SAFT, "application/xml")},
    )
    assert response.status_code == 503
