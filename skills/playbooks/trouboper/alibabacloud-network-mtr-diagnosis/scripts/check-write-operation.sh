#!/bin/bash
# check-write-operation.sh - PreToolUse Hook for alibabacloud-network-mtr-diagnosis skill
# This script checks if the Bash command is a read-only or write operation.
# Read operations (Describe/List/Get/Check/Parse) are allowed automatically.
# Write operations (Create/Delete/Modify/run-command) require user confirmation.

# Read tool invocation info from stdin
INPUT=$(cat)

# Extract command from input (PreToolUse format: {tool_name, tool_input: {command}})
COMMAND=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    ti = data.get('tool_input', {})
    cmd = ti.get('command', '') if isinstance(ti, dict) else ''
    if not cmd:
        cmd = data.get('command', '') or data.get('input', '')
    print(cmd)
except:
    print('')
" 2>/dev/null)

# If we can't extract command, allow by default (don't block unrelated tasks)
if [ -z "$COMMAND" ]; then
    cat << 'EOF'
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow",
    "permissionDecisionReason": "Unable to parse command details, allowing by default"
  }
}
EOF
    exit 0
fi

# Define write operation keywords (Aliyun API actions that modify state)
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
    "run-command"
    "invoke-command"
    "send-command"
)

# Check if command contains write operation keywords
IS_WRITE=false
DECISION_REASON=""

for keyword in "${WRITE_KEYWORDS[@]}"; do
    if echo "$COMMAND" | grep -qi "$keyword"; then
        IS_WRITE=true
        if [ "$keyword" = "run-command" ] || [ "$keyword" = "invoke-command" ] || [ "$keyword" = "send-command" ]; then
            DECISION_REASON="Detected remote command execution API call (${keyword}). This will execute a script remotely on the ECS instance and requires user confirmation."
        else
            DECISION_REASON="Detected write operation API call (${keyword}). This may modify cloud resource configuration and requires user confirmation."
        fi
        break
    fi
done

# Make decision
if [ "$IS_WRITE" = true ]; then
    # Write operation requires user confirmation
    cat << EOF
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "ask",
    "permissionDecisionReason": "${DECISION_REASON}"
  }
}
EOF
else
    # Read operation allowed automatically
    cat << 'EOF'
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow",
    "permissionDecisionReason": "Read-only diagnostic operation, automatically allowed"
  }
}
EOF
fi
