#!/bin/bash
# RedisShake 启动脚本（幂等）
# 用法: bash start.sh [shake_dir]
# 默认 shake_dir 为脚本所在目录的上级（即 /opt/redis-shake）

set -euo pipefail

SHAKE_DIR="${1:-$(cd "$(dirname "$0")/.." && pwd)}"
cd "$SHAKE_DIR" && mkdir -p data

# 幂等检查：已在运行则直接退出
if [ -f data/shake.pid ] && kill -0 "$(cat data/shake.pid)" 2>/dev/null; then
    echo "Already running, PID: $(cat data/shake.pid)"
    exit 1
fi

# 校验二进制与配置存在
[ -x ./redis-shake ] || { echo "redis-shake binary not found or not executable"; exit 2; }
[ -f ./shake.toml ]  || { echo "shake.toml not found"; exit 2; }

nohup ./redis-shake shake.toml > data/shake.log 2>&1 &
echo $! > data/shake.pid
echo "Started, PID: $(cat data/shake.pid)"
