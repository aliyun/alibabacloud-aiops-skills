#!/bin/bash
set -u
# check-write-operation.sh
# Intercept aliyun CLI write operations and require user confirmation

INPUT=$(cat)
COMMAND=$(printf '%s' "$INPUT" | python3 -c "
import sys, json
try:
    cmd = json.load(sys.stdin).get('tool_input', {}).get('command', '')
    if cmd and cmd.isprintable():
        print(cmd)
except Exception:
    pass
" 2>/dev/null)

# If empty, allow directly
if [ -z "$COMMAND" ]; then
  echo '{}'
  exit 0
fi

# Block mysql client connections and mysql installation attempts
if printf '%s' "$COMMAND" | grep -qE '(^mysql\s|mysql\s+-[hupP]|apt.*install.*mysql|yum.*install.*mysql|brew.*install.*mysql|pip.*install.*mysql)'; then
  cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "BLOCKED: This skill prohibits direct database connections and mysql client installation. Use DAS API (CreateStorageAnalysisTask + GetStorageAnalysisResult) for space analysis."
  }
}
EOF
  exit 0
fi

# If not an aliyun CLI command, allow directly
if ! printf '%s' "$COMMAND" | grep -q "^aliyun "; then
  echo '{}'
  exit 0
fi

# Extract product and action from: aliyun <product> <action> [options...]
PRODUCT=$(printf '%s' "$COMMAND" | tr ' ' '\n' | grep -v '^--' | sed -n '2p')
ACTION=$(printf '%s' "$COMMAND" | tr ' ' '\n' | grep -v '^--' | sed -n '3p')

# Skip non-API commands (configure, version, plugin, etc.)
case "$PRODUCT" in
  configure|version|plugin|help) echo '{}'; exit 0 ;;
esac

# Product whitelist: only polardb, das, cms are allowed
case "$PRODUCT" in
  polardb|das) ;; # allowed
  cms)
    # CMS: only describe-alert-log-list and describe-metric-rule-list are allowed
    if [ "$ACTION" != "describe-alert-log-list" ] && [ "$ACTION" != "describe-metric-rule-list" ]; then
      cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "BLOCKED: Only 'cms describe-alert-log-list' is allowed. Use 'polardb DescribeDBClusterPerformance/DescribeDBNodePerformance/DescribeDBProxyPerformance' for monitoring data, NOT cms DescribeMetricList."
  }
}
EOF
      exit 0
    fi
    ;;
  *)
    cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "BLOCKED: Product '$PRODUCT' is not in the allowed list (polardb, das, cms). This skill only uses PolarDB and DAS APIs."
  }
}
EOF
    exit 0
    ;;
esac

if [ -z "$ACTION" ]; then
  echo '{}'
  exit 0
fi

# Write operation prefixes (plugin mode: lowercase-hyphenated)
WRITE_PREFIXES="create- delete- remove- modify- update- attach- detach- grant- revoke- start- stop- reboot- release- allocate- associate- disassociate- enable- disable- reset- resize- set- add- clear- activate- deactivate-"

IS_WRITE=false
for PREFIX in $WRITE_PREFIXES; do
  case "$ACTION" in
    ${PREFIX}*) IS_WRITE=true; break ;;
  esac
done

# Read-equivalent exceptions (not actual write operations)
READ_EXCEPTIONS="create-storage-analysis-task"
for EXCEPTION in $READ_EXCEPTIONS; do
  if [ "$ACTION" = "$EXCEPTION" ]; then
    IS_WRITE=false
    break
  fi
done

if [ "$IS_WRITE" = true ]; then
  cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "ask",
    "permissionDecisionReason": "Detected write operation API ($ACTION). User confirmation required before execution."
  }
}
EOF
else
  cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow",
    "permissionDecisionReason": "Read operation API ($ACTION), no confirmation needed."
  }
}
EOF
fi
