"""Read-path test helpers: JWT-shaped events and a seeded store."""

import pytest

from vault.ingest import pipeline
from vault.read.store_read import ReadStore
from vault.store import FlightStore
from vault.tests.conftest import make_span
from vault.tests.fakes import FakeS3Client, FakeTable

TRACE_A = "a" * 32
TRACE_B = "b" * 32


def jwt_event(path, tenant="tenant-a", username="tenant-a", limit=None,
              trace_id=None, claims=None):
    event = {
        "version": "2.0",
        "rawPath": path,
        "requestContext": {
            "authorizer": {
                "jwt": {
                    "claims": claims
                    if claims is not None
                    else {"custom:tenant_id": tenant, "cognito:username": username}
                }
            }
        },
    }
    if limit is not None:
        event["queryStringParameters"] = {"limit": limit}
    if trace_id is not None:
        event["pathParameters"] = {"trace_id": trace_id}
    return event


@pytest.fixture
def seeded(store_env):
    """One flight per tenant, ingested through the real pipeline."""
    s3, table = FakeS3Client(), FakeTable()
    write = FlightStore(s3_client=s3, table=table)
    for tenant, trace, cost in (("tenant-a", TRACE_A, 0.0021), ("tenant-b", TRACE_B, 0.004)):
        spans = [
            make_span(trace_id=trace, tenant_id=tenant),
            make_span(
                trace_id=trace,
                tenant_id=tenant,
                span_id="cccc333333333333",
                parent_id="1111111111111111",
                kind="llm",
                cost_usd=cost,
                prompt_preview="User [EMAIL] asked about [SSN]",
                start_time="2026-08-18T18:00:00.370Z",
                end_time="2026-08-18T18:00:01.150Z",
            ),
        ]
        response = pipeline.ingest(tenant, {"spans": spans}, write)
        assert response["statusCode"] == 202
    return ReadStore(s3_client=s3, table=table)
