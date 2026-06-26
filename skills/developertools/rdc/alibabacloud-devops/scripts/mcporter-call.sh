#!/usr/bin/env bash
# Wrapper for mcporter MCP tool calls with standard flags.
# Usage: ./mcporter-call.sh <tool_name> [key:"value" ...]
# Example: ./mcporter-call.sh get_current_organization_info
#          ./mcporter-call.sh list_repositories organizationId:"abc123"
#          ./mcporter-call.sh list   (list all available tools)
#          ./mcporter-call.sh schema <tool_name>  (show tool schema)

set -euo pipefail

MCP_SERVER="alibabacloud-devops-mcp-server@0.3.38"
MCPORTER="mcporter@0.11.1"

if [[ $# -eq 0 ]]; then
  echo "Usage: $0 <tool_name> [key:\"value\" ...]"
  echo "       $0 list              — list all available tools"
  echo "       $0 schema <tool>     — show schema for a specific tool"
  exit 0
fi

ACTION="$1"
shift

if [[ "$ACTION" == "list" ]]; then
  npx -y "$MCPORTER" list --stdio "npx -y $MCP_SERVER"
elif [[ "$ACTION" == "schema" ]]; then
  TOOL="${1:-}"
  if [[ -z "$TOOL" ]]; then
    npx -y "$MCPORTER" list --stdio "npx -y $MCP_SERVER" --schema
  else
    npx -y "$MCPORTER" list --stdio "npx -y $MCP_SERVER" --schema 2>&1 | grep -A 30 "function $TOOL"
  fi
else
  npx -y "$MCPORTER" call --no-coerce --stdio "npx -y $MCP_SERVER" "$ACTION" "$@"
fi
