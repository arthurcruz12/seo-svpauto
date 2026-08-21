from pathlib import Path


def test_work_executor_targets_operational_traceability_backend():
    bridge = Path("api/assistant.py").read_text(encoding="utf-8")
    assert "/assistant/work/billing/persist" in bridge
    assert "PENDING_BACKEND_UPGRADE" in bridge
    assert "operational_persistence" in bridge
    assert "source_file" in bridge
    assert "output_file" in bridge
    assert "audit_json" in bridge


def test_protected_frontend_exposes_reference_date_without_touching_core_source():
    build = Path("scripts/build-agent-frontend.sh").read_text(encoding="utf-8")
    patch = Path("scripts/patch-work-traceability-ui.py").read_text(encoding="utf-8")
    assert "python scripts/patch-work-traceability-ui.py" in build
    assert build.index("patch-work-cloud-sync.py") < build.index("patch-work-traceability-ui.py")
    assert "Rastreabilidade operacional" in patch
    assert "Data de referência do Excel na Nuvem" in patch
    assert "/assistant/work/files/" in patch
    assert "/reference-date" in patch
    for protected_marker in ("handleLogin", "handleMfa", "handleRegister", "admin@seo.local"):
        assert protected_marker not in patch
