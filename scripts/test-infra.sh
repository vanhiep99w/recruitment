#!/usr/bin/env bash
# Structural validation tests for Docker Compose & CI Setup
# TDD Phase 1: RED — all checks should FAIL before files exist

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PASS=0
FAIL=0
ERRORS=()

pass() {
    echo "  [PASS] $1"
    PASS=$((PASS + 1))
}

fail() {
    echo "  [FAIL] $1"
    ERRORS+=("$1")
    FAIL=$((FAIL + 1))
}

check_file_exists() {
    local file="$1"
    if [[ -f "$REPO_ROOT/$file" ]]; then
        pass "File exists: $file"
    else
        fail "Missing file: $file"
    fi
}

check_file_executable() {
    local file="$1"
    if [[ -x "$REPO_ROOT/$file" ]]; then
        pass "File is executable: $file"
    else
        fail "File not executable: $file"
    fi
}

check_file_contains() {
    local file="$1"
    local pattern="$2"
    local description="${3:-$pattern}"
    if [[ -f "$REPO_ROOT/$file" ]] && grep -qF -- "$pattern" "$REPO_ROOT/$file" 2>/dev/null; then
        pass "$file contains: $description"
    else
        fail "$file missing: $description"
    fi
}

check_file_contains_regex() {
    local file="$1"
    local pattern="$2"
    local description="${3:-$pattern}"
    if [[ -f "$REPO_ROOT/$file" ]] && grep -qE "$pattern" "$REPO_ROOT/$file" 2>/dev/null; then
        pass "$file contains regex: $description"
    else
        fail "$file missing pattern: $description"
    fi
}

echo "======================================"
echo " Infrastructure Validation Test Suite"
echo "======================================"
echo ""

# ---- Check 1: Required files exist ----
echo "[1] Checking required files exist..."
check_file_exists "docker-compose.yml"
check_file_exists "backend/Dockerfile"
check_file_exists "frontend/Dockerfile"
check_file_exists "nginx/nginx.conf"
check_file_exists "scripts/init-db.sql"
check_file_exists "scripts/wait-for.sh"
check_file_exists ".github/workflows/ci.yml"
check_file_exists ".github/workflows/deploy.yml"
check_file_exists ".env.example"
echo ""

# ---- Check 2: docker-compose.yml syntax & required services ----
echo "[2] Validating docker-compose.yml..."
if [[ -f "$REPO_ROOT/docker-compose.yml" ]]; then
    # Create a temporary .env from .env.example for syntax validation only
    _env_created=false
    if [[ ! -f "$REPO_ROOT/.env" ]] && [[ -f "$REPO_ROOT/.env.example" ]]; then
        REDIS_PASSWORD=changeme POSTGRES_PASSWORD=changeme \
          envsubst < "$REPO_ROOT/.env.example" > "$REPO_ROOT/.env" 2>/dev/null || \
          cp "$REPO_ROOT/.env.example" "$REPO_ROOT/.env"
        _env_created=true
    fi
    if docker compose -f "$REPO_ROOT/docker-compose.yml" config --quiet 2>/dev/null; then
        pass "docker-compose.yml syntax is valid"
    else
        fail "docker-compose.yml syntax error (docker compose config failed)"
    fi
    if [[ "$_env_created" == true ]]; then
        rm -f "$REPO_ROOT/.env"
    fi
    for service in postgres redis backend frontend arq-worker nginx; do
        check_file_contains "docker-compose.yml" "$service" "service: $service"
    done
    check_file_contains "docker-compose.yml" "pgvector/pgvector:pg16" "postgres image pgvector/pgvector:pg16"
    check_file_contains "docker-compose.yml" "POSTGRES_INITDB_ARGS" "POSTGRES_INITDB_ARGS for UTF8 encoding"
    check_file_contains "docker-compose.yml" "--encoding=UTF8" "UTF8 encoding arg"
else
    fail "docker-compose.yml does not exist — skipping service checks"
fi
echo ""

# ---- Check 3: nginx/nginx.conf required directives ----
echo "[3] Validating nginx/nginx.conf..."
check_file_contains "nginx/nginx.conf" "listen 80" "listen on port 80"
check_file_contains "nginx/nginx.conf" "listen 443" "listen on port 443"
check_file_contains "nginx/nginx.conf" "proxy_pass" "proxy_pass directive"
check_file_contains_regex "nginx/nginx.conf" "backend:?8000|localhost:8000" "proxy to backend:8000"
check_file_contains_regex "nginx/nginx.conf" "frontend:?3000|localhost:3000" "proxy to frontend:3000"
check_file_contains_regex "nginx/nginx.conf" "/api" "route /api to backend"
echo ""

# ---- Check 4: .github/workflows/ci.yml is valid YAML ----
echo "[4] Validating .github/workflows/ci.yml..."
if [[ -f "$REPO_ROOT/.github/workflows/ci.yml" ]]; then
    if command -v python3 &>/dev/null; then
        if python3 -c "import yaml; yaml.safe_load(open('$REPO_ROOT/.github/workflows/ci.yml'))" 2>/dev/null; then
            pass ".github/workflows/ci.yml is valid YAML"
        else
            fail ".github/workflows/ci.yml is not valid YAML"
        fi
    else
        pass ".github/workflows/ci.yml exists (python3 not available for YAML check)"
    fi
    check_file_contains ".github/workflows/ci.yml" "pytest" "CI runs pytest"
    check_file_contains ".github/workflows/ci.yml" "playwright" "CI runs playwright"
    check_file_contains ".github/workflows/ci.yml" "on:" "CI trigger defined"
    check_file_contains_regex ".github/workflows/ci.yml" "push|pull_request" "CI triggers on push or PR"
else
    fail ".github/workflows/ci.yml does not exist — skipping YAML checks"
fi
echo ""

# ---- Check 4b: .github/workflows/deploy.yml is valid YAML ----
echo "[4b] Validating .github/workflows/deploy.yml..."
if [[ -f "$REPO_ROOT/.github/workflows/deploy.yml" ]]; then
    if command -v python3 &>/dev/null; then
        if python3 -c "import yaml; yaml.safe_load(open('$REPO_ROOT/.github/workflows/deploy.yml'))" 2>/dev/null; then
            pass ".github/workflows/deploy.yml is valid YAML"
        else
            fail ".github/workflows/deploy.yml is not valid YAML"
        fi
    else
        pass ".github/workflows/deploy.yml exists (python3 not available for YAML check)"
    fi
    check_file_contains ".github/workflows/deploy.yml" "EC2_SSH_PRIVATE_KEY" "deploy uses EC2_SSH_PRIVATE_KEY secret"
    check_file_contains ".github/workflows/deploy.yml" "AWS_EC2_HOST" "deploy uses AWS_EC2_HOST secret"
    check_file_contains ".github/workflows/deploy.yml" "DEPLOY_DOMAIN" "deploy uses DEPLOY_DOMAIN secret"
    check_file_contains ".github/workflows/deploy.yml" "git pull origin main" "deploy pulls latest code"
    check_file_contains ".github/workflows/deploy.yml" "docker compose build --pull" "deploy rebuilds containers with fresh base images"
    check_file_contains_regex ".github/workflows/deploy.yml" "curl.*health|health.*curl" "deploy health check"
else
    fail ".github/workflows/deploy.yml does not exist — skipping checks"
fi
echo ""

# ---- Check 5: scripts/init-db.sql correctness ----
echo "[5] Validating scripts/init-db.sql..."
check_file_contains "scripts/init-db.sql" "CREATE EXTENSION" "CREATE EXTENSION directive"
check_file_contains "scripts/init-db.sql" "vector(1536)" "vector(1536) embedding column"
for table in organizations users candidates candidate_profiles cvs jobs jd_profiles matches talent_pools pipeline_stages; do
    check_file_contains "scripts/init-db.sql" "$table" "table: $table"
done
check_file_contains_regex "scripts/init-db.sql" "IVFFlat|HNSW|ivfflat|hnsw" "pgvector index (IVFFlat or HNSW)"
check_file_contains_regex "scripts/init-db.sql" "full.text|to_tsvector|GIN|gin" "full-text search index"
echo ""

# ---- Check 6: scripts/wait-for.sh is executable and has wait logic ----
echo "[6] Validating scripts/wait-for.sh..."
check_file_executable "scripts/wait-for.sh"
check_file_contains_regex "scripts/wait-for.sh" "while|until|sleep|pg_isready|redis-cli|nc " "wait/loop logic"
check_file_contains_regex "scripts/wait-for.sh" "postgres|POSTGRES|pg_isready" "waits for postgres"
check_file_contains_regex "scripts/wait-for.sh" "redis|REDIS" "waits for redis"
echo ""

# ---- Check 7: backend/Dockerfile has required components ----
echo "[7] Validating backend/Dockerfile..."
check_file_contains "backend/Dockerfile" "python:3.12" "Python 3.12 base image"
check_file_contains "backend/Dockerfile" "tesseract-ocr" "Tesseract OCR installed"
check_file_contains "backend/Dockerfile" "tesseract-ocr-vie" "Vietnamese tessdata installed"
check_file_contains "backend/Dockerfile" "poetry" "Poetry installed"
echo ""

# ---- Check 8: frontend/Dockerfile has required components ----
echo "[8] Validating frontend/Dockerfile..."
check_file_contains_regex "frontend/Dockerfile" "node:20|node:20-" "Node 20 base image"
check_file_contains_regex "frontend/Dockerfile" "standalone|output.*standalone" "standalone output mode"
echo ""

# ---- Summary ----
echo "======================================"
echo " Results: $PASS passed, $FAIL failed"
echo "======================================"
if [[ ${#ERRORS[@]} -gt 0 ]]; then
    echo ""
    echo "Failed checks:"
    for err in "${ERRORS[@]}"; do
        echo "  - $err"
    done
    echo ""
    exit 1
fi

echo ""
echo "All checks passed!"
exit 0
