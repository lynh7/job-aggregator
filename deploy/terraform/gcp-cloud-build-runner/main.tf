provider "google" {
  project = var.project_id
  region  = var.region
}

data "google_project" "current" {
  project_id = var.project_id
}

locals {
  cloud_build_service_account_email = coalesce(
    var.cloud_build_service_account_email,
    "${data.google_project.current.number}@cloudbuild.gserviceaccount.com"
  )
}

resource "google_project_service" "required" {
  for_each = toset([
    "cloudbuild.googleapis.com",
    "secretmanager.googleapis.com",
    "iam.googleapis.com",
  ])

  project            = var.project_id
  service            = each.value
  disable_on_destroy = false
}

resource "google_service_account" "runner" {
  account_id   = var.runner_service_account_id
  display_name = "GitHub self-hosted runner for Cloud Build submit"
}

resource "google_project_iam_member" "runner_cloudbuild_editor" {
  project = var.project_id
  role    = "roles/cloudbuild.builds.editor"
  member  = "serviceAccount:${google_service_account.runner.email}"
}

resource "google_project_iam_member" "runner_serviceusage_consumer" {
  project = var.project_id
  role    = "roles/serviceusage.serviceUsageConsumer"
  member  = "serviceAccount:${google_service_account.runner.email}"
}

resource "google_secret_manager_secret" "ghcr_token" {
  secret_id = "ghcr-token"

  replication {
    auto {}
  }

  depends_on = [google_project_service.required]
}

resource "google_secret_manager_secret_iam_member" "cloud_build_secret_accessor" {
  secret_id = google_secret_manager_secret.ghcr_token.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${local.cloud_build_service_account_email}"
}
