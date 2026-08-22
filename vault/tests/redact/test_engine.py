"""redact(): hash + masked preview, schema-shaped, no raw substrings."""

import hashlib

import pytest

from vault.redact import redact

_RAW_AKIA = "".join(("AKI", "A", "ABCDEFGHIJKLMNOP"))
PII_PROMPT = f"reach me at user@example.com ssn 123-45-6789 key {_RAW_AKIA}"


def test_masks_all_contractual_entities():
    result = redact(PII_PROMPT)
    assert result.safe
    assert "[EMAIL]" in result.prompt_preview
    assert "[SSN]" in result.prompt_preview
    assert "[AWS_KEY]" in result.prompt_preview
    assert "user@example.com" not in result.prompt_preview
    assert "123-45-6789" not in result.prompt_preview
    assert _RAW_AKIA not in result.prompt_preview


def test_hash_is_sha256_of_original():
    result = redact(PII_PROMPT)
    assert result.prompt_hash == hashlib.sha256(PII_PROMPT.encode("utf-8")).hexdigest()
    assert len(result.prompt_hash) == 64
    int(result.prompt_hash, 16)  # valid hex


def test_preview_capped_at_schema_max():
    long_text = "a" * 500 + " user@example.com"
    result = redact(long_text)
    assert result.safe
    assert len(result.prompt_preview) <= 200  # span.schema.json maxLength


def test_clean_prompt_passes_through():
    result = redact("what is the refund policy?")
    assert result.safe
    assert result.prompt_preview == "what is the refund policy?"
    assert result.findings == ()


def test_empty_string():
    result = redact("")
    assert result.safe
    assert result.prompt_preview == ""
    assert result.prompt_hash == hashlib.sha256(b"").hexdigest()


def test_unicode_prompt():
    text = "courriel : usagé@exemple.fr — merci"
    result = redact(text)
    assert result.safe
    assert "usagé@exemple.fr" not in result.prompt_preview
    assert "[EMAIL]" in result.prompt_preview


def test_non_string_raises_redaction_error_not_typeerror():
    # Issue #46: callers map RedactionError -> 400; TypeError would be a 500.
    from vault.redact import RedactionError

    for bad in (None, 42, 3.14, b"bytes", ["list"], {"dict": 1}):
        with pytest.raises(RedactionError):
            redact(bad)


def test_oversized_input_fails_closed_fast():
    # Issue #46: ~16k chars of pathological input cost seconds in regex
    # backtracking; the cap rejects before any regex runs.
    import time

    hostile = ("a" * 15_000) + "@" * 100
    start = time.monotonic()
    result = redact(hostile)
    elapsed = time.monotonic() - start
    assert not result.safe
    assert result.prompt_preview == ""
    assert "INPUT_TOO_LONG" in result.findings
    assert elapsed < 0.5


def test_result_repr_never_contains_raw_pii():
    result = redact(PII_PROMPT)
    for raw in ("user@example.com", "123-45-6789", _RAW_AKIA):
        assert raw not in repr(result)
