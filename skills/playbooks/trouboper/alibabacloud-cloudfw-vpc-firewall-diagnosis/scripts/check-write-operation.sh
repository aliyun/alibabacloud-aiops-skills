#!/usr/bin/env bash
# PreToolUse hook for the VPC firewall diagnosis skill.
#
# This skill is read-only. The hook uses a whitelist model:
# only clearly identified read-only Alibaba Cloud CLI commands,
# local inspection commands, and bundled diagnostic scripts are allowed.
# All write operations or unmatched Bash commands return permissionDecision=ask.
#
# Input from stdin:
#   {"tool_name":"Bash","tool_input":{"command":"<command>"}}
#
# Output to stdout:
#   {
#     "hookSpecificOutput": {
#       "hookEventName": "PreToolUse",
#       "permissionDecision": "allow" | "ask",
#       "permissionDecisionReason": "..."
#     }
#   }
set -euo pipefail

INPUT="$(cat)"
CMD="$(printf '%s' "$INPUT" | python3 -c '
import json, sys
try:
    data = json.load(sys.stdin)
    print(data.get("tool_input", {}).get("command", ""))
except Exception:
    print("")
' 2>/dev/null || echo "")"

ALLOW_REASON=""
ASK_REASON=""

if [ -z "${CMD//[[:space:]]/}" ]; then
    ASK_REASON="Unable to parse the Bash command; user confirmation is required."
elif echo "$CMD" | grep -qE '(;|&&|\|\||\||`|\$\()'; then
    ASK_REASON="The command contains shell composition, pipe, or command substitution and cannot be safely matched as a single read-only command."
elif echo "$CMD" | grep -qE '(^|\s)\s*(rm|mv|chmod|chown|sudo|dd|mkfs|truncate|shutdown|reboot|kill|pkill|touch|cp|tee)\b'; then
    ASK_REASON="The command contains local write or destructive operations that conflict with read-only diagnosis."
elif echo "$CMD" | grep -qE '(^|[^>])\s*>\s*[^&]|>>\s'; then
    ASK_REASON="The command contains output redirection that may modify local files or hide errors."
elif echo "$CMD" | grep -qE '\baliyun\b.*\s+(create|delete|modify|update|put|set|attach|detach|start|stop|enable|disable|add|remove|associate|disassociate|grant|revoke|reset|replace|authorize|submit|apply|register|deregister|publish|withdraw|refresh)(-[a-z0-9]+)*\b'; then
    ASK_REASON="The command is an Alibaba Cloud write API. This skill is read-only; review manually before confirming."
elif echo "$CMD" | grep -qE '\baliyun\b.*\s+(Create|Delete|Modify|Update|Put|Set|Attach|Detach|Start|Stop|Enable|Disable|Add|Remove|Associate|Disassociate|Grant|Revoke|Reset|Replace|Authorize|Submit|Apply|Register|Deregister|Publish|Withdraw|Refresh)[A-Z]'; then
    ASK_REASON="The command is an Alibaba Cloud write API in PascalCase. This skill is read-only; review manually before confirming."
elif echo "$CMD" | grep -qE '^\s*(cat|ls|head|tail|grep|find|wc|echo|pwd|which|printenv|env|uname|date|stat|file)\b'; then
    ALLOW_REASON="Local read-only inspection command."
elif echo "$CMD" | grep -qE '^\s*python3\s+--version\b'; then
    ALLOW_REASON="Python version check."
elif echo "$CMD" | grep -qE '(^|\s)python3\s+([^;&|]*\/)?scripts\/(analyze_routes|closure_precheck)\.py\b'; then
    ALLOW_REASON="Bundled diagnostic script; the script only calls read-only APIs."
elif echo "$CMD" | grep -qE '^\s*aliyun\s+version\b|^\s*aliyun\s+configure\s+list\b|^\s*aliyun\s+sts\s+get-caller-identity\b'; then
    ALLOW_REASON="Alibaba Cloud CLI environment or identity read-only check."
elif echo "$CMD" | grep -qE '\baliyun\b.*\s+(describe|list|get|query|lookup|check|search|test)(-[a-z0-9]+)*\b'; then
    ALLOW_REASON="Alibaba Cloud CLI read-only API."
elif echo "$CMD" | grep -qE '\baliyun\b.*\s+(Describe|List|Get|Query|Lookup|Check|Search|Test)[A-Z]'; then
    ASK_REASON="Alibaba Cloud CLI action is not in plugin lowercase-hyphenated format; use plugin mode such as describe-*, list-*, get-*, or lookup-*."
else
    ASK_REASON="The Bash command is not in the read-only whitelist; user confirmation is required."
fi

if [ -n "$ASK_REASON" ]; then
    cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "ask",
    "permissionDecisionReason": "$ASK_REASON"
  }
}
EOF
else
    REASON="$ALLOW_REASON"
    cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow",
    "permissionDecisionReason": "$REASON"
  }
}
EOF
fi
