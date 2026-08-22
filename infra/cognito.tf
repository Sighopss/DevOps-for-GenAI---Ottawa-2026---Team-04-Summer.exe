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
  allowed_oauth_flows                  = ["code"]
  allowed_oauth_scopes                 = ["openid", "email", "profile"]
  supported_identity_providers         = ["COGNITO"]
  callback_urls                        = [local.web_origin]
  logout_urls                          = [local.web_origin]
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
