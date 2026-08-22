"""Fail-closed behavior: when masking cannot be trusted, safe=False with an
empty preview, and redact_strict raises RedactionError (ingest maps that to
400 redaction_failed with nothing stored)."""

import pytest

from vault.redact import RedactionError, redact, redact_strict
from vault.redact import denylist, engine

RAW_SSN = "123-45-6789"


def test_presidio_failure_mid_analysis_fails_closed(monkeypatch):
    def broken(_text):
        raise RedactionError("presidio analysis failed")

    monkeypatch.setattr(engine, "_presidio_mask", broken)
    result = redact(f"ssn {RAW_SSN}")
    assert not result.safe
    assert result.prompt_preview == ""
    assert RAW_SSN not in repr(result)


def test_residual_pii_after_masking_fails_closed(monkeypatch):
    # Simulate a masking bug: mask() reports success but leaves the SSN.
    monkeypatch.setattr(denylist, "mask", lambda text: (text, ()))
    result = redact(f"ssn {RAW_SSN}")
    assert not result.safe
    assert result.prompt_preview == ""
    assert "SSN" in result.findings  # entity *name* only


def test_redact_strict_raises_on_unsafe(monkeypatch):
    monkeypatch.setattr(denylist, "mask", lambda text: (text, ()))
    with pytest.raises(RedactionError) as excinfo:
        redact_strict(f"ssn {RAW_SSN}")
    assert RAW_SSN not in str(excinfo.value)  # error text never carries PII


def test_redact_strict_passes_safe_payloads():
    result = redact_strict("what is the refund policy?")
    assert result.safe


def test_hash_still_computed_when_unsafe(monkeypatch):
    # Even a failed redaction identifies the payload by hash for audit trails.
    monkeypatch.setattr(denylist, "mask", lambda text: (text, ()))
    result = redact(f"ssn {RAW_SSN}")
    assert len(result.prompt_hash) == 64
