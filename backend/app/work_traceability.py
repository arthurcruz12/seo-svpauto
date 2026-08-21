from __future__ import annotations

import json
from datetime import date
from uuid import uuid4

from .store import connect, init_db, migrate_column, utc_now


WORK_ORIGIN_SOURCE = "assistant-work-source"
WORK_ORIGIN_OUTPUT = "assistant-work-output"
WORK_ORIGIN_AUDIT = "assistant-work-audit"


def ensure_work_traceability_schema() -> None:
    init_db()
    with connect() as connection:
        migrate_column(connection, "uploaded_files", "reference_date", "TEXT")
        migrate_column(connection, "uploaded_files", "source_task_id", "TEXT")
        migrate_column(connection, "uploaded_files", "origin", "TEXT NOT NULL DEFAULT 'upload'")
        migrate_column(connection, "uploaded_files", "parent_file_id", "TEXT")
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS work_document_records (
                id TEXT PRIMARY KEY,
                company_id TEXT NOT NULL,
                owner_email TEXT NOT NULL,
                task_id TEXT NOT NULL,
                source_file_id TEXT NOT NULL,
                row_ordinal INTEGER NOT NULL,
                document_number TEXT NOT NULL,
                document_type TEXT NOT NULL,
                issue_date TEXT,
                entity TEXT NOT NULL,
                financial_state TEXT NOT NULL,
                net_amount REAL NOT NULL,
                vat_amount REAL NOT NULL,
                total_amount REAL NOT NULL,
                confidence INTEGER NOT NULL,
                validations_json TEXT NOT NULL,
                needs_review INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                UNIQUE(company_id, task_id, row_ordinal)
            )
            """
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_work_docs_company_date ON work_document_records (company_id, issue_date, created_at DESC)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_work_docs_task ON work_document_records (company_id, task_id, row_ordinal)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_uploaded_files_reference_date ON uploaded_files (company_id, reference_date, uploaded_at DESC)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_uploaded_files_task ON uploaded_files (company_id, source_task_id, uploaded_at DESC)"
        )


def tag_cloud_file(
    *,
    company_id: str,
    file_id: str,
    origin: str,
    task_id: str,
    reference_date: str | None = None,
    parent_file_id: str | None = None,
) -> None:
    ensure_work_traceability_schema()
    with connect() as connection:
        cursor = connection.execute(
            """
            UPDATE uploaded_files
            SET origin = ?, source_task_id = ?, reference_date = ?, parent_file_id = ?
            WHERE id = ? AND company_id = ?
            """,
            (origin, task_id, reference_date, parent_file_id, file_id, company_id),
        )
        if cursor.rowcount != 1:
            raise ValueError("Cloud file not found for this company")


def assign_reference_date(company_id: str, file_id: str, reference_date: date) -> dict:
    ensure_work_traceability_schema()
    value = reference_date.isoformat()
    with connect() as connection:
        cursor = connection.execute(
            """
            UPDATE uploaded_files
            SET reference_date = ?
            WHERE id = ? AND company_id = ? AND source_task_id IS NOT NULL
            """,
            (value, file_id, company_id),
        )
        if cursor.rowcount != 1:
            raise ValueError("Work file not found for this company")
        row = connection.execute(
            """
            SELECT id, filename, content_type, category, size_bytes, sha256, uploaded_at,
                   reference_date, source_task_id, origin, parent_file_id
            FROM uploaded_files
            WHERE id = ? AND company_id = ?
            """,
            (file_id, company_id),
        ).fetchone()
    return _cloud_row(row)


def list_work_cloud_files(company_id: str, limit: int = 100) -> list[dict]:
    ensure_work_traceability_schema()
    safe_limit = min(max(int(limit), 1), 250)
    with connect() as connection:
        rows = connection.execute(
            """
            SELECT id, filename, content_type, category, size_bytes, sha256, uploaded_at,
                   reference_date, source_task_id, origin, parent_file_id
            FROM uploaded_files
            WHERE company_id = ? AND source_task_id IS NOT NULL
            ORDER BY COALESCE(reference_date, uploaded_at) DESC, uploaded_at DESC
            LIMIT ?
            """,
            (company_id, safe_limit),
        ).fetchall()
    return [_cloud_row(row) for row in rows]


def save_work_documents(
    *,
    company_id: str,
    owner_email: str,
    task_id: str,
    source_file_id: str,
    documents: list[dict],
) -> int:
    ensure_work_traceability_schema()
    now = utc_now()
    normalized_owner = owner_email.strip().lower()
    with connect() as connection:
        connection.execute(
            "DELETE FROM work_document_records WHERE company_id = ? AND task_id = ?",
            (company_id, task_id),
        )
        connection.executemany(
            """
            INSERT INTO work_document_records (
                id, company_id, owner_email, task_id, source_file_id, row_ordinal,
                document_number, document_type, issue_date, entity, financial_state,
                net_amount, vat_amount, total_amount, confidence, validations_json,
                needs_review, created_at
            ) VALUES (
                :id, :company_id, :owner_email, :task_id, :source_file_id, :row_ordinal,
                :document_number, :document_type, :issue_date, :entity, :financial_state,
                :net_amount, :vat_amount, :total_amount, :confidence, :validations_json,
                :needs_review, :created_at
            )
            """,
            [
                {
                    "id": str(uuid4()),
                    "company_id": company_id,
                    "owner_email": normalized_owner,
                    "task_id": task_id,
                    "source_file_id": source_file_id,
                    "row_ordinal": index + 1,
                    "document_number": str(document.get("number") or "-")[:120],
                    "document_type": str(document.get("documentType") or "Documento")[:80],
                    "issue_date": _normalise_date(document.get("date")),
                    "entity": str(document.get("entity") or "Não identificado")[:180],
                    "financial_state": str(document.get("financialState") or "Desconhecido")[:40],
                    "net_amount": float(document.get("netAmount") or 0),
                    "vat_amount": float(document.get("vatAmount") or 0),
                    "total_amount": float(document.get("totalAmount") or 0),
                    "confidence": int(document.get("confidence") or 0),
                    "validations_json": json.dumps(document.get("validations") or [], ensure_ascii=False),
                    "needs_review": 1 if document.get("needsReview") else 0,
                    "created_at": now,
                }
                for index, document in enumerate(documents)
            ],
        )
    return len(documents)


def list_work_documents(company_id: str, *, task_id: str | None = None, limit: int = 500) -> list[dict]:
    ensure_work_traceability_schema()
    safe_limit = min(max(int(limit), 1), 2000)
    params: list[object] = [company_id]
    where = "company_id = ?"
    if task_id:
        where += " AND task_id = ?"
        params.append(task_id)
    params.append(safe_limit)
    with connect() as connection:
        rows = connection.execute(
            f"""
            SELECT id, task_id, source_file_id, row_ordinal, document_number, document_type,
                   issue_date, entity, financial_state, net_amount, vat_amount, total_amount,
                   confidence, validations_json, needs_review, created_at
            FROM work_document_records
            WHERE {where}
            ORDER BY created_at DESC, row_ordinal ASC
            LIMIT ?
            """,
            params,
        ).fetchall()
    return [
        {
            "id": row["id"],
            "taskId": row["task_id"],
            "sourceFileId": row["source_file_id"],
            "row": row["row_ordinal"],
            "number": row["document_number"],
            "documentType": row["document_type"],
            "date": row["issue_date"],
            "entity": row["entity"],
            "financialState": row["financial_state"],
            "netAmount": row["net_amount"],
            "vatAmount": row["vat_amount"],
            "totalAmount": row["total_amount"],
            "confidence": row["confidence"],
            "validations": json.loads(row["validations_json"]),
            "needsReview": bool(row["needs_review"]),
            "createdAt": row["created_at"],
        }
        for row in rows
    ]


def _cloud_row(row) -> dict:
    return {
        "id": row["id"],
        "filename": row["filename"],
        "contentType": row["content_type"],
        "category": row["category"],
        "sizeBytes": row["size_bytes"],
        "sha256": row["sha256"],
        "uploadedAt": row["uploaded_at"],
        "referenceDate": row["reference_date"],
        "taskId": row["source_task_id"],
        "origin": row["origin"],
        "parentFileId": row["parent_file_id"],
    }


def _normalise_date(value) -> str | None:
    if value in (None, "", "-"):
        return None
    if hasattr(value, "date"):
        try:
            return value.date().isoformat()
        except (TypeError, ValueError):
            pass
    text = str(value).strip()
    return text[:10] if text else None
