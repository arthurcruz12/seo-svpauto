from .main import app
from .password_routes import router as password_router
from .work_routes import router as work_router


app.include_router(password_router)
app.include_router(work_router)
