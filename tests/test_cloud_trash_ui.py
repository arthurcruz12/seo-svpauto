from pathlib import Path


def test_protected_frontend_restores_cloud_trash_without_replacing_core_ui():
    build = Path("scripts/build-agent-frontend.sh").read_text(encoding="utf-8")
    patch = Path("scripts/patch-cloud-trash-ui.py").read_text(encoding="utf-8")

    assert "python scripts/patch-cloud-trash-ui.py" in build
    assert build.index("patch-work-traceability-ui.py") < build.index("patch-cloud-trash-ui.py")
    assert "type TrashCloudFile" in patch
    assert "/cloud/trash?limit=250" in patch
    assert "Mover para a Lixeira" in patch
    assert "Restaurar" in patch
    assert "Eliminar definitivamente" in patch
    assert "Lixeira preparada" in patch

    for protected_marker in ("handleLogin", "handleMfa", "handleRegister", "admin@seo.local"):
        assert protected_marker not in patch
