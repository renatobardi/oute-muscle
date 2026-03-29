# Deployment Runbook

## Environment

Single environment: **prod** — Trunk-Based CD.

| Environment | URL | Trigger |
|-------------|-----|---------|
| Prod | https://muscle.oute.pro/api | Merge to `main` |

## Normal deploy flow

Every PR merged to `main` triggers an automatic deploy to prod via `.github/workflows/deploy.yml`.

No manual steps. No tags. No staging.

```
feature branch → PR → CI (lint + tests + semgrep) → merge main → deploy prod
```

Monitor at: https://github.com/renatobardi/oute-muscle/actions/workflows/deploy.yml

## Rollback

```bash
# List recent Cloud Run revisions
gcloud run revisions list --service=muscle-prod-api --region=us-central1

# Roll back to a specific revision
gcloud run services update-traffic muscle-prod-api \
  --region=us-central1 \
  --to-revisions=muscle-prod-api-00003-xyz=100
```

Then fix the issue on a feature branch, open a PR, and let CI/CD redeploy.

## First-time bootstrap

Run once to provision all GCP resources and configure GitHub Actions.

### Prerequisites

```bash
# 1. Authenticated gcloud
gcloud auth login
gcloud auth application-default login

# 2. Authenticated GitHub CLI
gh auth login

# 3. Terraform >= 1.8
brew install hashicorp/tap/terraform
terraform --version

# 4. Correct GCP project
gcloud config set project oute-488706
```

### Bootstrap

```bash
bash scripts/deploy-bootstrap.sh
```

The script will:
1. Enable required GCP APIs
2. Create the GCS Terraform state bucket (idempotent)
3. Run `terraform init && terraform apply`
4. Set all GitHub Actions environment variables and secrets in the `production` environment

If it fails mid-way, it's safe to re-run — all operations are idempotent.

### Common bootstrap errors

**`database already exists`**

The database was created in a prior partial run but isn't in Terraform state. Import it:

```bash
cd infra/gcp
terraform import \
  -var="project_id=oute-488706" \
  -var="environment=prod" \
  -var="github_org=renatobardi" \
  -var="github_repo=oute-muscle" \
  -var="api_image=placeholder" \
  -var="existing_cloud_sql_instance=oute-postgres" \
  -var="db_name=oute_muscle_prod" \
  -var="db_user=muscle_app" \
  module.cloud_sql.google_sql_database.oute \
  "projects/oute-488706/instances/oute-postgres/databases/oute_muscle_prod"
cd ../..
bash scripts/deploy-bootstrap.sh
```

**`Permission denied on secret` (Cloud Run)**

IAM propagation lag (~60s). Wait a minute and re-run the bootstrap.

**`workload_identity_provider` not set**

The GitHub Actions environment vars weren't configured. Bootstrap again to set them:

```bash
bash scripts/deploy-bootstrap.sh
```

## Database migrations

Migrations run automatically on every deploy (in the CI/CD pipeline before Cloud Run revision swap). To run manually:

```bash
# Apply all pending migrations
make migrate-up

# Rollback last migration
make migrate-down

# Create a new migration
make migrate-gen MSG="add_column_to_foo"
```

Migrations live in `packages/db/src/migrations/versions/`. Naming convention: `{NNN}_{description}.py`.

Migration files are tracked in git normally (not ignored). Just `git add` as usual.

## Terraform changes

Changes to `infra/gcp/` are not auto-applied. They require a manual plan + apply:

```bash
cd infra/gcp

# Init (if needed)
terraform init \
  -backend-config="bucket=oute-terraform-state" \
  -backend-config="prefix=oute-muscle/prod"

# Plan
terraform plan \
  -var="project_id=oute-488706" \
  -var="environment=prod" \
  -var="github_org=renatobardi" \
  -var="github_repo=oute-muscle" \
  -var="api_image=$(gcloud run services describe muscle-prod-api --region=us-central1 --format='value(spec.template.spec.containers[0].image)')" \
  -var="existing_cloud_sql_instance=oute-postgres"

# Apply
terraform apply [same vars]
```

## Monitoring

```bash
# Cloud Run logs (prod)
gcloud logging read \
  'resource.type="cloud_run_revision" resource.labels.service_name="muscle-prod-api"' \
  --limit=50 --format=json | jq '.[].jsonPayload'

# Health endpoints
curl https://muscle.oute.pro/api/health/live
curl https://muscle.oute.pro/api/health/ready
curl https://muscle.oute.pro/api/health/startup
```

## GCP resources reference

| Resource | Name | Notes |
|----------|------|-------|
| GCP project | `oute-488706` | |
| Cloud SQL | `oute-postgres` | Shared instance, `us-central1` |
| DB (prod) | `oute_muscle_prod` | User: `muscle_app` |
| Cloud Run (prod) | `muscle-prod-api` | Min 0 instances |
| Artifact Registry (prod) | `muscle-prod-docker` | |
| Terraform state bucket | `oute-terraform-state` | `gs://oute-terraform-state/oute-muscle/prod/` |
| WIF pool (prod) | `muscle-prod-gh-pool` | |
| GH Actions SA (prod) | `muscle-prod-gh-actions@oute-488706.iam.gserviceaccount.com` | |
