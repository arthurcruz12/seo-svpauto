from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from urllib.parse import quote
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, selectinload

from app.agents.manager import AgentExecutionFailure, AgentManager
from app.artifact_storage import ArtifactStorage, get_artifact_storage
from app.database import get_db
from app.main import get_current_user, write_audit_log
from app.models import AgentArtifact, AgentExecution, AgentTask, Company, User
from app.security import require_permission

router = APIRouter(prefix="/api/v1/assistant", tags=["assistant"])

MAX_UPLOAD_BYTES = int(os.getenv("SEO_MAX_UPLOAD_BYTES", str(10 * 1024 * 1024)))
MANAGER = AgentManager()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _billing_intent(message: str) -> bool:
    normalized = message.casefold()
    return any(term in normalized for term in ("faturação", "faturacao", "fatura", "mapa diário", "mapa diario"))


def _safe_name(filename: str) -> str:
    name = Path(filename or "upload.xlsx").name
    cleaned = re.sub(r"[^A-Za-z0-9._() \-À-ÿ]+", "_", name).strip(" .")
    return cleaned[:180] or "upload.xlsx"


def _artifact_payload(artifact: AgentArtifact) -> dict:
    return {
        "file_id": artifact.id,
        "filename": artifact.filename,
        "content_type": artifact.content_type,
        "size": artifact.size,
        "sha256": artifact.sha256,
        "role": artifact.role,
        "created_at": artifact.created_at.isoformat() if artifact.created_at else None,
        "download_url": f"/api/v1/assistant/artifacts/{artifact.id}" if artifact.role == "OUTPUT" else None,
    }


def _execution_payload(execution: AgentExecution) -> dict:
    return {
        "execution_id": execution.id,
        "agent_name": execution.agent_name,
        "status": execution.status,
        "started_at": execution.started_at.isoformat() if execution.started_at else None,
        "finished_at": execution.finished_at.isoformat() if execution.finished_at else None,
        "input_summary": execution.input_summary,
        "output_summary": execution.output_summary,
        "confidence": execution.confidence,
        "error_message": execution.error_message,
    }


def _task_payload(task: AgentTask, include_executions: bool = True) -> dict:
    source = next((artifact for artifact in task.artifacts if artifact.role == "SOURCE"), None)
    outputs = [artifact for artifact in task.artifacts if artifact.role == "OUTPUT"]
    audit = json.loads(task.audit_json) if task.audit_json else None
    payload = {
        "task_id": task.id,
        "agent": task.task_type,
        "agent_type": task.agent_type,
        "task_type": task.task_type,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "finished_at": task.finished_at.isoformat() if task.finished_at else None,
        "status": task.status,
        "progress": task.progress,
        "source_file": _artifact_payload(source) if source else None,
        "output_files": [_artifact_payload(artifact) for artifact in outputs],
        "errors": [task.error_message] if task.error_message else [],
        "error_code": task.error_code,
        "audit": audit,
        "agents_used": [execution.agent_name for execution in task.executions],
        "records_processed": task.records_processed,
        "records_rejected": task.records_rejected,
        "approval_required": task.approval_required,
        "confidence": task.confidence,
    }
    if include_executions:
        payload["executions"] = [_execution_payload(item) for item in task.executions]
    return payload


def _persist_artifact(
    *,
    db: Session,
    storage: ArtifactStorage,
    task: AgentTask,
    user: User,
    filename: str,
    content_type: str,
    content: bytes,
    role: str,
    digest: str | None = None,
) -> AgentArtifact:
    artifact_id = str(uuid4())
    safe_name = _safe_name(filename)
    storage_reference = storage.save(
        tenant_id=user.tenant_id,
        artifact_id=artifact_id,
        filename=safe_name,
        content=content,
    )
    artifact = AgentArtifact(
        id=artifact_id,
        task_id=task.id,
        tenant_id=user.tenant_id,
        user_id=user.id,
        filename=safe_name,
        content_type=content_type,
        size=len(content),
        sha256=digest or sha256(content).hexdigest(),
        role=role,
        storage_provider=storage.provider,
        storage_reference=storage_reference,
        created_at=_now(),
    )
    db.add(artifact)
    return artifact


def _persist_executions(db: Session, task_id: str, executions: list[dict]) -> None:
    existing = {item.agent_name for item in db.query(AgentExecution).filter(AgentExecution.task_id == task_id).all()}
    for item in executions:
        if item["agent_name"] in existing:
            continue
        db.add(
            AgentExecution(
                id=str(uuid4()),
                task_id=task_id,
                agent_name=item["agent_name"],
                status=item["status"],
                started_at=item["started_at"],
                finished_at=item.get("finished_at"),
                input_summary=item.get("input_summary"),
                output_summary=item.get("output_summary"),
                confidence=float(item.get("confidence", 0.0)),
                error_message=item.get("error_message"),
            )
        )


def _task_query(db: Session):
    return db.query(AgentTask).options(selectinload(AgentTask.executions), selectinload(AgentTask.artifacts))


def _mark_failed(
    *,
    db: Session,
    task_id: str,
    tenant_id: int,
    user_email: str,
    filename: str,
    exc: Exception,
    executions: list[dict] | None = None,
) -> AgentTask | None:
    db.rollback()
    task = db.query(AgentTask).filter(AgentTask.id == task_id, AgentTask.tenant_id == tenant_id).first()
    if not task:
        return None
    if executions:
        _persist_executions(db, task.id, executions)
    task.status = "FAILED"
    task.progress = 100
    task.error_code = getattr(exc, "stage", None) or type(exc).__name__
    task.error_message = str(exc)[:4000]
    task.finished_at = _now()
    write_audit_log(
        db,
        tenant_id,
        "agent_billing_failed",
        "agent_task",
        None,
        f"task_id={task.id}; user={user_email}; filename={filename}; error={str(exc)[:300]}",
    )
    db.commit()
    return task


@router.post("/messages")
async def assistant_messages(
    message: str = Form(...),
    file: UploadFile | None = File(default=None),
    company_id: int | None = Form(default=None),
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

    if company_id is not None:
        company = db.query(Company).filter(Company.id == company_id, Company.tenant_id == current_user.tenant_id).first()
        if not company:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

    filename = _safe_name(file.filename or "faturacao.xlsx")
    if not filename.lower().endswith((".xlsx", ".xlsm")):
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Billing source must be XLSX/XLSM")

    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Billing workbook exceeds upload limit")

    task = AgentTask(
        id=str(uuid4()),
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        company_id=company_id,
        agent_type="manager",
        task_type="billing",
        status="PENDING",
        progress=0,
        instruction=message,
        source_filename=filename,
        records_processed=0,
        records_rejected=0,
        approval_required=False,
        confidence=0.0,
        created_at=_now(),
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    task.status = "RUNNING"
    task.progress = 5
    task.started_at = _now()
    db.commit()

    manager_executions: list[dict] = []
    try:
        storage = get_artifact_storage()
        source_digest = sha256(content).hexdigest()
        _persist_artifact(
            db=db,
            storage=storage,
            task=task,
            user=current_user,
            filename=filename,
            content_type=file.content_type or "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            content=content,
            role="SOURCE",
            digest=source_digest,
        )
        task.progress = 15
        db.commit()

        result = MANAGER.execute_billing(content, filename, task_id=task.id)
        manager_executions = result.get("executions", [])
        _persist_executions(db, task.id, manager_executions)

        audit_bytes = json.dumps(result["audit"], ensure_ascii=False, default=str, indent=2).encode("utf-8")
        _persist_artifact(
            db=db,
            storage=storage,
            task=task,
            user=current_user,
            filename=f"{Path(filename).stem} - Auditoria.json",
            content_type="application/json",
            content=audit_bytes,
            role="AUDIT_REPORT",
        )

        artifacts: list[AgentArtifact] = []
        if result["status"] == "COMPLETED" and result["output_content"]:
            output_artifact = _persist_artifact(
                db=db,
                storage=storage,
                task=task,
                user=current_user,
                filename=result["output_filename"],
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                content=result["output_content"],
                role="OUTPUT",
                digest=result["output_sha256"],
            )
            artifacts.append(output_artifact)

        task.status = result["status"]
        task.progress = 100
        task.records_processed = result["records_processed"]
        task.records_rejected = result["records_rejected"]
        task.confidence = float(result["confidence"])
        task.audit_json = json.dumps(result["audit"], ensure_ascii=False, default=str)
        task.error_code = "audit_failed" if result["status"] == "FAILED" else None
        task.error_message = "; ".join(result["errors"])[:4000] if result["errors"] else None
        task.finished_at = _now()

        write_audit_log(
            db,
            current_user.tenant_id,
            "agent_billing_completed" if result["status"] == "COMPLETED" else "agent_billing_failed",
            "agent_task",
            None,
            f"task_id={task.id}; user={current_user.email}; source_sha256={source_digest}; output_sha256={result['output_sha256']}; status={result['status']}; records_processed={result['records_processed']}; records_rejected={result['records_rejected']}",
        )
        db.commit()

        return {
            "answer": (
                "Faturação concluída e auditada. O Excel final contém Faturação Separada, Resumo Vendedores e Mapa Diário."
                if result["status"] == "COMPLETED"
                else "A faturação foi processada, mas o auditor rejeitou o resultado."
            ),
            "conversation_id": None,
            "task_id": task.id,
            "status": result["status"],
            "agents_used": result["agents_used"],
            "executions": manager_executions,
            "artifacts": [_artifact_payload(item) for item in artifacts],
            "audit": result["audit"],
            "approval_required": False,
            "confidence": result["confidence"],
            "errors": result["errors"],
        }
    except AgentExecutionFailure as exc:
        task = _mark_failed(
            db=db,
            task_id=task.id,
            tenant_id=current_user.tenant_id,
            user_email=current_user.email,
            filename=filename,
            exc=exc,
            executions=exc.executions,
        )
        return {
            "answer": "Não foi possível processar o Excel de faturação.",
            "conversation_id": None,
            "task_id": task.id if task else None,
            "status": "FAILED",
            "agents_used": [item["agent_name"] for item in exc.executions],
            "executions": exc.executions,
            "artifacts": [],
            "audit": None,
            "approval_required": False,
            "confidence": 0.0,
            "errors": [str(exc)],
        }
    except Exception as exc:
        task = _mark_failed(
            db=db,
            task_id=task.id,
            tenant_id=current_user.tenant_id,
            user_email=current_user.email,
            filename=filename,
            exc=exc,
            executions=manager_executions,
        )
        return {
            "answer": "Não foi possível processar o Excel de faturação.",
            "conversation_id": None,
            "task_id": task.id if task else None,
            "status": "FAILED",
            "agents_used": [item["agent_name"] for item in manager_executions],
            "executions": manager_executions,
            "artifacts": [],
            "audit": None,
            "approval_required": False,
            "confidence": 0.0,
            "errors": [str(exc)],
        }


@router.get("/artifacts/{file_id}")
def download_artifact(
    file_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(current_user, "dashboard:read")
    artifact = (
        db.query(AgentArtifact)
        .filter(
            AgentArtifact.id == file_id,
            AgentArtifact.tenant_id == current_user.tenant_id,
            AgentArtifact.role == "OUTPUT",
        )
        .first()
    )
    if not artifact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found")
    storage = get_artifact_storage()
    if artifact.storage_provider != storage.provider or not storage.exists(artifact.storage_reference):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact file missing")
    stream = storage.open(artifact.storage_reference)
    headers = {"Content-Disposition": f"attachment; filename*=UTF-8''{quote(artifact.filename)}"}
    return StreamingResponse(stream, media_type=artifact.content_type, headers=headers)


@router.get("/tasks/{task_id}")
def get_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(current_user, "dashboard:read")
    task = _task_query(db).filter(AgentTask.id == task_id, AgentTask.tenant_id == current_user.tenant_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return _task_payload(task, include_executions=True)


@router.get("/tasks")
def list_tasks(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    task_status: str | None = Query(default=None, alias="status"),
    agent_type: str | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(current_user, "dashboard:read")
    query = _task_query(db).filter(AgentTask.tenant_id == current_user.tenant_id)
    if task_status:
        query = query.filter(AgentTask.status == task_status.upper())
    if agent_type:
        query = query.filter(AgentTask.agent_type == agent_type)
    if date_from:
        query = query.filter(AgentTask.created_at >= date_from)
    if date_to:
        query = query.filter(AgentTask.created_at <= date_to)
    total = query.count()
    tasks = query.order_by(AgentTask.created_at.desc()).offset(offset).limit(limit).all()
    return {
        "tasks": [_task_payload(task, include_executions=True) for task in tasks],
        "pagination": {"limit": limit, "offset": offset, "total": total},
    }
