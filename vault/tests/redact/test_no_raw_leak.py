"""The judge-watchable guarantee: redaction never emits raw PII anywhere —
not stdout, not logging, not the result object."""

import logging

from vault.redact import redact

RAW_EMAIL = "user@example.com"
RAW_SSN = "123-45-6789"
PII_PROMPT = f"reach me at {RAW_EMAIL} ssn {RAW_SSN}"


def test_no_raw_pii_on_stdout_or_stderr(capsys):
    redact(PII_PROMPT)
    captured = capsys.readouterr()
    assert RAW_EMAIL not in captured.out
    assert RAW_SSN not in captured.out
    assert RAW_EMAIL not in captured.err
    assert RAW_SSN not in captured.err


def test_no_raw_pii_in_log_records(caplog):
    with caplog.at_level(logging.DEBUG):
        redact(PII_PROMPT)
    text = caplog.text
    assert RAW_EMAIL not in text
    assert RAW_SSN not in text


def test_result_object_carries_no_raw_pii():
    result = redact(PII_PROMPT)
    dumped = repr(result) + result.prompt_preview + result.prompt_hash
    assert RAW_EMAIL not in dumped
    assert RAW_SSN not in dumped
