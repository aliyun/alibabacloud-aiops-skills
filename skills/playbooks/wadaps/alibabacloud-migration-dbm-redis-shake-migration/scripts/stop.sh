#!/bin/bash
# RedisShake 停止脚本（幂等）
# 用法: bash stop.sh [shake_dir]

set -euo pipefail

SHAKE_DIR="${1:-$(cd "$(dirname "$0")/.." && pwd)}"
PID_FILE="$SHAKE_DIR/data/shake.pid"

if [ ! -f "$PID_FILE" ]; then
    # 兜底：按进程名杀
    if pkill -f "redis-shake shake.toml"; then
        echo "Stopped (via pkill)."
    else
        echo "Not running."
    fi
    exit 0
fi

PID=$(cat "$PID_FILE")
if kill -0 "$PID" 2>/dev/null; then
    kill "$PID"
    rm -f "$PID_FILE"
    echo "Stopped, PID: $PID"
else
    echo "Not running, cleaning stale PID file."
    rm -f "$PID_FILE"
fi
