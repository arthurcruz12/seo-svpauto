import hashlib
import json
import os
import sys
import tempfile
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKBOOK = ROOT / "outputs" / "large-import-e2e" / "faturas_teste_grande_50000.xlsx"
REPORT = ROOT / "outputs" / "large-import-e2e" / "relatorio_testes.json"

database = tempfile.NamedTemporaryFile(suffix="-large-e2e.sqlite3", delete=False)
database.close()
os.environ["SEO_DATABASE_PATH"] = database.name
os.environ["SEO_EXPOSE_DEV_MFA"] = "1"
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402
from backend.app.main import app  # noqa: E402


def require(response, status=200):
    assert response.status_code == status, f"{response.request.method} {response.request.url}: {response.status_code} {response.text[:500]}"
    return response


def main():
    content = WORKBOOK.read_bytes()
    local_hash = hashlib.sha256(content).hexdigest()
    started = time.perf_counter()
    results = {"workbook": str(WORKBOOK), "bytes": len(content), "sha256": local_hash, "checks": []}

    with TestClient(app) as client:
        require(client.get("/health"))
        results["checks"].append("health")

        login = require(client.post("/auth/login", json={"email": "admin@seo.local", "password": "Seo-Admin-2026"})).json()
        token = require(client.post("/auth/mfa", json={"challenge_id": login["challenge_id"], "code": login["development_code"]})).json()["access_token"]
        auth = {"Authorization": f"Bearer {token}"}
        require(client.get("/me", headers=auth))
        results["checks"].append("auth+mfa+me")

        upload_started = time.perf_counter()
        upload = require(
            client.post(
                "/files/analyze",
                headers=auth,
                files={"file": (WORKBOOK.name, content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            )
        ).json()
        results["upload_seconds"] = round(time.perf_counter() - upload_started, 3)
        summary = upload["summary"]
        stats = upload["documentIntelligence"]["stats"]
        assert summary["rowsRead"] == 50000, summary
        assert stats["processed"] == 50000, stats
        assert stats["corrected"] >= 400, stats
        assert stats["duplicates"] >= 40, stats
        assert stats["review"] > 0, stats
        results["summary"] = summary
        results["document_stats"] = stats
        results["document_totals"] = upload["documentIntelligence"]["totals"]
        results["checks"].append("upload+header-detection+correction+calculations+duplicates")

        file_id = upload["storedFile"]["id"]
        cloud = require(client.get("/cloud/files", headers=auth)).json()
        assert any(item["id"] == file_id for item in cloud)
        download = require(client.get(f"/cloud/files/{file_id}/download", headers=auth))
        assert download.content == content
        assert download.headers["x-content-sha256"] == local_hash
        results["checks"].append("cloud-list+binary-download+sha256")

        inventory = require(client.get("/inventory/items", headers=auth)).json()
        debts = require(client.get("/finance/debts", headers=auth)).json()
        issues = require(client.get("/reconciliation/issues", headers=auth)).json()
        assert inventory and debts and issues
        results["derived_counts"] = {"inventory": len(inventory), "debts": len(debts), "issues": len(issues)}
        results["checks"].append("inventory+finance+reconciliation")

        ai = require(client.post("/ai/analyze", headers=auth, json={"question": "Analise riscos, duplicados e valores em aberto do ficheiro grande."})).json()
        assert ai.get("actions") and ai.get("answer")
        decision = require(client.get("/decision-center", headers=auth)).json()
        executive = require(client.get("/reports/executive", headers=auth)).json()
        executive_pdf = require(client.get("/reports/executive.pdf", headers=auth))
        assert executive_pdf.content.startswith(b"%PDF")
        assert decision and executive
        results["checks"].append("ai+decision-center+executive-report+pdf")

        require(client.post("/reports/snapshots", headers=auth, json={"period": "monthly", "label": "Teste Excel 50k"}))
        snapshots = require(client.get("/reports/snapshots?period=monthly", headers=auth)).json()
        assert snapshots
        results["checks"].append("snapshots")

        invalid = client.post("/files/analyze", headers=auth, files={"file": ("teste.exe", b"x", "application/octet-stream")})
        assert invalid.status_code == 400
        oversized = client.post("/files/analyze", headers=auth, files={"file": ("grande.csv", b"x" * (10 * 1024 * 1024 + 1), "text/csv")})
        assert oversized.status_code == 413
        results["checks"].append("invalid-extension+10mb-limit")

    results["total_seconds"] = round(time.perf_counter() - started, 3)
    results["status"] = "PASS"
    REPORT.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    finally:
        try:
            os.unlink(database.name)
        except (FileNotFoundError, PermissionError):
            pass
