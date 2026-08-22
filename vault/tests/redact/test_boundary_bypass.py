"""Regression tests for issue #45: every reported deny-list bypass masks,
and none returns safe=True with the raw value intact."""

import pytest

from vault.redact import denylist, redact

SSN = "123-45-6789"
_RAW_AKIA = "".join(("AKI", "A", "IOSFODNN7EXAMPLE"))
_RAW_SK = "".join(("sk", "-", "abcdefghijklmnop1234"))


@pytest.mark.parametrize(
    "payload",
    [
        f"SSN{SSN}",  # no space before digits
        f"My SSN is{SSN}",  # letter abuts first digit
        f"x{SSN}",  # single-char prefix
        f"{SSN}a",  # alphanumeric suffix
        "123456789",  # bare nine digits
        "123 45 6789",  # space-separated
        "ssn:123-45 6789",  # mixed separators
    ],
)
def test_reported_ssn_bypasses_now_mask(payload):
    masked, found = denylist.mask(payload)
    assert "SSN" in found
    assert "123-45-6789" not in masked
    assert "123 45 6789" not in masked
    assert "123456789" not in masked
    result = redact(payload)
    assert result.safe
    assert "[SSN]" in result.prompt_preview


def test_aws_key_masks_mid_token():
    masked, found = denylist.mask(f"key={_RAW_AKIA}ZZ")
    assert "AWS_KEY" in found
    assert _RAW_AKIA not in masked  # 20-char key id destroyed


def test_sk_key_masks_after_separator():
    masked, found = denylist.mask(f"token:{_RAW_SK}")
    assert "API_KEY" in found
    assert _RAW_SK not in masked


def test_longer_digit_runs_not_partial_masked():
    # Digit-excluding lookarounds: a 12-digit id is not an SSN and must not
    # be chewed into a half-masked number.
    masked, found = denylist.mask("order 123456789012 confirmed")
    assert masked == "order 123456789012 confirmed"
    assert found == ()


def test_word_with_risk_prefix_not_false_positived():
    masked, found = denylist.mask("risk-assessment-methodology-notes")
    assert masked == "risk-assessment-methodology-notes"
    assert found == ()


def test_ten_digit_number_untouched():
    masked, _ = denylist.mask("epoch 1780000000 fine")
    assert masked == "epoch 1780000000 fine"
