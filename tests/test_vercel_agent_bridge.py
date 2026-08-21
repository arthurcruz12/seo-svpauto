from api.agents import _integration_catalog, _route


def test_vercel_bridge_routes_snc_write_to_approval(monkeypatch):
    monkeypatch.delenv("AGENT_EXECUTION_ENABLED", raising=False)
    plan = _route("Lance no SNC este lançamento contabilístico", "work")

    assert "accounting" in plan["agents"]
    assert "audit" in plan["agents"]
    assert "snc" in plan["agents"]
    assert plan["approval_required"] is True
    assert plan["write_blocked"] is True


def test_vercel_bridge_integration_catalog_does_not_expose_secrets(monkeypatch):
    monkeypatch.setenv("POSTGRES_URL", "postgresql://very-secret")
    monkeypatch.setenv("UPSTASH_VECTOR_REST_TOKEN", "vector-secret")
    monkeypatch.setenv("SENTRY_DSN", "https://secret@sentry.invalid/1")

    serialized = repr(_integration_catalog())

    assert "very-secret" not in serialized
    assert "vector-secret" not in serialized
    assert "secret@sentry" not in serialized


def test_vercel_bridge_keeps_atena_and_snc_separate():
    catalog = {item["id"]: item for item in _integration_catalog()}

    assert catalog["atena"]["name"] == "Atena"
    assert catalog["snc"]["name"] == "SNC"
    assert catalog["atena"]["permissions"] == ["READ"]
    assert catalog["snc"]["approval_required"] is True
