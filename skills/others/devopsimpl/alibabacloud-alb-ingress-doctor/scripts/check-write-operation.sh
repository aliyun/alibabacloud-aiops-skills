#!/bin/bash
# check-write-operation.sh
# 检查 kubectl / aliyun CLI 命令是否为写操作，写操作需要用户确认
#
# 读操作 (自动放行): kubectl get, kubectl describe, kubectl version, kubectl cluster-info, aliyun Describe/List/Get
# 写操作 (需确认):   kubectl edit, kubectl patch, kubectl apply, kubectl delete, aliyun Create/Delete/Modify/...

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_input',{}).get('command',''))" 2>/dev/null)

# 如果无法解析命令，直接放行
if [ -z "$COMMAND" ]; then
  echo '{}'
  exit 0
fi

# ============================================================
# 检查 kubectl 写操作
# ============================================================
if echo "$COMMAND" | grep -q "kubectl"; then
  # kubectl 写操作子命令列表
  KUBECTL_WRITE_CMDS="edit patch apply delete create replace scale annotate label taint cordon drain uncordon"

  IS_WRITE=false
  for SUBCMD in $KUBECTL_WRITE_CMDS; do
    if echo "$COMMAND" | grep -qE "kubectl\s+$SUBCMD(\s|$)"; then
      IS_WRITE=true
      break
    fi
  done

  if [ "$IS_WRITE" = true ]; then
    # 对不可逆操作增加醒目提示
    IRREVERSIBLE_CMDS="delete"
    IS_IRREVERSIBLE=false
    for ICMD in $IRREVERSIBLE_CMDS; do
      if echo "$COMMAND" | grep -qE "kubectl\s+$ICMD(\s|$)"; then
        IS_IRREVERSIBLE=true
        break
      fi
    done

    if [ "$IS_IRREVERSIBLE" = true ]; then
      cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "ask",
    "permissionDecisionReason": "[不可逆操作] 检测到 kubectl 写操作 ($SUBCMD), 此操作不可逆, 删除后资源无法恢复, 请确认是否执行"
  }
}
EOF
    else
      cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "ask",
    "permissionDecisionReason": "检测到 kubectl 写操作 ($SUBCMD)，修改集群资源前需要用户确认"
  }
}
EOF
    fi
    exit 0
  fi

  # kubectl 读操作，直接放行
  echo '{}'
  exit 0
fi

# ============================================================
# 检查 aliyun CLI 写操作
# ============================================================
if echo "$COMMAND" | grep -q "^aliyun "; then
  ACTION=$(echo "$COMMAND" | awk '{print $3}')

  WRITE_PREFIXES="Create Delete Remove Modify Update Attach Detach Grant Revoke Start Stop Reboot Release Allocate Associate Disassociate Enable Disable Reset Resize"

  IS_WRITE=false
  for PREFIX in $WRITE_PREFIXES; do
    if echo "$ACTION" | grep -q "^${PREFIX}"; then
      IS_WRITE=true
      break
    fi
  done

  if [ "$IS_WRITE" = true ]; then
    # 对不可逆操作增加醒目提示
    IS_IRREVERSIBLE=false
    for IPREFIX in Delete Remove Release; do
      if echo "$ACTION" | grep -q "^${IPREFIX}"; then
        IS_IRREVERSIBLE=true
        break
      fi
    done

    if [ "$IS_IRREVERSIBLE" = true ]; then
      cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "ask",
    "permissionDecisionReason": "[不可逆操作] 检测到写操作 API 调用 ($ACTION), 此操作不可逆, 资源删除/释放后无法恢复, 请确认是否执行"
  }
}
EOF
    else
      cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "ask",
    "permissionDecisionReason": "检测到写操作 API 调用 ($ACTION)，需要用户确认后才能执行"
  }
}
EOF
    fi
    exit 0
  fi

  # aliyun 读操作，直接放行
  echo '{}'
  exit 0
fi

# 其他命令（bash diagnose.sh 等），直接放行
echo '{}'
