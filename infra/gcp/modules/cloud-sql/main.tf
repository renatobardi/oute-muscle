# Module: cloud-sql
# Provisions a Cloud SQL for PostgreSQL 16 instance with pgvector,
# OR references an existing shared instance when existing_instance_name is set.
#
# Shared-instance mode (recommended to reduce cost):
#   Pass existing_instance_name = "oute-postgres" to skip instance creation.
#   Only the database and user are created on the existing instance.
#
# Standalone mode (default):
#   Omit existing_instance_name (or set it to "") to create a dedicated instance.

locals {
  use_existing  = var.existing_instance_name != ""
  instance_name = local.use_existing ? var.existing_instance_name : google_sql_database_instance.postgres[0].name
}

resource "random_password" "db_password" {
  length  = 32
  special = false
}

# ─── Standalone instance (skipped when existing_instance_name is set) ─────────

resource "google_sql_database_instance" "postgres" {
  count = local.use_existing ? 0 : 1

  name             = "${var.name_prefix}-postgres"
  database_version = "POSTGRES_16"
  region           = var.region
  project          = var.project_id

  settings {
    tier              = var.db_tier
    availability_type = var.environment == "prod" ? "REGIONAL" : "ZONAL"
    disk_autoresize   = true
    disk_size         = 20

    backup_configuration {
      enabled                        = var.environment == "prod"
      point_in_time_recovery_enabled = var.environment == "prod"
      start_time                     = "03:00"
      transaction_log_retention_days = 7
    }

    database_flags {
      name  = "cloudsql.enable_pgvector"
      value = "on"
    }

    database_flags {
      name  = "max_connections"
      value = "100"
    }

    insights_config {
      query_insights_enabled  = true
      record_application_tags = true
      record_client_address   = false
    }

    user_labels = var.labels
  }

  deletion_protection = var.environment == "prod"
}

# ─── Shared instance reference (read-only, used when existing_instance_name set) ─

data "google_sql_database_instance" "existing" {
  count   = local.use_existing ? 1 : 0
  name    = var.existing_instance_name
  project = var.project_id
}

# ─── Database and user (always created on whichever instance is active) ────────

resource "google_sql_database" "oute" {
  name     = var.db_name
  instance = local.instance_name
  project  = var.project_id
}

resource "google_sql_user" "app" {
  name     = var.db_user
  instance = local.instance_name
  password = random_password.db_password.result
  project  = var.project_id
}

# ─── Outputs ──────────────────────────────────────────────────────────────────

output "connection_name" {
  value = local.use_existing ? data.google_sql_database_instance.existing[0].connection_name : google_sql_database_instance.postgres[0].connection_name
}

output "db_password" {
  value     = random_password.db_password.result
  sensitive = true
}
