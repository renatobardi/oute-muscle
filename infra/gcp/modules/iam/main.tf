# T179: IAM module — Workload Identity Federation + service accounts
#
# Creates:
#   1. API service account (used by Cloud Run)
#   2. GitHub Actions service account (used by CI to push images + deploy)
#   3. Workload Identity Pool + Provider (OIDC → GitHub)
#   4. Bindings: WIF → GitHub Actions SA via attribute conditions

# ─── API service account ───────────────────────────────────────────────────

resource "google_service_account" "api" {
  project      = var.project_id
  account_id   = "${var.name_prefix}-api"
  display_name = "Oute Muscle API (${var.environment})"
}

# Cloud SQL client — required for Cloud SQL proxy
resource "google_project_iam_member" "api_cloudsql_client" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.api.email}"
}

# Secret Manager accessor — read DB password and other secrets at runtime
resource "google_project_iam_member" "api_secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.api.email}"
}

# Vertex AI user — call Gemini / Claude models
resource "google_project_iam_member" "api_vertex_user" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.api.email}"
}

# Cloud Trace agent — write spans
resource "google_project_iam_member" "api_trace_agent" {
  project = var.project_id
  role    = "roles/cloudtrace.agent"
  member  = "serviceAccount:${google_service_account.api.email}"
}

# Cloud Monitoring metric writer
resource "google_project_iam_member" "api_monitoring_writer" {
  project = var.project_id
  role    = "roles/monitoring.metricWriter"
  member  = "serviceAccount:${google_service_account.api.email}"
}

# ─── GitHub Actions service account ───────────────────────────────────────

resource "google_service_account" "github_actions" {
  project      = var.project_id
  account_id   = "${var.name_prefix}-gh-actions"
  display_name = "GitHub Actions — Oute Muscle (${var.environment})"
}

# Push images to Artifact Registry
resource "google_artifact_registry_repository_iam_member" "gh_actions_ar_writer" {
  project    = var.project_id
  location   = var.region
  repository = var.ar_repository_id
  role       = "roles/artifactregistry.writer"
  member     = "serviceAccount:${google_service_account.github_actions.email}"
}

# Deploy to Cloud Run
resource "google_project_iam_member" "gh_actions_run_developer" {
  project = var.project_id
  role    = "roles/run.developer"
  member  = "serviceAccount:${google_service_account.github_actions.email}"
}

# Allow GH Actions SA to act as the API SA when deploying
resource "google_service_account_iam_member" "gh_actions_impersonate_api" {
  service_account_id = google_service_account.api.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.github_actions.email}"
}

# ─── Workload Identity Federation ─────────────────────────────────────────

resource "google_iam_workload_identity_pool" "github" {
  project                   = var.project_id
  workload_identity_pool_id = "${var.name_prefix}-gh-pool"
  display_name              = "GitHub Actions pool (${var.environment})"
}

resource "google_iam_workload_identity_pool_provider" "github_oidc" {
  project                            = var.project_id
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = "${var.name_prefix}-gh-provider"
  display_name                       = "GitHub OIDC provider"

  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.actor"      = "assertion.actor"
    "attribute.repository" = "assertion.repository"
    "attribute.ref"        = "assertion.ref"
  }

  # Only tokens from the configured repo are accepted
  attribute_condition = "attribute.repository == \"${var.github_org}/${var.github_repo}\""

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

# Allow tokens from the GitHub repo to impersonate the GitHub Actions SA
resource "google_service_account_iam_member" "wif_binding" {
  service_account_id = google_service_account.github_actions.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/attribute.repository/${var.github_org}/${var.github_repo}"
}

# ─── Outputs ──────────────────────────────────────────────────────────────

output "api_service_account_email" {
  value = google_service_account.api.email
}

output "github_actions_service_account_email" {
  value = google_service_account.github_actions.email
}

output "workload_identity_provider" {
  value = google_iam_workload_identity_pool_provider.github_oidc.name
}
