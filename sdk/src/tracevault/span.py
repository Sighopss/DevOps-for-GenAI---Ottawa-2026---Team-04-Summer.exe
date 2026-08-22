"""start_span / end_span — nest llm|tool|rag|http under one trace_id."""

from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from tracevault.client import TraceVaultClient
from tracevault.context import SpanScope, current_span_id
from tracevault.redact_hint import sensitive_fields

if TYPE_CHECKING:
    from opentelemetry.trace import Span as _OtelSpan  # types/shape only; no OTLP export

Kind = Literal["llm", "tool", "rag", "http"]
Status = Literal["ok", "error"]
_KINDS = {"llm", "tool", "rag", "http"}


class SpanRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    trace_id: str
    span_id: str
    parent_id: str | None = None
    tenant_id: str
    kind: Kind
    name: str = Field(min_length=1, max_length=128)
    status: Status
    start_time: str
    end_time: str
    gen_ai_request_model: str | None = Field(default=None, alias="gen_ai.request.model")
    gen_ai_usage_input_tokens: int | None = Field(
        default=None, alias="gen_ai.usage.input_tokens", ge=0
    )
    gen_ai_usage_output_tokens: int | None = Field(
        default=None, alias="gen_ai.usage.output_tokens", ge=0
    )
    cost_usd: float = Field(default=0.0, ge=0)
    error_message: str | None = None
    attributes: dict[str, Any] | None = None
    events: list[dict[str, Any]] | None = None
    prompt_preview: str | None = Field(default=None, max_length=200)
    prompt_hash: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")


class Span:
    def __init__(
        self,
        client: TraceVaultClient,
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
        self._scope = SpanScope()
        self._closed = False
        self.span_id = secrets.token_hex(8)
        self.parent_id: str | None = None
        self.start_time = ""
        self.end_time = ""
        self.status: Status = "ok"
        self.error_message: str | None = None

    def __enter__(self) -> Span:
        self.parent_id = current_span_id()
        self.start_time = _utc_now_z()
        self._scope.push(
            trace_id=self._client.trace_id,
            span_id=self.span_id,
            tenant_id=self._client.tenant_id,
        )
        return self

    def __exit__(self, exc_type: type[BaseException] | None, exc: BaseException | None, tb: Any) -> bool:
        if exc_type is not None:
            self.status = "error"
            self.error_message = type(exc).__name__
        self.finish()
        return False

    def set_usage(
        self,
        *,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        cost_usd: float | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> None:
        if input_tokens is not None:
            self._input_tokens = int(input_tokens)
        if output_tokens is not None:
            self._output_tokens = int(output_tokens)
        if cost_usd is not None:
            self.cost_usd = float(cost_usd)
        if attributes:
            self._attributes = {**(self._attributes or {}), **attributes}

    def finish(self, status: Status | None = None) -> dict[str, Any]:
        if self._closed:
            return {}
        if status is not None:
            self.status = status
        if not self.end_time:
            self.end_time = _utc_now_z()
        try:
            record = self._to_record()
            payload = record.model_dump(by_alias=True, exclude_none=False, exclude_unset=True)
            self._client.record(payload)
            return payload
        finally:
            self._scope.pop()
            self._closed = True
            self._prompt = None

    def _to_record(self) -> SpanRecord:
        kwargs: dict[str, Any] = {
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
            kwargs["gen_ai.request.model"] = self._model
        if self._input_tokens is not None:
            kwargs["gen_ai.usage.input_tokens"] = int(self._input_tokens)
        if self._output_tokens is not None:
            kwargs["gen_ai.usage.output_tokens"] = int(self._output_tokens)
        if self.error_message is not None:
            kwargs["error_message"] = self.error_message
        if self._attributes is not None:
            kwargs["attributes"] = self._attributes
        if self._events is not None:
            kwargs["events"] = self._events
        if self._sensitive and self._prompt is not None:
            prompt_hash, preview = sensitive_fields(self._prompt)
            kwargs["prompt_hash"] = prompt_hash
            kwargs["prompt_preview"] = preview
        return SpanRecord.model_validate(kwargs)


def start_span(
    client: TraceVaultClient,
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
) -> Span:
    return Span(
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


def end_span(span: Span, status: Status | None = None) -> dict[str, Any]:
    return span.finish(status=status)


def _utc_now_z() -> str:
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
