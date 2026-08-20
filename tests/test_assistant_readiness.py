from fastapi.testclient import TestClient

from app.main_saft import app


client = TestClient(app)


def test_assistant_readiness_requires_explicit_persistent_storage(monkeypatch):
    monkeypatch.delenv("SEO_ARTIFACT_STORAGE_PATH", raising=False)
    monkeypatch.setenv("SEO_ARTIFACT_STORAGE_PROVIDER", "local")

    response = client.get("/api/v1/assistant/ready")

    assert response.status_code == 503
    assert response.json()["detail"] == "Assistant persistence is not ready"


def test_assistant_readiness_checks_database_and_writable_storage(monkeypatch, tmp_path):
    storage_root = tmp_path / "agent-storage"
    monkeypatch.setenv("SEO_ARTIFACT_STORAGE_PATH", str(storage_root))
    monkeypatch.setenv("SEO_ARTIFACT_STORAGE_PROVIDER", "local")

    response = client.get("/api/v1/assistant/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "task_storage": "database",
        "artifact_storage": "persistent",
        "storage_provider": "local",
    }
    assert storage_root.is_dir()
    assert list(storage_root.glob(".seo-readiness-*")) == []
