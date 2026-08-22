"""X-Tenant-Key resolution against the two per-tenant secrets."""

from vault.ingest import tenant_key
from vault.tests.fakes import fake_secret_fetch

SECRETS = {
    "arn:a": {"tenant_id": "tenant-a", "key": "key-for-a-1234"},
    "arn:b": {"tenant_id": "tenant-b", "key": "key-for-b-5678"},
}


def _env(monkeypatch):
    monkeypatch.setenv("TENANT_A_SECRET_ARN", "arn:a")
    monkeypatch.setenv("TENANT_B_SECRET_ARN", "arn:b")


def test_key_maps_to_tenant_a(monkeypatch):
    _env(monkeypatch)
    fetch = fake_secret_fetch(SECRETS)
    assert tenant_key.resolve({"X-Tenant-Key": "key-for-a-1234"}, fetch) == "tenant-a"


def test_key_maps_to_tenant_b_case_insensitive_header(monkeypatch):
    _env(monkeypatch)
    fetch = fake_secret_fetch(SECRETS)
    assert tenant_key.resolve({"x-tenant-key": "key-for-b-5678"}, fetch) == "tenant-b"


def test_unknown_key_rejected(monkeypatch):
    _env(monkeypatch)
    fetch = fake_secret_fetch(SECRETS)
    assert tenant_key.resolve({"X-Tenant-Key": "wrong"}, fetch) is None


def test_missing_header_rejected(monkeypatch):
    _env(monkeypatch)
    fetch = fake_secret_fetch(SECRETS)
    assert tenant_key.resolve({}, fetch) is None
    assert tenant_key.resolve({"X-Tenant-Key": ""}, fetch) is None


def test_placeholder_secret_never_matches(monkeypatch):
    # Trevor provisions placeholder secrets with empty values pre-deploy.
    _env(monkeypatch)
    fetch = fake_secret_fetch({
        "arn:a": {"tenant_id": "tenant-a", "key": ""},
        "arn:b": {},
    })
    assert tenant_key.resolve({"X-Tenant-Key": ""}, fetch) is None
    assert tenant_key.resolve({"X-Tenant-Key": "anything"}, fetch) is None


def test_unreadable_secret_never_authenticates(monkeypatch):
    _env(monkeypatch)

    def broken(_arn):
        raise RuntimeError("secretsmanager down")

    assert tenant_key.resolve({"X-Tenant-Key": "key-for-a-1234"}, broken) is None
