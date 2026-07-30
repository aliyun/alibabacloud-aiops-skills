#!/bin/bash
# check-write-operation.sh - read-only command checker for alibabacloud-network-diagnose.
# This script checks whether a command appears to call a write-style aliyun API.
# Read operations are allowed; write operations are reported as unsafe.

INPUT=$(cat)

COMMAND=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    cmd = data.get('command', '') or data.get('input', '')
    print(cmd)
except:
    print('')
" 2>/dev/null)

if [ -z "$COMMAND" ]; then
    cat << 'EOF'
{
  "safe": true,
  "reason": "No command was provided."
}
EOF
    exit 0
fi

WRITE_KEYWORDS=(
    "Create"
    "Delete"
    "Modify"
    "Update"
    "Enable"
    "Disable"
    "Add"
    "Remove"
    "Attach"
    "Detach"
    "Start"
    "Stop"
    "Reboot"
    "Replace"
    "Grant"
    "Revoke"
)

IS_WRITE=false
DECISION_REASON=""

WRITE_PATTERN='aliyun [a-z]+ (Create|Delete|Modify|Update|Enable|Disable|Add|Remove|Attach|Detach|Start|Stop|Reboot|Replace|Grant|Revoke)[A-Za-z]'

if echo "$COMMAND" | grep -qE "$WRITE_PATTERN"; then
    MATCHED_ACTION=$(echo "$COMMAND" | grep -oE "$WRITE_PATTERN" | head -1)
    IS_WRITE=true
    DECISION_REASON="Detected write-style aliyun API call (${MATCHED_ACTION})."
fi

if [ "$IS_WRITE" = true ]; then
    cat << EOF
{
  "safe": false,
  "reason": "${DECISION_REASON}"
}
EOF
else
    cat << 'EOF'
{
  "safe": true,
  "reason": "No write-style aliyun API call was detected."
}
EOF
fi
