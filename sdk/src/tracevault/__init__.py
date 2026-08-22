"""TraceVault SDK — emit one-flight span batches. Not the vault. Not the UI."""

from tracevault.client import IngestError, TraceVaultClient
from tracevault.span import end_span, start_span

__all__ = ["IngestError", "TraceVaultClient", "end_span", "start_span"]
