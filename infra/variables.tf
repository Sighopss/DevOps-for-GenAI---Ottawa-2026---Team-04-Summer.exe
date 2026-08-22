variable "aws_region" {
  type        = string
  description = "AWS region for the stack."
  default     = "us-east-1"
}

variable "env" {
  type        = string
  description = "Environment name (tag Env and name prefix)."
  default     = "dev"

  validation {
    condition     = contains(["dev", "prod"], var.env)
    error_message = "env must be dev or prod."
  }
}

variable "project" {
  type        = string
  description = "Lowercase name prefix for AWS resources."
  default     = "tracevault"
}

variable "github_repository" {
  type        = string
  description = "GitHub org/repo allowed to assume the OIDC role (no other repos)."
  default     = "Sighopss/DevOps-for-GenAI---Ottawa-2026---Team-04-Summer.exe"
}

variable "bedrock_model_ids" {
  type        = list(string)
  description = "Bedrock foundation model ids the OIDC role may invoke. Not *."
  default = [
    "anthropic.claude-3-5-sonnet-20241022-v2:0",
    "amazon.nova-lite-v1:0",
  ]
}

variable "api_throttle_rate" {
  type        = number
  description = "API Gateway steady-state requests per second (demo cap, not unlimited)."
  default     = 10
}

variable "api_throttle_burst" {
  type        = number
  description = "API Gateway burst limit (demo cap, not unlimited)."
  default     = 20
}

variable "alarm_email" {
  type        = string
  description = "Optional SNS email for the API 5xx alarm. Empty = alarm with no actions."
  default     = ""
}

variable "cognito_domain_prefix" {
  type        = string
  description = "Cognito hosted UI domain prefix. Empty = tracevault-{env}-{account_id}."
  default     = ""
}

variable "tenant_a_password" {
  type        = string
  description = "Permanent password for Cognito user tenant-a. Set via TF_VAR_tenant_a_password."
  sensitive   = true
}

variable "tenant_b_password" {
  type        = string
  description = "Permanent password for Cognito user tenant-b. Set via TF_VAR_tenant_b_password."
  sensitive   = true
}

variable "lambda_timeout_seconds" {
  type        = number
  description = "Timeout for both vault Lambdas."
  default     = 30
}

variable "lambda_memory_mb" {
  type        = number
  description = "Memory for both vault Lambdas."
  default     = 512
}
