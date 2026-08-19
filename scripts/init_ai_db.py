"""Initialize additive AI/SAF-T tables in the isolated database.

Use POSTGRES_URL_NON_POOLING (or AI_DATABASE_URL) in the environment before
running this script against Neon. It never touches DATABASE_URL.
"""

import os

from app import saft_models as _saft_models  # noqa: F401
from app.ai_database import initialize_ai_schema, reset_ai_database_caches


if __name__ == "__main__":
    non_pooling = os.getenv("AI_DATABASE_URL_NON_POOLING") or os.getenv("POSTGRES_URL_NON_POOLING")
    if non_pooling and not os.getenv("AI_DATABASE_URL"):
        os.environ["AI_DATABASE_URL"] = non_pooling
        reset_ai_database_caches()

    initialize_ai_schema()
    print("AI/SAF-T schema initialized successfully.")
