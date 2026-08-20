from pathlib import Path


def test_work_tasks_ui_is_applied_after_protected_frontend_patch():
    build_script = Path("scripts/build-agent-frontend.sh").read_text(encoding="utf-8")
    work_patch = Path("scripts/patch-work-tasks-ui.py").read_text(encoding="utf-8")
    preview_patch = Path("scripts/patch-work-preview-bridge.py").read_text(encoding="utf-8")

    assert "python scripts/patch-agent-frontend.py" in build_script
    assert "python scripts/patch-work-tasks-ui.py" in build_script
    assert "python scripts/patch-work-preview-bridge.py" in build_script
    assert build_script.index("patch-agent-frontend.py") < build_script.index("patch-work-tasks-ui.py")
    assert build_script.index("patch-work-tasks-ui.py") < build_script.index("patch-work-preview-bridge.py")

    assert 'assistantMode === "work" && <AssistantWorkPanel accessToken={accessToken} />' in work_patch
    assert '/api/v1/assistant/messages' in work_patch
    assert '/api/v1/assistant/tasks' in work_patch
    assert 'artifact.download_url.startsWith("/api/")' in work_patch
    assert 'DocumentAgent' in work_patch
    assert 'BillingAgent' in work_patch
    assert 'AuditAgent' in work_patch
    assert 'Executor real' in work_patch

    assert '/api/assistant?op=tasks' in preview_patch
    assert '/api/assistant?op=execute' in preview_patch
    assert 'inline_base64' in preview_patch
    assert 'Preview seguro:' in preview_patch


def test_work_panel_does_not_modify_protected_public_auth_markers():
    patches = [
        Path("scripts/patch-work-tasks-ui.py").read_text(encoding="utf-8"),
        Path("scripts/patch-work-preview-bridge.py").read_text(encoding="utf-8"),
    ]

    forbidden_targets = [
        "handleLogin",
        "handleMfa",
        "handleRegister",
        "admin@seo.local",
        'setAppScreen("landing")',
    ]
    for patch in patches:
        for target in forbidden_targets:
            assert target not in patch
