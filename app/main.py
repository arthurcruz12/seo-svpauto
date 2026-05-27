from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from app.database import Base, engine, get_db
from app.models import Company, FinancialDocument
from app.schemas import CompanyCreate, FinancialDocumentCreate
from app.neuro_ai import neuro_ai_engine

Base.metadata.create_all(bind=engine)

app = FastAPI(title='SEO NeuroAI Backoffice', version='2.0.0')

audit_logs = []

@app.get('/')
def root():
    return {
        'status': 'online',
        'system': 'SEO NeuroAI Backoffice',
        'neuro_ai': 'enabled'
    }

@app.get('/health')
def health():
    return {'status': 'healthy'}

@app.post('/companies')
def create_company(company: CompanyCreate, db: Session = Depends(get_db)):
    db_company = Company(
        name=company.name,
        tax_id=company.tax_id,
        country=company.country
    )

    db.add(db_company)
    db.commit()
    db.refresh(db_company)

    audit_logs.append({'action': 'company_created'})

    return db_company

@app.get('/companies')
def list_companies(db: Session = Depends(get_db)):
    return db.query(Company).all()

@app.post('/documents')
def create_document(document: FinancialDocumentCreate, db: Session = Depends(get_db)):
    neuro_result = neuro_ai_engine.classify_document(
        document.description,
        document.amount
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
        category=neuro_result['category']
    )

    db.add(db_document)
    db.commit()
    db.refresh(db_document)

    audit_logs.append({
        'action': 'document_classified',
        'category': neuro_result['category']
    })

    return {
        'document': db_document,
        'neuro_ai': neuro_result
    }

@app.get('/documents')
def list_documents(db: Session = Depends(get_db)):
    return db.query(FinancialDocument).all()

@app.post('/documents/{document_id}/process')
def process_document(document_id: int, db: Session = Depends(get_db)):
    document = db.query(FinancialDocument).filter(FinancialDocument.id == document_id).first()

    if not document:
        return {'error': 'Document not found'}

    document.status = 'processed'

    db.commit()

    return {
        'message': 'processed',
        'document_id': document.id,
        'category': document.category,
        'ai_confidence': 0.94
    }

@app.get('/dashboard/{company_id}')
def dashboard(company_id: int, db: Session = Depends(get_db)):
    docs = db.query(FinancialDocument).filter(
        FinancialDocument.company_id == company_id
    ).all()

    total_expenses = sum(doc.amount for doc in docs)

    neuro_state = neuro_ai_engine.analyze_financial_state([
        {
            'amount': doc.amount,
            'category': doc.category
        }
        for doc in docs
    ])

    return {
        'company_id': company_id,
        'documents': len(docs),
        'total_expenses': total_expenses,
        'efficiency_score': 87,
        'neuro_analysis': neuro_state
    }

@app.get('/companies/{company_id}/neuro-insights')
def neuro_insights(company_id: int, db: Session = Depends(get_db)):
    docs = db.query(FinancialDocument).filter(
        FinancialDocument.company_id == company_id
    ).all()

    insight = neuro_ai_engine.generate_executive_insight(
        company_id,
        [
            {
                'amount': doc.amount,
                'category': doc.category
            }
            for doc in docs
        ]
    )

    return insight

@app.get('/audit-logs')
def get_logs():
    return audit_logs
