"""SAF-T/agentic application entrypoint.

Deploying app.main:app preserves the current API surface. Deploying
app.main_saft:app adds isolated agent/SAF-T capabilities without replacing
existing authentication, users, tenants or the protected frontend.
"""

# Register isolated AI models before optional schema initialization.
from app import saft_models as _saft_models  # noqa: F401
from app.agent_api import router as agent_router
from app.ai_database import maybe_initialize_ai_schema
from app.assistant_api import router as assistant_router
from app.main import app
from app.saft_api import router as saft_router

maybe_initialize_ai_schema()
app.include_router(saft_router)
app.include_router(agent_router)
app.include_router(assistant_router)
