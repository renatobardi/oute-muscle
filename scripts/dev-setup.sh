#!/usr/bin/env bash
# dev-setup.sh — Initialize local development environment for Oute Muscle
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RESET='\033[0m'

info()    { echo -e "${BLUE}[INFO]${RESET} $*"; }
success() { echo -e "${GREEN}[OK]${RESET}   $*"; }
warn()    { echo -e "${YELLOW}[WARN]${RESET} $*"; }
error()   { echo -e "${RED}[ERROR]${RESET} $*" >&2; exit 1; }

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "${BLUE}  Oute Muscle — dev environment setup${RESET}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"

# ── Prerequisites check ────────────────────────────────────────────────────
info "Checking prerequisites..."

command -v uv     >/dev/null 2>&1 || error "uv not found. Install: https://docs.astral.sh/uv/getting-started/installation/"
command -v node   >/dev/null 2>&1 || error "Node.js not found. Install: https://nodejs.org/"
command -v npm    >/dev/null 2>&1 || error "npm not found. Install Node.js."
command -v git    >/dev/null 2>&1 || error "git not found."
command -v gcloud >/dev/null 2>&1 || warn "gcloud CLI not found — required for GCP features (Ph4+). Install: https://cloud.google.com/sdk/"
command -v semgrep>/dev/null 2>&1 || warn "semgrep not found — required for rule testing (Ph3+). Install: pip install semgrep"

success "Prerequisites OK"

# ── Python dependencies ────────────────────────────────────────────────────
info "Installing Python dependencies..."
uv sync --all-packages --extra dev
success "Python dependencies installed"

# ── Frontend dependencies ──────────────────────────────────────────────────
info "Installing frontend dependencies..."
(cd apps/web && npm install)
success "Frontend dependencies installed"

# ── GCP authentication (optional, needed for Ph4+) ────────────────────────
if command -v gcloud >/dev/null 2>&1; then
    info "Checking GCP authentication..."
    if ! gcloud auth application-default print-access-token >/dev/null 2>&1; then
        warn "GCP Application Default Credentials not set."
        warn "Run: gcloud auth application-default login"
        warn "(Required for Phase 4+ features — Vertex AI, Cloud SQL)"
    else
        success "GCP ADC configured"
    fi
fi

# ── pre-commit hooks ───────────────────────────────────────────────────────
if command -v pre-commit >/dev/null 2>&1 && [ -f .pre-commit-config.yaml ]; then
    info "Installing pre-commit hooks..."
    pre-commit install
    success "pre-commit hooks installed"
else
    warn "pre-commit not found or .pre-commit-config.yaml missing — skipping hook install (configured in Ph3)"
fi

# ── Summary ────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "${GREEN}  Setup complete!${RESET}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo ""
echo "  Commands:"
echo "    make dev          — Start FastAPI dev server"
echo "    make dev-web      — Start SvelteKit dev server"
echo "    make test         — Run all tests"
echo "    make lint         — Run all linters"
echo "    make type-check   — Run type checkers"
echo ""
