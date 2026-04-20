#!/bin/bash
# SysOM Alert Destination SDK 环境初始化脚本
# 功能：检测 Python 版本 >= 3.8，创建虚拟环境，安装 alibabacloud_sysom20231230 SDK
# 用法：bash scripts/setup-sdk.sh

set -e

VENV_DIR=".sysom-sdk-venv"
MIN_PYTHON_VERSION="3.8"
SDK_PACKAGE="alibabacloud_sysom20231230==1.16.0"

echo "🔍 检测 Python 环境..."

# 查找可用的 Python 解释器
PYTHON_CMD=""
for cmd in python3 python; do
    if command -v "$cmd" &>/dev/null; then
        PYTHON_CMD="$cmd"
        break
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    echo "❌ 未找到 Python 解释器，请先安装 Python >= ${MIN_PYTHON_VERSION}"
    echo "   安装指南：https://www.python.org/downloads/"
    exit 1
fi

# 检测 Python 版本
PYTHON_VERSION=$($PYTHON_CMD -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PYTHON_MAJOR=$($PYTHON_CMD -c "import sys; print(sys.version_info.major)")
PYTHON_MINOR=$($PYTHON_CMD -c "import sys; print(sys.version_info.minor)")

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 8 ]); then
    echo "❌ Python 版本过低：当前 ${PYTHON_VERSION}，要求 >= ${MIN_PYTHON_VERSION}"
    echo "   请升级 Python：https://www.python.org/downloads/"
    exit 1
fi

echo "✅ Python ${PYTHON_VERSION} 满足要求（>= ${MIN_PYTHON_VERSION}）"

# 确定脚本所在目录（scripts/），虚拟环境创建在 skill 根目录
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_ROOT="$(dirname "$SCRIPT_DIR")"
VENV_PATH="${SKILL_ROOT}/${VENV_DIR}"

# 创建虚拟环境
if [ -d "$VENV_PATH" ]; then
    echo "📦 虚拟环境已存在：${VENV_PATH}"
else
    echo "📦 创建虚拟环境：${VENV_PATH}"
    $PYTHON_CMD -m venv "$VENV_PATH"
fi

# 激活虚拟环境并安装 SDK
echo "📥 安装 SDK：${SDK_PACKAGE}"
"${VENV_PATH}/bin/pip" install --quiet --upgrade pip
"${VENV_PATH}/bin/pip" install --quiet "$SDK_PACKAGE"

# 验证安装
SDK_VERSION=$("${VENV_PATH}/bin/python" -c "import alibabacloud_sysom20231230; print(alibabacloud_sysom20231230.__version__)")
echo "✅ SDK 安装成功：${SDK_PACKAGE} v${SDK_VERSION}"
echo ""
echo "📌 后续使用 SDK 时，请通过以下方式运行 Python 脚本："
echo "   ${VENV_PATH}/bin/python scripts/create-alert-destination.py <webhook_url> [name]"
