from pathlib import Path


def test_work_cloud_sync_is_part_of_protected_frontend_build():
    build_script = Path("scripts/build-agent-frontend.sh").read_text(encoding="utf-8")
    cloud_patch = Path("scripts/patch-work-cloud-sync.py").read_text(encoding="utf-8")

    assert "python scripts/patch-work-cloud-sync.py" in build_script
    assert build_script.index("patch-work-preview-bridge.py") < build_script.index("patch-work-cloud-sync.py")
    assert build_script.index("patch-work-cloud-sync.py") < build_script.index("patch-agent-vercel-bridge.py")

    assert 'ASSISTANT_CLOUD_EVENT = "seo:assistant-cloud-artifacts"' in cloud_patch
    assert 'category: "Assistente IA · Trabalho"' in cloud_patch
    assert "/api/v1/assistant/tasks?status=COMPLETED&limit=100" in cloud_patch
    assert '/api/assistant?op=tasks' in cloud_patch
    assert "assistantCloudArtifacts.get(file.id)" in cloud_patch
    assert "emitAssistantCloudArtifacts(payload.artifacts ?? [])" in cloud_patch
    assert "inline_base64" in cloud_patch


def test_work_cloud_sync_does_not_target_authentication_or_public_landing():
    cloud_patch = Path("scripts/patch-work-cloud-sync.py").read_text(encoding="utf-8")
    forbidden_targets = [
        "handleLogin",
        "handleMfa",
        "handleRegister",
        "admin@seo.local",
        'setAppScreen("landing")',
    ]
    for target in forbidden_targets:
        assert target not in cloud_patch
