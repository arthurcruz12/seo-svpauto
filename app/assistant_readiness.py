from __future__ import annotations

import os
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.artifact_storage import LocalPersistentStorage, get_artifact_storage
from app.database import get_db

router = APIRouter(prefix="/api/v1/assistant", tags=["assistant"])


@router.get("/ready", include_in_schema=False)
def assistant_ready(db: Session = Depends(get_db)):
    """Readiness gate for the persistent Assistant execution backend.

    This endpoint intentionally exposes only coarse readiness state. It proves
    that the migrated task tables are queryable and the configured persistent
    artifact directory is writable without exposing database or filesystem
    connection details.
    """

    try:
        for table_name in ("agent_tasks", "agent_executions", "agent_artifacts"):
            db.execute(text(f"SELECT 1 FROM {table_name} LIMIT 1"))

        configured_path = os.getenv("SEO_ARTIFACT_STORAGE_PATH")
        if not configured_path:
            raise RuntimeError("persistent artifact storage is not configured")

        storage = get_artifact_storage()
        if not isinstance(storage, LocalPersistentStorage):
            raise RuntimeError("persistent local artifact storage is not available")

        probe = storage.root / f".seo-readiness-{uuid4().hex}"
        probe.write_bytes(b"ready")
        if not probe.is_file() or probe.read_bytes() != b"ready":
            raise RuntimeError("artifact storage probe failed")
        probe.unlink()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Assistant persistence is not ready",
        ) from exc

    return {
        "status": "ready",
        "task_storage": "database",
        "artifact_storage": "persistent",
        "storage_provider": storage.provider,
    }
