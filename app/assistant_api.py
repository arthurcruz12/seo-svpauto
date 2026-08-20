from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.agents.manager import AgentManager
from app.database import get_db
from app.main import get_current_user, write_audit_log
from app.models import User
from app.security import require_permission

router = APIRouter(prefix="/api/v1/assistant", tags=["assistant"])

MAX_UPLOAD_BYTES = int(os.getenv("SEO_MAX_UPLOAD_BYTES", str(10 * 1024 * 1024)))
STORAGE_ROOT = Path(os.getenv("SEO_ARTIFACT_STORAGE_PATH", "data/agent-storage"))
MANAGER = AgentManager()


def _billing_intent(message: str) -> bool:
    normalized = message.casefold()
    return any(term in normalized for term in ("faturação", "faturacao", "fatura", "mapa diário", "mapa diario"))


def _safe_name(filename: str) -> str:
    name = Path(filename or "upload.xlsx").name
    cleaned = re.sub(r"[^A-Za-z0-9._() \-À-ÿ]+", "_", name).strip(" .")
    return cleaned[:180] or "upload.xlsx"


def _tenant_root(tenant_id: int) -> Path:
    path = STORAGE_ROOT / f"tenant-{tenant_id}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _write_file_manifest(tenant_id: int, user_id: int, metadata: dict) -> None:
    folder = _tenant_root(tenant_id) / "metadata"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{metadata['file_id']}.json").write_text(
        json.dumps({**metadata, "tenant_id": tenant_id, "user_id": user_id}, ensure_ascii=False),
        encoding="utf-8",
    )


def _write_task_manifest(tenant_id: int, user_id: int, task: dict) -> None:
    folder = _tenant_root(tenant_id) / "tasks"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{task['task_id']}.json").write_text(
        json.dumps({**task, "tenant_id": tenant_id, "user_id": user_id}, ensure_ascii=False),
        encoding="utf-8",
    )


def _store_file(
    *,
    tenant_id: int,
    user_id: int,
    content: bytes,
    filename: str,
    content_type: str,
    source: str,
    sha256: str,
) -> dict:
    file_id = str(uuid4())
    safe_name = _safe_name(filename)
    folder = _tenant_root(tenant_id) / "files"
    folder.mkdir(parents=True, exist_ok=True)
    storage_path = folder / f"{file_id}__{safe_name}"
    storage_path.write_bytes(content)
    metadata = {
        "file_id": file_id,
        "filename": safe_name,
        "content_type": content_type,
        "size": len(content),
        "sha256": sha256,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "storage_reference": str(storage_path),
    }
    _write_file_manifest(tenant_id, user_id, metadata)
    return {key: value for key, value in metadata.items() if key != "storage_reference"}


@router.post("/messages")
async def assistant_messages(
    message: str = Form(...),
    file: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(current_user, "dashboard:read")
    if not _billing_intent(message):
        return {
            "answer": "Fluxo executor disponível nesta fase para faturação diária. Outros pedidos permanecem no fluxo existente da Assistente IA.",
            "conversation_id": None,
            "task_id": None,
            "status": "NEEDS_REVIEW",
            "agents_used": ["SEO Agent Manager"],
            "artifacts": [],
            "audit": None,
            "approval_required": False,
            "confidence": 0.0,
            "errors": ["unsupported_execution_intent"],
        }

    if file is None:
        return {
            "answer": "Envie o Excel bruto da faturação para executar a tarefa.",
            "conversation_id": None,
            "task_id": None,
            "status": "NEEDS_REVIEW",
            "agents_used": ["SEO Agent Manager", "DocumentAgent"],
            "artifacts": [],
            "audit": None,
            "approval_required": False,
            "confidence": 0.0,
            "errors": ["billing_source_file_required"],
        }

    filename = _safe_name(file.filename or "faturacao.xlsx")
    if not filename.lower().endswith((".xlsx", ".xlsm")):
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Billing source must be XLSX/XLSM")

    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Billing workbook exceeds upload limit")

    created_at = datetime.now(timezone.utc).isoformat()
    try:
        result = MANAGER.execute_billing(content, filename)
    except ValueError as exc:
        write_audit_log(
            db,
            current_user.tenant_id,
            "agent_billing_failed",
            "agent_task",
            None,
            f"user={current_user.email}; filename={filename}; error={str(exc)[:300]}",
        )
        db.commit()
        return {
            "answer": "Não foi possível processar o Excel de faturação.",
            "conversation_id": None,
            "task_id": None,
            "status": "FAILED",
            "agents_used": ["SEO Agent Manager", "DocumentAgent"],
            "artifacts": [],
            "audit": None,
            "approval_required": False,
            "confidence": 0.0,
            "errors": [str(exc)],
        }

    source_meta = _store_file(
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        content=content,
        filename=filename,
        content_type=file.content_type or "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        source="original",
        sha256=result["source_sha256"],
    )

    artifacts = []
    if result["output_content"]:
        output_meta = _store_file(
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            content=result["output_content"],
            filename=result["output_filename"],
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            source="billing_result",
            sha256=result["output_sha256"],
        )
        artifacts.append({
            **output_meta,
            "download_url": f"/api/v1/assistant/artifacts/{output_meta['file_id']}",
        })

    task_manifest = {
        "task_id": result["task_id"],
        "agent": "billing",
        "created_at": created_at,
        "started_at": created_at,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "status": result["status"],
        "progress": 100 if result["status"] in {"COMPLETED", "FAILED"} else 0,
        "source_file": source_meta,
        "output_files": artifacts,
        "errors": result["errors"],
        "audit": result["audit"],
        "agents_used": result["agents_used"],
        "records_processed": result["records_processed"],
        "records_rejected": result["records_rejected"],
    }
    _write_task_manifest(current_user.tenant_id, current_user.id, task_manifest)

    write_audit_log(
        db,
        current_user.tenant_id,
        "agent_billing_completed" if result["status"] == "COMPLETED" else "agent_billing_failed",
        "agent_task",
        None,
        f"task_id={result['task_id']}; user={current_user.email}; source_sha256={result['source_sha256']}; output_sha256={result['output_sha256']}; status={result['status']}",
    )
    db.commit()

    return {
        "answer": (
            "Faturação concluída e auditada. O Excel final contém Faturação Separada, Resumo Vendedores e Mapa Diário."
            if result["status"] == "COMPLETED"
            else "A faturação foi processada, mas o auditor rejeitou o resultado."
        ),
        "conversation_id": None,
        "task_id": result["task_id"],
        "status": result["status"],
        "agents_used": result["agents_used"],
        "artifacts": artifacts if result["status"] == "COMPLETED" else [],
        "audit": result["audit"],
        "approval_required": False,
        "confidence": result["confidence"],
        "errors": result["errors"],
    }


@router.get("/artifacts/{file_id}")
def download_artifact(file_id: str, current_user: User = Depends(get_current_user)):
    require_permission(current_user, "dashboard:read")
    metadata_path = _tenant_root(current_user.tenant_id) / "metadata" / f"{file_id}.json"
    if not metadata_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if metadata.get("tenant_id") != current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found")
    storage_path = Path(metadata["storage_reference"])
    if not storage_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact file missing")
    return FileResponse(storage_path, media_type=metadata["content_type"], filename=metadata["filename"])


@router.get("/tasks")
def list_tasks(current_user: User = Depends(get_current_user)):
    require_permission(current_user, "dashboard:read")
    task_dir = _tenant_root(current_user.tenant_id) / "tasks"
    if not task_dir.exists():
        return {"tasks": []}
    tasks = []
    for path in sorted(task_dir.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True)[:50]:
        task = json.loads(path.read_text(encoding="utf-8"))
        if task.get("tenant_id") != current_user.tenant_id:
            continue
        task.pop("tenant_id", None)
        task.pop("user_id", None)
        tasks.append(task)
    return {"tasks": tasks}
