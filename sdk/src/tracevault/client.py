"""TraceVaultClient — buffer spans and POST a flight to ingest."""

from __future__ import annotations

import json
import os
import secrets
from pathlib import Path
from typing import Any

import httpx

from tracevault.schema import validate_span

_INGEST_TIMEOUT_S = 5.0
_LAST_FLIGHT = Path(__file__).resolve().parents[2] / ".last-flight.json"


class IngestError(RuntimeError):
    """Ingest rejected the flight after retry. Message has no payload."""

    def __init__(self, status_code: int) -> None:
        self.status_code = status_code
        super().__init__(f"ingest failed status={status_code}")


class TraceVaultClient:
    """One client = one flight = one trace_id."""

    def __init__(
        self,
        *,
        tenant_id: str = "tenant-a",
        ingest_url: str | None = None,
        tenant_key: str | None = None,
        timeout: float = _INGEST_TIMEOUT_S,
    ) -> None:
        if tenant_id not in {"tenant-a", "tenant-b"}:
            raise ValueError("tenant_id must be tenant-a or tenant-b")
        self.tenant_id = tenant_id
        self.ingest_url = ingest_url or None
        self.tenant_key = tenant_key or None
        self.timeout = timeout
        self.trace_id = _new_trace_id()
        self.spans: list[dict[str, Any]] = []

    @classmethod
    def from_env(cls) -> TraceVaultClient:
        ingest = os.environ.get("TRACEVAULT_INGEST_URL", "").strip()
        key = os.environ.get("TRACEVAULT_TENANT_KEY", "").strip()
        tenant = os.environ.get("TRACEVAULT_TENANT_ID", "tenant-a").strip() or "tenant-a"
        return cls(
            tenant_id=tenant,
            ingest_url=ingest or None,
            tenant_key=key or None,
        )

    def record(self, span: dict[str, Any]) -> None:
        validate_span(span)
        self.spans.append(span)

    def flush(self) -> None:
        if not self.ingest_url:
            self._write_last_flight()
            return
        try:
            self._post_with_retry()
        except IngestError as err:
            # Unreachable ingest (network / timeout): park the flight locally.
            # HTTP 4xx/5xx still raise — the server was reachable.
            if err.status_code == 0:
                self._write_last_flight()
                return
            raise

    def _write_last_flight(self) -> None:
        _LAST_FLIGHT.write_text(
            json.dumps(self.spans, indent=2) + "\n",
            encoding="utf-8",
        )

    def _post_with_retry(self) -> None:
        url = self.ingest_url.rstrip("/") + "/v1/traces"
        headers = {"Content-Type": "application/json"}
        if self.tenant_key:
            headers["X-Tenant-Key"] = self.tenant_key
        payload = {"spans": self.spans}
        last_status = 0
        for _ in range(2):
            try:
                with httpx.Client(timeout=self.timeout) as http:
                    response = http.post(url, json=payload, headers=headers)
            except httpx.HTTPError:
                last_status = 0
                continue
            if response.status_code < 400:
                return
            last_status = response.status_code
        raise IngestError(last_status)


def _new_trace_id() -> str:
    return secrets.token_hex(16)
