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

# Block mongo client connections and installation attempts
if printf '%s' "$COMMAND" | grep -qE '(^mongo\s|^mongosh\s|mongo\s+-|mongosh\s+-|apt.*install.*mongo|yum.*install.*mongo|brew.*install.*mongo|pip.*install.*pymongo)'; then
  cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "BLOCKED: This skill prohibits direct database connections and mongo/mongosh client installation. Use DAS API (CreateStorageAnalysisTask + GetStorageAnalysisResult) for space analysis and GetMongoDBCurrentOp for session data."
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

# Product whitelist: only dds, das, cms are allowed
case "$PRODUCT" in
  dds|das) ;; # allowed
  cms)
    # CMS: only DescribeAlertHistoryList and DescribeMetricRuleList are allowed
    if [ "$ACTION" != "DescribeAlertHistoryList" ] && [ "$ACTION" != "DescribeMetricRuleList" ]; then
      cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "BLOCKED: Only 'cms DescribeAlertHistoryList' and 'cms DescribeMetricRuleList' are allowed. Use 'dds DescribeDBInstancePerformance' for monitoring data, NOT cms DescribeMetricList/DescribeMetricData."
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
    "permissionDecisionReason": "BLOCKED: Product '$PRODUCT' is not in the allowed list (dds, das, cms). This skill only uses MongoDB DDS, DAS, and CMS APIs."
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

# Write operation prefixes (both PascalCase and lowercase-hyphenated plugin mode)
WRITE_PREFIXES="Create Delete Remove Modify Update Attach Detach Grant Revoke Start Stop Reboot Release Allocate Associate Disassociate Enable Disable Reset Resize Set Add Clear Activate Deactivate create- delete- remove- modify- update- attach- detach- grant- revoke- start- stop- reboot- release- allocate- associate- disassociate- enable- disable- reset- resize- set- add- clear- activate- deactivate-"

IS_WRITE=false
for PREFIX in $WRITE_PREFIXES; do
  case "$ACTION" in
    ${PREFIX}*) IS_WRITE=true; break ;;
  esac
done

# Read-equivalent exceptions (not actual write operations)
READ_EXCEPTIONS="CreateStorageAnalysisTask create-storage-analysis-task"
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
