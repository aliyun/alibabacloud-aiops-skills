#!/usr/bin/env bash
# uninstall.sh - Uninstall lhm-sch-ds-cli global tool
set -euo pipefail

TOOL_NAME="lhm-sch-ds-cli"

echo "🗑️  Uninstalling ${TOOL_NAME}..."

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "❌ Error: 'uv' is not installed."
    echo "   Cannot uninstall without uv."
    exit 1
fi

# Check if tool is installed
if ! uv tool list | grep -q "$TOOL_NAME"; then
    echo "⚠️  ${TOOL_NAME} is not installed. Nothing to uninstall."
    exit 0
fi

# Uninstall the tool
echo "📦 Removing ${TOOL_NAME}..."
if uv tool uninstall "$TOOL_NAME"; then
    echo ""
    echo "✅ Uninstallation successful!"
    echo "   The 'lhm-sch-ds' command has been removed."
else
    echo "❌ Uninstallation failed. Please check the error messages above."
    exit 1
fi
