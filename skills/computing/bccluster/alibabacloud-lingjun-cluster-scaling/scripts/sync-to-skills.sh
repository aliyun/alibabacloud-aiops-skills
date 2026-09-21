#!/usr/bin/env bash
# Dependencies: bash >= 4, rsync (dev-time sync tooling only; runtime prerequisites are declared in SKILL.md "Prerequisites & Dependencies")
# Sync the current workspace content into the Qoder / QoderWork skill install directories.
# Usage:
#   bash scripts/sync-to-skills.sh                  # dry-run by default, lists the diff only
#   bash scripts/sync-to-skills.sh --apply          # real sync (incremental, keeps extra files)
#   bash scripts/sync-to-skills.sh --apply --mirror # mirror (deletes extra files in the target)
#   bash scripts/sync-to-skills.sh --target DIR     # add another target (repeatable)
set -euo pipefail

SRC="$(cd "$(dirname "$0")/.." && pwd)"

# Default targets: the standard Qoder and QoderWork install paths.
TARGETS=(
  "$HOME/.qoder/skills/alibabacloud-lingjun-cluster-scaling"
  "$HOME/.qoderwork/skills/alibabacloud-lingjun-cluster-scaling"
)

# Discover other install locations (2026-08-21: a missed path made the IDE load stale 06-23 code):
#   - ~/.agents/skills/NAME            generic agent install location
#   - ~/.real/users/*/.skills/UUID/    Qoder per-user/UUID skill storage (accepted only when its SKILL.md names this skill)
SKILL_NAME="alibabacloud-lingjun-cluster-scaling"
if [[ -d "$HOME/.agents/skills/$SKILL_NAME" ]]; then
  TARGETS+=("$HOME/.agents/skills/$SKILL_NAME")
fi
for cand in "$HOME"/.real/users/*/.skills/*/; do
  [[ -f "${cand}SKILL.md" ]] || continue
  if grep -q "$SKILL_NAME" "${cand}SKILL.md" 2>/dev/null; then
    TARGETS+=("${cand%/}")
  fi
done

# Ignored paths (kept aligned with the main .gitignore entries).
EXCLUDES=(
  --exclude=.git
  --exclude=.qoder
  --exclude=.qwen
  --exclude=.claude
  --exclude=.agents
  --exclude=.tmp-tests
  --exclude=.region.lock
  --exclude=.DS_Store
  --exclude=node_modules
  --exclude=__pycache__
  --exclude='*.pyc'
  --exclude='*.bak'
  --exclude='*.swp'
  --exclude='validation-result-*.json'
  --exclude=tests/reports
  --exclude=skills-lock.json
)

MODE="dry"
MIRROR=0
EXTRA_TARGETS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --apply)    MODE="apply"; shift ;;
    --dry-run)  MODE="dry"; shift ;;
    --mirror)   MIRROR=1; shift ;;
    --target)   EXTRA_TARGETS+=("$2"); shift 2 ;;
    -h|--help)  sed -n '2,9p' "$0"; exit 0 ;;
    *)          echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done

[[ ${#EXTRA_TARGETS[@]} -gt 0 ]] && TARGETS=("${EXTRA_TARGETS[@]}")

RSYNC_OPTS=(-a --human-readable --itemize-changes)
[[ "$MODE" == "dry" ]] && RSYNC_OPTS+=(--dry-run)
[[ "$MIRROR" == "1" ]] && RSYNC_OPTS+=(--delete)

printf 'source: %s\nmode: %s  mirror: %s\n\n' "$SRC" "$MODE" "$MIRROR"

any_diff=0
for dest in "${TARGETS[@]}"; do
  if [[ ! -d "$dest" ]]; then
    printf '⚠ skipped (directory does not exist): %s\n\n' "$dest"
    continue
  fi
  printf '===== → %s =====\n' "$dest"
  out=$(rsync "${RSYNC_OPTS[@]}" "${EXCLUDES[@]}" "$SRC/" "$dest/" 2>&1 || true)
  if [[ -n "$out" ]]; then
    printf '%s\n' "$out"
    any_diff=1
  else
    echo "  (no differences)"
  fi
  echo
done

if [[ "$MODE" == "dry" ]]; then
  if [[ "$any_diff" == "1" ]]; then
    echo "ℹ dry-run found differences; to sync for real: bash $0 --apply"
  else
    echo "✅ dry-run complete: every target already matches the source, nothing to sync"
  fi
  exit 0
fi

# Pre-apply gate (2026-08-23): the hermetic regression suite must be green before any sync; red is
# rejected. This turns the tests from optional into mandatory and stops the whack-a-mole loop.
echo "===== pre-apply gate: tests/16-utterance-parser (hermetic) ====="
gate_out="$(cd "$SRC" && REGION=me-east-1 TEST_REGION=me-east-1 bash tests/16-utterance-parser.sh 2>&1)"
printf '%s\n' "$gate_out" | grep -E '\[(PASS|FAIL|SKIP) \]|Summary' || true
if printf '%s\n' "$gate_out" | grep -q '\[FAIL'; then
  echo "❌ pre-apply gate is red (a FAIL was reported); sync refused - fix it and rerun."
  exit 1
fi

# Apply mode: assert the retired node-naming term is fully gone from the installed copies.
echo "===== checking for leftover legacy hostname wording ====="
fail=0
for dest in "${TARGETS[@]}"; do
  [[ -d "$dest" ]] || continue
  leftover=$(grep -rln --exclude-dir=scripts "主机名" "$dest" 2>/dev/null || true)
  if [[ -z "$leftover" ]]; then
    echo "✅ $dest"
  else
    echo "❌ $dest:"
    echo "$leftover" | sed 's/^/    /'
    fail=1
  fi
done
exit "$fail"
