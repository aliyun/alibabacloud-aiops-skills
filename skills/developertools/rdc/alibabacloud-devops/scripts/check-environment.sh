#!/usr/bin/env bash
# Check readiness of all three invocation channels (CLI, MCP Server, mcporter).
# Usage: ./check-environment.sh

set -euo pipefail

echo "=== Yunxiao DevOps Environment Check ==="
echo ""

# 1. Alibaba Cloud CLI
echo "[1/4] Alibaba Cloud CLI (aliyun devops)"
if aliyun devops --help >/dev/null 2>&1; then
  echo "  Status: READY"
  echo "  Version: $(aliyun devops version 2>/dev/null || echo 'unknown')"
else
  echo "  Status: NOT AVAILABLE"
  echo "  Install: https://help.aliyun.com/zh/cli/install-update-alibaba-cloud-cli"
fi
echo ""

# 2. Node.js / npx
echo "[2/4] Node.js / npx"
if command -v node >/dev/null 2>&1; then
  echo "  Node.js: $(node --version)"
  echo "  npx: $(npx --version 2>/dev/null || echo 'not found')"
else
  echo "  Status: NOT AVAILABLE"
  echo "  Install Node.js 18+ from https://nodejs.org"
fi
echo ""

# 3. Yunxiao Access Token
echo "[3/4] Yunxiao Access Token"
if [ -n "${YUNXIAO_ACCESS_TOKEN:-}" ]; then
  echo "  Status: CONFIGURED"
else
  echo "  Status: NOT CONFIGURED"
  echo "  Guide: https://help.aliyun.com/zh/yunxiao/developer-reference/obtain-personal-access-token"
fi
echo ""

# 4. MCP Server / mcporter availability
echo "[4/4] MCP Server packages"
if command -v npx >/dev/null 2>&1; then
  if npm list -g alibabacloud-devops-mcp-server >/dev/null 2>&1; then
    echo "  alibabacloud-devops-mcp-server: INSTALLED (global)"
  else
    echo "  alibabacloud-devops-mcp-server: not pre-installed (npx will download on demand)"
  fi
  if npm list -g mcporter >/dev/null 2>&1; then
    echo "  mcporter: INSTALLED (global)"
  else
    echo "  mcporter: not pre-installed (npx will download on demand)"
  fi
else
  echo "  Status: SKIPPED (npx not available)"
fi
echo ""
echo "=== Check Complete ==="
