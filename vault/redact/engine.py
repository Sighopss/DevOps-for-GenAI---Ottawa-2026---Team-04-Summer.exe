"""Redaction engine. Fail-closed: when we cannot be sure the output is clean,
we return safe=False with an empty preview, and redact_strict() raises so
ingest maps it to 400 redaction_failed with nothing stored.

Layering (issue #12 / PLAN.md):
- deny-list (denylist.py) — deterministic, stdlib-only, contractual. The
  judge-path guarantees (SSN / email / AWS keys never at rest) rest here.
- Presidio — best-effort extra coverage (names, phone numbers, ...). Loaded
  lazily; if it is not installed (CI installs only pytest+bandit, and the
  Lambda zip may not carry it) we run deny-list-only. If Presidio is present
  but *fails mid-analysis*, we fail closed — it may have seen something we
  cannot classify.

The raw prompt is never logged, printed, or stored on the result object.
"""

from __future__ import annotations

import hashlib

from vault.redact import denylist
from vault.redact.models import RedactResult

_PREVIEW_MAX = 200  # contracts/span.schema.json: prompt_preview maxLength
_PRESIDIO_MASK = "[REDACTED]"

# Hard input cap (issue #46): pathological non-matching input around ~16k
# chars costs seconds in regex backtracking. Legit fields are tiny (preview
# is 200); anything huge is hostile or a bug — fail closed before any regex.
_MAX_INPUT_CHARS = 10_000


class RedactionError(Exception):
    """Raised when a payload cannot be safely masked — including non-string
    input (issue #46: callers must get 400, never a TypeError 500).

    Never carries the offending text — only entity type names."""


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


_presidio_engine = None
_presidio_checked = False


def _get_presidio():
    """Lazy singleton. Returns an AnalyzerEngine or None when unavailable."""
    global _presidio_engine, _presidio_checked
    if not _presidio_checked:
        _presidio_checked = True
        try:
            from presidio_analyzer import AnalyzerEngine

            _presidio_engine = AnalyzerEngine()
        except Exception:  # not installed / model missing -> deny-list-only
            _presidio_engine = None
    return _presidio_engine


def _presidio_mask(text: str) -> tuple[str, tuple[str, ...], bool]:
    """Best-effort second pass. Returns (masked, extra findings, used).

    Raises RedactionError if Presidio starts an analysis it cannot finish."""
    engine = _get_presidio()
    if engine is None:
        return text, (), False
    try:
        results = engine.analyze(text=text, language="en")
        found: list[str] = []
        # Replace right-to-left so earlier offsets stay valid.
        for res in sorted(results, key=lambda r: r.start, reverse=True):
            text = text[: res.start] + _PRESIDIO_MASK + text[res.end :]
            if res.entity_type not in found:
                found.append(res.entity_type)
        return text, tuple(found), True
    except Exception as exc:
        raise RedactionError("presidio analysis failed") from exc


def redact(text: str) -> RedactResult:
    """Mask `text`. Redaction *failure* comes back as .safe=False; only a
    non-string argument raises (RedactionError, so ingest still maps it to
    400 redaction_failed rather than a 500)."""
    if not isinstance(text, str):
        raise RedactionError("redact() requires str input")

    prompt_hash = _sha256(text)

    if len(text) > _MAX_INPUT_CHARS:  # before any regex runs (ReDoS gate)
        return RedactResult(
            prompt_hash=prompt_hash,
            prompt_preview="",
            safe=False,
            findings=("INPUT_TOO_LONG",),
        )

    masked, found = denylist.mask(text)
    try:
        masked, extra, presidio_used = _presidio_mask(masked)
    except RedactionError:
        return RedactResult(
            prompt_hash=prompt_hash, prompt_preview="", safe=False, findings=found
        )

    # Defense in depth: nothing the deny-list knows about may survive masking.
    residual = denylist.residual_matches(masked)
    if residual:
        return RedactResult(
            prompt_hash=prompt_hash,
            prompt_preview="",
            safe=False,
            findings=found + residual,
            presidio_used=presidio_used,
        )

    return RedactResult(
        prompt_hash=prompt_hash,
        prompt_preview=masked[:_PREVIEW_MAX],
        safe=True,
        findings=found + extra,
        presidio_used=presidio_used,
    )


def redact_strict(text: str) -> RedactResult:
    """Like redact(), but raises RedactionError when the result is not safe.

    Ingest calls this and maps RedactionError -> 400 redaction_failed,
    storing nothing."""
    result = redact(text)
    if not result.safe:
        raise RedactionError(
            "redaction failed for entities: " + ",".join(result.findings)
        )
    return result
