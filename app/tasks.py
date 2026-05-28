from celery import Celery
from app.config import settings

celery_app = Celery(
    'seo_neuroai',
    broker=settings.redis_url,
    backend=settings.redis_url
)


@celery_app.task
def process_financial_document(document_id: int):
    return {
        'document_id': document_id,
        'status': 'processed_async',
        'engine': 'NeuroAI Async Processing'
    }
