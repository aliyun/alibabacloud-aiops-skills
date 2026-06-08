#!/bin/bash
# SysOM SDK environment bootstrap script
# Purpose: Detect Python >= 3.8, create a virtual environment, and install the alibabacloud_sysom20231230 SDK
# Usage:   bash scripts/setup-sdk.sh

set -e

VENV_DIR=".sysom-sdk-venv"
MIN_PYTHON_VERSION="3.8"
# Pinned dependencies installed into the virtual environment.
# Keep these in sync with the docstring of scripts/create-cluster-vpc-endpoint-connection.py.
SDK_PACKAGE="alibabacloud_sysom20231230==1.18.0"
TEA_OPENAPI_PACKAGE="alibabacloud_tea_openapi==0.3.12"
CREDENTIALS_PACKAGE="alibabacloud_credentials>=1.0.2"

echo "Detecting Python environment..."

# Locate an available Python interpreter
PYTHON_CMD=""
for cmd in python3 python; do
    if command -v "$cmd" &>/dev/null; then
        PYTHON_CMD="$cmd"
        break
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    echo "ERROR: Python interpreter not found. Please install Python >= ${MIN_PYTHON_VERSION}." >&2
    echo "  Install guide: https://www.python.org/downloads/" >&2
    echo "  After installing, ensure 'python3' is on PATH and re-run: bash scripts/setup-sdk.sh" >&2
    exit 1
fi

# Detect Python version
PYTHON_VERSION=$($PYTHON_CMD -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PYTHON_MAJOR=$($PYTHON_CMD -c "import sys; print(sys.version_info.major)")
PYTHON_MINOR=$($PYTHON_CMD -c "import sys; print(sys.version_info.minor)")

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 8 ]); then
    echo "ERROR: Python version ${PYTHON_VERSION} is too low. Required: >= ${MIN_PYTHON_VERSION}." >&2
    echo "  Upgrade guide: https://www.python.org/downloads/" >&2
    echo "  After upgrading, re-run: bash scripts/setup-sdk.sh" >&2
    exit 1
fi

echo "Python ${PYTHON_VERSION} satisfies the minimum requirement (>= ${MIN_PYTHON_VERSION})."

# The script lives in scripts/; the virtual environment is created at the skill root.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_ROOT="$(dirname "$SCRIPT_DIR")"
VENV_PATH="${SKILL_ROOT}/${VENV_DIR}"

# Create the virtual environment
if [ -d "$VENV_PATH" ]; then
    echo "Virtual environment already exists: ${VENV_PATH}"
else
    echo "Creating virtual environment: ${VENV_PATH}"
    if ! $PYTHON_CMD -m venv "$VENV_PATH"; then
        echo "ERROR: Failed to create virtual environment at ${VENV_PATH}." >&2
        echo "  Possible cause: 'venv' module missing (Debian/Ubuntu: 'apt-get install python3-venv')." >&2
        echo "  Or insufficient disk space / permissions on ${SKILL_ROOT}." >&2
        exit 1
    fi
fi

# Install the SDK and its pinned dependencies into the virtual environment
echo "Installing pinned dependencies: ${SDK_PACKAGE}, ${TEA_OPENAPI_PACKAGE}, ${CREDENTIALS_PACKAGE}"
if ! "${VENV_PATH}/bin/pip" install --quiet --upgrade pip; then
    echo "ERROR: Failed to upgrade pip in ${VENV_PATH}." >&2
    echo "  Check network connectivity to PyPI (https://pypi.org)." >&2
    echo "  If behind a proxy, export HTTPS_PROXY before re-running." >&2
    exit 1
fi
if ! "${VENV_PATH}/bin/pip" install --quiet "$SDK_PACKAGE" "$TEA_OPENAPI_PACKAGE" "$CREDENTIALS_PACKAGE"; then
    echo "ERROR: Failed to install ${SDK_PACKAGE}, ${TEA_OPENAPI_PACKAGE}, and/or ${CREDENTIALS_PACKAGE}." >&2
    echo "  Check network connectivity to PyPI (https://pypi.org)." >&2
    echo "  Retry with verbose output: ${VENV_PATH}/bin/pip install ${SDK_PACKAGE} ${TEA_OPENAPI_PACKAGE} ${CREDENTIALS_PACKAGE}" >&2
    exit 1
fi

# Verify the installation
SDK_VERSION=$("${VENV_PATH}/bin/python" -c "import alibabacloud_sysom20231230; print(alibabacloud_sysom20231230.__version__)")
echo "SDK installation successful: ${SDK_PACKAGE} v${SDK_VERSION}"
echo "Tea OpenAPI installed: ${TEA_OPENAPI_PACKAGE}"
echo "Credentials installed: ${CREDENTIALS_PACKAGE}"
echo ""
echo "To run SDK-based scripts, use the venv interpreter explicitly, for example:"
echo "  ${VENV_PATH}/bin/python scripts/create-cluster-vpc-endpoint-connection.py --region <region> --cluster-id <cluster_id> [--dry-run]"
