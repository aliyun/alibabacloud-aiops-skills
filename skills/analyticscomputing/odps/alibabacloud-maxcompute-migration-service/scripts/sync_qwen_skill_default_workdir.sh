#!/usr/bin/env bash
# Sync repo SKILL.md + references/ into the fixed qwen workdir used for manual checks.
# Layout:
#   <workdir>/.qwen/skills/alibabacloud-maxcompute-migration-service/SKILL.md
#   <workdir>/.qwen/skills/alibabacloud-maxcompute-migration-service/references/**
#
# Override workdir root:
#   MMS_DEFAULT_WORKDIR=/path/to/dir ./scripts/sync_qwen_skill_default_workdir.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
WORKDIR="${MMS_DEFAULT_WORKDIR:-${HOME}/tmp/mms_skill_test/default-workdir}"
TARGET_SKILL_DIR="${WORKDIR}/.qwen/skills/alibabacloud-maxcompute-migration-service"

mkdir -p "${TARGET_SKILL_DIR}"

if [[ ! -f "${REPO_ROOT}/SKILL.md" ]]; then
  echo "error: missing ${REPO_ROOT}/SKILL.md" >&2
  exit 1
fi

cp "${REPO_ROOT}/SKILL.md" "${TARGET_SKILL_DIR}/SKILL.md"
rm -rf "${TARGET_SKILL_DIR}/references"
if [[ -d "${REPO_ROOT}/references" ]]; then
  cp -R "${REPO_ROOT}/references" "${TARGET_SKILL_DIR}/references"
fi

echo "Synced MMS skill into: ${TARGET_SKILL_DIR}"
echo "Run qwen from this directory (cd here first): ${WORKDIR}"
