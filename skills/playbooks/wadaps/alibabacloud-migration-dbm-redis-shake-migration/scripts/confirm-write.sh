#!/bin/bash
# PreToolUse Hook: 拦截写操作要求用户确认
# 输入: Hook 系统通过 stdin 传入 JSON，包含即将执行的 Bash 命令
# 输出: JSON { "decision": "allow" | "ask", "reason": "..." }
#
# 规则:
#   - 命中高危/写操作关键字 -> ask（要求用户确认）
#   - 其他纯读命令 -> allow

set -eo pipefail

# 读取 stdin 中的命令内容（兼容多种 Hook 实现，允许命令直接作为 $1）
INPUT="${*:-$(cat)}"
CMD=$(echo "$INPUT" | tr -d '\n' | tr '[:upper:]' '[:lower:]')

# 高危写操作关键字（任何一条命中 -> ask）
DANGEROUS_PATTERNS=(
    "empty_db_before_sync *= *true"   # 清空目标端
    "systemctl +(start|stop|restart|enable|disable)"  # systemd 服务变更
    "kill +-[0-9]+"                    # 强杀进程
    "kill +[0-9]+"                     # kill 进程
    "pkill "                           # pkill
    "rm +-rf? "                        # 递归删除
    "rm +-f "                          # 强制删除
    "chmod "                           # 权限变更
    "cat +> +"                         # 文件写入
    "tee "                             # 文件写入
    "scp "                             # 文件传输
    "> */etc/"                         # 写入系统目录
    "sudo "                            # sudo 操作
    "flushall"                         # Redis 清库
    "flushdb"
)

for pattern in "${DANGEROUS_PATTERNS[@]}"; do
    if echo "$CMD" | grep -Eq "$pattern"; then
        cat <<EOF
{"decision": "ask", "reason": "检测到写操作或高危命令（匹配: $pattern），请用户确认后执行。"}
EOF
        exit 0
    fi
done

# 默认放行（读操作）
echo '{"decision": "allow"}'
