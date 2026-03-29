#!/usr/bin/env bash
# =============================================================================
# deploy-bootstrap.sh — One-shot bootstrap for Oute Muscle on GCP (prod only)
#
# Usage:
#   bash scripts/deploy-bootstrap.sh
#
# What it does:
#   1. Validates prerequisites (gcloud, terraform, gh)
#   2. Enables required GCP APIs
#   3. Creates the GCS bucket for Terraform state (idempotent)
#   4. Runs terraform init + apply for prod
#   5. Reads terraform outputs and sets GitHub Actions environment vars/secrets
#   6. Prints a smoke-test command for the deployed service
#
# Requirements:
#   - gcloud authenticated: `gcloud auth application-default login`
#   - gh authenticated: `gh auth login`
#   - terraform >= 1.8 installed
#   - Run from the repo root
#
# Gitflow: Trunk-Based CD — single environment (prod).
#   PR → CI → merge main → auto-deploy prod
# =============================================================================

set -euo pipefail

# ─── Colours ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
info()    { echo -e "${CYAN}[INFO]${NC} $*"; }
success() { echo -e "${GREEN}[OK]${NC}   $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC} $*"; }
error()   { echo -e "${RED}[ERR]${NC}  $*" >&2; exit 1; }

# ─── Project constants ────────────────────────────────────────────────────────
ENV="prod"
PROJECT_ID="oute-488706"
REGION="us-central1"
GITHUB_ORG="renatobardi"
GITHUB_REPO="oute-muscle"
STATE_BUCKET="oute-terraform-state"
STATE_PREFIX="oute-muscle/prod"
DB_USER="muscle_app"
DB_NAME="oute_muscle_prod"
SHARED_SQL_INSTANCE="oute-postgres"
INFRA_DIR="infra/gcp"
PLACEHOLDER_IMAGE="us-docker.pkg.dev/cloudrun/container/hello"   # replaced on first CI deploy

echo ""
echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}  Oute Muscle — Bootstrap: ${YELLOW}prod${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
echo ""

# ─── Step 0: Prerequisites ────────────────────────────────────────────────────
info "Checking prerequisites..."

for cmd in gcloud terraform gh; do
  command -v "$cmd" >/dev/null 2>&1 || error "'$cmd' not found. Please install it before running this script."
done

TF_VERSION=$(terraform version -json | python3 -c "import sys,json; print(json.load(sys.stdin)['terraform_version'])")
info "terraform ${TF_VERSION} ✓"

GCLOUD_ACCOUNT=$(gcloud config get-value account 2>/dev/null)
[[ -n "$GCLOUD_ACCOUNT" ]] || error "gcloud not authenticated. Run: gcloud auth application-default login"
info "gcloud authenticated as ${GCLOUD_ACCOUNT} ✓"

GH_STATUS=$(gh auth status 2>&1 || true)
echo "$GH_STATUS" | grep -q "Logged in" || error "gh not authenticated. Run: gh auth login"
info "gh authenticated ✓"

success "Prerequisites OK"
echo ""

# ─── Step 1: Enable GCP APIs ──────────────────────────────────────────────────
info "Enabling required GCP APIs (this may take ~2 min on first run)..."

APIS=(
  "run.googleapis.com"
  "sqladmin.googleapis.com"
  "artifactregistry.googleapis.com"
  "secretmanager.googleapis.com"
  "aiplatform.googleapis.com"
  "cloudtrace.googleapis.com"
  "monitoring.googleapis.com"
  "iam.googleapis.com"
  "iamcredentials.googleapis.com"
  "sts.googleapis.com"
  "storage.googleapis.com"
)

gcloud services enable "${APIS[@]}" --project="${PROJECT_ID}" --quiet
success "APIs enabled"
echo ""

# ─── Step 2: Terraform state bucket ───────────────────────────────────────────
info "Ensuring Terraform state bucket: gs://${STATE_BUCKET}"

if gsutil ls -b "gs://${STATE_BUCKET}" >/dev/null 2>&1; then
  info "Bucket already exists, skipping creation"
else
  gsutil mb -p "${PROJECT_ID}" -l "${REGION}" -b on "gs://${STATE_BUCKET}"
  gsutil versioning set on "gs://${STATE_BUCKET}"
  success "Bucket created: gs://${STATE_BUCKET}"
fi

echo ""

# ─── Step 3: Terraform init ───────────────────────────────────────────────────
info "Running terraform init (backend: gs://${STATE_BUCKET}/${STATE_PREFIX})..."

cd "${INFRA_DIR}"

terraform init \
  -backend-config="bucket=${STATE_BUCKET}" \
  -backend-config="prefix=${STATE_PREFIX}" \
  -reconfigure \
  -input=false

success "terraform init OK"
echo ""

# ─── Step 4: Terraform plan ───────────────────────────────────────────────────
info "Running terraform plan..."

terraform plan \
  -var="project_id=${PROJECT_ID}" \
  -var="region=${REGION}" \
  -var="environment=${ENV}" \
  -var="github_org=${GITHUB_ORG}" \
  -var="github_repo=${GITHUB_REPO}" \
  -var="api_image=${PLACEHOLDER_IMAGE}" \
  -var="existing_cloud_sql_instance=${SHARED_SQL_INSTANCE}" \
  -var="db_name=${DB_NAME}" \
  -var="db_user=${DB_USER}" \
  -var="cloud_run_min_instances=0" \
  -out=tfplan \
  -input=false

echo ""
echo -e "${YELLOW}Review the plan above.${NC}"
read -r -p "Apply? [y/N] " CONFIRM
[[ "$CONFIRM" =~ ^[Yy]$ ]] || { warn "Aborted."; exit 0; }

# ─── Step 5: Terraform apply ──────────────────────────────────────────────────
info "Running terraform apply..."
terraform apply -input=false tfplan
rm -f tfplan

success "terraform apply complete"
echo ""

# ─── Step 6: Capture outputs ──────────────────────────────────────────────────
info "Reading terraform outputs..."

WIF_PROVIDER=$(terraform output -raw workload_identity_provider)
GH_ACTIONS_SA=$(terraform output -raw github_actions_service_account)
API_URL=$(terraform output -raw api_url)
AR_URL=$(terraform output -raw artifact_registry_url)
CLOUD_SQL_CONN=$(terraform output -raw cloud_sql_connection_name)

# DB password from Secret Manager (terraform put it there)
SECRET_NAME="muscle-prod-db-password"
DB_PASSWORD=$(gcloud secrets versions access latest \
  --secret="${SECRET_NAME}" \
  --project="${PROJECT_ID}" 2>/dev/null || echo "")

cd - >/dev/null

echo ""

# ─── Step 7: Set GitHub Actions environment vars ──────────────────────────────
info "Setting GitHub Actions environment: production..."

GH_REPO="${GITHUB_ORG}/${GITHUB_REPO}"

# Create environment if it doesn't exist
gh api "repos/${GH_REPO}/environments/production" \
  --method PUT \
  --field wait_timer=0 \
  --silent 2>/dev/null || true

# Variables (plain text)
set_var() {
  gh variable set "$1" --env "production" --repo "${GH_REPO}" --body "$2"
  info "  var: $1 ✓"
}

set_var "WIF_PROVIDER"       "${WIF_PROVIDER}"
set_var "GH_ACTIONS_SA"      "${GH_ACTIONS_SA}"
set_var "REGION"             "${REGION}"
set_var "PROJECT_ID"         "${PROJECT_ID}"
set_var "CLOUD_SQL_INSTANCE" "${CLOUD_SQL_CONN}"
set_var "DB_USER"            "${DB_USER}"
set_var "DB_NAME"            "${DB_NAME}"

# Secret (DB password)
if [[ -n "$DB_PASSWORD" ]]; then
  gh secret set "DB_PASSWORD" \
    --env "production" \
    --repo "${GH_REPO}" \
    --body "${DB_PASSWORD}"
  info "  secret: DB_PASSWORD ✓"
else
  warn "Could not read DB_PASSWORD from Secret Manager — set it manually:"
  warn "  gh secret set DB_PASSWORD --env production --repo ${GH_REPO}"
fi

success "GitHub Actions environment 'production' configured"
echo ""

# ─── Done ─────────────────────────────────────────────────────────────────────
echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  Bootstrap complete: prod${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
echo ""
echo -e "  ${CYAN}API URL:${NC}            ${API_URL}"
echo -e "  ${CYAN}Artifact Registry:${NC}  ${AR_URL}"
echo -e "  ${CYAN}Cloud SQL:${NC}          ${CLOUD_SQL_CONN}"
echo ""
echo -e "  ${YELLOW}Next steps:${NC}"
echo -e "  1. Merge a PR to main — CI/CD deploys to prod automatically"
echo -e ""
echo -e "  2. Smoke test after deploy:"
echo -e "     ${CYAN}curl ${API_URL}/health/ready${NC}"
echo ""
