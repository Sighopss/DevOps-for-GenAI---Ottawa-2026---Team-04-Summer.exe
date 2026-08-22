"""sensitive=True must never print or log the raw prompt or leak it in preview."""

from __future__ import annotations

import hashlib
import logging

import pytest

from tracevault import TraceVaultClient, start_span

PROMPT = "reach me at user@example.com ssn 123-45-6789"
EMAIL = "user@example.com"
SSN = "123-45-6789"


def test_sensitive_prompt_not_in_logs_stdout_or_preview(
    capsys, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    client = TraceVaultClient(tenant_id="tenant-a")
    with start_span(
        client,
        kind="llm",
        name="chat",
        model="test-model",
        sensitive=True,
        prompt=PROMPT,
    ):
        pass
    client.flush()

    captured = capsys.readouterr()
    blob = f"{captured.out}{captured.err}{caplog.text}"
    assert EMAIL not in blob
    assert SSN not in blob

    span = client.spans[0]
    preview = span["prompt_preview"]
    assert EMAIL not in preview
    assert SSN not in preview
    assert "[EMAIL]" in preview
    assert "[SSN]" in preview
    assert span["prompt_hash"] == _sha256_hex(PROMPT)
    assert len(span["prompt_hash"]) == 64


def _sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
