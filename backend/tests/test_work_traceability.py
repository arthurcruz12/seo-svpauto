from __future__ import annotations

import io
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient
from openpyxl import Workbook

from backend.app import store
from backend.app.security import pwd_context
from backend.app.server import app
from backend.app.work_routes import _severe_anomalies
from backend.app.work_traceability import list_work_documents


class WorkTraceabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.database = tempfile.NamedTemporaryFile(suffix="-work-traceability.sqlite3", delete=False)
        cls.database.close()
        cls.storage_dir = Path(tempfile.mkdtemp(prefix="seo-work-files-"))
        store.DATABASE_PATH = Path(cls.database.name)
        store.FILE_STORAGE_DIR = cls.storage_dir
        store.ensure_company("SEO Empresa Teste")
        store.ensure_user(
            name="Administrador Trabalho",
            email="admin-work@seo.local",
            role="admin",
            company_id="default-company",
            password_hash=pwd_context.hash("Seo-Admin-2026"),
        )
        cls.client = TestClient(app)
        cls.token = cls._login()

    @classmethod
    def tearDownClass(cls):
        cls.client.close()
        Path(cls.database.name).unlink(missing_ok=True)
        for path in sorted(cls.storage_dir.rglob("*"), reverse=True):
            if path.is_file():
                path.unlink(missing_ok=True)
            elif path.is_dir():
                path.rmdir()
        cls.storage_dir.rmdir()

    @classmethod
    def _login(cls) -> str:
        first = cls.client.post("/auth/login", json={"email": "admin-work@seo.local", "password": "Seo-Admin-2026"})
        assert first.status_code == 200, first.text
        challenge = first.json()
        second = cls.client.post(
            "/auth/mfa",
            json={"challenge_id": challenge["challenge_id"], "code": challenge["development_code"]},
        )
        assert second.status_code == 200, second.text
        return second.json()["access_token"]

    @staticmethod
    def _workbook(*, bad_total: bool = False) -> bytes:
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Faturação"
        sheet.append([
            "Documento",
            "Data Doc.",
            "Entidade",
            "Total",
            "Total liquido",
            "Total IVA",
            "Estado",
            "Vendedor",
        ])
        sheet.append([
            "FR CUSA/100",
            "2026-08-21",
            "CLIENTE TESTE",
            123.0 if not bad_total else 150.0,
            100.0,
            23.0,
            "Liquidado",
            "1005 - TESTE",
        ])
        buffer = io.BytesIO()
        workbook.save(buffer)
        return buffer.getvalue()

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"}

    def test_gross_validation_filter_only_routes_blocking_errors(self):
        anomalies = _severe_anomalies(
            "task-test",
            [
                {
                    "number": "FT CUSA/1",
                    "totalAmount": 150,
                    "validations": ["Total não corresponde à soma do valor líquido e IVA", "Entidade não identificada"],
                },
                {
                    "number": "FT CUSA/2",
                    "totalAmount": 100,
                    "validations": ["Entidade não identificada"],
                },
            ],
        )
        self.assertEqual(len(anomalies), 1)
        self.assertEqual(anomalies[0]["document"], "FT CUSA/1")
        self.assertEqual(anomalies[0]["status"], "Alerta")

    def test_work_result_registers_documents_anomalies_cloud_and_reference_date(self):
        source = self._workbook(bad_total=True)
        output = self._workbook(bad_total=False)
        response = self.client.post(
            "/assistant/work/billing/persist",
            headers=self._headers(),
            data={"task_id": "task-trace-001", "audit_json": '{"valid": true, "checks": {"totals": true}}'},
            files={
                "source_file": ("Faturação 21.08.xlsx", source, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
                "output_file": ("Faturação 21.08 - Separada, Resumo e Mapa Diário.xlsx", output, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(payload["status"], "PERSISTED")
        self.assertGreaterEqual(payload["documentsRegistered"], 1)
        self.assertGreaterEqual(payload["severeAnomaliesCreated"], 1)
        self.assertEqual(len(payload["cloudFiles"]), 4)

        documents = list_work_documents("default-company", task_id="task-trace-001")
        self.assertGreaterEqual(len(documents), 1)
        self.assertEqual(documents[0]["taskId"], "task-trace-001")

        cloud = self.client.get("/assistant/work/files", headers=self._headers())
        self.assertEqual(cloud.status_code, 200, cloud.text)
        files = cloud.json()
        output_file = next(item for item in files if item["origin"] == "assistant-work-output")
        self.assertIsNone(output_file["referenceDate"])

        dated = self.client.post(
            f"/assistant/work/files/{output_file['id']}/reference-date",
            headers=self._headers(),
            data={"reference_date": "2026-08-21"},
        )
        self.assertEqual(dated.status_code, 200, dated.text)
        self.assertEqual(dated.json()["referenceDate"], "2026-08-21")
        self.assertEqual(dated.json()["taskId"], "task-trace-001")

        issues = self.client.get("/reconciliation/issues", headers=self._headers())
        self.assertEqual(issues.status_code, 200, issues.text)
        self.assertTrue(any(item["source"] == "Assistente IA · Trabalho" for item in issues.json()))

        dashboard = self.client.get("/dashboard/state", headers=self._headers())
        self.assertEqual(dashboard.status_code, 200, dashboard.text)
        intelligence = dashboard.json().get("documentIntelligence") or {}
        self.assertTrue(intelligence.get("documents"))


if __name__ == "__main__":
    unittest.main()
