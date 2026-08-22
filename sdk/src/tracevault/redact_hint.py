"""Hash and mask prompts when sensitive=True. Never log the raw prompt."""

from __future__ import annotations

import hashlib
import re

_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
_SSN_RE = re.compile(r"\d{3}-\d{2}-\d{4}")
_PREVIEW_MAX = 200


def hash_prompt(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


def mask_preview(prompt: str) -> str:
    masked = _EMAIL_RE.sub("[EMAIL]", prompt)
    masked = _SSN_RE.sub("[SSN]", masked)
    if len(masked) > _PREVIEW_MAX:
        return masked[:_PREVIEW_MAX]
    return masked


def sensitive_fields(prompt: str) -> tuple[str, str]:
    """Return (prompt_hash, prompt_preview). Caller must not log `prompt`."""
    return hash_prompt(prompt), mask_preview(prompt)
