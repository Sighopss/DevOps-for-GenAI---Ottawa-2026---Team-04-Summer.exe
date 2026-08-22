# Tenancy

Two tenants exist: `tenant-a` and `tenant-b`. Ingest authenticates with
`X-Tenant-Key`. Reads use a Cognito JWT `custom:tenant_id`.

A tenant-b token asking for a tenant-a `trace_id` must return **403**, not 404.
List endpoints are tenant-scoped. Do not mix tenant keys on a flight.
