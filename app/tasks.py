from celery import Celery

from app.config import settings

celery_app = Celery(
    "seo_neuroai",
    broker=settings.redis_url,
    backend=settings.redis_url,
)


@celery_app.task
def process_financial_document(document_id: int):
    """Legacy task entrypoint kept for compatibility.

    The former implementation returned `processed_async` without doing any
    work. That false-success behavior is disabled. Real billing execution now
    runs through the authenticated Agent Manager workflow.
    """
    return {
        "document_id": document_id,
        "status": "NEEDS_REVIEW",
        "engine": "SEO Agent Manager",
        "executed": False,
        "reason": "legacy_celery_placeholder_disabled",
    }
