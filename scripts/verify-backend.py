from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.main import ai_analyze, build_simple_pdf, decision_center
from backend.app.schemas import AiQuestionRequest
from backend.app.security import authenticate_user, account_profile
from backend.app.store import replace_operational_dataset


def main() -> None:
    user = authenticate_user("admin@seo.local", "Seo-Admin-2026")
    assert user, "admin login failed"
    profile = account_profile(user)

    replace_operational_dataset(
        company_id=profile.company_id,
        owner_email=profile.email,
        inventory=[
            {
                "ref": "TEST-SKU",
                "product": "Produto Teste",
                "stock": 1,
                "lastSaleDays": 120,
                "margin": 22,
                "alert": "Parado",
            }
        ],
        debts=[
            {
                "id": 9901,
                "entity": "Cliente Teste",
                "type": "Cliente",
                "amount": 500.0,
                "dueDays": 45,
                "state": "Em atraso",
            }
        ],
        issues=[
            {
                "id": 5901,
                "document": "TEST-1",
                "source": "Teste",
                "value": "500.00 EUR",
                "issue": "Validação",
                "status": "Rever",
            }
        ],
    )

    decision = decision_center(user)
    assert decision["seoIndex"] < 100
    assert decision["priorities"]

    answer = ai_analyze(AiQuestionRequest(question="Onde estou a perder dinheiro?"), user)
    assert answer["answer"]
    assert answer["priorities"]

    pdf = build_simple_pdf(["SEO Core", "Verificação"])
    assert pdf.startswith(b"%PDF-1.4")
    assert b"%%EOF" in pdf

    print("backend verification ok")


if __name__ == "__main__":
    main()
