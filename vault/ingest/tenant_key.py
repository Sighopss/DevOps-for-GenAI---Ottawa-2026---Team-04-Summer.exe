"""Resolve X-Tenant-Key to a tenant_id.

Trevor's Terraform provisions one Secrets Manager secret per tenant
(TENANT_A_SECRET_ARN / TENANT_B_SECRET_ARN env vars on the Lambda), each
holding `{"tenant_id": "...", "key": "..."}` — see infra/README.md. The
presented header is compared against each secret's key with a constant-time
compare. Unknown, missing, or empty keys resolve to None (handler -> 401).

boto3 is imported lazily: the Lambda runtime provides it, CI does not.
"""

from __future__ import annotations

import hmac
import json
import os

_SECRET_ENV_VARS = ("TENANT_A_SECRET_ARN", "TENANT_B_SECRET_ARN")

# Warm-container cache: list of (key, tenant_id). Never logged.
_cache: list[tuple[str, str]] | None = None


def _default_fetch(secret_arn: str) -> str:
    import boto3  # Lambda runtime provides it; CI injects fetch instead

    client = boto3.client("secretsmanager")
    return client.get_secret_value(SecretId=secret_arn)["SecretString"]


def _load_tenant_keys(fetch) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for env_var in _SECRET_ENV_VARS:
        arn = os.environ.get(env_var)
        if not arn:
            continue
        try:
            data = json.loads(fetch(arn))
        except Exception:  # nosec B112 — fail closed: unreadable secret authenticates nobody
            continue
        key = data.get("key")
        tenant_id = data.get("tenant_id")
        if key and tenant_id:  # placeholder secrets (empty key) never match
            pairs.append((key, tenant_id))
    return pairs


def resolve(headers: dict, fetch=None) -> str | None:
    """Map the request's X-Tenant-Key header to a tenant_id, or None."""
    presented = None
    for name, value in (headers or {}).items():
        if name.lower() == "x-tenant-key":
            presented = value
            break
    if not presented:
        return None

    global _cache
    if fetch is not None:
        pairs = _load_tenant_keys(fetch)
    else:
        if _cache is None:
            _cache = _load_tenant_keys(_default_fetch)
        pairs = _cache

    presented_bytes = presented.encode("utf-8")
    for key, tenant_id in pairs:
        # bytes, not str: compare_digest raises TypeError on non-ASCII str,
        # and a hostile header must yield 401, not a 500.
        if hmac.compare_digest(presented_bytes, key.encode("utf-8")):
            return tenant_id
    return None
