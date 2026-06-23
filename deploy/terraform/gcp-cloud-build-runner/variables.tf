variable "project_id" {
  description = "Google Cloud project ID."
  type        = string
}

variable "region" {
  description = "Default Google Cloud region for provider operations."
  type        = string
  default     = "asia-southeast1"
}

variable "runner_service_account_id" {
  description = "Account ID for the Raspberry Pi GitHub runner service account."
  type        = string
  default     = "github-runner-cloudbuild"
}

variable "cloud_build_service_account_email" {
  description = "Service account email used by Cloud Build execution. Leave null to use the default PROJECT_NUMBER@cloudbuild.gserviceaccount.com account."
  type        = string
  default     = null
}
