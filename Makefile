# TraceVault — Unix Makefile. No PowerShell. No windows-* targets.
# `make help` is the runbook. Missing dirs skip (greenfield-safe).

.DEFAULT_GOAL := help
.PHONY: help test vault web demo plan fmt redact-check sbom

help:
	@echo "TraceVault runbook (no secrets — never paste passwords, keys, or AKIA here)"
	@echo ""
	@echo "Health"
	@echo "  GET /health is unauthenticated and has no Lambda."
	@echo "  HTTP API (API Gateway v2) has no MOCK integration type, so infra/api.tf"
	@echo "  routes GET /health as HTTP_PROXY to the static health.json object on the"
	@echo "  CloudFront origin. Same 200 {\"ok\":true} body, no function to cold-start."
	@echo "  API_URL=\$$(terraform -chdir=infra output -raw api_url)"
	@echo "  curl -sS \"\$$API_URL/health\""
	@echo "  Expect HTTP 200 and JSON: {\"ok\":true}"
	@echo "  api_url is an infra output (HTTP API base URL). Do not hardcode it."
	@echo "  TRACEVAULT_INGEST_URL is that same base with no path — the SDK appends"
	@echo "  /v1/traces itself. Never feed it the ingest_url output: that one already"
	@echo "  ends in /v1/traces and you get a 404 on the first live flight."
	@echo ""
	@echo "Cognito tenants (usernames = tenant ids)"
	@echo "  tenant-a"
	@echo "  tenant-b"
	@echo "  custom:tenant_id matches the username. Sign-in is Cognito hosted UI;"
	@echo "  ingest uses X-Tenant-Key instead and is never a user JWT."
	@echo "  GET /v1/traces* sends the Cognito ID token, NOT the access token."
	@echo "  Cognito puts custom attributes on the ID token only; an access token"
	@echo "  carries sub / client_id / scope / username and no custom:tenant_id."
	@echo "  The JWT authorizer accepts either, so the wrong token does not fail at"
	@echo "  the gateway — it reaches vault-read with no tenant claim and 401s there."
	@echo "  Debugging a 401 on a signed-in user? Check which token the UI sent first."
	@echo "  Passwords come from TF_VAR_tenant_a_password / TF_VAR_tenant_b_password — not git."
	@echo ""
	@echo "Rollback"
	@echo "  Re-run the last green GitHub Actions workflow deploy.yml on main."
	@echo "  Actions → deploy.yml → last successful run → Re-run jobs."
	@echo "  Do not terraform apply from a feature branch. No CodePipeline. No SSH."
	@echo ""
	@echo "CloudWatch logs (retention 7d, us-east-1)"
	@echo "  /aws/lambda/tracevault-dev-vault-ingest"
	@echo "  /aws/lambda/tracevault-dev-vault-read"
	@echo "  Group names are /aws/lambda/{project}-{env}-vault-{ingest,read};"
	@echo "  swap dev for prod. /health has no log group — it never hits a Lambda."
	@echo "  No raw prompts in logs. Dynamo TTL is also 7d (expires_at)."
	@echo ""
	@echo "Updating a pinned GitHub Action (supply chain)"
	@echo "  Every uses: in .github/workflows is pinned to a full 40-char commit SHA,"
	@echo "  with the human-readable version in a trailing comment. A moving tag can be"
	@echo "  repointed by whoever controls that repo; configure-aws-credentials runs in"
	@echo "  the job holding our OIDC deploy role, so a hijacked tag there would be a"
	@echo "  live AWS credential, not a broken build."
	@echo "  To bump one deliberately — resolve the tag, then verify the SHA is the tag"
	@echo "  you expect before pasting it:"
	@echo "    gh api repos/OWNER/REPO/git/ref/tags/vX.Y.Z --jq '.object.sha,.object.type'"
	@echo "  If type is 'tag' (annotated), dereference it to the commit:"
	@echo "    gh api repos/OWNER/REPO/git/tags/<sha> --jq '.object.sha'"
	@echo "  Confirm the commit exists in that repo, then update BOTH the SHA and the"
	@echo "  trailing version comment. Never leave the comment stale — it is the only"
	@echo "  human-readable record of what the SHA means."
	@echo "  Never reintroduce a bare @v tag, and never add a TODO in place of a pin."
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
	@echo ""
	@echo "Human checklist (set once in the GitHub UI — CI does not automate this)"
	@echo "  [ ] main is protected: PR required, no direct push, no force-push."
	@echo "  [ ] Required status checks: gitleaks and trivy-fs. Only those two run on"
	@echo "      every PR. sdk / vault / web / infra are path-filtered, so on a PR that"
	@echo "      does not touch them they report nothing at all — mark those required"
	@echo "      and every unrelated PR waits forever. Leave them optional."
	@echo "  [ ] Trevor is the only merger. Alexis and Michael open PRs; they do not merge."

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
