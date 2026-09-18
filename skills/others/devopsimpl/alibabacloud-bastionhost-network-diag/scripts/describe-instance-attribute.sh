#!/usr/bin/env bash
set -euo pipefail

# Dependencies:
#   - aliyun-cli (Alibaba Cloud CLI)
#   - SESSION_ID environment variable (generated once by the skill orchestrator)

# Step 1: Read and validate manifest.json before any session preparation.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
MANIFEST_FILE="${SCRIPT_DIR}/../references/manifest.json"
if [[ ! -f "${MANIFEST_FILE}" ]]; then
  echo "Error: manifest file not found at ${MANIFEST_FILE}." >&2
  exit 1
fi

VERSION="$(sed -n 's/.*"version"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "${MANIFEST_FILE}" | head -n1)"
if [[ -z "${VERSION}" ]]; then
  echo "Error: version field is missing or empty in ${MANIFEST_FILE}." >&2
  exit 1
fi

# Step 2: Verify required tools are available.
if ! command -v aliyun >/dev/null 2>&1; then
  echo "Error: aliyun-cli is not installed or not available in PATH." >&2
  exit 1
fi

# Step 3: Use the session ID provided by the skill orchestrator.
if [[ -z "${SESSION_ID:-}" ]]; then
  echo "Error: SESSION_ID environment variable is not set. The skill orchestrator must generate it once before calling any scripts." >&2
  exit 1
fi
USER_AGENT="AlibabaCloud-Agent-Skills/alibabacloud-bastionhost-network-diag/${SESSION_ID} skill-version/${VERSION}"

INSTANCE_ID="${1:-}"
if [[ -z "${INSTANCE_ID}" ]]; then
  echo "Error: instance ID is required as the first argument." >&2
  exit 1
fi

if ! aliyun yundun-bastionhost describe-instance-attribute --instance-id "${INSTANCE_ID}" --user-agent "${USER_AGENT}"; then
  echo "Error: failed to query attributes for Bastion Host instance ${INSTANCE_ID}. Please verify the instance ID and permissions." >&2
  exit 1
fi
