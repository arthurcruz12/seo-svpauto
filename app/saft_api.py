from __future__ import annotations

import json
import logging
import os

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.ai_database import AIStorageUnavailable, ai_database_configured, get_ai_db
from app.database import get_db
from app.integrations import infrastructure_status
from app.models import AuditLog, Company, User
from app.saft_models import SaftAnomaly, SaftImport, SaftStagedDocument
from app.saft_service import normalize_saft
from app.security import decode_access_token, require_permission

router = APIRouter(prefix="/api/v1/saft", tags=["SAF-T"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
MAX_SAFT_BYTES = int(os.getenv("SAFT_MAX_UPLOAD_BYTES", str(25 * 1024 * 1024)))
logger = logging.getLogger("seo-api.saft")


def _enabled() -> bool:
    return os.getenv("SAFT_INTEGRATION_ENABLED", "false").lower() == "true"


def _require_feature() -> None:
    if not _enabled():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SAF-T integration is disabled by feature flag",
        )
    if not ai_database_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI/SAF-T database is not configured",
        )


def get_ai_session():
    try:
        yield from get_ai_db()
    except AIStorageUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI/SAF-T database is unavailable",
        ) from exc


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    try:
        payload = decode_access_token(token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication token") from exc
    email = payload.get("sub")
    if not email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication token")
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


def _audit(db: Session, tenant_id: int, action: str, entity_id: int | None, details: dict) -> None:
    db.add(
        AuditLog(
            tenant_id=tenant_id,
            action=action,
            entity_type="saft_import",
            entity_id=entity_id,
            details=json.dumps(details, ensure_ascii=False, default=str),
        )
    )


def _get_import(ai_db: Session, current_user: User, import_id: int) -> SaftImport:
    item = (
        ai_db.query(SaftImport)
        .filter(SaftImport.id == import_id, SaftImport.tenant_id == current_user.tenant_id)
        .first()
    )
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SAF-T import not found")
    return item


@router.get("/status")
def saft_status(current_user: User = Depends(get_current_user)):
    require_permission(current_user, "saft:read")
    return {
        "enabled": _enabled(),
        "mode": "isolated_read_only_staging",
        "ai_database_configured": ai_database_configured(),
        "writes_to_operational_database": False,
        "writes_to_financial_documents": False,
        "writes_to_snc": False,
        "validation_mode": "safe_xml_and_structural",
        "infrastructure": infrastructure_status(),
    }


@router.post("/import", status_code=status.HTTP_201_CREATED)
async def import_saft(
    company_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    ai_db: Session = Depends(get_ai_session),
    current_user: User = Depends(get_current_user),
):
    _require_feature()
    require_permission(current_user, "saft:write")

    # Company and tenant authorization always come from the operational database.
    company = (
        db.query(Company)
        .filter(Company.id == company_id, Company.tenant_id == current_user.tenant_id)
        .first()
    )
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

    filename = file.filename or "saft.xml"
    if not filename.lower().endswith(".xml"):
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="SAF-T upload must be XML")

    payload = await file.read(MAX_SAFT_BYTES + 1)
    if len(payload) > MAX_SAFT_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="SAF-T file exceeds configured size limit")

    try:
        normalized = normalize_saft(payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    existing = (
        ai_db.query(SaftImport)
        .filter(
            SaftImport.tenant_id == current_user.tenant_id,
            SaftImport.company_id == company.id,
            SaftImport.sha256 == normalized["sha256"],
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": "This SAF-T file was already imported", "import_id": existing.id},
        )

    validation = normalized["validation"]
    header = normalized["header"]
    errors = list(validation["errors"])
    warnings = list(validation["warnings"])

    if header.get("tax_registration_number") and str(header["tax_registration_number"]).strip() != str(company.tax_id).strip():
        errors.append("SAF-T TaxRegistrationNumber does not match the selected company")

    import_status = "quarantine" if errors else "staged"
    saft_import = SaftImport(
        tenant_id=current_user.tenant_id,
        company_id=company.id,
        filename=filename,
        sha256=normalized["sha256"],
        schema_version=validation.get("schema_version"),
        namespace=validation.get("namespace"),
        status=import_status,
        company_tax_id=header.get("tax_registration_number"),
        source_company_name=header.get("company_name"),
        fiscal_year=header.get("fiscal_year"),
        start_date=header.get("start_date"),
        end_date=header.get("end_date"),
        currency_code=header.get("currency_code") or "EUR",
        validation_errors=json.dumps(errors, ensure_ascii=False),
        validation_warnings=json.dumps(warnings, ensure_ascii=False),
        raw_file_reference=None,
        created_by=current_user.email,
    )
    ai_db.add(saft_import)
    ai_db.flush()

    seen_numbers: set[str] = set()
    staged_count = 0
    for document in normalized["documents"]:
        number = document.get("document_number")
        if number and number in seen_numbers:
            continue
        if number:
            seen_numbers.add(number)
        ai_db.add(
            SaftStagedDocument(
                tenant_id=current_user.tenant_id,
                company_id=company.id,
                saft_import_id=saft_import.id,
                document_number=number,
                document_type=document.get("document_type") or "UNKNOWN",
                document_status=document.get("document_status"),
                invoice_date=document.get("invoice_date"),
                customer_id=document.get("customer_id"),
                net_total=document.get("net_total") or 0,
                tax_payable=document.get("tax_payable") or 0,
                gross_total=document.get("gross_total") or 0,
                raw_gross_total=document.get("raw_gross_total") or 0,
                stage_status="read_only",
            )
        )
        staged_count += 1

    for anomaly in normalized["anomalies"]:
        ai_db.add(
            SaftAnomaly(
                tenant_id=current_user.tenant_id,
                company_id=company.id,
                saft_import_id=saft_import.id,
                code=anomaly.get("code", "UNKNOWN"),
                severity=anomaly.get("severity", "warning"),
                document_number=anomaly.get("document"),
                details=json.dumps(anomaly, ensure_ascii=False, default=str),
            )
        )

    if errors:
        ai_db.add(
            SaftAnomaly(
                tenant_id=current_user.tenant_id,
                company_id=company.id,
                saft_import_id=saft_import.id,
                code="IMPORT_QUARANTINED",
                severity="critical",
                details=json.dumps({"errors": errors}, ensure_ascii=False),
            )
        )

    # Commit isolated staging first. A failure cannot mutate operational tables.
    try:
        ai_db.commit()
        ai_db.refresh(saft_import)
    except IntegrityError as exc:
        ai_db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="SAF-T staging conflict") from exc

    audit_logged = True
    try:
        _audit(
            db,
            current_user.tenant_id,
            "saft_import_staged",
            saft_import.id,
            {
                "company_id": company.id,
                "filename": filename,
                "sha256": normalized["sha256"],
                "status": import_status,
                "staged_documents": staged_count,
                "anomalies": normalized["counts"]["anomalies"],
                "storage": "isolated_ai_database",
                "writes_to_financial_documents": False,
                "writes_to_snc": False,
            },
        )
        db.commit()
    except Exception:
        db.rollback()
        audit_logged = False
        logger.exception("SAF-T import staged but operational audit log could not be written")

    return {
        "id": saft_import.id,
        "status": import_status,
        "sha256": saft_import.sha256,
        "schema_version": saft_import.schema_version,
        "header": header,
        "counts": {**normalized["counts"], "staged_documents": staged_count},
        "validation": {**validation, "errors": errors, "warnings": warnings},
        "safety": {
            "read_only_staging": True,
            "isolated_ai_database": True,
            "operational_database_unchanged": True,
            "financial_documents_unchanged": True,
            "snc_execution_enabled": False,
            "audit_logged": audit_logged,
            "raw_file_storage": "integration_required",
        },
    }


@router.get("/imports")
def list_saft_imports(
    company_id: int | None = None,
    limit: int = 50,
    ai_db: Session = Depends(get_ai_session),
    current_user: User = Depends(get_current_user),
):
    require_permission(current_user, "saft:read")
    query = ai_db.query(SaftImport).filter(SaftImport.tenant_id == current_user.tenant_id)
    if company_id is not None:
        query = query.filter(SaftImport.company_id == company_id)
    items = query.order_by(SaftImport.created_at.desc()).limit(min(max(limit, 1), 100)).all()
    return [
        {
            "id": item.id,
            "company_id": item.company_id,
            "filename": item.filename,
            "sha256": item.sha256,
            "schema_version": item.schema_version,
            "status": item.status,
            "company_tax_id": item.company_tax_id,
            "source_company_name": item.source_company_name,
            "fiscal_year": item.fiscal_year,
            "created_by": item.created_by,
            "created_at": item.created_at,
        }
        for item in items
    ]


@router.get("/imports/{import_id}")
def get_saft_import(
    import_id: int,
    ai_db: Session = Depends(get_ai_session),
    current_user: User = Depends(get_current_user),
):
    require_permission(current_user, "saft:read")
    item = _get_import(ai_db, current_user, import_id)
    return {
        "id": item.id,
        "company_id": item.company_id,
        "filename": item.filename,
        "sha256": item.sha256,
        "schema_version": item.schema_version,
        "namespace": item.namespace,
        "status": item.status,
        "company_tax_id": item.company_tax_id,
        "source_company_name": item.source_company_name,
        "fiscal_year": item.fiscal_year,
        "start_date": item.start_date,
        "end_date": item.end_date,
        "currency_code": item.currency_code,
        "validation_errors": json.loads(item.validation_errors or "[]"),
        "validation_warnings": json.loads(item.validation_warnings or "[]"),
        "created_by": item.created_by,
        "created_at": item.created_at,
    }


@router.get("/imports/{import_id}/preview")
def preview_saft_import(
    import_id: int,
    limit: int = 100,
    ai_db: Session = Depends(get_ai_session),
    current_user: User = Depends(get_current_user),
):
    require_permission(current_user, "saft:read")
    item = _get_import(ai_db, current_user, import_id)
    documents = (
        ai_db.query(SaftStagedDocument)
        .filter(
            SaftStagedDocument.saft_import_id == item.id,
            SaftStagedDocument.tenant_id == current_user.tenant_id,
        )
        .limit(min(max(limit, 1), 500))
        .all()
    )
    return {
        "import_id": item.id,
        "status": item.status,
        "read_only": True,
        "storage": "isolated_ai_database",
        "documents": [
            {
                "document_number": document.document_number,
                "document_type": document.document_type,
                "document_status": document.document_status,
                "invoice_date": document.invoice_date,
                "customer_id": document.customer_id,
                "net_total": document.net_total,
                "tax_payable": document.tax_payable,
                "gross_total": document.gross_total,
                "stage_status": document.stage_status,
            }
            for document in documents
        ],
    }


@router.get("/imports/{import_id}/anomalies")
def saft_anomalies(
    import_id: int,
    ai_db: Session = Depends(get_ai_session),
    current_user: User = Depends(get_current_user),
):
    require_permission(current_user, "saft:read")
    item = _get_import(ai_db, current_user, import_id)
    anomalies = (
        ai_db.query(SaftAnomaly)
        .filter(SaftAnomaly.saft_import_id == item.id, SaftAnomaly.tenant_id == current_user.tenant_id)
        .order_by(SaftAnomaly.id.asc())
        .all()
    )
    return [
        {
            "id": anomaly.id,
            "code": anomaly.code,
            "severity": anomaly.severity,
            "document_number": anomaly.document_number,
            "details": json.loads(anomaly.details or "{}"),
            "created_at": anomaly.created_at,
        }
        for anomaly in anomalies
    ]
