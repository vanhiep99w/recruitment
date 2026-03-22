#!/usr/bin/env bash
# destroy-infra.sh — Terraform destroy + GitHub Secrets cleanup + infraState reset
# Usage: ./destroy-infra.sh <feature-slug> <ec2-host> <fqdn>
# Environment: uses CLOUDFLARE_API_TOKEN (from env or ~/.cloudflare), AWS credentials

set -euo pipefail

FEATURE_SLUG="${1:?Usage: $0 <feature-slug> <ec2-host> <fqdn>}"
EC2_HOST="${2:?}"
FQDN="${3:?}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"

# Terraform expects CLOUDFLARE_API_TOKEN in the environment. Fall back to ~/.cloudflare
# so the destroy path matches the credential precheck behavior.
if [ -z "${CLOUDFLARE_API_TOKEN:-}" ] && [ -f "$HOME/.cloudflare" ]; then
  # shellcheck source=/dev/null
  source "$HOME/.cloudflare"
fi

STATE_FILE="$REPO_ROOT/docs/c4flow/.state.json"
TF_DIR=$(jq -r '.infraState.tfDir // empty' "$STATE_FILE")
if [ -n "$TF_DIR" ] && [[ "$TF_DIR" != /* ]]; then
  TF_DIR="$REPO_ROOT/$TF_DIR"
fi

# ── Terraform destroy ─────────────────────────────────────────────────────────
if [ -d "$TF_DIR" ] && [ -f "$TF_DIR/terraform.tfstate" ]; then
  cd "$TF_DIR"
  echo "=== terraform destroy ==="
  if ! terraform destroy -input=false -auto-approve; then
    echo "WARNING: terraform destroy had errors — some resources may remain."
    read -p "Continue with cleanup anyway? [y/N] " CONTINUE
    if [ "$CONTINUE" != "y" ] && [ "$CONTINUE" != "Y" ]; then
      echo "Stopped. Fix terraform issues and re-run /c4flow:infra-destroy."
      exit 1
    fi
  else
    echo "Terraform destroy complete."
  fi
elif [ -d "$TF_DIR" ]; then
  echo "WARNING: Terraform state file missing — skipping terraform destroy."
  echo "Resources may have been manually removed or state was lost."
else
  echo "WARNING: Terraform directory not found — skipping terraform destroy."
fi

# ── Remove GitHub Secrets ──────────────────────────────────────────────────────
if gh auth status > /dev/null 2>&1; then
  echo "Removing GitHub Secrets..."
  for SECRET in AWS_EC2_HOST AWS_REGION EC2_SSH_PRIVATE_KEY DEPLOY_DOMAIN; do
    if gh secret delete "$SECRET" 2>/dev/null; then
      echo "  ✓ Removed $SECRET"
    else
      echo "  - $SECRET not found (already removed or never set)"
    fi
  done
else
  echo "WARNING: gh CLI not authenticated — GitHub Secrets not removed."
  echo "Remove manually: GitHub → Settings → Secrets and variables → Actions:"
  echo "  - AWS_EC2_HOST"
  echo "  - AWS_REGION"
  echo "  - EC2_SSH_PRIVATE_KEY"
  echo "  - DEPLOY_DOMAIN"
fi

# ── Delete Terraform state files ───────────────────────────────────────────────
if [ -d "$TF_DIR" ]; then
  echo "Removing Terraform state files..."
  rm -f "$TF_DIR/terraform.tfstate"
  rm -f "$TF_DIR/terraform.tfstate.backup"
  rm -f "$TF_DIR/tfplan"
  rm -f "$TF_DIR/tfplan.out"
  rm -rf "$TF_DIR/.terraform"
  echo "  ✓ State files deleted (Terraform source files preserved in $TF_DIR)"
fi

# ── Clear infraState from .state.json ─────────────────────────────────────────
CLEARED_AT=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
jq \
  --arg clearedAt "$CLEARED_AT" \
  'del(.infraState) | .infraConfig.destroyedAt = $clearedAt' \
  "$STATE_FILE" > "${STATE_FILE}.tmp" \
  && mv -f "${STATE_FILE}.tmp" "$STATE_FILE"

echo ""
echo "=== Infrastructure Destroyed ==="
echo "  Feature:   $FEATURE_SLUG"
echo "  Host:      $EC2_HOST (no longer accessible)"
echo "  Domain:    https://$FQDN (DNS record removed)"
echo "  Destroyed: $CLEARED_AT"
echo ""
echo "infraState cleared from .state.json."
echo ""
echo "To provision fresh infrastructure, run /c4flow:infra"
