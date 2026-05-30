from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app.models import Company, FinancialDocument
from app.neuro_ai import neuro_ai_engine
from app.schemas import CompanyCreate, FinancialDocumentCreate

Base.metadata.create_all(bind=engine)

app = FastAPI(title="SEO NeuroAI Backoffice", version="2.0.1")

audit_logs = []


@app.get("/")
def root():
    return {
        "status": "online",
        "system": "SEO NeuroAI Backoffice",
        "neuro_ai": "enabled",
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/companies", status_code=status.HTTP_201_CREATED)
def create_company(company: CompanyCreate, db: Session = Depends(get_db)):
    db_company = Company(
        name=company.name,
        tax_id=company.tax_id,
        country=company.country,
    )

    db.add(db_company)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Company with this tax_id already exists.",
        ) from exc

    db.refresh(db_company)
    audit_logs.append({"action": "company_created", "company_id": db_company.id})
    return db_company


@app.get("/companies")
def list_companies(db: Session = Depends(get_db)):
    return db.query(Company).all()


@app.post("/documents", status_code=status.HTTP_201_CREATED)
def create_document(document: FinancialDocumentCreate, db: Session = Depends(get_db)):
    company = db.query(Company).filter(Company.id == document.company_id).first()
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found.",
        )

    neuro_result = neuro_ai_engine.classify_document(
        document.description,
        document.amount,
    )

    db_document = FinancialDocument(
        company_id=document.company_id,
        document_type=document.document_type,
        supplier=document.supplier,
        amount=document.amount,
        vat_amount=document.vat_amount,
        currency=document.currency,
        issue_date=document.issue_date,
        description=document.description,
        category=neuro_result["category"],
        confidence_score=neuro_result["confidence_score"],
    )

    db.add(db_document)
    db.commit()
    db.refresh(db_document)

    audit_logs.append(
        {
            "action": "document_classified",
            "document_id": db_document.id,
            "company_id": db_document.company_id,
            "category": neuro_result["category"],
            "confidence_score": neuro_result["confidence_score"],
        }
    )

    return {
        "document": db_document,
        "neuro_ai": neuro_result,
    }


@app.get("/documents")
def list_documents(db: Session = Depends(get_db)):
    return db.query(FinancialDocument).all()


@app.post("/documents/{document_id}/process")
def process_document(document_id: int, db: Session = Depends(get_db)):
    document = db.query(FinancialDocument).filter(FinancialDocument.id == document_id).first()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    document.status = "processed"
    db.commit()
    db.refresh(document)

    audit_logs.append({"action": "document_processed", "document_id": document.id})

    return {
        "message": "processed",
        "document_id": document.id,
        "category": document.category,
        "ai_confidence": document.confidence_score,
    }


@app.get("/dashboard/{company_id}")
def dashboard(company_id: int, db: Session = Depends(get_db)):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found.",
        )

    docs = db.query(FinancialDocument).filter(
        FinancialDocument.company_id == company_id,
    ).all()

    total_expenses = sum(doc.amount for doc in docs)

    neuro_state = neuro_ai_engine.analyze_financial_state(
        [
            {
                "amount": doc.amount,
                "category": doc.category,
            }
            for doc in docs
        ]
    )

    return {
        "company_id": company_id,
        "company_name": company.name,
        "documents": len(docs),
        "total_expenses": total_expenses,
        "efficiency_score": 87,
        "neuro_analysis": neuro_state,
    }


@app.get("/companies/{company_id}/neuro-insights")
def neuro_insights(company_id: int, db: Session = Depends(get_db)):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found.",
        )

    docs = db.query(FinancialDocument).filter(
        FinancialDocument.company_id == company_id,
    ).all()

    return neuro_ai_engine.generate_executive_insight(
        company_id,
        [
            {
                "amount": doc.amount,
                "category": doc.category,
            }
            for doc in docs
        ],
    )


@app.get("/audit-logs")
def get_logs():
    return audit_logs
