from fastapi import FastAPI
from pydantic import BaseModel
from typing import List

app = FastAPI(title='SEO - Sistema de Eficiência Operacional')

companies = []
documents = []
audit_logs = []

class Company(BaseModel):
    name: str
    tax_id: str
    country: str = 'Portugal'

class FinancialDocument(BaseModel):
    company_id: int
    document_type: str
    supplier: str
    amount: float
    vat_amount: float
    currency: str = 'EUR'
    issue_date: str
    description: str

@app.get('/')
def root():
    return {
        'message': 'SEO AI Backoffice API running',
        'status': 'online'
    }

@app.get('/health')
def health():
    return {'status': 'healthy'}

@app.post('/companies')
def create_company(company: Company):
    company_data = company.dict()
    company_data['id'] = len(companies) + 1
    companies.append(company_data)

    audit_logs.append({
        'action': 'company_created',
        'company': company.name
    })

    return company_data

@app.get('/companies')
def list_companies():
    return companies

@app.post('/documents')
def create_document(document: FinancialDocument):
    document_data = document.dict()
    document_data['id'] = len(documents) + 1
    document_data['status'] = 'uploaded'

    documents.append(document_data)

    audit_logs.append({
        'action': 'document_uploaded',
        'supplier': document.supplier,
        'amount': document.amount
    })

    return document_data

@app.get('/documents')
def list_documents():
    return documents

@app.post('/documents/{document_id}/process')
def process_document(document_id: int):
    for document in documents:
        if document['id'] == document_id:
            document['status'] = 'processed'
            document['category'] = 'Operational Expense'
            document['ai_confidence'] = 0.94

            audit_logs.append({
                'action': 'document_processed',
                'document_id': document_id
            })

            return {
                'message': 'Document processed successfully',
                'document': document
            }

    return {'error': 'Document not found'}

@app.get('/dashboard/{company_id}')
def dashboard(company_id: int):
    company_documents = [d for d in documents if d['company_id'] == company_id]

    total_expenses = sum(d['amount'] for d in company_documents)
    total_vat = sum(d['vat_amount'] for d in company_documents)

    return {
        'company_id': company_id,
        'documents': len(company_documents),
        'total_expenses': total_expenses,
        'total_vat': total_vat,
        'alerts': [
            'Operational expenses increased 12% this month.'
        ]
    }

@app.get('/audit-logs')
def get_logs():
    return audit_logs
