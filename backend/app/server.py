from . import main as main_module
from .main import app
from .password_routes import router as password_router
from .trash_routes import get_active_uploaded_file, list_active_uploaded_files, router as trash_router
from .work_routes import router as work_router


# Keep the existing /cloud/files endpoints, but make their global store lookups
# trash-aware without rewriting the preserved legacy main.py route definitions.
main_module.list_uploaded_files = list_active_uploaded_files
main_module.get_uploaded_file = get_active_uploaded_file

app.include_router(password_router)
app.include_router(work_router)
app.include_router(trash_router)
