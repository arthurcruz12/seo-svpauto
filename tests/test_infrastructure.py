import json

import pytest

from app import integrations
from app.observability import _before_send


class FakeResponse:
    def __init__(self, payload=None, status_code=200):
        self._payload = payload or {"result": "Success"}
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError("http error")

    def json(self):
        return self._payload


def test_infrastructure_status_reports_capabilities_without_values(monkeypatch):
    monkeypatch.setenv("POSTGRES_URL", "postgresql://secret")
    monkeypatch.setenv("POSTGRES_URL_NON_POOLING", "postgresql://admin-secret")
    monkeypatch.setenv("REDIS_URL", "rediss://secret")
    monkeypatch.setenv("UPSTASH_VECTOR_REST_URL", "https://vector.example")
    monkeypatch.setenv("UPSTASH_VECTOR_REST_TOKEN", "vector-secret")
    monkeypatch.setenv("UPSTASH_SEARCH_REST_URL", "https://search.example")
    monkeypatch.setenv("UPSTASH_SEARCH_REST_TOKEN", "search-secret")
    monkeypatch.setenv("upseo_QSTASH_URL", "https://qstash.example")
    monkeypatch.setenv("upseo_QSTASH_TOKEN", "qstash-secret")
    monkeypatch.setenv("upseo_QSTASH_CURRENT_SIGNING_KEY", "current-secret")
    monkeypatch.setenv("upseo_QSTASH_NEXT_SIGNING_KEY", "next-secret")
    monkeypatch.setenv("SENTRY_DSN", "https://public@example.ingest.sentry.io/1")
    monkeypatch.setenv("CHECKLY_ACCOUNT_ID", "account-1")

    status = integrations.infrastructure_status()

    assert status["neon"]["configured"] is True
    assert status["qstash"]["configured"] is True
    assert status["vector"]["configured"] is True
    assert status["sentry"]["configured"] is True
    serialized = json.dumps(status)
    assert "secret" not in serialized
    assert "postgresql://" not in serialized


def test_vector_memory_is_tenant_scoped(monkeypatch):
    monkeypatch.setenv("UPSTASH_VECTOR_REST_URL", "https://vector.example")
    monkeypatch.setenv("UPSTASH_VECTOR_REST_TOKEN", "token")
    calls = []

    def fake_post(url, **kwargs):
        calls.append((url, kwargs))
        if "query-data" in url:
            return FakeResponse({"result": [{"id": "pattern-1", "score": 0.9}]})
        return FakeResponse()

    monkeypatch.setattr(integrations.httpx, "post", fake_post)

    integrations.remember_semantic_pattern(
        item_id="pattern-1",
        text="Vodafone -> conta 6261",
        tenant_id=42,
        metadata={"kind": "snc_mapping"},
    )
    results = integrations.find_semantic_patterns(text="Vodafone", tenant_id=42)

    assert results[0]["id"] == "pattern-1"
    upsert_body = calls[0][1]["json"]
    query_body = calls[1][1]["json"]
    assert upsert_body["metadata"]["tenant_id"] == 42
    assert query_body["filter"] == "tenant_id = 42"
    assert query_body["queryMode"] == "HYBRID"


def test_qstash_uses_prefixed_vercel_variables_and_redacts_body(monkeypatch):
    monkeypatch.setenv("upseo_QSTASH_URL", "https://qstash.example")
    monkeypatch.setenv("upseo_QSTASH_TOKEN", "qstash-token")
    captured = {}

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured.update(kwargs)
        return FakeResponse({"messageId": "msg-1"})

    monkeypatch.setattr(integrations.httpx, "post", fake_post)

    result = integrations.publish_qstash(
        destination="https://api.example/jobs/saft",
        payload={"import_id": 10},
        delay="10m",
    )

    assert result["messageId"] == "msg-1"
    assert captured["headers"]["Authorization"] == "Bearer qstash-token"
    assert captured["headers"]["Upstash-Redact-Fields"] == "body,header[Authorization]"
    assert captured["headers"]["Upstash-Delay"] == "10m"
    assert json.loads(captured["content"])["import_id"] == 10


def test_qstash_rejects_non_http_destination(monkeypatch):
    monkeypatch.setenv("upseo_QSTASH_URL", "https://qstash.example")
    monkeypatch.setenv("upseo_QSTASH_TOKEN", "token")

    with pytest.raises(ValueError, match="absolute HTTP"):
        integrations.publish_qstash(destination="javascript:alert(1)", payload={})


def test_sentry_scrubber_removes_financial_payloads_and_auth_headers():
    event = {
        "request": {
            "data": {"invoice": "secret"},
            "cookies": {"session": "secret"},
            "headers": {"Authorization": "Bearer abc", "Content-Type": "application/json"},
        },
        "extra": {
            "saft_payload": "raw xml",
            "document_number": "FT 1",
            "safe_metric": 12,
        },
    }

    cleaned = _before_send(event, {})

    assert "data" not in cleaned["request"]
    assert "cookies" not in cleaned["request"]
    assert cleaned["request"]["headers"]["Authorization"] == "[Filtered]"
    assert cleaned["extra"]["saft_payload"] == "[Filtered]"
    assert cleaned["extra"]["document_number"] == "[Filtered]"
    assert cleaned["extra"]["safe_metric"] == 12
