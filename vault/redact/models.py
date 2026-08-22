"""Result type for redaction. Holds only the hash and the masked preview —
never the original text, so leaking a RedactResult cannot leak PII."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class RedactResult:
    prompt_hash: str
    prompt_preview: str
    safe: bool
    # Entity *type* names only (e.g. "EMAIL", "SSN") — never matched values.
    findings: tuple[str, ...] = field(default=())
    presidio_used: bool = False
