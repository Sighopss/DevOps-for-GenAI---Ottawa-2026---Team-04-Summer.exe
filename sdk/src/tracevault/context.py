"""contextvars for the current flight (trace_id, span_id, tenant_id)."""

from __future__ import annotations

from contextvars import ContextVar, Token
from typing import Any

_trace_id: ContextVar[str | None] = ContextVar("tracevault_trace_id", default=None)
_span_id: ContextVar[str | None] = ContextVar("tracevault_span_id", default=None)
_tenant_id: ContextVar[str | None] = ContextVar("tracevault_tenant_id", default=None)
_span_stack: ContextVar[tuple[str, ...]] = ContextVar("tracevault_span_stack", default=())


def current_trace_id() -> str | None:
    return _trace_id.get()


def current_span_id() -> str | None:
    return _span_id.get()


def current_tenant_id() -> str | None:
    return _tenant_id.get()


class SpanScope:
    """Push/pop the current span without leaking ids across tasks."""

    def __init__(self) -> None:
        self._tokens: list[tuple[ContextVar[Any], Token]] = []

    def push(self, *, trace_id: str, span_id: str, tenant_id: str) -> None:
        stack = _span_stack.get()
        self._tokens.append((_span_stack, _span_stack.set((*stack, span_id))))
        self._tokens.append((_trace_id, _trace_id.set(trace_id)))
        self._tokens.append((_span_id, _span_id.set(span_id)))
        self._tokens.append((_tenant_id, _tenant_id.set(tenant_id)))

    def pop(self) -> None:
        while self._tokens:
            var, token = self._tokens.pop()
            var.reset(token)
