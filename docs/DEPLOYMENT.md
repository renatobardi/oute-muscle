# Deployment Runbook

## Environments

| Environment | URL | Trigger |
|-------------|-----|---------|
| Staging | https://oute-staging-api-ujzimacvza-uc.a.run.app | Push to `main` |
| Prod | https://oute-prod-api-ujzimacvza-uc.a.run.app | Git tag `v*.*.*` |

## Normal deploy flow

### Staging (automatic)

Every push to `main` triggers a staging deploy via `.github/workflows/deploy.yml`. No action needed.

Monitor at: https://github.com/renatobardi/oute-muscle/actions/workflows/deploy.yml

### Prod release

```bash
# 1. Make sure main is green and you're on main
git checkout main && git pull

# 2. Tag the release (semver)
git tag v0.2.0
git push origin v0.2.0

# 3. Watch the deploy
gh run list --workflow=deploy.yml --limit 5
gh run watch <run-id>

# 4. Smoke test
curl https://oute-prod-api-ujzimacvza-uc.a.run.app/health/live
```

## First-time environment bootstrap

Run once per environment to provision all GCP resources and configure GitHub Actions.

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
# Staging
bash scripts/deploy-bootstrap.sh staging

# Prod
bash scripts/deploy-bootstrap.sh prod
```

The script will:
1. Enable required GCP APIs
2. Create the GCS Terraform state bucket (idempotent)
3. Run `terraform init && terraform apply`
4. Set all GitHub Actions environment variables and secrets

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
bash scripts/deploy-bootstrap.sh prod
```

**`Permission denied on secret` (Cloud Run)**

IAM propagation lag (~60s). Wait a minute and re-run the bootstrap.

**`workload_identity_provider` not set**

The GitHub Actions environment vars weren't configured. Bootstrap again to set them:

```bash
bash scripts/deploy-bootstrap.sh prod
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
  -var="api_image=$(gcloud run services describe oute-prod-api --region=us-central1 --format='value(spec.template.spec.containers[0].image)')" \
  -var="existing_cloud_sql_instance=oute-postgres"

# Apply
terraform apply [same vars]
```

## Rollback

### Cloud Run revision rollback

```bash
# List recent revisions
gcloud run revisions list --service=oute-prod-api --region=us-central1

# Roll back to a specific revision
gcloud run services update-traffic oute-prod-api \
  --region=us-central1 \
  --to-revisions=oute-prod-api-00003-xyz=100
```

### Database migration rollback

```bash
make migrate-down   # rollback one migration
# Repeat if needed
```

Then redeploy the previous image version.

## Monitoring

```bash
# Cloud Run logs (prod)
gcloud logging read \
  'resource.type="cloud_run_revision" resource.labels.service_name="oute-prod-api"' \
  --limit=50 --format=json | jq '.[].jsonPayload'

# Cloud Run logs (staging)
gcloud logging read \
  'resource.type="cloud_run_revision" resource.labels.service_name="oute-staging-api"' \
  --limit=50

# Health endpoints
curl https://oute-prod-api-ujzimacvza-uc.a.run.app/health/live
curl https://oute-prod-api-ujzimacvza-uc.a.run.app/health/ready
curl https://oute-prod-api-ujzimacvza-uc.a.run.app/health/startup
```

## GCP resources reference

| Resource | Name | Notes |
|----------|------|-------|
| GCP project | `oute-488706` | |
| Cloud SQL | `oute-postgres` | Shared instance, `us-central1` |
| DB (staging) | `oute_muscle_staging` | User: `muscle_app` |
| DB (prod) | `oute_muscle_prod` | User: `muscle_app` |
| Cloud Run (staging) | `oute-staging-api` | Min 0 instances |
| Cloud Run (prod) | `oute-prod-api` | Min 1 instance |
| Artifact Registry (staging) | `oute-staging-docker` | |
| Artifact Registry (prod) | `oute-prod-docker` | |
| Terraform state bucket | `oute-terraform-state` | `gs://` |
| WIF pool (staging) | `oute-staging-gh-pool` | |
| WIF pool (prod) | `oute-prod-gh-pool` | |
| GH Actions SA (staging) | `oute-staging-gh-actions@oute-488706.iam.gserviceaccount.com` | |
| GH Actions SA (prod) | `oute-prod-gh-actions@oute-488706.iam.gserviceaccount.com` | |
