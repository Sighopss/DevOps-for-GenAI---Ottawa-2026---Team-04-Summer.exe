"""Fail-closed prompt redaction. Raw prompts never leave this package unmasked."""

from vault.redact.engine import RedactionError, redact, redact_strict
from vault.redact.models import RedactResult

__all__ = ["RedactResult", "RedactionError", "redact", "redact_strict"]
