# TraceVault — Unix Makefile. No PowerShell. No windows-* targets.
# `make help` is the runbook. Missing dirs skip (greenfield-safe).

.DEFAULT_GOAL := help
.PHONY: help test vault web demo plan fmt redact-check sbom

help:
	@echo "TraceVault runbook (no secrets — never paste passwords, keys, or AKIA here)"
	@echo ""
	@echo "Health"
	@echo "  GET /health is unauthenticated. No Lambda."
	@echo "  HTTP API v2 cannot MOCK; the route HTTP_PROXYs {\"ok\":true} from the web origin (health.json)."
	@echo "  curl -sS \"\$$TRACEVAULT_INGEST_URL/health\""
	@echo "  Expect HTTP 200 and JSON: {\"ok\":true}"
	@echo "  TRACEVAULT_INGEST_URL is an infra output (HTTP API). Do not hardcode it."
	@echo ""
	@echo "Cognito tenants (usernames = tenant ids)"
	@echo "  tenant-a"
	@echo "  tenant-b"
	@echo "  custom:tenant_id matches the username. Passwords live in Cognito / TF_VAR_* — not git."
	@echo ""
	@echo "Rollback"
	@echo "  Re-run the last green GitHub Actions workflow deploy.yml on main."
	@echo "  Actions → deploy.yml → last successful run → Re-run jobs."
	@echo "  Do not terraform apply from a feature branch. No CodePipeline. No SSH."
	@echo ""
	@echo "CloudWatch logs (retention 7d, us-east-1)"
	@echo "  /aws/lambda/vault-ingest"
	@echo "  /aws/lambda/vault-read"
	@echo "  No raw prompts in logs. Dynamo TTL is also 7d (expires_at)."
	@echo ""
	@echo "Targets (skip cleanly if the directory is missing)"
	@echo "  make test          pytest sdk/ (uv if present)"
	@echo "  make vault         pytest vault/"
	@echo "  make web           skip until web/ exists"
	@echo "  make demo          scripts/demo_pii_flight.sh"
	@echo "  make plan          terraform plan in infra/"
	@echo "  make fmt           terraform fmt -recursive when infra/ exists"
	@echo "  make redact-check  alias of vault"
	@echo "  make sbom          trivy CycloneDX → sbom.cdx.json (gitignored CI artifact)"

test:
	@if [ -d sdk ]; then \
		if command -v uv >/dev/null 2>&1; then \
			(cd sdk && uv run pytest); \
		else \
			python3 -m pytest sdk; \
		fi; \
	else \
		echo "skip: sdk/ missing (greenfield)"; \
	fi

vault:
	@if [ -d vault ]; then \
		if command -v uv >/dev/null 2>&1 && [ -f vault/pyproject.toml ]; then \
			(cd vault && uv run pytest); \
		else \
			python3 -m pytest vault; \
		fi; \
	else \
		echo "skip: vault/ missing (greenfield)"; \
	fi

web:
	@if [ -d web ]; then \
		(cd web && pnpm lint); \
	else \
		echo "skip: web/ missing (greenfield)"; \
	fi

demo:
	@if [ -f scripts/demo_pii_flight.sh ]; then \
		bash scripts/demo_pii_flight.sh; \
	else \
		echo "skip: scripts/demo_pii_flight.sh missing (greenfield)"; \
	fi

plan:
	@if [ -d infra ]; then \
		if command -v terraform >/dev/null 2>&1; then \
			terraform -chdir=infra init -backend=false >/dev/null && terraform -chdir=infra plan; \
		else \
			echo "skip: terraform not installed"; \
		fi; \
	else \
		echo "skip: infra/ missing (greenfield)"; \
	fi

fmt:
	@if [ -d infra ] && command -v terraform >/dev/null 2>&1; then \
		terraform fmt -recursive infra; \
	else \
		echo "skip: terraform fmt (infra/ or terraform missing)"; \
	fi

redact-check: vault

sbom:
	@if command -v trivy >/dev/null 2>&1; then \
		trivy fs --format cyclonedx -o sbom.cdx.json .; \
		echo "wrote sbom.cdx.json (gitignored; CI uploads the artifact — do not commit secrets)"; \
	else \
		echo "skip: trivy not installed"; \
	fi
