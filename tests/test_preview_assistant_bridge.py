import hashlib

from api import assistant as preview_assistant


def test_preview_bridge_is_disabled_in_production(monkeypatch):
    monkeypatch.setenv("VERCEL_ENV", "production")
    assert preview_assistant._preview_only() is False


def test_preview_bridge_is_available_outside_production(monkeypatch):
    monkeypatch.setenv("VERCEL_ENV", "preview")
    assert preview_assistant._preview_only() is True


def test_preview_task_cache_key_never_exposes_bearer_token():
    token = "sensitive-bearer-token"
    key = preview_assistant._session_key(token)

    assert key == hashlib.sha256(token.encode("utf-8")).hexdigest()
    assert token not in key


def test_preview_filename_is_reduced_to_safe_basename():
    assert preview_assistant._safe_filename("../folder/Faturação 20.08.xlsx") == "Faturação 20.08.xlsx"
