#!/bin/bash
# RedisShake 状态查询脚本（只读操作）
# 用法: bash status.sh [shake_dir]

set -euo pipefail

SHAKE_DIR="${1:-$(cd "$(dirname "$0")/.." && pwd)}"
PID_FILE="$SHAKE_DIR/data/shake.pid"
LOG_FILE="$SHAKE_DIR/data/shake.log"

echo "=== RedisShake Status ==="
if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
    PID=$(cat "$PID_FILE")
    echo "Status: RUNNING | PID: $PID"
    echo "Uptime: $(ps -o etime= -p "$PID" 2>/dev/null | tr -d ' ')"
else
    echo "Status: STOPPED"
fi

echo ""
echo "=== Recent Logs (last 20 lines) ==="
if [ -f "$LOG_FILE" ]; then
    tail -20 "$LOG_FILE"
else
    echo "No log file: $LOG_FILE"
fi
