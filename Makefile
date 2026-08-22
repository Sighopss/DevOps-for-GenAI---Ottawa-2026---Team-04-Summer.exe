# TraceVault — Unix Makefile. No PowerShell. No windows-* targets.
# `make help` is the runbook. Missing dirs skip (greenfield-safe).

.DEFAULT_GOAL := help
.PHONY: help hooks test vault web demo plan fmt redact-check sbom

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
	@echo "Deploy state (deploy.yml)"
	@echo "  infra/backend.tf is gitignored — the real bucket name is account-scoped,"
	@echo "  not secret (see infra/backend.tf.example). deploy.yml writes it fresh"
	@echo "  every run before terraform init: bucket tracevault-tfstate-887991000498,"
	@echo "  dynamodb_table tracevault-tf-locks, region us-east-1. dev and prod use"
	@echo "  separate keys (dev/terraform.tfstate, prod/terraform.tfstate) and"
	@echo "  separate TF_VAR_env — a prod run can never read or write dev's state."
	@echo "  Skipping this step is what silently switches terraform to a LOCAL,"
	@echo "  empty backend: apply then tries to re-create all live resources, and"
	@echo "  terraform output has nothing to report."
	@echo ""
	@echo "Rollback (command-level mechanics; PR #130 / docs/DEPLOY_GATE.md carries"
	@echo "  the recorded drill + failure-demo evidence for #49 once it lands — this"
	@echo "  is how to actually run a re-run, not a second, competing drill log)"
	@echo "  1. Confirm the break:      curl -sS \"\$$API_URL/health\""
	@echo "  2. Find the last good run: gh run list --workflow=deploy.yml --limit 5"
	@echo "  3. Re-run it exactly:      gh run rerun <run-id> --workflow=deploy.yml"
	@echo "     (or: Actions → deploy.yml → that run → Re-run all jobs)"
	@echo "  4. Watch it:               gh run watch <run-id>"
	@echo "  5. Confirm recovery:       curl -sS \"\$$API_URL/health\" → 200 {\"ok\":true}"
	@echo "                             CloudFront '/' → 200 (web-sync republished)"
	@echo "  Re-running does not roll back Terraform state to an older revision — it"
	@echo "  re-applies the SAME commit's infra/ and re-publishes the SAME commit's"
	@echo "  web/. If the break is a bad commit on main (not a flaky run), the rollback"
	@echo "  is: open a revert PR, get Trevor's merge, then re-run deploy.yml on the"
	@echo "  new main tip."
	@echo "  Do not terraform apply from a feature branch. No CodePipeline. No SSH."
	@echo "  prod requires a reviewer approval (GitHub Environment protection) before"
	@echo "  its terraform apply runs — that is the approval gate, and it is live."
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
	@echo "  make hooks         chmod git hooks; then run once: git config core.hooksPath scripts/git-hooks"
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
	@echo "  [x] main is protected: PR required (1 approval), no force-push. (verified live)"
	@echo "  [ ] Required status checks: gitleaks and trivy-fs. Only those two run on"
	@echo "      every PR. sdk / vault / web / infra are path-filtered, so on a PR that"
	@echo "      does not touch them they report nothing at all — mark those required"
	@echo "      and every unrelated PR waits forever. Leave them optional."
	@echo "  [ ] Trevor is the only merger. Alexis and Michael open PRs; they do not merge."
	@echo "  [x] GitHub Environments dev + prod exist. prod requires a reviewer"
	@echo "      (Sighopss) and restricts deploys to protected branches. (verified live)"
	@echo "  [x] Secret AWS_ROLE_ARN is set (OIDC deploy role). (verified live)"
	@echo "  [ ] Secrets TF_VAR_TENANT_A_PASSWORD / TF_VAR_TENANT_B_PASSWORD are not"
	@echo "      set. deploy.yml falls back to a placeholder password when they are"
	@echo "      unset, which is harmless for existing Cognito users (password"
	@echo "      changes are lifecycle.ignore_changes'd) but means the real judge"
	@echo "      login was set out-of-band, not from a secret. Optional to set."
	@echo "  [ ] No deploy.yml run on main has gone fully green yet. First real CI"
	@echo "      deploy — apply-dev, then web-sync — is still Trevor's to trigger and"
	@echo "      watch (gh run watch), since applying AWS changes isn't something"
	@echo "      this agent can do."
	@echo "  [ ] Rollback drill (see above) has not been rehearsed for real yet."

hooks:
	@chmod +x scripts/git-hooks/* scripts/strip_cursor_trailer.py 2>/dev/null || true
	@echo "Run once per clone: git config core.hooksPath scripts/git-hooks"
	@echo "Hooks strip Co-authored-by: Cursor / cursoragent trailers before commits land."

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
