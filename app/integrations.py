from __future__ import annotations

import json
import os
from typing import Any
from urllib.parse import quote

import httpx
import redis


def _first_env(*names: str) -> str | None:
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return None


def infrastructure_status() -> dict[str, Any]:
    """Return capability flags only. Never expose credentials or URLs."""

    return {
        "neon": {
            "configured": bool(_first_env("AI_DATABASE_URL", "POSTGRES_URL")),
            "non_pooling_configured": bool(_first_env("AI_DATABASE_URL_NON_POOLING", "POSTGRES_URL_NON_POOLING")),
        },
        "redis": {
            "configured": bool(_first_env("REDIS_URL", "KV_URL")),
        },
        "vector": {
            "configured": bool(_first_env("UPSTASH_VECTOR_REST_URL"))
            and bool(_first_env("UPSTASH_VECTOR_REST_TOKEN")),
        },
        "search": {
            "configured": bool(_first_env("UPSTASH_SEARCH_REST_URL"))
            and bool(_first_env("UPSTASH_SEARCH_REST_TOKEN")),
        },
        "qstash": {
            "configured": bool(_qstash_url()) and bool(_qstash_token()),
            "signing_keys_configured": bool(_qstash_current_signing_key())
            and bool(_qstash_next_signing_key()),
        },
        "sentry": {
            "configured": bool(_first_env("SENTRY_DSN")),
        },
        "checkly": {
            "configured": bool(_first_env("CHECKLY_ACCOUNT_ID")),
        },
    }


def get_redis_client() -> redis.Redis:
    url = _first_env("REDIS_URL", "KV_URL")
    if not url:
        raise RuntimeError("REDIS_URL/KV_URL is not configured")
    return redis.Redis.from_url(url, decode_responses=True)


def redis_healthcheck() -> bool:
    return bool(get_redis_client().ping())


def _vector_config() -> tuple[str, str]:
    url = _first_env("UPSTASH_VECTOR_REST_URL")
    token = _first_env("UPSTASH_VECTOR_REST_TOKEN")
    if not url or not token:
        raise RuntimeError("Upstash Vector is not configured")
    return url.rstrip("/"), token


def remember_semantic_pattern(
    *,
    item_id: str,
    text: str,
    tenant_id: int,
    metadata: dict[str, Any] | None = None,
    namespace: str = "business-memory",
) -> dict[str, Any]:
    """Store an approved business pattern as raw text.

    The configured Upstash index embeds the text server-side. Only approved or
    intentionally persisted patterns should call this function.
    """

    url, token = _vector_config()
    body = {
        "id": item_id,
        "data": text,
        "metadata": {"tenant_id": tenant_id, **(metadata or {})},
    }
    response = httpx.post(
        f"{url}/upsert-data/{quote(namespace, safe='')}",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json=body,
        timeout=15.0,
    )
    response.raise_for_status()
    return response.json()


def find_semantic_patterns(
    *,
    text: str,
    tenant_id: int,
    top_k: int = 5,
    namespace: str = "business-memory",
) -> list[dict[str, Any]]:
    url, token = _vector_config()
    response = httpx.post(
        f"{url}/query-data/{quote(namespace, safe='')}",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={
            "data": text,
            "topK": min(max(top_k, 1), 20),
            "includeMetadata": True,
            "includeData": True,
            "filter": f"tenant_id = {int(tenant_id)}",
            "queryMode": "HYBRID",
        },
        timeout=15.0,
    )
    response.raise_for_status()
    payload = response.json()
    return payload.get("result", [])


def _qstash_url() -> str | None:
    return _first_env("upseo_QSTASH_URL", "QSTASH_URL")


def _qstash_token() -> str | None:
    return _first_env("upseo_QSTASH_TOKEN", "QSTASH_TOKEN")


def _qstash_current_signing_key() -> str | None:
    return _first_env(
        "upseo_QSTASH_CURRENT_SIGNING_KEY",
        "QSTASH_CURRENT_SIGNING_KEY",
        "upseo_QSTASH_SIGNING_KEY",
    )


def _qstash_next_signing_key() -> str | None:
    return _first_env(
        "upseo_QSTASH_NEXT_SIGNING_KEY",
        "QSTASH_NEXT_SIGNING_KEY",
    )


def publish_qstash(
    *,
    destination: str,
    payload: dict[str, Any],
    delay: str | None = None,
    retries: int = 3,
) -> dict[str, Any]:
    """Durably enqueue a JSON POST to a public SEO endpoint."""

    base_url = _qstash_url()
    token = _qstash_token()
    if not base_url or not token:
        raise RuntimeError("QStash is not configured")
    if not destination.startswith(("https://", "http://")):
        raise ValueError("QStash destination must be an absolute HTTP(S) URL")

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Upstash-Retries": str(min(max(retries, 0), 10)),
        # Avoid sensitive job bodies appearing in QStash dashboard/API output.
        "Upstash-Redact-Fields": "body,header[Authorization]",
    }
    if delay:
        headers["Upstash-Delay"] = delay

    response = httpx.post(
        f"{base_url.rstrip('/')}/v2/publish/{quote(destination, safe='')}",
        headers=headers,
        content=json.dumps(payload, ensure_ascii=False, default=str),
        timeout=15.0,
    )
    response.raise_for_status()
    return response.json()


def create_qstash_schedule(
    *,
    destination: str,
    cron: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    base_url = _qstash_url()
    token = _qstash_token()
    if not base_url or not token:
        raise RuntimeError("QStash is not configured")
    if not destination.startswith(("https://", "http://")):
        raise ValueError("QStash destination must be an absolute HTTP(S) URL")

    response = httpx.post(
        f"{base_url.rstrip('/')}/v2/schedules/{quote(destination, safe='')}",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Upstash-Cron": cron,
            "Upstash-Redact-Fields": "body,header[Authorization]",
        },
        content=json.dumps(payload, ensure_ascii=False, default=str),
        timeout=15.0,
    )
    response.raise_for_status()
    return response.json()
