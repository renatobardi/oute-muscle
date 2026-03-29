# T176: GCP Terraform main configuration
# Manages: Cloud Run, Cloud SQL, Vertex AI, Secret Manager, Artifact Registry, IAM

terraform {
  required_version = ">= 1.8"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.30"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 5.30"
    }
  }

  backend "gcs" {
    # Populated by -backend-config flags in CI
    # bucket = "oute-terraform-state"
    # prefix = "oute-muscle/{env}"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

provider "google-beta" {
  project = var.project_id
  region  = var.region
}

# ─────────────────────────────────────────────────────────────
# Locals
# ─────────────────────────────────────────────────────────────

locals {
  name_prefix = "muscle-${var.environment}"
  labels = {
    app         = "oute-muscle"
    environment = var.environment
    managed_by  = "terraform"
  }
}

# ─────────────────────────────────────────────────────────────
# Modules
# ─────────────────────────────────────────────────────────────

module "artifact_registry" {
  source = "./modules/artifact-registry"

  project_id   = var.project_id
  region       = var.region
  name_prefix  = local.name_prefix
  labels       = local.labels
}

module "cloud_sql" {
  source = "./modules/cloud-sql"

  project_id              = var.project_id
  region                  = var.region
  name_prefix             = local.name_prefix
  environment             = var.environment
  labels                  = local.labels

  existing_instance_name  = var.existing_cloud_sql_instance
  db_tier                 = var.db_tier
  db_name                 = var.db_name
  db_user                 = var.db_user
}

module "secret_manager" {
  source = "./modules/secret-manager"

  project_id  = var.project_id
  name_prefix = local.name_prefix
  labels      = local.labels

  db_password_value = module.cloud_sql.db_password
}

module "iam" {
  source = "./modules/iam"

  project_id         = var.project_id
  region             = var.region
  name_prefix        = local.name_prefix
  github_org         = var.github_org
  github_repo        = var.github_repo
  environment        = var.environment
  ar_repository_id   = module.artifact_registry.repository_id
}

module "cloud_run" {
  source = "./modules/cloud-run"

  project_id         = var.project_id
  region             = var.region
  name_prefix        = local.name_prefix
  environment        = var.environment
  labels             = local.labels

  image              = var.api_image
  service_account    = module.iam.api_service_account_email
  db_instance        = module.cloud_sql.connection_name
  db_name            = var.db_name
  db_user            = var.db_user
  db_password_secret = module.secret_manager.db_password_secret_id
  min_instances      = var.cloud_run_min_instances
  max_instances      = var.cloud_run_max_instances
  cpu                = var.cloud_run_cpu
  memory             = var.cloud_run_memory

  custom_domains = [
    { domain = "muscle.oute.pro",     service_name = "${local.name_prefix}-web" },
    { domain = "mcp.muscle.oute.pro", service_name = "${local.name_prefix}-mcp" },
  ]
}

module "vertex_ai" {
  source = "./modules/vertex-ai"

  project_id       = var.project_id
  region           = var.region
  name_prefix      = local.name_prefix
  service_account  = module.iam.api_service_account_email
}

# ─────────────────────────────────────────────────────────────
# Outputs
# ─────────────────────────────────────────────────────────────

output "api_url" {
  description = "Cloud Run service URL"
  value       = module.cloud_run.service_url
}

output "artifact_registry_url" {
  description = "Docker image registry base URL"
  value       = module.artifact_registry.registry_url
}

output "cloud_sql_connection_name" {
  description = "Cloud SQL connection name for Cloud Run"
  value       = module.cloud_sql.connection_name
}

output "workload_identity_provider" {
  description = "Workload Identity Federation provider resource name (for GitHub Actions)"
  value       = module.iam.workload_identity_provider
}

output "github_actions_service_account" {
  description = "Service account email used by GitHub Actions"
  value       = module.iam.github_actions_service_account_email
}

output "domain_mappings" {
  description = "Custom domain mappings for Cloud Run services"
  value       = module.cloud_run.domain_mappings
}
