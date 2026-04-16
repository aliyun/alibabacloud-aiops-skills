#!/usr/bin/env bash
# OS-Ops CLI Initialization Script
# Automatically setup the shared CLI environment

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# sysom-diagnosis/（技能根）
SKILL_ROOT="$(dirname "$SCRIPT_DIR")"

# Work in scripts directory where pyproject.toml is
cd "$SCRIPT_DIR"

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║        OS-Ops CLI Initialization                             ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Check Python version
echo "📋 Checking prerequisites..."
if ! command -v python3 &>/dev/null; then
    echo "❌ Python 3 is required but not found"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | awk '{print $2}')
echo "  ✓ Python $PYTHON_VERSION found"

# Check if uv is available
UV_AVAILABLE=false
if command -v uv &>/dev/null; then
    UV_VERSION=$(uv --version | awk '{print $2}')
    echo "  ✓ uv $UV_VERSION found (recommended)"
    UV_AVAILABLE=true
else
    echo "  ℹ uv not found (will use pip + venv)"
    echo "    Install uv for better experience: curl -LsSf https://astral.sh/uv/install.sh | sh"
fi

echo ""
echo "🔧 Setting up environment..."

# Method 1: Use uv (fastest)
if [ "$UV_AVAILABLE" = true ]; then
    echo "  Using uv for dependency management..."
    
    # Sync dependencies
    uv sync --quiet
    
    echo ""
    echo "✅ Setup complete!"
    echo ""
    echo "📚 Available commands:"
    echo "  uv run osops --help                    # Show all commands"
    echo "  uv run osops precheck                  # Verify SysOM credentials"
    echo "  uv run osops memory oom --deep-diagnosis ...  # 快速排查 + 远程专项（示例）"
    echo "  # 维护者 OpenAPI 直调：见 references/invoke-diagnosis.md"
    echo ""
    echo "🎯 Quick start:"
    echo "  cd $SKILL_ROOT"
    echo "  export PYTHONPATH=\"$SCRIPT_DIR:\$PYTHONPATH\""
    echo "  uv run --directory scripts osops precheck"
    echo "  # Or use wrapper:"
    echo "  ./scripts/osops.sh precheck"
    echo ""

    exit 0
fi

# Method 2: Use pip + venv
echo "  Using pip + venv..."

# Create venv if not exists
if [[ ! -d ".venv" ]]; then
    python3 -m venv .venv
    echo "    Created virtual environment: .venv/"
fi

# Activate and install
source .venv/bin/activate
pip install --quiet --upgrade pip
pip install --quiet -e .

echo ""
echo "✅ Setup complete!"
echo ""
echo "📚 Available commands:"
echo "  source .venv/bin/activate              # Activate venv"
echo "  osops --help                           # Show all commands"
echo "  osops precheck                         # Verify SysOM credentials"
echo "  osops memory classify --deep-diagnosis ...   # 内存：快速 + 远程专项（示例）"
echo "  # 维护者 OpenAPI 直调：见 references/invoke-diagnosis.md"
echo ""
echo "🎯 Quick start:"
echo "  cd $SKILL_ROOT"
echo "  export PYTHONPATH=\"$SCRIPT_DIR:\$PYTHONPATH\""
echo "  # Use wrapper (recommended):"
echo "  ./scripts/osops.sh precheck"
echo "  # Or activate venv:"
echo "  source scripts/.venv/bin/activate"
echo "  osops precheck"
echo ""
