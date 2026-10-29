#!/bin/bash
# init-session.sh
# Must be sourced/executed before the first Alibaba Cloud API call in a session.
# Reads assets/manifest.json, generates a UUID4 session ID, and exports the
# User-Agent string used by every aliyun CLI invocation.
#
# Usage:
#   source "$(dirname "$0")/scripts/init-session.sh"
#   source "$(dirname "$0")/scripts/init-session.sh" --env-file ./ran_scripts/00-session-env.sh
#   bash scripts/init-session.sh --env-file ./ran_scripts/00-session-env.sh
#
# --env-file writes the exported variables to the given file so later shell
# invocations can reload them with "source <file>" instead of re-running this
# script (re-running generates a new session ID that no longer matches your logs).

set -euo pipefail

ENV_FILE=""
while [ $# -gt 0 ]; do
  case "$1" in
    --env-file)
      ENV_FILE="${2:?--env-file requires a path}"
      shift 2
      ;;
    *)
      # Positional parameters belong to the calling script when this file is sourced.
      shift
      ;;
  esac
done

# Resolve SKILL_ROOT: directory containing this script's parent.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
MANIFEST_PATH="$SKILL_ROOT/assets/manifest.json"

if [ ! -f "$MANIFEST_PATH" ]; then
  echo "ERROR: manifest not found at $MANIFEST_PATH" >&2
  exit 1
fi

# Read manifest metadata before any cloud call.
SKILL_NAME=$(jq -r '.name' "$MANIFEST_PATH")
SKILL_VERSION=$(jq -r '.version' "$MANIFEST_PATH")
SESSION_GENERATOR=$(jq -r '.session_id_generator' "$MANIFEST_PATH")

# Validate expected session generator.
if [ "$SESSION_GENERATOR" != "uuid4" ]; then
  echo "ERROR: unsupported session_id_generator '$SESSION_GENERATOR'" >&2
  exit 1
fi

# Generate a UUID4 session ID (RFC 4122 variant).
if command -v uuidgen >/dev/null 2>&1; then
  GA_SESSION_ID=$(uuidgen | tr '[:upper:]' '[:lower:]')
else
  GA_SESSION_ID=$(python3 -c 'import uuid; print(uuid.uuid4())')
fi

# Compose the full versioned User-Agent per skill specification:
# AlibabaCloud-Agent-Skills/{name}/{session-id} skill-version/{version}
GA_USER_AGENT="AlibabaCloud-Agent-Skills/${SKILL_NAME}/${GA_SESSION_ID} skill-version/${SKILL_VERSION}"

export SKILL_ROOT
export GA_SKILL_NAME="$SKILL_NAME"
export GA_SKILL_VERSION="$SKILL_VERSION"
export GA_SESSION_ID
export GA_USER_AGENT

echo "Session initialized: $GA_SKILL_NAME/$GA_SKILL_VERSION"
echo "Session ID: $GA_SESSION_ID"
echo "User-Agent: $GA_USER_AGENT"

if [ -n "$ENV_FILE" ]; then
  mkdir -p "$(dirname "$ENV_FILE")"
  cat > "$ENV_FILE" <<EOF
export SKILL_ROOT="$SKILL_ROOT"
export GA_SKILL_NAME="$GA_SKILL_NAME"
export GA_SKILL_VERSION="$GA_SKILL_VERSION"
export GA_SESSION_ID="$GA_SESSION_ID"
export GA_USER_AGENT="$GA_USER_AGENT"
EOF
  echo "Env file written: $ENV_FILE"
fi
