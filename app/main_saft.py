"""SAF-T/agentic application entrypoint.

This wrapper keeps app.main untouched. Deploying app.main:app preserves the
current behaviour; deploying app.main_saft:app enables additive SAF-T routes,
Sentry observability and the isolated AI storage layer.
"""

from app.observability import init_sentry

# Initialize Sentry before importing FastAPI application code so integrations
# can instrument requests. No-op when SENTRY_DSN is absent.
init_sentry()

# Register isolated AI models before optional schema initialization.
from app import saft_models as _saft_models  # noqa: E402,F401
from app.ai_database import maybe_initialize_ai_schema  # noqa: E402
from app.main import app  # noqa: E402
from app.saft_api import router as saft_router  # noqa: E402

maybe_initialize_ai_schema()
app.include_router(saft_router)
