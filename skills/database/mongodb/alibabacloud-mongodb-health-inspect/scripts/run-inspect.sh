#!/bin/bash
# MongoDB (DDS) Health Inspection — ONLY entry point
# Usage: SKILL_SESSION_ID={session-id} bash scripts/run-inspect.sh [args...]
# Do NOT call health-inspect.py or aliyun CLI directly.
exec python3 "$(dirname "$0")/health-inspect.py" "$@"
