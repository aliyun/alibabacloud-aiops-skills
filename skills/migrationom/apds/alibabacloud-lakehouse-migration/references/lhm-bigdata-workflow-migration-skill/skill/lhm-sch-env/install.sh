#!/usr/bin/env bash
# install.sh - Install lhm-sch-env-cli as a global tool using uv
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOOL_NAME="lhm-sch-env-cli"

echo "🔧 Installing ${TOOL_NAME}..."

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "❌ Error: 'uv' is not installed."
    echo "   Please install uv first: https://docs.astral.sh/uv/getting-started/installation/"
    exit 1
fi

# Navigate to project directory (pyproject.toml is one level up from scripts/)
cd "$SCRIPT_DIR"

# Install as global tool
echo "📦 Installing dependencies and CLI entry point..."
if uv tool install . --force; then
    echo ""
    echo "✅ Installation successful!"
    echo ""
    echo "You can now use the CLI:"
    echo "  lhm-sch-env --help"
    echo "  lhm-sch-env check --profile schedule"
    echo ""
else
    echo "❌ Installation failed. Please check the error messages above."
    exit 1
fi
