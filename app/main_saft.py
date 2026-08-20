"""SAF-T/agentic application entrypoint.

Deploying app.main:app preserves the current API surface. Deploying
app.main_saft:app adds SAF-T staging, the isolated AI storage layer and the
safe Agent Manager read/routing API. Sentry is initialized centrally by
app.main when SENTRY_DSN is configured.
"""

# Register isolated AI models before optional schema initialization.
from app import saft_models as _saft_models  # noqa: F401
from app.ai_database import maybe_initialize_ai_schema
from app.agent_api import router as agent_router
from app.main import app
from app.saft_api import router as saft_router

maybe_initialize_ai_schema()
app.include_router(saft_router)
app.include_router(agent_router)
