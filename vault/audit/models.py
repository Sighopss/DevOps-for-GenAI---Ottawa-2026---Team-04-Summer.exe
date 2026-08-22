"""Audit event: exactly the four contract fields, nothing else — an audit
row can never leak prompt data because it never holds any."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AuditEvent:
    actor: str
    tenant_id: str
    trace_id: str
    ts: str  # UTC ISO-8601 with Z

    def to_dict(self) -> dict:
        """Shape of one entry in GET .../audit's events[] (contracts/http.md)."""
        return {
            "actor": self.actor,
            "tenant_id": self.tenant_id,
            "trace_id": self.trace_id,
            "ts": self.ts,
        }
