#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_ROOT="$(dirname "$SCRIPT_DIR")"

if command -v uv >/dev/null 2>&1; then
    exec uv run --directory "$SCRIPT_DIR" python -m sysom_cli "$@"
fi

if [[ -f "$SCRIPT_DIR/.venv/bin/python" ]]; then
    export PYTHONPATH="$SCRIPT_DIR:${PYTHONPATH:-}"
    exec "$SCRIPT_DIR/.venv/bin/python" -m sysom_cli "$@"
fi

if command -v sysom-inspection >/dev/null 2>&1; then
    exec sysom-inspection "$@"
fi

cat >&2 <<EOF
[ERROR] SysOM inspection CLI not initialized

Please run:
  cd $SKILL_ROOT
  ./scripts/init.sh
EOF
exit 1
