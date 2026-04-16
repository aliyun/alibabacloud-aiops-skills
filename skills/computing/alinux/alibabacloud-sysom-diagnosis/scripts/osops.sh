#!/usr/bin/env bash
# OS-Ops CLI Wrapper
# Universal entry point for all osops commands

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# sysom-diagnosis/（技能根）：scripts → .
SKILL_ROOT="$(dirname "$SCRIPT_DIR")"

# Try uv first (fastest)
if command -v uv &>/dev/null; then
    exec uv run --directory "$SCRIPT_DIR" python -m sysom_cli "$@"
fi

# Try venv in scripts directory
if [[ -f "$SCRIPT_DIR/.venv/bin/python" ]]; then
    export PYTHONPATH="$SCRIPT_DIR:${PYTHONPATH:-}"
    exec "$SCRIPT_DIR/.venv/bin/python" -m sysom_cli "$@"
fi

# Try installed command
if command -v osops &>/dev/null; then
    exec osops "$@"
fi

# Not initialized
cat >&2 <<EOF
[ERROR] OS-Ops CLI not initialized

Please run initialization first:
  cd $SKILL_ROOT
  ./scripts/init.sh

Or install manually:
  cd $SCRIPT_DIR
  pip install -e .
EOF
exit 1
