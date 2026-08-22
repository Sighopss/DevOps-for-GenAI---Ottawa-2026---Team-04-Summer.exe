"""Audit trail: who opened which trace, when (issue #16).

Rows live in the traces table under SK prefix a# (vault/store/keys.py), so
they inherit the table's tenant partitioning, SSE-KMS, and TTL — and the
flights list (begins_with "t#") never sees them.
"""

from vault.audit.log import list_events, record
from vault.audit.models import AuditEvent

__all__ = ["AuditEvent", "list_events", "record"]
