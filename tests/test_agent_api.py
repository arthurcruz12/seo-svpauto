from app.agent_api import _integration_catalog, _route


def test_routes_billing_to_specialists_and_auditor():
    plan = _route("Faça a faturação de Coimbra e Picoto com NC pendentes", "work")

    assert plan["agents"] == ["manager", "billing", "documents", "audit"]
    assert plan["approval_required"] is False
    assert plan["write_blocked"] is False


def test_routes_sensitive_snc_write_to_human_approval(monkeypatch):
    monkeypatch.delenv("AGENT_EXECUTION_ENABLED", raising=False)
    monkeypatch.delenv("SNC_INTEGRATION_ENABLED", raising=False)

    plan = _route("Prepare e lance no SNC o lançamento contabilístico", "work")

    assert "accounting" in plan["agents"]
    assert "audit" in plan["agents"]
    assert "snc" in plan["agents"]
    assert plan["approval_required"] is True
    assert plan["write_blocked"] is True
    assert plan["execution_enabled"] is False


def test_code_mode_routes_to_code_agent():
    plan = _route("Analise este problema", "code")

    assert plan["agents"][:2] == ["manager", "code"]


def test_integration_catalog_never_contains_secret_values(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "must-not-leak")
    monkeypatch.setenv("POSTGRES_URL", "postgresql://secret")
    monkeypatch.setenv("ATENA_API_URL", "https://atena.example.test")

    catalog = _integration_catalog()
    serialized = repr(catalog)

    assert "must-not-leak" not in serialized
    assert "postgresql://secret" not in serialized
    assert "https://atena.example.test" not in serialized
    assert next(item for item in catalog if item["id"] == "atena")["configured"] is True


def test_atena_and_snc_are_separate_integrations():
    catalog = _integration_catalog()
    by_id = {item["id"]: item for item in catalog}

    assert by_id["atena"]["name"] == "Atena"
    assert by_id["snc"]["name"] == "SNC"
    assert by_id["atena"]["permissions"] == ["READ"]
    assert by_id["snc"]["approval_required"] is True
