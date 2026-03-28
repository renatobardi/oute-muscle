# Module: vertex-ai
# Enables required Vertex AI APIs and grants the API service account access.
# The actual model calls are made directly via the Vertex AI SDK — no
# additional resources (endpoints, indexes) are needed for online prediction.

resource "google_project_service" "aiplatform" {
  project            = var.project_id
  service            = "aiplatform.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "ml" {
  project            = var.project_id
  service            = "ml.googleapis.com"
  disable_on_destroy = false
}

# Outputs — consumed by other modules / CI for documentation
output "region" {
  value = var.region
}

output "project_id" {
  value = var.project_id
}
