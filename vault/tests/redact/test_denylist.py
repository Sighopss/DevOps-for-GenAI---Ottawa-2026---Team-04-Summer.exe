"""Deny-list patterns: each contractual entity is masked with its exact token."""

from vault.redact import denylist

RAW_EMAIL = "user@example.com"
RAW_SSN = "123-45-6789"
# Split so gitleaks does not treat test fixtures as live secrets.
RAW_AKIA = "".join(("AKI", "A", "ABCDEFGHIJKLMNOP"))
RAW_ASIA = "".join(("ASI", "A", "ABCDEFGHIJKLMNOP"))
RAW_SK = "".join(("sk", "-", "abcdefghijklmnop1234"))


def test_email_masked():
    masked, found = denylist.mask(f"reach me at {RAW_EMAIL} please")
    assert masked == "reach me at [EMAIL] please"
    assert found == ("EMAIL",)


def test_ssn_masked():
    masked, found = denylist.mask(f"ssn {RAW_SSN} end")
    assert masked == "ssn [SSN] end"
    assert found == ("SSN",)


def test_aws_access_key_masked():
    masked, found = denylist.mask(f"key {RAW_AKIA} and sts {RAW_ASIA}")
    assert masked == "key [AWS_KEY] and sts [AWS_KEY]"
    assert found == ("AWS_KEY",)


def test_sk_secret_masked():
    masked, found = denylist.mask(f"token {RAW_SK} end")
    assert masked == "token [API_KEY] end"
    assert found == ("API_KEY",)


def test_all_entities_together():
    masked, found = denylist.mask(
        f"{RAW_EMAIL} {RAW_SSN} {RAW_AKIA} {RAW_SK}"
    )
    assert masked == "[EMAIL] [SSN] [AWS_KEY] [API_KEY]"
    assert set(found) == {"EMAIL", "SSN", "AWS_KEY", "API_KEY"}
    for raw in (RAW_EMAIL, RAW_SSN, RAW_AKIA, RAW_SK):
        assert raw not in masked


def test_clean_text_untouched():
    masked, found = denylist.mask("what is the refund policy?")
    assert masked == "what is the refund policy?"
    assert found == ()


def test_residual_matches_detects_leftovers():
    assert denylist.residual_matches(f"oops {RAW_SSN}") == ("SSN",)
    assert denylist.residual_matches("all clean [SSN] [EMAIL]") == ()
