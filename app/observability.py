from __future__ import annotations

import os
from typing import Any

import sentry_sdk


SENSITIVE_HEADERS = {"authorization", "cookie", "set-cookie", "x-api-key"}


def _before_send(event: dict[str, Any], hint: dict[str, Any]) -> dict[str, Any] | None:
    """Strip request bodies and sensitive headers before an event leaves the app."""

    request = event.get("request")
    if isinstance(request, dict):
        request.pop("data", None)
        request.pop("cookies", None)
        headers = request.get("headers")
        if isinstance(headers, dict):
            for key in list(headers):
                if str(key).lower() in SENSITIVE_HEADERS:
                    headers[key] = "[Filtered]"

    # Avoid accidentally shipping accounting payloads through custom extras.
    extra = event.get("extra")
    if isinstance(extra, dict):
        for key in list(extra):
            if any(marker in str(key).lower() for marker in ("saft", "document", "invoice", "nif", "tax_id", "payload")):
                extra[key] = "[Filtered]"

    return event


def init_sentry() -> bool:
    dsn = os.getenv("SENTRY_DSN")
    if not dsn:
        return False

    sentry_sdk.init(
        dsn=dsn,
        environment=os.getenv("ENVIRONMENT", "development"),
        release=os.getenv("VERCEL_GIT_COMMIT_SHA") or os.getenv("APP_RELEASE"),
        traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
        profiles_sample_rate=float(os.getenv("SENTRY_PROFILES_SAMPLE_RATE", "0.0")),
        send_default_pii=False,
        before_send=_before_send,
    )
    return True
