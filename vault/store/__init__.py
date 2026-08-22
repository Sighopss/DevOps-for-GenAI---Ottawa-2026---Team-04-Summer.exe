"""Persistence: S3 (redacted span payloads) + DynamoDB (flight summaries).

The Dynamo item is the commit point: S3 is written first, and a flight only
becomes visible once its Dynamo summary lands (reads resolve through the
item's s3_keys). The ingest IAM role has no s3:DeleteObject, so a failed
Dynamo write leaves an unreachable S3 object, never a half-visible flight.
"""

from vault.store.flight_store import FlightStore

__all__ = ["FlightStore"]
