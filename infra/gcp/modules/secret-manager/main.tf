# Module: secret-manager
# Stores the DB password as a versioned secret.

resource "google_secret_manager_secret" "db_password" {
  project   = var.project_id
  secret_id = "${var.name_prefix}-db-password"
  labels    = var.labels

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "db_password" {
  secret      = google_secret_manager_secret.db_password.id
  secret_data = var.db_password_value
}

output "db_password_secret_id" {
  value = google_secret_manager_secret.db_password.secret_id
}
