#!/bin/bash
# Alibaba Cloud Security Health Check - One-click Collection Entry
# ================================================================
# Usage:
#   bash run.sh             # Collect all (4 products)
#   bash run.sh waf sas     # Collect specified products only
# Outputs 4 JSON files to current directory for security delivery team.
# ================================================================

set -e

PRODUCTS=("$@")
[ ${#PRODUCTS[@]} -eq 0 ] && PRODUCTS=(waf sas cfw ddos)

# Generate session-id (UUID v4) for observability tracing; exported for child scripts
export SESSION_ID="${SESSION_ID:-$(uuidgen 2>/dev/null || python3 -c 'import uuid; print(uuid.uuid4())' 2>/dev/null || cat /proc/sys/kernel/random/uuid 2>/dev/null || echo unknown)}"

# Dependency check
command -v aliyun >/dev/null 2>&1 || {
  echo "Missing aliyun CLI, please install first:" >&2
  echo "  curl -sLf https://aliyuncli.alicdn.com/aliyun-cli-linux-latest-amd64.tgz | tar xz" >&2
  exit 1
}
command -v jq >/dev/null 2>&1 || {
  echo "Missing jq, please install: apt install jq / brew install jq" >&2
  exit 1
}

# Authentication check
if ! aliyun sts get-caller-identity --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-security-health-check/${SESSION_ID}" >/dev/null 2>&1; then
  echo "aliyun CLI not configured or credentials invalid, please run: aliyun configure" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
echo "=========================================="
echo " Alibaba Cloud Security Health Check - Data Collection"
echo " Products: ${PRODUCTS[*]}"
echo " Output directory: $(pwd)"
echo "=========================================="
echo ""

for p in "${PRODUCTS[@]}"; do
  case "$p" in
    waf|sas|cfw|ddos)
      echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
      echo ">>> Starting collection: $p"
      echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
      bash "$SCRIPT_DIR/$p-collect.sh"
      echo ""
      ;;
    *)
      echo "Unknown product: $p (supported: waf/sas/cfw/ddos)" >&2
      ;;
  esac
done

echo "=========================================="
echo " Collection complete. Please package and return the following JSON files:"
ls -lh *-collected.json 2>/dev/null || true
echo "=========================================="
