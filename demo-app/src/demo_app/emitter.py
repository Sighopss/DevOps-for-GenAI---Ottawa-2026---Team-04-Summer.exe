"""DemoEmitter protocol + SDK-or-stub factory. Do not copy sdk/ into this tree."""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
from contextlib import AbstractContextManager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Protocol

try:
    from tracevault import TraceVaultClient, start_span as sdk_start_span
except ImportError:
    TraceVaultClient = None  # type: ignore[misc, assignment]
    sdk_start_span = None

_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
_SSN_RE = re.compile(r"\d{3}-\d{2}-\d{4}")
_LAST_FLIGHT = Path(__file__).resolve().parents[2] / ".last-flight.json"
_KINDS = {"llm", "tool", "rag", "http"}


class SpanHandle(Protocol):
    span_id: str
    parent_id: str | None

    def set_usage(
        self,
        *,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        cost_usd: float | None = None,
    ) -> None: ...


class DemoEmitter(Protocol):
    """Minimal emit surface. Real impl is TraceVaultClient after #28 merges."""

    tenant_id: str
    trace_id: str
    spans: list[dict[str, Any]]

    def record(self, span: dict[str, Any]) -> None: ...

    def flush(self) -> None: ...


StartSpan = Callable[..., AbstractContextManager[SpanHandle]]


def load_emitter(tenant_id: str) -> tuple[DemoEmitter, StartSpan]:
    ingest = os.environ.get("TRACEVAULT_INGEST_URL", "").strip() or None
    key = os.environ.get("TRACEVAULT_TENANT_KEY", "").strip() or None
    if TraceVaultClient is not None and sdk_start_span is not None:
        client = TraceVaultClient(
            tenant_id=tenant_id,
            ingest_url=ingest,
            tenant_key=key,
        )
        return client, sdk_start_span
    return StubClient(tenant_id=tenant_id), stub_start_span


class StubClient:
    """Stand-in until `tracevault` is importable from ../sdk (PR #28)."""

    def __init__(self, *, tenant_id: str) -> None:
        if tenant_id not in {"tenant-a", "tenant-b"}:
            raise ValueError("tenant_id must be tenant-a or tenant-b")
        self.tenant_id = tenant_id
        self.trace_id = secrets.token_hex(16)
        self.spans: list[dict[str, Any]] = []
        self._span_stack: list[str] = []

    def record(self, span: dict[str, Any]) -> None:
        self.spans.append(span)

    def flush(self) -> None:
        _LAST_FLIGHT.write_text(
            json.dumps(self.spans, indent=2) + "\n",
            encoding="utf-8",
        )


class StubSpan:
    def __init__(
        self,
        client: StubClient,
        *,
        kind: str,
        name: str,
        model: str | None = None,
        sensitive: bool = False,
        prompt: str | None = None,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        cost_usd: float = 0.0,
        attributes: dict[str, Any] | None = None,
        events: list[dict[str, Any]] | None = None,
    ) -> None:
        if kind not in _KINDS:
            raise ValueError("kind must be llm|tool|rag|http")
        self._client = client
        self._kind = kind
        self._name = name
        self._model = model
        self._sensitive = sensitive
        self._prompt = prompt
        self._input_tokens = input_tokens
        self._output_tokens = output_tokens
        self.cost_usd = float(cost_usd)
        self._attributes = attributes
        self._events = events
        self.span_id = secrets.token_hex(8)
        self.parent_id: str | None = None
        self.status = "ok"
        self.start_time = ""
        self.end_time = ""
        self._closed = False

    def __enter__(self) -> StubSpan:
        stack = self._client._span_stack
        self.parent_id = stack[-1] if stack else None
        stack.append(self.span_id)
        self.start_time = _utc_now_z()
        return self

    def __exit__(self, exc_type: type[BaseException] | None, exc: BaseException | None, tb: Any) -> bool:
        if exc_type is not None:
            self.status = "error"
        self.finish()
        return False

    def set_usage(
        self,
        *,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        cost_usd: float | None = None,
    ) -> None:
        if input_tokens is not None:
            self._input_tokens = int(input_tokens)
        if output_tokens is not None:
            self._output_tokens = int(output_tokens)
        if cost_usd is not None:
            self.cost_usd = float(cost_usd)

    def finish(self) -> dict[str, Any]:
        if self._closed:
            return {}
        self.end_time = _utc_now_z()
        payload: dict[str, Any] = {
            "trace_id": self._client.trace_id,
            "span_id": self.span_id,
            "parent_id": self.parent_id,
            "tenant_id": self._client.tenant_id,
            "kind": self._kind,
            "name": self._name,
            "status": self.status,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "cost_usd": self.cost_usd,
        }
        if self._model is not None:
            payload["gen_ai.request.model"] = self._model
        if self._input_tokens is not None:
            payload["gen_ai.usage.input_tokens"] = int(self._input_tokens)
        if self._output_tokens is not None:
            payload["gen_ai.usage.output_tokens"] = int(self._output_tokens)
        if self._attributes is not None:
            payload["attributes"] = self._attributes
        if self._events is not None:
            payload["events"] = self._events
        if self._sensitive and self._prompt is not None:
            payload["prompt_hash"] = hashlib.sha256(self._prompt.encode("utf-8")).hexdigest()
            masked = _EMAIL_RE.sub("[EMAIL]", self._prompt)
            masked = _SSN_RE.sub("[SSN]", masked)
            payload["prompt_preview"] = masked[:200]
        self._client.record(payload)
        stack = self._client._span_stack
        if stack and stack[-1] == self.span_id:
            stack.pop()
        self._closed = True
        self._prompt = None
        return payload


def stub_start_span(
    client: StubClient,
    *,
    kind: str,
    name: str,
    model: str | None = None,
    sensitive: bool = False,
    prompt: str | None = None,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    cost_usd: float = 0.0,
    attributes: dict[str, Any] | None = None,
    events: list[dict[str, Any]] | None = None,
) -> StubSpan:
    return StubSpan(
        client,
        kind=kind,
        name=name,
        model=model,
        sensitive=sensitive,
        prompt=prompt,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=cost_usd,
        attributes=attributes,
        events=events,
    )


def _utc_now_z() -> str:
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
