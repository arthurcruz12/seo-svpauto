import os
import tempfile
import unittest
from io import BytesIO
from unittest.mock import patch


_database = tempfile.NamedTemporaryFile(suffix="-api.sqlite3", delete=False)
_database.close()
os.environ["SEO_DATABASE_PATH"] = _database.name
os.environ["SEO_EXPOSE_DEV_MFA"] = "1"
os.environ["SEO_MAX_UPLOAD_MB"] = "12"

from fastapi.testclient import TestClient  # noqa: E402
from openpyxl import Workbook  # noqa: E402

from backend.app.audit import list_audit_events  # noqa: E402
from backend.app.main import MAX_OCR_FILE_SIZE, MAX_UPLOAD_BYTES, app  # noqa: E402
from backend.app.security import ROLE_PERMISSIONS  # noqa: E402


class ApiIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.admin_token = cls.login("admin@seo.local", "Seo-Admin-2026")
        cls.admin_company_id = cls.client.get("/me", headers=cls.auth(cls.admin_token)).json()["company_id"]

    @classmethod
    def tearDownClass(cls):
        cls.client.close()
        try:
            os.unlink(_database.name)
        except (FileNotFoundError, PermissionError):
            pass

    @classmethod
    def login(cls, email: str, password: str) -> str:
        login = cls.client.post("/auth/login", json={"email": email, "password": password})
        assert login.status_code == 200, login.text
        challenge = login.json()
        mfa = cls.client.post("/auth/mfa", json={"challenge_id": challenge["challenge_id"], "code": challenge["development_code"]})
        assert mfa.status_code == 200, mfa.text
        return mfa.json()["access_token"]

    @staticmethod
    def auth(token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {token}"}

    @staticmethod
    def malformed_workbook() -> bytes:
        workbook = Workbook()
        sheet = workbook.active
        sheet.append(["Mapa exportado do sistema antigo"])
        sheet.append([])
        sheet.append(["Documento", "Descrição", "Entidade", "Valor sem IVA", "IVA", "Total", "Produto", "Referência", "Stock", "Valor em aberto", "Dias"])
        sheet.append(["FT 1", "Fatura fornecedor peças", "Fornecedor A", 100, 23, None, "Farol LED", "SKU-1", 1, 123, 15])
        sheet.append(["TOTAL GERAL", None, None, 100, 23, 123])
        output = BytesIO()
        workbook.save(output)
        return output.getvalue()

    def test_01_health_and_protected_endpoint(self):
        self.assertEqual(self.client.get("/health").status_code, 200)
        self.assertEqual(self.client.get("/cloud/files").status_code, 401)

    def test_02_invalid_login_and_mfa_are_rejected(self):
        self.assertEqual(self.client.post("/auth/login", json={"email": "admin@seo.local", "password": "palavra-passe-errada"}).status_code, 401)
        self.assertEqual(self.client.post("/auth/mfa", json={"challenge_id": "missing", "code": "000000"}).status_code, 401)

    def test_03_excel_upload_calculates_and_persists_original(self):
        content = self.malformed_workbook()
        response = self.client.post(
            "/files/analyze",
            headers=self.auth(self.admin_token),
            files={"file": ("faturas.xlsx", content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(payload["documentIntelligence"]["totals"]["total"], 123)
        self.assertEqual(payload["documentIntelligence"]["stats"]["corrected"], 1)
        dashboard_state = self.client.get("/dashboard/state", headers=self.auth(self.admin_token))
        self.assertEqual(dashboard_state.status_code, 200, dashboard_state.text)
        self.assertEqual(dashboard_state.json()["summary"]["sourceName"], "faturas.xlsx")
        self.assertEqual(dashboard_state.json()["documentIntelligence"]["totals"]["total"], 123)
        file_id = payload["storedFile"]["id"]
        self.__class__.admin_file_id = file_id
        download = self.client.get(f"/cloud/files/{file_id}/download", headers=self.auth(self.admin_token))
        self.assertEqual(download.status_code, 200)
        self.assertEqual(download.content, content)
        self.assertEqual(len(download.headers["x-content-sha256"]), 64)

    def test_04_inventory_finance_reconciliation_and_ai(self):
        inventory = self.client.get("/inventory/items", headers=self.auth(self.admin_token)).json()
        self.assertTrue(inventory)
        sold = self.client.post(f"/inventory/items/{inventory[0]['ref']}/sale", headers=self.auth(self.admin_token))
        self.assertEqual(sold.status_code, 200)
        sold_again = self.client.post(f"/inventory/items/{inventory[0]['ref']}/sale", headers=self.auth(self.admin_token))
        self.assertGreaterEqual(sold_again.json()["stock"], 0)

        debts = self.client.get("/finance/debts", headers=self.auth(self.admin_token)).json()
        self.assertTrue(debts)
        paid = self.client.post(f"/finance/debts/{debts[0]['id']}/pay", headers=self.auth(self.admin_token))
        self.assertEqual(paid.json()["state"], "Pago")

        imported = self.client.post(
            "/reconciliation/import",
            headers=self.auth(self.admin_token),
            files={"file": ("conciliacao.csv", b"documento;entidade;valor;problema\nFT-X;Fornecedor;50;Confirmar pagamento\n", "text/csv")},
        )
        self.assertEqual(imported.status_code, 200, imported.text)
        resolved = self.client.post("/reconciliation/issues/resolve-all", headers=self.auth(self.admin_token))
        self.assertTrue(all(item["status"] == "Resolvido" for item in resolved.json()))
        analysis = self.client.post("/ai/analyze", headers=self.auth(self.admin_token), json={"question": "Qual é o maior risco?"})
        self.assertEqual(analysis.status_code, 200)
        self.assertTrue(analysis.json()["actions"])

    def test_05_snapshots_and_billing_safety(self):
        created = self.client.post("/reports/snapshots", headers=self.auth(self.admin_token), json={"period": "monthly", "label": "Teste mensal"})
        self.assertEqual(created.status_code, 200)
        listed = self.client.get("/reports/snapshots?period=monthly", headers=self.auth(self.admin_token))
        self.assertGreaterEqual(len(listed.json()), 1)
        self.client.post("/reports/snapshots", headers=self.auth(self.admin_token), json={"period": "monthly", "label": "Segundo teste"})
        compared = self.client.get("/reports/compare?period=monthly", headers=self.auth(self.admin_token))
        self.assertEqual(compared.status_code, 200)
        self.assertIsNotNone(compared.json()["previous"])
        self.assertEqual(self.client.post("/billing/webhook", content=b"{}", headers={"stripe-signature": "invalid"}).status_code, 503)

    def test_05b_daily_report_calendar_and_cloud_history(self):
        created = self.client.post(
            "/reports/snapshots",
            headers=self.auth(self.admin_token),
            json={"period": "daily", "label": "Relatório diário", "report_date": "2026-07-21"},
        )
        self.assertEqual(created.status_code, 200, created.text)
        self.assertEqual(created.json()["reportDate"], "2026-07-21")
        history = self.client.get(
            "/reports/snapshots?period=daily&report_date=2026-07-21",
            headers=self.auth(self.admin_token),
        )
        self.assertEqual(history.status_code, 200, history.text)
        self.assertTrue(history.json())
        self.assertTrue(all(item["reportDate"] == "2026-07-21" for item in history.json()))

    def test_06_company_file_isolation(self):
        email = "cliente-integracao@example.com"
        registered = self.client.post("/auth/register", json={"name": "Cliente Integração", "email": email, "password": "Password-123", "company_name": "Empresa Isolada"})
        self.assertEqual(registered.status_code, 200, registered.text)
        client_token = self.login(email, "Password-123")
        self.assertEqual(self.client.get("/cloud/files", headers=self.auth(client_token)).json(), [])
        forbidden_download = self.client.get(f"/cloud/files/{self.admin_file_id}/download", headers=self.auth(client_token))
        self.assertEqual(forbidden_download.status_code, 404)

    def test_07_invalid_uploads_are_rejected(self):
        response = self.client.post(
            "/files/analyze",
            headers=self.auth(self.admin_token),
            files={"file": ("malware.exe", b"not allowed", "application/octet-stream")},
        )
        self.assertEqual(response.status_code, 400)

    def test_08_oversized_upload_is_rejected_before_parsing(self):
        response = self.client.post(
            "/files/analyze",
            headers=self.auth(self.admin_token),
            files={"file": ("demasiado-grande.csv", b"x" * (MAX_UPLOAD_BYTES + 1), "text/csv")},
        )
        self.assertEqual(response.status_code, 413)

    def test_09_ocr_requires_authentication_and_valid_company(self):
        path = f"/api/v1/documents/ocr?company_id={self.admin_company_id}"
        self.assertEqual(self.client.post(path, files={"file": ("foto.png", b"x", "image/png")}).status_code, 401)
        missing = self.client.post("/api/v1/documents/ocr?company_id=missing", headers=self.auth(self.admin_token), files={"file": ("foto.png", b"x", "image/png")})
        self.assertEqual(missing.status_code, 404)

    def test_10_ocr_rejects_invalid_empty_and_oversized_files(self):
        path = f"/api/v1/documents/ocr?company_id={self.admin_company_id}"
        invalid = self.client.post(path, headers=self.auth(self.admin_token), files={"file": ("malware.exe", b"x", "application/octet-stream")})
        empty = self.client.post(path, headers=self.auth(self.admin_token), files={"file": ("empty.png", b"", "image/png")})
        oversized = self.client.post(path, headers=self.auth(self.admin_token), files={"file": ("large.png", b"x" * (MAX_OCR_FILE_SIZE + 1), "image/png")})
        self.assertEqual(invalid.status_code, 422)
        self.assertEqual(empty.status_code, 422)
        self.assertEqual(oversized.status_code, 413)

    @patch("backend.app.main.read_full_file")
    def test_11_ocr_audits_without_creating_financial_document(self, read_full_file):
        read_full_file.return_value = {"filename": "fatura.pdf", "content_type": "application/pdf", "page_count": 2, "pages": [{"page": 1, "method": "embedded_text", "text": "A"}, {"page": 2, "method": "ocr", "text": "B"}], "full_text": "--- PÁGINA 1 ---\nA\n\n--- PÁGINA 2 ---\nB"}
        before = len(self.client.get("/cloud/files", headers=self.auth(self.admin_token)).json())
        response = self.client.post(f"/api/v1/documents/ocr?company_id={self.admin_company_id}", headers=self.auth(self.admin_token), files={"file": ("fatura.pdf", b"%PDF-test", "application/pdf")})
        after = len(self.client.get("/cloud/files", headers=self.auth(self.admin_token)).json())
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["page_count"], 2)
        self.assertEqual(before, after)
        self.assertTrue(any(event["action"] == "document_ocr_completed" and "pages=2" in event["details"] for event in list_audit_events(50)))

    def test_12_ocr_enforces_tenant_and_permission(self):
        email = "ocr-tenant@example.com"
        registered = self.client.post("/auth/register", json={"name": "OCR Tenant", "email": email, "password": "Password-123", "company_name": "OCR Empresa"})
        self.assertEqual(registered.status_code, 200)
        token = self.login(email, "Password-123")
        company_id = self.client.get("/me", headers=self.auth(token)).json()["company_id"]
        other_tenant = self.client.post(f"/api/v1/documents/ocr?company_id={self.admin_company_id}", headers=self.auth(token), files={"file": ("foto.png", b"x", "image/png")})
        self.assertEqual(other_tenant.status_code, 404)
        original = list(ROLE_PERMISSIONS["client"])
        try:
            ROLE_PERMISSIONS["client"] = [permission for permission in original if permission != "documents:write"]
            forbidden = self.client.post(f"/api/v1/documents/ocr?company_id={company_id}", headers=self.auth(token), files={"file": ("foto.png", b"x", "image/png")})
            self.assertEqual(forbidden.status_code, 403)
        finally:
            ROLE_PERMISSIONS["client"] = original

    def test_13_frontend_audit_event_is_persisted(self):
        created = self.client.post(
            "/audit/events",
            headers=self.auth(self.admin_token),
            json={"actor": "ignored@example.com", "action": "UI_TEST", "details": "Ação iniciada na interface."},
        )
        self.assertEqual(created.status_code, 201, created.text)
        events = self.client.get("/audit", headers=self.auth(self.admin_token)).json()
        self.assertTrue(any(event["action"] == "UI_TEST" for event in events))


if __name__ == "__main__":
    unittest.main()
