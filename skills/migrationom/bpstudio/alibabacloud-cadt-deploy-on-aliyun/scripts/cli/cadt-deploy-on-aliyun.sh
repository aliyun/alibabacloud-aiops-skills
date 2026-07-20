#!/bin/bash
set -e

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPTS_DIR="$SKILL_DIR"
VENV="$HOME/.cache/cadt-skills/cadt-deploy-on-aliyun/.venv"
HASH_FILE="$VENV/.hash"

if command -v sha256sum &> /dev/null; then
    REQ_HASH=$(sha256sum "$SCRIPTS_DIR/pyproject.toml" | cut -d' ' -f1)
elif command -v shasum &> /dev/null; then
    REQ_HASH=$(shasum -a 256 "$SCRIPTS_DIR/pyproject.toml" | cut -d' ' -f1)
else
    echo "Error: sha256sum or shasum not found" >&2
    exit 1
fi

NEED_REBUILD=false
if [ ! -d "$VENV" ]; then
    NEED_REBUILD=true
    echo "Creating virtual environment..." >&2
elif [ ! -f "$HASH_FILE" ]; then
    NEED_REBUILD=true
    echo "Hash file not found, rebuilding virtual environment..." >&2
elif [ "$(cat "$HASH_FILE")" != "$REQ_HASH" ]; then
    NEED_REBUILD=true
    echo "Dependencies changed, rebuilding virtual environment..." >&2
fi

if [ "$NEED_REBUILD" = true ]; then
    rm -rf "$VENV"
    python3 -m venv "$VENV"

    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
        "$VENV/Scripts/pip" install --upgrade pip
        "$VENV/Scripts/pip" install -e "$SCRIPTS_DIR"
    else
        "$VENV/bin/pip" install --upgrade pip
        "$VENV/bin/pip" install -e "$SCRIPTS_DIR"
    fi

    mkdir -p "$VENV"
    echo "$REQ_HASH" > "$HASH_FILE"
    echo "Virtual environment setup complete!" >&2
fi

mkdir -p "$HOME/.local/bin"
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    ln -sf "$VENV/Scripts/cadt-deploy-on-aliyun" "$HOME/.local/bin/cadt-deploy-on-aliyun"
else
    ln -sf "$VENV/bin/cadt-deploy-on-aliyun" "$HOME/.local/bin/cadt-deploy-on-aliyun"
fi

if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    exec "$VENV/Scripts/cadt-deploy-on-aliyun" "$@"
else
    exec "$VENV/bin/cadt-deploy-on-aliyun" "$@"
fi
