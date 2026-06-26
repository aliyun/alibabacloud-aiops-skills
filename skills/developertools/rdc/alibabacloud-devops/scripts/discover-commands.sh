#!/usr/bin/env bash
# Discover aliyun devops CLI commands by product prefix.
# Usage: ./discover-commands.sh <product-prefix>
# Example: ./discover-commands.sh flow
#          ./discover-commands.sh codeup
#          ./discover-commands.sh   (no args = show all prefixes)

set -euo pipefail

PREFIXES=(flow codeup projex test-hub app-stack packages base lingma insight)

if [[ $# -eq 0 ]]; then
  echo "Available product prefixes:"
  for p in "${PREFIXES[@]}"; do
    count=$(aliyun devops --help 2>&1 | grep -c "^  ${p}-" || true)
    printf "  %-12s (%d commands)\n" "$p" "$count"
  done
  echo ""
  echo "Usage: $0 <prefix>  — list commands for a product"
  echo "       $0 <prefix> <keyword>  — filter commands by keyword"
  exit 0
fi

PREFIX="$1"
KEYWORD="${2:-}"

if [[ -n "$KEYWORD" ]]; then
  aliyun devops --help 2>&1 | grep "^  ${PREFIX}-" | grep -i "$KEYWORD"
else
  aliyun devops --help 2>&1 | grep "^  ${PREFIX}-"
fi
