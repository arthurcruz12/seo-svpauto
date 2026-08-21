from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query

from .security import require_permission
from .store import FILE_STORAGE_DIR, add_audit_event, connect, init_db, migrate_column, utc_now


router = APIRouter(tags=["cloud-trash"])


def ensure_trash_schema() -> None:
    init_db()
    with connect() as connection:
        # The Trash can be opened before the Work traceability module. Keep all
        # additive uploaded_files metadata available independently of route order.
        migrate_column(connection, "uploaded_files", "reference_date", "TEXT")
        migrate_column(connection, "uploaded_files", "source_task_id", "TEXT")
        migrate_column(connection, "uploaded_files", "origin", "TEXT NOT NULL DEFAULT 'upload'")
        migrate_column(connection, "uploaded_files", "parent_file_id", "TEXT")
        migrate_column(connection, "uploaded_files", "deleted_at", "TEXT")
        migrate_column(connection, "uploaded_files", "deleted_by", "TEXT")
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_uploaded_files_trash ON uploaded_files (company_id, deleted_at, uploaded_at DESC)"
        )


def _file_payload(row) -> dict:
    return {
        "id": row["id"],
        "filename": row["filename"],
        "contentType": row["content_type"],
        "category": row["category"],
        "sizeBytes": row["size_bytes"],
        "sha256": row["sha256"],
        "uploadedAt": row["uploaded_at"],
        "deletedAt": row["deleted_at"],
        "deletedBy": row["deleted_by"],
        "referenceDate": row["reference_date"] if "reference_date" in row.keys() else None,
        "taskId": row["source_task_id"] if "source_task_id" in row.keys() else None,
        "origin": row["origin"] if "origin" in row.keys() else None,
        "parentFileId": row["parent_file_id"] if "parent_file_id" in row.keys() else None,
    }


def _select_columns() -> str:
    return (
        "id, filename, content_type, category, size_bytes, sha256, uploaded_at, "
        "deleted_at, deleted_by, reference_date, source_task_id, origin, parent_file_id"
    )


def list_active_uploaded_files(company_id: str, limit: int = 100) -> list[dict]:
    """Drop-in replacement used by the legacy /cloud/files route."""
    ensure_trash_schema()
    safe_limit = max(1, min(int(limit), 500))
    with connect() as connection:
        rows = connection.execute(
            f"""
            SELECT {_select_columns()}
            FROM uploaded_files
            WHERE company_id = ? AND deleted_at IS NULL
            ORDER BY uploaded_at DESC
            LIMIT ?
            """,
            (company_id, safe_limit),
        ).fetchall()
    return [_file_payload(row) for row in rows]


def get_active_uploaded_file(company_id: str, file_id: str) -> dict | None:
    """Drop-in replacement used by the legacy /cloud/files/{id}/download route."""
    ensure_trash_schema()
    with connect() as connection:
        row = connection.execute(
            """
            SELECT id, filename, content_type, category, size_bytes, sha256, content,
                   storage_path, uploaded_at, deleted_at, deleted_by,
                   reference_date, source_task_id, origin, parent_file_id
            FROM uploaded_files
            WHERE company_id = ? AND id = ? AND deleted_at IS NULL
            """,
            (company_id, file_id),
        ).fetchone()
    if not row:
        return None
    payload = dict(row)
    storage_path = payload.get("storage_path")
    if storage_path:
        candidate = Path(storage_path)
        try:
            if candidate.is_file() and candidate.resolve().is_relative_to(FILE_STORAGE_DIR.resolve()):
                payload["content"] = candidate.read_bytes()
        except (OSError, RuntimeError):
            pass
    return payload


@router.get("/cloud/trash")
def list_trash(
    limit: int = Query(default=100, ge=1, le=500),
    user: dict = Depends(require_permission("files:upload")),
) -> list[dict]:
    ensure_trash_schema()
    with connect() as connection:
        rows = connection.execute(
            f"""
            SELECT {_select_columns()}
            FROM uploaded_files
            WHERE company_id = ? AND deleted_at IS NOT NULL
            ORDER BY deleted_at DESC
            LIMIT ?
            """,
            (user["company_id"], limit),
        ).fetchall()
    return [_file_payload(row) for row in rows]


@router.post("/cloud/files/{file_id}/trash")
def move_file_to_trash(
    file_id: str,
    user: dict = Depends(require_permission("files:upload")),
) -> dict:
    ensure_trash_schema()
    deleted_at = utc_now()
    with connect() as connection:
        row = connection.execute(
            f"SELECT {_select_columns()} FROM uploaded_files WHERE company_id = ? AND id = ?",
            (user["company_id"], file_id),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Ficheiro não encontrado.")
        if row["deleted_at"] is not None:
            return _file_payload(row)
        connection.execute(
            """
            UPDATE uploaded_files
            SET deleted_at = ?, deleted_by = ?
            WHERE company_id = ? AND id = ? AND deleted_at IS NULL
            """,
            (deleted_at, user["email"], user["company_id"], file_id),
        )
        updated = connection.execute(
            f"SELECT {_select_columns()} FROM uploaded_files WHERE company_id = ? AND id = ?",
            (user["company_id"], file_id),
        ).fetchone()

    add_audit_event(
        user["company_id"],
        user["email"],
        "CLOUD_FILE_MOVED_TO_TRASH",
        f"file_id={file_id}; filename={row['filename']}; task_id={row['source_task_id'] if 'source_task_id' in row.keys() else None}",
    )
    return _file_payload(updated)


@router.post("/cloud/trash/{file_id}/restore")
def restore_file_from_trash(
    file_id: str,
    user: dict = Depends(require_permission("files:upload")),
) -> dict:
    ensure_trash_schema()
    with connect() as connection:
        row = connection.execute(
            f"SELECT {_select_columns()} FROM uploaded_files WHERE company_id = ? AND id = ? AND deleted_at IS NOT NULL",
            (user["company_id"], file_id),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Ficheiro não encontrado na Lixeira.")
        connection.execute(
            """
            UPDATE uploaded_files
            SET deleted_at = NULL, deleted_by = NULL
            WHERE company_id = ? AND id = ? AND deleted_at IS NOT NULL
            """,
            (user["company_id"], file_id),
        )
        updated = connection.execute(
            f"SELECT {_select_columns()} FROM uploaded_files WHERE company_id = ? AND id = ?",
            (user["company_id"], file_id),
        ).fetchone()

    add_audit_event(
        user["company_id"],
        user["email"],
        "CLOUD_FILE_RESTORED",
        f"file_id={file_id}; filename={row['filename']}; task_id={row['source_task_id'] if 'source_task_id' in row.keys() else None}",
    )
    return _file_payload(updated)


@router.post("/cloud/trash/{file_id}/delete")
def permanently_delete_file(
    file_id: str,
    user: dict = Depends(require_permission("files:upload")),
) -> dict:
    """Permanent deletion is only allowed after the file has first entered the Trash."""
    ensure_trash_schema()
    with connect() as connection:
        row = connection.execute(
            """
            SELECT id, filename, storage_path, source_task_id
            FROM uploaded_files
            WHERE company_id = ? AND id = ? AND deleted_at IS NOT NULL
            """,
            (user["company_id"], file_id),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Ficheiro não encontrado na Lixeira.")
        connection.execute(
            "DELETE FROM uploaded_files WHERE company_id = ? AND id = ? AND deleted_at IS NOT NULL",
            (user["company_id"], file_id),
        )

    storage_path = row["storage_path"]
    if storage_path:
        candidate = Path(storage_path)
        try:
            if candidate.is_file() and candidate.resolve().is_relative_to(FILE_STORAGE_DIR.resolve()):
                candidate.unlink(missing_ok=True)
        except (OSError, RuntimeError):
            pass

    try:
        from .azure_storage import delete_document

        delete_document(user["company_id"], file_id, row["filename"])
    except Exception:
        # The database operation remains authoritative; remote cleanup is best effort.
        pass

    add_audit_event(
        user["company_id"],
        user["email"],
        "CLOUD_FILE_PERMANENTLY_DELETED",
        f"file_id={file_id}; filename={row['filename']}; task_id={row['source_task_id']}",
    )
    return {"id": file_id, "deleted": True, "message": "Ficheiro eliminado definitivamente da Lixeira."}
