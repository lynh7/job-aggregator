output "runner_service_account_email" {
  value       = google_service_account.runner.email
  description = "Service account email for the Raspberry Pi self-hosted runner."
}

output "cloud_build_service_account_email" {
  value       = local.cloud_build_service_account_email
  description = "Cloud Build service account granted access to ghcr-token."
}

output "ghcr_token_secret_name" {
  value       = google_secret_manager_secret.ghcr_token.secret_id
  description = "Secret Manager secret name used by cloudbuild.yaml."
}
