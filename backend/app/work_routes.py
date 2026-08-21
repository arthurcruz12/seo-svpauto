from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from starlette.concurrency import run_in_threadpool

from .main import MAX_UPLOAD_BYTES, read_rows, rows_to_dataset
from .security import require_permission
from .store import add_audit_event, append_reconciliation_issues, save_operational_state, save_uploaded_file
from .work_traceability import (
    WORK_ORIGIN_AUDIT,
    WORK_ORIGIN_OUTPUT,
    WORK_ORIGIN_SOURCE,
    assign_reference_date,
    list_work_cloud_files,
    list_work_documents,
    save_work_documents,
    tag_cloud_file,
)


router = APIRouter(prefix="/assistant/work", tags=["assistant-work"])

SEVERE_VALIDATION_MARKERS = (
    "não corresponde",
    "invalida",
    "inválida",
    "invalido",
    "inválido",
    "duplicado",
    "duplicada",
)


async def _read_excel_upload(file: UploadFile, label: str) -> tuple[bytes, str]:
    filename = Path(file.filename or f"{label}.xlsx").name
    if not filename.lower().endswith((".xlsx", ".xlsm")):
        raise HTTPException(status_code=415, detail=f"{label} deve ser XLSX/XLSM.")
    try:
        content = await file.read(MAX_UPLOAD_BYTES + 1)
    finally:
        await file.close()
    if not content:
        raise HTTPException(status_code=400, detail=f"{label} está vazio.")
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail=f"{label} excede o limite de upload.")
    if not content.startswith(b"PK\x03\x04"):
        raise HTTPException(status_code=400, detail=f"O conteúdo de {label} não corresponde a um Excel válido.")
    return content, filename


def _severe_anomalies(task_id: str, documents: list[dict]) -> list[dict]:
    anomalies: list[dict] = []
    for document in documents:
        severe = []
        for validation in document.get("validations") or []:
            normalized = str(validation).casefold()
            if any(marker in normalized for marker in SEVERE_VALIDATION_MARKERS):
                severe.append(str(validation))
        if not severe:
            continue
        seed = f"{task_id}|{document.get('number')}|{'|'.join(severe)}"
        public_id = 10_000 + (int(hashlib.sha1(seed.encode("utf-8")).hexdigest()[:8], 16) % 89_000)
        anomalies.append(
            {
                "id": public_id,
                "document": str(document.get("number") or "Documento sem número")[:120],
                "source": "Assistente IA · Trabalho",
                "value": f"{float(document.get('totalAmount') or 0):.2f} EUR",
                "issue": "; ".join(severe)[:500],
                "status": "Alerta",
            }
        )
    return anomalies


def _save_and_tag(
    *,
    user: dict,
    filename: str,
    content_type: str,
    category: str,
    content: bytes,
    origin: str,
    task_id: str,
    parent_file_id: str | None = None,
) -> dict:
    stored = save_uploaded_file(
        user["company_id"],
        user["email"],
        filename,
        content_type,
        category,
        content,
    )
    tag_cloud_file(
        company_id=user["company_id"],
        file_id=stored["id"],
        origin=origin,
        task_id=task_id,
        parent_file_id=parent_file_id,
    )
    return stored


@router.post("/billing/persist")
async def persist_billing_work(
    task_id: str = Form(default=""),
    source_file: UploadFile = File(...),
    output_file: UploadFile = File(...),
    audit_json: str | None = Form(default=None),
    user: dict = Depends(require_permission("files:upload")),
) -> dict:
    task_id = task_id.strip() or str(uuid4())
    source_content, source_name = await _read_excel_upload(source_file, "Excel de origem")
    output_content, output_name = await _read_excel_upload(output_file, "Excel final")

    rows = await run_in_threadpool(read_rows, source_content, "xlsx")
    dataset = await run_in_threadpool(rows_to_dataset, source_name, rows)
    documents = list(dataset.get("documentIntelligence", {}).get("documents") or [])

    source_cloud = _save_and_tag(
        user=user,
        filename=source_name,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        category="assistente-trabalho-origem",
        content=source_content,
        origin=WORK_ORIGIN_SOURCE,
        task_id=task_id,
    )
    output_cloud = _save_and_tag(
        user=user,
        filename=output_name,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        category="assistente-trabalho-resultado",
        content=output_content,
        origin=WORK_ORIGIN_OUTPUT,
        task_id=task_id,
        parent_file_id=source_cloud["id"],
    )

    document_manifest = json.dumps(
        {
            "taskId": task_id,
            "sourceFileId": source_cloud["id"],
            "documents": documents,
        },
        ensure_ascii=False,
        default=str,
        indent=2,
    ).encode("utf-8")
    manifest_cloud = _save_and_tag(
        user=user,
        filename=f"{Path(source_name).stem} - Documentos.json",
        content_type="application/json",
        category="assistente-trabalho-documentos",
        content=document_manifest,
        origin="assistant-work-documents",
        task_id=task_id,
        parent_file_id=source_cloud["id"],
    )

    audit_cloud = None
    if audit_json:
        try:
            parsed_audit = json.loads(audit_json)
            audit_bytes = json.dumps(parsed_audit, ensure_ascii=False, default=str, indent=2).encode("utf-8")
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=422, detail="Auditoria JSON inválida.") from exc
        audit_cloud = _save_and_tag(
            user=user,
            filename=f"{Path(source_name).stem} - Auditoria.json",
            content_type="application/json",
            category="assistente-trabalho-auditoria",
            content=audit_bytes,
            origin=WORK_ORIGIN_AUDIT,
            task_id=task_id,
            parent_file_id=source_cloud["id"],
        )

    saved_documents = save_work_documents(
        company_id=user["company_id"],
        owner_email=user["email"],
        task_id=task_id,
        source_file_id=source_cloud["id"],
        documents=documents,
    )

    # Documents module: the latest Work execution becomes the current document intelligence view.
    save_operational_state(
        company_id=user["company_id"],
        owner_email=user["email"],
        source_name=source_name,
        summary=dataset["summary"],
        document_intelligence=dataset["documentIntelligence"],
    )

    # Anomalies receive only blocking/gross validation errors. Minor warnings remain in Documents.
    anomalies = _severe_anomalies(task_id, documents)
    if anomalies:
        append_reconciliation_issues(user["company_id"], user["email"], anomalies)

    add_audit_event(
        user["company_id"],
        user["email"],
        "ASSISTANT_WORK_BILLING_PERSISTED",
        (
            f"task_id={task_id}; source_file_id={source_cloud['id']}; output_file_id={output_cloud['id']}; "
            f"documents={saved_documents}; severe_anomalies={len(anomalies)}"
        ),
    )

    return {
        "taskId": task_id,
        "status": "PERSISTED",
        "documentsRegistered": saved_documents,
        "severeAnomaliesCreated": len(anomalies),
        "cloudFiles": [item for item in (source_cloud, output_cloud, manifest_cloud, audit_cloud) if item],
        "sourceFileId": source_cloud["id"],
        "outputFileId": output_cloud["id"],
        "referenceDate": None,
        "message": "Documentos registados, anomalias graves encaminhadas e artefactos guardados na Nuvem.",
    }


@router.get("/files")
def work_files(
    limit: int = Query(default=100, ge=1, le=250),
    user: dict = Depends(require_permission("files:upload")),
) -> list[dict]:
    return list_work_cloud_files(user["company_id"], limit)


@router.post("/files/{file_id}/reference-date")
def set_work_file_reference_date(
    file_id: str,
    reference_date: date = Form(...),
    user: dict = Depends(require_permission("files:upload")),
) -> dict:
    try:
        updated = assign_reference_date(user["company_id"], file_id, reference_date)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    add_audit_event(
        user["company_id"],
        user["email"],
        "ASSISTANT_WORK_REFERENCE_DATE_SET",
        f"file_id={file_id}; reference_date={reference_date.isoformat()}; task_id={updated.get('taskId')}",
    )
    return updated


@router.get("/documents")
def work_documents(
    task_id: str | None = Query(default=None),
    limit: int = Query(default=500, ge=1, le=2000),
    user: dict = Depends(require_permission("dashboard:read")),
) -> list[dict]:
    return list_work_documents(user["company_id"], task_id=task_id, limit=limit)
