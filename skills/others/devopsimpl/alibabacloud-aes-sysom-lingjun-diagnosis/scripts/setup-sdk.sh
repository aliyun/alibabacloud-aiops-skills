#!/bin/bash
# SysOM Alert Destination SDK environment setup script
# Purpose: check Python >= 3.8, create a virtual environment, install the alibabacloud_sysom20231230 SDK
# Usage: bash scripts/setup-sdk.sh

set -e

VENV_DIR=".sysom-sdk-venv"
MIN_PYTHON_VERSION="3.8"
SDK_PACKAGE="alibabacloud_sysom20231230==1.16.0"

echo "🔍 Checking Python environment..."

# Locate an available Python interpreter
PYTHON_CMD=""
for cmd in python3 python; do
    if command -v "$cmd" &>/dev/null; then
        PYTHON_CMD="$cmd"
        break
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    echo "❌ No Python interpreter found. Install Python >= ${MIN_PYTHON_VERSION} first."
    echo "   Installation guide: https://www.python.org/downloads/"
    exit 1
fi

# Check the Python version
PYTHON_VERSION=$($PYTHON_CMD -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PYTHON_MAJOR=$($PYTHON_CMD -c "import sys; print(sys.version_info.major)")
PYTHON_MINOR=$($PYTHON_CMD -c "import sys; print(sys.version_info.minor)")

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 8 ]); then
    echo "❌ Python version too low: found ${PYTHON_VERSION}, requires >= ${MIN_PYTHON_VERSION}"
    echo "   Please upgrade Python: https://www.python.org/downloads/"
    exit 1
fi

echo "✅ Python ${PYTHON_VERSION} meets the requirement (>= ${MIN_PYTHON_VERSION})"

# Resolve the script directory (scripts/); the virtual environment is created at the skill root
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_ROOT="$(dirname "$SCRIPT_DIR")"
VENV_PATH="${SKILL_ROOT}/${VENV_DIR}"

# Create the virtual environment
if [ -d "$VENV_PATH" ]; then
    echo "📦 Virtual environment already exists: ${VENV_PATH}"
else
    echo "📦 Creating virtual environment: ${VENV_PATH}"
    $PYTHON_CMD -m venv "$VENV_PATH"
fi

# Install the SDK into the virtual environment
echo "📥 Installing SDK: ${SDK_PACKAGE}"
"${VENV_PATH}/bin/pip" install --quiet --upgrade pip
"${VENV_PATH}/bin/pip" install --quiet "$SDK_PACKAGE"

# Verify the installation
SDK_VERSION=$("${VENV_PATH}/bin/python" -c "import alibabacloud_sysom20231230; print(alibabacloud_sysom20231230.__version__)")
echo "✅ SDK installed successfully: ${SDK_PACKAGE} v${SDK_VERSION}"
echo ""
echo "📌 To use the SDK later, run Python scripts as follows:"
echo "   ${VENV_PATH}/bin/python scripts/create-alert-destination.py <webhook_url> [name]"
