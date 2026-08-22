"""Deterministic deny-list. This is the contractual layer (PLAN.md, issue #12):
SSN, email, AWS access keys, sk- secrets are masked here with no ML involved,
so the judge-path guarantees never depend on Presidio being installed.

Mask tokens for EMAIL/SSN are locked by contracts/fixtures (hour 0): the
Explorer renders them verbatim and the SDK emits the same two.

Boundary rules (issue #45): `\\b` word boundaries let PII through when it
abuts letters (`SSN123-45-6789`, `key=AKIA…` + trailing chars), so SSNs use
digit-excluding lookarounds — adjacent letters still mask, longer digit runs
do not partial-mask — and key patterns match mid-token. Over-masking is the
acceptable direction; under-masking loses the judge path.
"""

from __future__ import annotations

import re

# Order matters: emails first (an email can contain digits or "sk-" in its
# local part), then the two SSN shapes, then bare nine digits, then keys.
_PATTERNS: tuple[tuple[str, re.Pattern[str], str], ...] = (
    # \w (unicode) instead of [a-zA-Z0-9]: an accented local part like
    # usagé@exemple.fr must still mask — under-masking loses the judge path.
    ("EMAIL", re.compile(r"[\w.%+\-]+@[\w.\-]+\.[a-zA-Z]{2,}"), "[EMAIL]"),
    # 3-2-4 with dash/space separators, letters allowed adjacent.
    ("SSN", re.compile(r"(?<!\d)\d{3}[- ]\d{2}[- ]\d{4}(?!\d)"), "[SSN]"),
    # Bare nine digits: exactly nine, not part of a longer run.
    ("SSN", re.compile(r"(?<!\d)\d{9}(?!\d)"), "[SSN]"),
    # AWS access key ids match anywhere, including mid-token (key=AKIA…).
    ("AWS_KEY", re.compile(r"(?:AKIA|ASIA)[0-9A-Z]{16}"), "[AWS_KEY]"),
    # sk- secrets: separator chars (= : - etc.) count as boundaries; a
    # letter prefix (risk-assessment-…) does not trigger it.
    ("API_KEY", re.compile(r"(?<![A-Za-z0-9])sk-[A-Za-z0-9_\-]{16,}"), "[API_KEY]"),
)


def mask(text: str) -> tuple[str, tuple[str, ...]]:
    """Replace every deny-list match with its token.

    Returns the masked text and the tuple of entity type names that were
    found (names only — never the matched values)."""
    found: list[str] = []
    masked = text
    for entity, pattern, token in _PATTERNS:
        masked, count = pattern.subn(token, masked)
        if count and entity not in found:
            found.append(entity)
    return masked, tuple(found)


def residual_matches(text: str) -> tuple[str, ...]:
    """Entity type names still present in `text`. Non-empty on already-masked
    text means masking failed — callers treat that as fail-closed."""
    residual: list[str] = []
    for entity, pattern, _ in _PATTERNS:
        if pattern.search(text) and entity not in residual:
            residual.append(entity)
    return tuple(residual)
