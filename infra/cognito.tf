resource "aws_cognito_user_pool" "this" {
  name = "${local.name}-users"

  mfa_configuration = "OFF"

  username_configuration {
    case_sensitive = true
  }

  admin_create_user_config {
    allow_admin_create_user_only = true
  }

  password_policy {
    minimum_length                   = 12
    require_lowercase                = true
    require_numbers                  = true
    require_symbols                  = true
    require_uppercase                = true
    temporary_password_validity_days = 7
  }

  schema {
    name                     = "tenant_id"
    attribute_data_type      = "String"
    developer_only_attribute = false
    mutable                  = true
    required                 = false
    string_attribute_constraints {
      min_length = 1
      max_length = 64
    }
  }
}

resource "aws_cognito_user_pool_client" "web" {
  name         = "${local.name}-web"
  user_pool_id = aws_cognito_user_pool.this.id

  generate_secret                      = false
  allowed_oauth_flows_user_pool_client = true

  # The Explorer is a static export with no server to hold a client secret, so
  # it uses the implicit flow: it requests `response_type=token` and reads the
  # ID token out of the URL fragment (`web/src/lib/cognito.ts`). The client was
  # configured for `code` only, so the hosted UI rejected every sign-in with
  # "An error was encountered with the requested page". Flows must match the
  # client that uses them.
  #
  # Implicit puts the token in the URL fragment, which is weaker than code +
  # PKCE. Accepted for a 48h demo with two seeded tenants and a 7-day TTL;
  # the durable fix is PKCE in the web app, which is a `web/` change.
  allowed_oauth_flows          = ["implicit"]
  allowed_oauth_scopes         = ["openid", "email", "profile"]
  supported_identity_providers = ["COGNITO"]

  # The app sends `redirect_uri = <origin>/explorer` (page.tsx) — no trailing
  # slash. An unregistered redirect_uri is the second reason sign-in failed:
  # Cognito matches these strings exactly, so `/explorer/` and `/explorer` are
  # different entries. All three forms are registered so the hosted UI accepts
  # the redirect whichever way the app or a hand-typed link spells it.
  callback_urls = [
    local.web_origin,
    "${local.web_origin}/explorer",
    "${local.web_origin}/explorer/",
  ]
  logout_urls = [
    local.web_origin,
    "${local.web_origin}/explorer",
    "${local.web_origin}/explorer/",
  ]
  prevent_user_existence_errors        = "ENABLED"
  explicit_auth_flows = [
    "ALLOW_USER_PASSWORD_AUTH",
    "ALLOW_USER_SRP_AUTH",
    "ALLOW_REFRESH_TOKEN_AUTH",
  ]
}

resource "aws_cognito_user_pool_domain" "this" {
  domain       = local.cognito_domain_prefix
  user_pool_id = aws_cognito_user_pool.this.id
}

resource "aws_cognito_user_group" "viewer" {
  name         = "viewer"
  user_pool_id = aws_cognito_user_pool.this.id
  description  = "Read flights for the user's custom:tenant_id"
}

resource "aws_cognito_user_group" "admin" {
  name         = "admin"
  user_pool_id = aws_cognito_user_pool.this.id
  description  = "Admin group (same tenant claim rules still apply in vault-read)"
}

resource "aws_cognito_user" "tenant_a" {
  user_pool_id = aws_cognito_user_pool.this.id
  username     = "tenant-a"
  password     = var.tenant_a_password
  enabled      = true

  attributes = {
    email              = "tenant-a@example.invalid"
    email_verified     = "true"
    "custom:tenant_id" = "tenant-a"
  }

  message_action = "SUPPRESS"

  # Password is set once at create (or via Cognito admin). Apply must not
  # rotate judge logins when deploy only has plan-only placeholder TF_VARs.
  lifecycle {
    ignore_changes = [password]
  }
}

resource "aws_cognito_user" "tenant_b" {
  user_pool_id = aws_cognito_user_pool.this.id
  username     = "tenant-b"
  password     = var.tenant_b_password
  enabled      = true

  attributes = {
    email              = "tenant-b@example.invalid"
    email_verified     = "true"
    "custom:tenant_id" = "tenant-b"
  }

  message_action = "SUPPRESS"

  lifecycle {
    ignore_changes = [password]
  }
}

resource "aws_cognito_user_in_group" "tenant_a_viewer" {
  user_pool_id = aws_cognito_user_pool.this.id
  group_name   = aws_cognito_user_group.viewer.name
  username     = aws_cognito_user.tenant_a.username
}

resource "aws_cognito_user_in_group" "tenant_b_viewer" {
  user_pool_id = aws_cognito_user_pool.this.id
  group_name   = aws_cognito_user_group.viewer.name
  username     = aws_cognito_user.tenant_b.username
}
