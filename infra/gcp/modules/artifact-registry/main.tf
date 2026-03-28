# Module: artifact-registry
# Hosts Docker images for the Oute Muscle API.

resource "google_artifact_registry_repository" "docker" {
  project       = var.project_id
  location      = var.region
  repository_id = "${var.name_prefix}-docker"
  description   = "Docker images for Oute Muscle"
  format        = "DOCKER"
  labels        = var.labels

  cleanup_policies {
    id     = "keep-last-10"
    action = "KEEP"
    most_recent_versions {
      keep_count = 10
    }
  }
}

output "repository_id" {
  value = google_artifact_registry_repository.docker.repository_id
}

output "registry_url" {
  value = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.docker.repository_id}"
}
