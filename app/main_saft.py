"""SAF-T enabled application entrypoint.

This wrapper keeps app.main untouched. Deploying app.main:app preserves the current
behaviour; deploying app.main_saft:app enables the additive SAF-T staging routes.
"""

# Import staging models before app.main in development/test so Base.metadata knows
# about the additive tables when create_all() runs.
from app import saft_models as _saft_models  # noqa: F401
from app.main import app
from app.saft_api import router as saft_router

app.include_router(saft_router)
