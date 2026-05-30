from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app.models import AuditLog, Company, FinancialDocument, Tenant, User
from app.neuro_ai import neuro_ai_engine
from app.schemas import CompanyCreate, FinancialDocumentCreate, Token, UserCreate, UserLogin
from app.security import create_access_token, create_refresh_token, decode_access_token, decode_refresh_token, get_password_hash, require_permission, verify_password

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="SEO NeuroAI Backoffice",
    description="Professional SaaS backend for accounting, financial and operational automation.",
    version="3.1.1",
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def write_audit_log(db: Session, tenant_id: int | None, action: str, entity_type: str, entity_id: int | None = None, details: str | None = None) -> None:
    db.add(AuditLog(tenant_id=tenant_id, action=action, entity_type=entity_type, entity_id=entity_id, details=details))


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


@app.get("/")
def root():
    return {"status": "online", "system": "SEO NeuroAI Backoffice", "api": "/api/v1"}


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/api/v1/auth/register", status_code=status.HTTP_201_CREATED)
def register_user(user_data: UserCreate, db: Session = Depends(get_db)):
    tenant = Tenant(name=f"{user_data.email} tenant")
    db.add(tenant)
    db.flush()
    user = User(tenant_id=tenant.id, email=user_data.email, hashed_password=get_password_hash(user_data.password), role=user_data.role)
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already exists") from exc
    db.refresh(user)
    write_audit_log(db, user.tenant_id, "user_registered", "user", user.id, user.email)
    db.commit()
    return {"id": user.id, "tenant_id": user.tenant_id, "email": user.email, "role": user.role}


@app.post("/api/v1/auth/login")
def login_user(credentials: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == credentials.email).first()
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    token_payload = {"sub": user.email, "role": user.role, "tenant_id": user.tenant_id}
    return {"access_token": create_access_token(token_payload), "refresh_token": create_refresh_token(token_payload), "token_type": "bearer"}


@app.post("/api/v1/auth/refresh", response_model=Token)
def refresh_access_token(refresh_token: str, db: Session = Depends(get_db)):
    try:
        payload = decode_refresh_token(refresh_token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token") from exc
    email = payload.get("sub")
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return Token(access_token=create_access_token({"sub": user.email, "role": user.role, "tenant_id": user.tenant_id}))


@app.post("/api/v1/companies", status_code=status.HTTP_201_CREATED)
def create_company(company: CompanyCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    require_permission(current_user, "companies:write")
    db_company = Company(tenant_id=current_user.tenant_id, name=company.name, tax_id=company.tax_id, country=company.country.upper())
    db.add(db_company)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Company with this tax_id and country already exists") from exc
    db.refresh(db_company)
    write_audit_log(db, current_user.tenant_id, "company_created", "company", db_company.id, f"created_by={current_user.email}")
    db.commit()
    return db_company


@app.get("/api/v1/companies")
def list_companies(limit: int = 50, offset: int = 0, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    require_permission(current_user, "companies:read")
    limit = min(max(limit, 1), 100)
    offset = max(offset, 0)
    return db.query(Company).filter(Company.tenant_id == current_user.tenant_id).offset(offset).limit(limit).all()


@app.post("/api/v1/documents", status_code=status.HTTP_201_CREATED)
def create_document(document: FinancialDocumentCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    require_permission(current_user, "documents:write")
    company = db.query(Company).filter(Company.id == document.company_id, Company.tenant_id == current_user.tenant_id).first()
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    neuro_result = neuro_ai_engine.classify_document(document.description, float(document.amount))
    db_document = FinancialDocument(tenant_id=current_user.tenant_id, company_id=document.company_id, document_type=document.document_type, supplier=document.supplier, amount=document.amount, vat_amount=document.vat_amount, currency=document.currency, issue_date=document.issue_date, description=document.description, category=neuro_result["category"], confidence_score=neuro_result["confidence_score"])
    db.add(db_document)
    db.commit()
    db.refresh(db_document)
    write_audit_log(db, current_user.tenant_id, "document_classified", "document", db_document.id, f"created_by={current_user.email}; category={db_document.category}")
    db.commit()
    return {"document": db_document, "neuro_ai": neuro_result}


@app.get("/api/v1/documents")
def list_documents(limit: int = 50, offset: int = 0, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    require_permission(current_user, "documents:read")
    limit = min(max(limit, 1), 100)
    offset = max(offset, 0)
    return db.query(FinancialDocument).filter(FinancialDocument.tenant_id == current_user.tenant_id).offset(offset).limit(limit).all()


@app.post("/api/v1/documents/{document_id}/process")
def process_document(document_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    require_permission(current_user, "documents:write")
    document = db.query(FinancialDocument).filter(FinancialDocument.id == document_id, FinancialDocument.tenant_id == current_user.tenant_id).first()
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    if document.status == "processed":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Document already processed")
    document.status = "processed"
    write_audit_log(db, current_user.tenant_id, "document_processed", "document", document.id, f"processed_by={current_user.email}")
    db.commit()
    db.refresh(document)
    return {"message": "processed", "document_id": document.id, "category": document.category, "ai_confidence": document.confidence_score}


@app.get("/api/v1/dashboard/{company_id}")
def dashboard(company_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    require_permission(current_user, "dashboard:read")
    company = db.query(Company).filter(Company.id == company_id, Company.tenant_id == current_user.tenant_id).first()
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    docs = db.query(FinancialDocument).filter(FinancialDocument.company_id == company_id, FinancialDocument.tenant_id == current_user.tenant_id).all()
    total_expenses = sum(doc.amount for doc in docs)
    neuro_state = neuro_ai_engine.analyze_financial_state([{"amount": float(doc.amount), "category": doc.category} for doc in docs])
    processed = len([doc for doc in docs if doc.status == "processed"])
    efficiency_score = round((processed / len(docs)) * 100, 2) if docs else 0
    return {"company_id": company_id, "company_name": company.name, "documents": len(docs), "total_expenses": total_expenses, "efficiency_score": efficiency_score, "neuro_analysis": neuro_state}


@app.get("/api/v1/companies/{company_id}/neuro-insights")
def neuro_insights(company_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    require_permission(current_user, "dashboard:read")
    company = db.query(Company).filter(Company.id == company_id, Company.tenant_id == current_user.tenant_id).first()
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    docs = db.query(FinancialDocument).filter(FinancialDocument.company_id == company_id, FinancialDocument.tenant_id == current_user.tenant_id).all()
    return neuro_ai_engine.generate_executive_insight(company_id, [{"amount": float(doc.amount), "category": doc.category} for doc in docs])


@app.get("/api/v1/audit-logs")
def get_logs(limit: int = 50, offset: int = 0, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    require_permission(current_user, "audit:read")
    limit = min(max(limit, 1), 100)
    offset = max(offset, 0)
    return db.query(AuditLog).filter(AuditLog.tenant_id == current_user.tenant_id).order_by(AuditLog.created_at.desc()).offset(offset).limit(limit).all()
