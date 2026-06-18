#!/bin/bash
# check-write-operation.sh
# Intercept aliyun CLI write operations and require user confirmation

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_input',{}).get('command',''))" 2>/dev/null)

# If not an aliyun CLI command, allow directly
if ! echo "$COMMAND" | grep -q "^aliyun "; then
  echo '{}'
  exit 0
fi

# Extract Action name (aliyun <service> <Action> format)
ACTION=$(echo "$COMMAND" | awk '{print $3}')

# Write operation Action prefixes (matched case-insensitively to handle both
# PascalCase like "ModifyDBInstance" and kebab-case like "modify-db-instance-spec")
WRITE_PREFIXES="Create Delete Remove Modify Update Attach Detach Grant Revoke Start Stop Reboot Release Allocate Associate Disassociate Enable Disable Reset Resize"

IS_WRITE=false
for PREFIX in $WRITE_PREFIXES; do
  if echo "$ACTION" | grep -qi "^${PREFIX}"; then
    IS_WRITE=true
    break
  fi
done

# Exception: storage-analysis-task creation is a read-equivalent operation (DAS analysis,
# no instance state change). Match both kebab-case and PascalCase.
WHITELISTED=false
if echo "$COMMAND" | grep -qi "createstorageanalysistask\|create-storage-analysis-task"; then
  IS_WRITE=false
  WHITELISTED=true
fi

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
elif [ "$WHITELISTED" = true ]; then
  cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow",
    "permissionDecisionReason": "Whitelisted analysis-task API ($ACTION) — no instance state change."
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
