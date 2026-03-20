---
name: c4flow:pr
description: Create a pull request with spec summary, task list from beads epic, and test/review results. Use when the user wants to create a PR, open a pull request, or submit code for merge. Triggers on "create PR", "open pull request", "submit for review", or after verify passes.
---

# /c4flow:pr — Create Pull Request

**Phase**: 6: Release
**Agent type**: Main agent (interactive with user)
**Status**: Implemented

## Overview

This skill creates a GitHub PR via the `gh` CLI, embeds a quality gate status summary table in the PR body so reviewers immediately see gate status, and writes the PR number to `docs/c4flow/.state.json` atomically. It warns (but does not block) when gates have not all passed.

**Key behaviors:**
- Gate failure triggers a **warn + confirm**, never a hard block
- Idempotency: detects existing PR and skips creation
- Atomic `.state.json` write: merge (not overwrite) — all other fields preserved
- PR body uses `--body-file` to avoid shell escaping issues

---

## Instructions

You are the `c4flow:pr` agent. Execute the following steps in order.

---

### Step 1: Tool Availability Detection

Check for the `gh` CLI before doing anything else:

```bash
command -v gh
```

**If `gh` is missing:**

Print the manual PR checklist and exit gracefully (exit 0, not exit 1):

```
WARNING: GitHub CLI (gh) not found.
Install from: https://cli.github.com

MANUAL PR CHECKLIST (gh fallback):
[ ] Push branch: git push -u origin <branch>
[ ] Open: https://github.com/<owner>/<repo>/compare/<branch>
[ ] Include quality gate summary from quality-gate-status.json in PR body manually
[ ] After creating PR, update docs/c4flow/.state.json prNumber field manually:
    jq '.prNumber = <number> | .currentState = "PR_REVIEW_LOOP" | .completedStates += ["PR"]' \
      docs/c4flow/.state.json > docs/c4flow/.state.json.tmp && \
      mv docs/c4flow/.state.json.tmp docs/c4flow/.state.json
```

Exit gracefully — do not proceed to further steps.

**If `gh` is available**, check authentication:

```bash
gh auth status
```

**If not authenticated:**

```
WARNING: gh CLI is not authenticated. Run: gh auth login
```

Exit with code 1.

**If authenticated:** Proceed to Step 2.

---

### Step 2: Read Gate Status and Warn if Not Passed

Read `quality-gate-status.json` at the project root:

```bash
GATE_FILE_EXISTS=false
OVERALL_PASS="missing"

if [ -f quality-gate-status.json ]; then
  GATE_FILE_EXISTS=true
  OVERALL_PASS=$(jq -r '.overall_pass' quality-gate-status.json 2>/dev/null || echo "parse_error")
fi
```

**If the file is missing or `overall_pass` is not `true`:**

Print a WARNING with current status:

```
WARNING: Quality gates have not all passed.
  overall_pass: $OVERALL_PASS
  Run /c4flow:review and /c4flow:verify to see current gate status.

Creating a PR before gates pass is allowed but not recommended.
The hard enforcement gate is at 'bd close', not at PR creation.
```

Ask the user: **"Proceed anyway? (yes/no)"**

- If user says **no**: exit 0.
- If user says **yes**: continue to Step 3.

**CRITICAL:** Never exit 1 solely because gates failed. Always offer the user a choice.

**If `overall_pass` is `true`:** Proceed to Step 3 silently.

---

### Step 3: Build PR Body

Construct the PR body markdown by reading fields from `quality-gate-status.json`.

```bash
BODY_FILE=$(mktemp /tmp/c4flow-pr-body.XXXXX.md)
```

**If `quality-gate-status.json` exists**, extract fields and build the table:

```bash
# Extract gate status fields
CODEX_PASS=$(jq -r 'if .checks.codex_review.pass == true then "PASS" elif .checks.codex_review.pass == false then "FAIL" else "NOT RUN" end' quality-gate-status.json 2>/dev/null || echo "NO STATUS FILE")
CODEX_DETAIL=$(jq -r '"\(.checks.codex_review.critical_count // 0) critical, \(.checks.codex_review.high_count // 0) high, \(.checks.codex_review.medium_count // 0) medium, \(.checks.codex_review.low_count // 0) low"' quality-gate-status.json 2>/dev/null || echo "—")
CODEX_RAN=$(jq -r '.checks.codex_review.ran_at // "—"' quality-gate-status.json 2>/dev/null || echo "—")

BD_PASS=$(jq -r 'if .checks.bd_preflight.pass == true then "PASS" elif .checks.bd_preflight.pass == false then "FAIL" else "NOT RUN" end' quality-gate-status.json 2>/dev/null || echo "NO STATUS FILE")
BD_ISSUES=$(jq -r '(.checks.bd_preflight.issues | length | tostring) + " issues"' quality-gate-status.json 2>/dev/null || echo "—")
BD_RAN=$(jq -r '.checks.bd_preflight.ran_at // "—"' quality-gate-status.json 2>/dev/null || echo "—")

OVERALL_STATUS=$(jq -r 'if .overall_pass then "Ready for PR" else "PR created before all gates passed" end' quality-gate-status.json 2>/dev/null || echo "No gate status file")
GATE_ID=$(jq -r '.gate_id // "none"' quality-gate-status.json 2>/dev/null || echo "none")
GENERATED_AT=$(jq -r '.generated_at // "unknown"' quality-gate-status.json 2>/dev/null || echo "unknown")
EXPIRES_AT=$(jq -r '.expires_at // "unknown"' quality-gate-status.json 2>/dev/null || echo "unknown")

# Write the PR body to temp file using printf to avoid heredoc escaping issues
printf '## Quality Gate Status\n\n' > "$BODY_FILE"
printf '| Check | Status | Details | Ran At |\n' >> "$BODY_FILE"
printf '|-------|--------|---------|--------|\n' >> "$BODY_FILE"
printf '| Codex Review | %s | %s | %s |\n' "$CODEX_PASS" "$CODEX_DETAIL" "$CODEX_RAN" >> "$BODY_FILE"
printf '| bd Preflight | %s | %s | %s |\n' "$BD_PASS" "$BD_ISSUES" "$BD_RAN" >> "$BODY_FILE"
printf '\n**Overall: %s**\n\n' "$OVERALL_STATUS" >> "$BODY_FILE"
printf 'Gate ID: %s\n' "$GATE_ID" >> "$BODY_FILE"
printf 'Status file generated: %s (expires: %s)\n' "$GENERATED_AT" "$EXPIRES_AT" >> "$BODY_FILE"
```

**If `quality-gate-status.json` is missing**, use a fallback body:

```bash
printf '## Quality Gate Status\n\nNo status available. Run /c4flow:review and /c4flow:verify first.\n' > "$BODY_FILE"
```

---

### Step 4: Determine PR Title

Read `docs/c4flow/.state.json` for `feature.name`:

```bash
STATE_FILE="docs/c4flow/.state.json"
FEATURE_NAME=""

if [ -f "$STATE_FILE" ]; then
  FEATURE_NAME=$(jq -r '.feature.name // empty' "$STATE_FILE" 2>/dev/null || echo "")
fi
```

Set the proposed title:

```bash
if [ -n "$FEATURE_NAME" ]; then
  PR_TITLE="feat: $FEATURE_NAME"
else
  BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown-branch")
  PR_TITLE=$(echo "$BRANCH" | sed 's|^feature/||; s|-| |g; s|_| |g')
fi
```

Print the proposed title and let the user confirm or customize:

```
Proposed PR title: $PR_TITLE

Press Enter to accept, or type a new title:
```

Read user input — if non-empty, use it as `PR_TITLE`.

---

### Step 5: Check for Existing PR

Check if a PR already exists for the current branch before creating one:

```bash
EXISTING_PR_NUMBER=$(gh pr view --json number --jq '.number' 2>/dev/null || echo "")
```

**If an existing PR is found** (non-empty, non-null value):

```bash
EXISTING_PR_URL=$(gh pr view --json url --jq '.url' 2>/dev/null || echo "")
echo "PR #$EXISTING_PR_NUMBER already exists for this branch."
echo "URL: $EXISTING_PR_URL"
```

Update `.state.json` if `prNumber` is currently null:

```bash
CURRENT_PR_NUM=$(jq -r '.prNumber // empty' "$STATE_FILE" 2>/dev/null || echo "")
if [ -z "$CURRENT_PR_NUM" ] && [ -f "$STATE_FILE" ]; then
  jq --argjson num "$EXISTING_PR_NUMBER" \
    '.prNumber = $num | .currentState = "PR_REVIEW_LOOP" | .completedStates += ["PR"] | .failedAttempts = 0 | .lastError = null' \
    "$STATE_FILE" > "${STATE_FILE}.tmp" && mv "${STATE_FILE}.tmp" "$STATE_FILE"
  echo "Updated .state.json with existing PR number."
fi
```

Clean up temp body file and exit 0. Do NOT create a duplicate PR.

**If no existing PR:** Proceed to Step 6.

---

### Step 6: Push Branch if Not Pushed

Check whether the current branch has a remote tracking branch:

```bash
BRANCH=$(git rev-parse --abbrev-ref HEAD)
REMOTE_EXISTS=$(git ls-remote --heads origin "$BRANCH" 2>/dev/null | wc -l)

if [ "$REMOTE_EXISTS" -eq 0 ]; then
  echo "Branch '$BRANCH' has no remote tracking branch. Pushing now..."
  git push -u origin "$BRANCH"
fi
```

---

### Step 7: Create PR

Create the PR using the temp body file:

```bash
PR_URL=$(gh pr create \
  --title "$PR_TITLE" \
  --body-file "$BODY_FILE" \
  --base main)

echo "PR created: $PR_URL"
```

Extract the PR number from the URL:

```bash
PR_NUMBER=$(echo "$PR_URL" | grep -o '[0-9]*$')
```

Clean up the temp body file:

```bash
rm -f "$BODY_FILE"
```

---

### Step 8: Write PR Number to .state.json

Use the atomic jq merge pattern — **never overwrite**, always merge to preserve existing fields:

```bash
STATE_FILE="docs/c4flow/.state.json"

if [ -f "$STATE_FILE" ]; then
  jq --argjson num "$PR_NUMBER" \
    '.prNumber = $num | .currentState = "PR_REVIEW_LOOP" | .completedStates += ["PR"] | .failedAttempts = 0 | .lastError = null' \
    "$STATE_FILE" > "${STATE_FILE}.tmp" && mv "${STATE_FILE}.tmp" "$STATE_FILE"
  echo "[STATE WRITE] prNumber=$PR_NUMBER currentState=PR_REVIEW_LOOP"
else
  echo "WARNING: docs/c4flow/.state.json not found. Creating minimal state with prNumber only."
  echo '{}' | jq --argjson num "$PR_NUMBER" '.prNumber = $num' \
    > "${STATE_FILE}.tmp" && mv "${STATE_FILE}.tmp" "$STATE_FILE"
fi
```

---

### Step 9: Summary Output

Print the final summary:

```
=== C4Flow PR Created ===

PR URL:    $PR_URL
PR Number: $PR_NUMBER
Gate Status: $OVERALL_STATUS

.state.json updated: prNumber=$PR_NUMBER, currentState=PR_REVIEW_LOOP

Next step: PR is open. Reviewers will see the gate summary.
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| (none — gh CLI handles auth) | — | — |

---

## Key Files

| File | Description |
|------|-------------|
| `quality-gate-status.json` | Read-only in this skill — provides gate data for PR body construction |
| `docs/c4flow/.state.json` | Updated with `prNumber` and `currentState=PR_REVIEW_LOOP` after PR creation |

---

## Implementation Notes

- **Warn, never block:** Gate failure triggers a warning and confirmation prompt. The hard gate is `bd close`, not PR creation.
- **Idempotency:** Step 5 checks for an existing PR before creating one. Running `c4flow:pr` twice is safe.
- **Atomic write:** All `.state.json` writes go through `.tmp` → `mv` to prevent partial-write corruption.
- **Merge, not overwrite:** The `jq` merge pattern preserves all existing `.state.json` fields (currentState, completedStates, feature, etc.).
- **Body file:** PR body written to a temp file and passed via `--body-file` to avoid shell escaping issues with special characters in gate findings.
- **PR number extraction:** `grep -o '[0-9]*$'` on the `gh pr create` URL output — stable format: `https://github.com/owner/repo/pull/N`.

---

## Beads-Driven PR Creation

Creates a well-structured pull request using data from the beads epic, quality gate status, and spec documents. The PR body includes a summary from the spec, a task checklist from beads, test results, and review status.

## Prerequisites

Before running this skill, the following must be true:
- `quality-gate-status.json` exists with `overall_pass: true`
- All tasks in the beads epic are closed
- Current branch has commits ahead of main

## Instructions

### Step 1: Verify Preconditions

```bash
# Check quality gate
GATE_PASS=$(jq -r '.overall_pass' quality-gate-status.json 2>/dev/null)
if [ "$GATE_PASS" != "true" ]; then
  echo "ERROR: Quality gate has not passed. Run /c4flow:verify first."
  exit 1
fi

# Check we're not on main
CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" = "main" ] || [ "$CURRENT_BRANCH" = "master" ]; then
  echo "ERROR: Cannot create PR from main/master. Create a feature branch first."
  exit 1
fi

# Check for commits ahead of main
COMMITS_AHEAD=$(git rev-list --count main..HEAD 2>/dev/null || echo 0)
if [ "$COMMITS_AHEAD" -eq 0 ]; then
  echo "ERROR: No commits ahead of main. Nothing to PR."
  exit 1
fi
```

### Step 2: Gather Context

Read the following to build the PR body:

```bash
# Read feature info from state
FEATURE_NAME=$(jq -r '.feature.name // empty' docs/c4flow/.state.json 2>/dev/null)
FEATURE_SLUG=$(jq -r '.feature.slug // empty' docs/c4flow/.state.json 2>/dev/null)
EPIC_ID=$(jq -r '.beadsEpic // empty' docs/c4flow/.state.json 2>/dev/null)
```

Read these files for context:
- `docs/specs/<feature-slug>/proposal.md` — one-line summary
- `docs/specs/<feature-slug>/spec.md` — requirements
- `quality-gate-status.json` — review and preflight results

Get the task list from beads:
```bash
bd dep tree "$EPIC_ID" 2>/dev/null
bd list --json 2>/dev/null | jq --arg epic "$EPIC_ID" '[.[] | select(.status == "closed")]'
```

Get review stats:
```bash
CODEX_CRITICAL=$(jq -r '.checks.codex_review.critical_count // 0' quality-gate-status.json)
CODEX_HIGH=$(jq -r '.checks.codex_review.high_count // 0' quality-gate-status.json)
CODEX_MEDIUM=$(jq -r '.checks.codex_review.medium_count // 0' quality-gate-status.json)
CODEX_LOW=$(jq -r '.checks.codex_review.low_count // 0' quality-gate-status.json)
```

### Step 3: Build PR Title and Body

**Title format**: Short, under 70 characters, describes the feature.

**Body template**:

```markdown
## Summary

<1-3 sentence summary from proposal.md>

**Spec**: `docs/specs/<feature-slug>/`

## Changes

<Bulleted list of key changes, derived from closed beads tasks>

## Task Checklist

<For each closed task in the epic, show as checked checkbox>
- [x] bd-xxxx: Task title
- [x] bd-yyyy: Task title
- [x] bd-zzzz: Task title

## Quality Gate

| Check | Status | Details |
|-------|--------|---------|
| Codex Review | PASS | C:0 H:0 M:{medium} L:{low} |
| bd Preflight | PASS | All checks passed |

## Test Plan

- [ ] Verify feature works as described in spec
- [ ] Check edge cases from acceptance criteria
- [ ] Confirm no regressions in existing functionality
```

### Step 4: Push and Create PR

```bash
# Ensure branch is pushed
git push -u origin "$CURRENT_BRANCH"

# Create PR
gh pr create \
  --title "<PR title>" \
  --body "$(cat <<'EOF'
<PR body from template above>

---
Generated by c4flow | Epic: <epic-id>
EOF
)"
```

### Step 5: Update State and Sync

After PR is created:

```bash
# Get PR number
PR_NUMBER=$(gh pr view --json number -q '.number')

# Update beads epic with PR link
bd comment "$EPIC_ID" "PR created: #$PR_NUMBER" 2>/dev/null

# Sync beads state
bd dolt push 2>/dev/null
```

Update `docs/c4flow/.state.json`:
- Set `prNumber` to the PR number
- Orchestrator handles state transition

### Step 6: Report

```
PR #<number> created: <URL>

Epic: <epic-id> (<task-count> tasks completed)
Branch: <branch-name> (<commits-ahead> commits)
Quality gate: PASSED

Next steps:
- Share the PR URL with reviewers
- When approved, merge with /c4flow:merge

REMINDER: When closing the epic with bd close, include --reason:
  bd close <epic-id> --reason "Shipped via PR #<number>"
```

## Implementation Notes

- **Always use `--json` with bd commands** for reliable parsing
- **Push before PR creation** to ensure remote branch exists
- **`bd dolt push` after updates** to sync task state with team
- **`bd close --reason` on the epic** when the PR is merged (handled by merge skill)
- **Discovered issues** that weren't addressed should be listed in the PR body as known limitations
