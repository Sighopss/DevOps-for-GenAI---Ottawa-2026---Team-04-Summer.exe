"""Factory for the real TraceVault SDK emitter used by the demo."""

from __future__ import annotations

import os
from contextlib import AbstractContextManager
from typing import Any, Callable

from tracevault import TraceVaultClient, start_span

StartSpan = Callable[..., AbstractContextManager[Any]]


def load_emitter(tenant_id: str) -> tuple[TraceVaultClient, StartSpan]:
    """Create one SDK client/flight; unset ingest keeps the SDK's local fallback."""
    ingest = os.environ.get("TRACEVAULT_INGEST_URL", "").strip() or None
    key = os.environ.get("TRACEVAULT_TENANT_KEY", "").strip() or None
    client = TraceVaultClient(
        tenant_id=tenant_id,
        ingest_url=ingest,
        tenant_key=key,
    )
    return client, start_span
