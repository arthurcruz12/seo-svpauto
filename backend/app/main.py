from fastapi import FastAPI

app = FastAPI(
    title="SEO - Sistema de Eficiência Operacional",
    description="Sistema contabilístico e operacional inteligente",
    version="1.0.0"
)

@app.get("/")
def home():
    return {
        "message": "SEO Backend Online"
    }
