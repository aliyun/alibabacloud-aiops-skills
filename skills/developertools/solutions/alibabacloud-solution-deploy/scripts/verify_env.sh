#!/bin/bash
# Alibaba Cloud CLI Environment Verification Script
# Usage: bash scripts/verify_env.sh

if [ -z "$BASH_VERSION" ]; then
    echo "Please run this script with bash: bash $0"
    exit 1
fi

TOTAL=0
PASSED=0
MISSING_ITEMS=()

check() {
    local name="$1"
    local result="$2"
    local fix_hint="$3"
    TOTAL=$((TOTAL + 1))
    if [ "$result" = "0" ]; then
        PASSED=$((PASSED + 1))
        echo "  ✅ PASS  $name"
    else
        echo "  ❌ FAIL  $name"
        if [ -n "$fix_hint" ]; then
            MISSING_ITEMS+=("$fix_hint")
        fi
    fi
}

echo "========================================="
echo "  Alibaba Cloud CLI Environment Check"
echo "========================================="
echo ""

# 1. Check aliyun CLI installed
echo "--- 1. Aliyun CLI ---"
if command -v aliyun &>/dev/null; then
    CLI_VERSION=$(aliyun version 2>&1 | head -1)
    echo "  Version: $CLI_VERSION"
    # Check version >= 3.3.0
    MAJOR=$(echo "$CLI_VERSION" | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1 | cut -d. -f1)
    MINOR=$(echo "$CLI_VERSION" | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1 | cut -d. -f2)
    PATCH=$(echo "$CLI_VERSION" | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1 | cut -d. -f3)
    if [ -n "$MAJOR" ] && [ "$MAJOR" -ge 3 ] && [ "$MINOR" -ge 3 ]; then
        check "Aliyun CLI >= 3.3.0" "0" ""
    elif [ -n "$MAJOR" ] && [ "$MAJOR" -gt 3 ]; then
        check "Aliyun CLI >= 3.3.0" "0" ""
    else
        check "Aliyun CLI >= 3.3.0" "1" "[CLI] Upgrade aliyun CLI to 3.3.0+: brew upgrade aliyun-cli (macOS) or download from https://aliyuncli.alicdn.com/"
    fi
else
    check "Aliyun CLI installed" "1" "[CLI] Install aliyun CLI: brew install aliyun-cli (macOS) or see https://help.aliyun.com/zh/cli/"
fi
echo ""

# 2. Check CLI credentials (via STS GetCallerIdentity)
echo "--- 2. CLI Credentials ---"
if command -v aliyun &>/dev/null; then
    STS_OUTPUT=$(aliyun sts GetCallerIdentity 2>&1)
    if echo "$STS_OUTPUT" | grep -q '"AccountId"'; then
        ACCOUNT_ID=$(echo "$STS_OUTPUT" | python3 -c "import sys,json;print(json.load(sys.stdin)['AccountId'])" 2>/dev/null)
        ARN=$(echo "$STS_OUTPUT" | python3 -c "import sys,json;print(json.load(sys.stdin)['Arn'])" 2>/dev/null)
        MASKED_ACCOUNT="${ACCOUNT_ID:0:4}****${ACCOUNT_ID: -4}"
        MASKED_ARN=$(echo "$ARN" | sed "s/$ACCOUNT_ID/${MASKED_ACCOUNT}/g")
        echo "  Account: $MASKED_ACCOUNT"
        echo "  Identity: $MASKED_ARN"
        check "CLI credentials valid" "0" ""
    else
        echo "  Error: $STS_OUTPUT"
        check "CLI credentials valid" "1" "[Config] Run: aliyun configure set --mode AK --access-key-id <your-ak> --access-key-secret <your-sk> --region cn-hangzhou"
    fi
else
    check "CLI credentials" "1" "[CLI] Install aliyun CLI first"
fi
echo ""

# 3. Check auto-plugin-install
echo "--- 3. Auto Plugin Install ---"
if command -v aliyun &>/dev/null; then
    CONFIG_JSON="$HOME/.aliyun/config.json"
    if [ -f "$CONFIG_JSON" ]; then
        AUTO_INSTALL=$(python3 -c "
import json
with open('$CONFIG_JSON') as f:
    cfg = json.load(f)
# Check current profile
profiles = cfg.get('profiles', [])
current = cfg.get('current', 'default')
for p in profiles:
    if p.get('name') == current:
        print(str(p.get('auto_plugin_install', False)).lower())
        break
else:
    print('false')
" 2>/dev/null || echo "false")
        if [ "$AUTO_INSTALL" = "true" ]; then
            check "Auto plugin install enabled" "0" ""
        else
            check "Auto plugin install enabled" "1" "[Config] Run: aliyun configure set --auto-plugin-install true"
        fi
    else
        check "Auto plugin install enabled" "1" "[Config] Run: aliyun configure set --auto-plugin-install true"
    fi
else
    check "Auto plugin install" "1" "[CLI] Install aliyun CLI first"
fi
echo ""

# 4. Check Python3 (needed for helper scripts)
echo "--- 4. Python3 (for helper scripts) ---"
if command -v python3 &>/dev/null; then
    PY_VERSION=$(python3 --version 2>&1 || echo "unknown")
    echo "  Version: $PY_VERSION"
    check "Python3 available" "0" ""
else
    check "Python3 available" "1" "[Python3] Install Python 3.8+: https://www.python.org/downloads/"
fi
echo ""

# 5. Check Python SDK (needed for helper scripts only)
echo "--- 5. Python SDK (for helper scripts) ---"
if command -v python3 &>/dev/null; then
    SDK_PACKAGES=(
        "alibabacloud_tea_openapi"
        "alibabacloud_credentials"
        "alibabacloud_tea_util"
        "alibabacloud_openapi_util"
    )
    MISSING_SDK=()
    for pkg in "${SDK_PACKAGES[@]}"; do
        if ! python3 -c "import $pkg" &>/dev/null; then
            MISSING_SDK+=("$pkg")
        fi
    done
    if [ ${#MISSING_SDK[@]} -eq 0 ]; then
        check "SDK packages for helper scripts" "0" ""
    else
        check "SDK packages for helper scripts (missing: ${MISSING_SDK[*]})" "1" "[SDK] Run: pip3 install alibabacloud-tea-openapi alibabacloud-credentials alibabacloud-tea-util alibabacloud-openapi-util"
    fi
else
    check "SDK packages check" "1" "[Python3] Install Python 3.8+ first"
fi

echo ""
echo "========================================="
echo "  Result: $PASSED/$TOTAL passed"
echo "========================================="

if [ "$PASSED" -eq "$TOTAL" ]; then
    echo "  ✅ All CLI environment checks passed!"
    exit 0
else
    echo ""
    IFS=$'\n' UNIQUE_MISSING=($(sort -u <<<"${MISSING_ITEMS[*]}")); unset IFS

    echo "  ❌ $((TOTAL - PASSED)) item(s) failed. How to fix:"
    echo ""
    for item in "${UNIQUE_MISSING[@]}"; do
        echo "  $item"
    done
    echo ""
    exit 1
fi
