#!/bin/bash
# check-write-operation.sh
# Intercept Redis/KVStore write operations and require user confirmation.
# This hook analyzes commands to detect potentially destructive operations.

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_input',{}).get('command',''))" 2>/dev/null)

# If not a redis-cli command or aliyun CLI command, allow
if ! echo "$COMMAND" | grep -qE "(redis-cli|aliyun )"; then
  # Check if running our analysis scripts (read-only, allow directly)
  if echo "$COMMAND" | grep -qE "(health-inspect\.py|find-instance-region\.py)"; then
    cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow",
    "permissionDecisionReason": "Health inspection script execution (read-only)."
  }
}
EOF
    exit 0
  fi
  # Non-redis commands, allow
  echo '{}'
  exit 0
fi

# For redis-cli commands, check for write operations
if echo "$COMMAND" | grep -qi "redis-cli"; then
  REDIS_CMD=$(echo "$COMMAND" | grep -oP '(?<=redis-cli[^"]*)\s+\K\S+' | head -1 | tr '[:lower:]' '[:upper:]')

  WRITE_CMDS="SET MSET MSETNX SETNX SETEX PSETEX SETRANGE APPEND DEL UNLINK EXPIRE PEXPIRE EXPIREAT PERSIST RENAME RENAMENX HSET HMSET HSETNX HDEL LPUSH RPUSH LPUSHX RPUSHX LPOP RPOP LSET LINSERT LTRIM SADD SREM SMOVE SPOP ZADD ZREM ZINCRBY ZREMRANGEBYRANK ZREMRANGEBYSCORE INCR DECR INCRBY DECRBY INCRBYFLOAT FLUSHDB FLUSHALL CONFIG SHUTDOWN DEBUG REPLICAOF SLAVEOF CLUSTER XADD XTRIM XDEL"

  IS_WRITE=false
  for CMD in $WRITE_CMDS; do
    if [ "$REDIS_CMD" = "$CMD" ]; then
      IS_WRITE=true
      break
    fi
  done

  if [ "$IS_WRITE" = true ]; then
    IRREVERSIBLE="DEL UNLINK FLUSHDB FLUSHALL SHUTDOWN"
    IS_IRREVERSIBLE=false
    for CMD in $IRREVERSIBLE; do
      if [ "$REDIS_CMD" = "$CMD" ]; then
        IS_IRREVERSIBLE=true
        break
      fi
    done

    if [ "$IS_IRREVERSIBLE" = true ]; then
      REASON="IRREVERSIBLE write operation detected: $REDIS_CMD. This operation cannot be undone. User confirmation required."
    else
      REASON="Write operation detected: $REDIS_CMD. User confirmation required before execution."
    fi

    cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "ask",
    "permissionDecisionReason": "$REASON"
  }
}
EOF
  else
    cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow",
    "permissionDecisionReason": "Read-only Redis command ($REDIS_CMD), no confirmation needed."
  }
}
EOF
  fi
  exit 0
fi

# For aliyun CLI commands
if echo "$COMMAND" | grep -q "^aliyun "; then
  PRODUCT=$(echo "$COMMAND" | awk '{print $2}')
  ACTION=$(echo "$COMMAND" | awk '{print $3}')

  # Only allow r-kvstore read operations
  if [ "$PRODUCT" = "r-kvstore" ]; then
    ALLOWED_ACTIONS="describe-instances describe-instance-attribute describe-history-monitor-values describe-logic-instance-topology"
    IS_ALLOWED=false
    for ALLOWED in $ALLOWED_ACTIONS; do
      if [ "$ACTION" = "$ALLOWED" ]; then
        IS_ALLOWED=true
        break
      fi
    done
    if [ "$IS_ALLOWED" = true ]; then
      cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow",
    "permissionDecisionReason": "Read-only R-kvstore API ($ACTION), no confirmation needed."
  }
}
EOF
      exit 0
    fi
  fi

  # Check for write operations
  WRITE_PREFIXES="Create Delete Remove Modify Update Attach Detach Grant Revoke Start Stop Reboot Release Allocate Associate Disassociate Enable Disable Reset Resize"

  IS_WRITE=false
  for PREFIX in $WRITE_PREFIXES; do
    if echo "$ACTION" | grep -q "^${PREFIX}"; then
      IS_WRITE=true
      break
    fi
  done

  if [ "$IS_WRITE" = true ]; then
    cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "Write operation API ($ACTION) is not allowed in health inspection mode."
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
  exit 0
fi

# Default: allow
echo '{}'
