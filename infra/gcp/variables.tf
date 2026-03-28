variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
  default     = "us-central1"
}

variable "environment" {
  description = "Deployment environment (dev | staging | prod)"
  type        = string
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "environment must be dev, staging, or prod."
  }
}

variable "github_org" {
  description = "GitHub organisation name (for Workload Identity Federation)"
  type        = string
}

variable "github_repo" {
  description = "GitHub repository name (for Workload Identity Federation)"
  type        = string
}

variable "api_image" {
  description = "Full Docker image reference for the API (e.g. us-central1-docker.pkg.dev/PROJECT/repo/oute-api:SHA)"
  type        = string
}

# Cloud SQL
variable "existing_cloud_sql_instance" {
  description = "Name of an existing Cloud SQL instance to reuse (e.g. 'oute-postgres'). Leave empty to create a dedicated instance per environment."
  type        = string
  default     = ""
}

variable "db_tier" {
  description = "Cloud SQL instance tier (only used when existing_cloud_sql_instance is empty)"
  type        = string
  default     = "db-custom-2-7680"
}

variable "db_name" {
  description = "Database name"
  type        = string
  default     = "oute"
}

variable "db_user" {
  description = "Database user name"
  type        = string
  default     = "muscle_app"
}

# Cloud Run
variable "cloud_run_min_instances" {
  description = "Minimum Cloud Run instances (use 0 for dev to save cost)"
  type        = number
  default     = 0
}

variable "cloud_run_max_instances" {
  type    = number
  default = 10
}

variable "cloud_run_cpu" {
  type    = string
  default = "1000m"
}

variable "cloud_run_memory" {
  type    = string
  default = "512Mi"
}
