from .main import app
from .password_routes import router as password_router


app.include_router(password_router)
