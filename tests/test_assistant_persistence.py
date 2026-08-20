from datetime import datetime, timezone
from io import BytesIO
from uuid import uuid4

from fastapi.testclient import TestClient
from openpyxl import Workbook

from app.database import SessionLocal
from app.main_saft import app
from app.models import AgentTask


client = TestClient(app)


HEADERS = [
    "ID", "Documento", "Data Doc.", "Entidade", "Total", "Total liquido", "Total IVA",
    "Estado", "Doc. Fornecedor", "Nº Enc. / Req. Ext.", "Canal de Anúncios", "Vendedor",
    "F. Liquidação",
]


def _source_workbook() -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(HEADERS)
    sheet.append(["1", "FR CUSA/1", "2026-08-20", "Cliente A", 123, 100, 23, "Liquidado", "", "", "Balcão", "1005 - VENDEDOR A", "MB"])
    sheet.append(["2", "NC CNOV/1", "2026-08-20", "Cliente B", 12.3, 10, 2.3, "Pendente", "", "", "Site", "1005 - VENDEDOR A", "TB"])
    sheet.append(["3", "FT PUSA/1", "2026-08-20", "SUCATAS DE RAMIL, S.A", 246, 200, 46, "Liquidado", "", "", "Balcão", "2004 - VENDEDOR C", "MB"])
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def _register(prefix: str) -> tuple[dict, str]:
    email = f"{prefix}-{uuid4().hex[:8]}@example.com"
    register = client.post("/api/v1/auth/register", json={"email": email, "password": "Password123", "role": "admin"})
    assert register.status_code == 201
    login = client.post("/api/v1/auth/login", json={"email": email, "password": "Password123"})
    assert login.status_code == 200
    return register.json(), login.json()["access_token"]


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _execute(token: str) -> dict:
    response = client.post(
        "/api/v1/assistant/messages",
        headers=_headers(token),
        data={"message": "Faça a faturação diária deste ficheiro."},
        files={"file": ("billing.xlsx", _source_workbook(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert response.status_code == 200
    return response.json()


def test_assistant_tasks_require_authentication():
    response = client.get("/api/v1/assistant/tasks")
    assert response.status_code == 401


def test_billing_task_persists_execution_and_artifact(monkeypatch, tmp_path):
    monkeypatch.setenv("SEO_ARTIFACT_STORAGE_PATH", str(tmp_path / "artifacts"))
    _, token = _register("assistant-persist")

    result = _execute(token)
    assert result["status"] == "COMPLETED", result
    assert result["task_id"]
    assert result["artifacts"]
    output = result["artifacts"][0]

    detail = client.get(f"/api/v1/assistant/tasks/{result['task_id']}", headers=_headers(token))
    assert detail.status_code == 200
    payload = detail.json()
    assert payload["status"] == "COMPLETED"
    assert [item["agent_name"] for item in payload["executions"]] == ["DocumentAgent", "BillingAgent", "AuditAgent"]
    assert all(item["status"] == "COMPLETED" for item in payload["executions"])
    assert payload["source_file"]["sha256"] != payload["output_files"][0]["sha256"]
    assert payload["records_processed"] == 3

    download = client.get(output["download_url"], headers=_headers(token))
    assert download.status_code == 200
    assert download.content.startswith(b"PK")

    repeated = client.get(f"/api/v1/assistant/tasks/{result['task_id']}", headers=_headers(token))
    repeated_download = client.get(output["download_url"], headers=_headers(token))
    assert repeated.status_code == 200
    assert repeated_download.status_code == 200


def test_tenant_cannot_read_or_download_another_tenants_task(monkeypatch, tmp_path):
    monkeypatch.setenv("SEO_ARTIFACT_STORAGE_PATH", str(tmp_path / "artifacts"))
    _, token_a = _register("assistant-tenant-a")
    _, token_b = _register("assistant-tenant-b")
    result = _execute(token_a)
    assert result["status"] == "COMPLETED", result
    artifact = result["artifacts"][0]

    detail = client.get(f"/api/v1/assistant/tasks/{result['task_id']}", headers=_headers(token_b))
    download = client.get(artifact["download_url"], headers=_headers(token_b))
    assert detail.status_code == 404
    assert download.status_code == 404


def test_tasks_support_pagination_and_filters():
    user, token = _register("assistant-pagination")
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        for index, task_status in enumerate(("COMPLETED", "FAILED", "NEEDS_REVIEW")):
            db.add(
                AgentTask(
                    id=str(uuid4()),
                    tenant_id=user["tenant_id"],
                    user_id=user["id"],
                    agent_type="manager",
                    task_type="billing",
                    status=task_status,
                    progress=100,
                    instruction=f"task {index}",
                    source_filename=f"task-{index}.xlsx",
                    records_processed=index,
                    records_rejected=0,
                    approval_required=False,
                    confidence=1.0 if task_status == "COMPLETED" else 0.0,
                    created_at=now,
                )
            )
        db.commit()

    first_page = client.get("/api/v1/assistant/tasks?limit=2&offset=0", headers=_headers(token))
    failed = client.get("/api/v1/assistant/tasks?status=FAILED&limit=100", headers=_headers(token))
    assert first_page.status_code == 200
    assert len(first_page.json()["tasks"]) == 2
    assert first_page.json()["pagination"]["total"] >= 3
    assert failed.status_code == 200
    assert failed.json()["tasks"]
    assert all(task["status"] == "FAILED" for task in failed.json()["tasks"])


def test_snc_write_and_saft_remain_disabled_without_explicit_flags(monkeypatch):
    monkeypatch.setenv("AGENT_EXECUTION_ENABLED", "true")
    monkeypatch.setenv("SNC_INTEGRATION_ENABLED", "true")
    monkeypatch.setenv("SNC_WRITE_ENABLED", "false")
    monkeypatch.setenv("SAFT_INTEGRATION_ENABLED", "false")
    _, token = _register("assistant-safety")

    status = client.get("/api/v1/agents/status", headers=_headers(token))
    route = client.post(
        "/api/v1/agents/route",
        headers=_headers(token),
        json={"message": "Lance este lançamento no SNC", "mode": "work"},
    )
    assert status.status_code == 200
    assert status.json()["snc_write"] is False
    assert status.json()["saft_ingestion"] is False
    assert route.status_code == 200
    assert route.json()["approval_required"] is True
    assert route.json()["write_blocked"] is True
