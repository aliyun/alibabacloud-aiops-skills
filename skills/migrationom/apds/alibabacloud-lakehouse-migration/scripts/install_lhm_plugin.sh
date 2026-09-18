#!/usr/bin/env bash
# 安装 aliyun CLI 的 lhm 插件（本项目网络层依赖，所有 LHM 接口经它调用）。
#
# lhm 插件已公开，直接走公共插件索引安装即可，无需内部源、无需申请权限：
#   aliyun plugin install --names lhm
#
# 仅在公共插件索引不可达（网络受限）时回落到离线包。离线包不随技能包分发
# （技能包内不携带二进制），由运行环境投放，按以下优先级查找：
#   1. $LHM_PLUGIN_PACKAGE   离线包完整路径（显式指定）
#   2. $LHM_PLUGIN_DIR       离线包所在目录（显式指定）
#   3. /eval/data            评测环境统一下发目录（与 credentials.json 的回退约定一致）
#   4. ${SKILL_HOME}/vendor  部署时投放目录
# 包名按平台自动匹配：darwin-amd64 / darwin-arm64 / linux-amd64 / linux-arm64，版本 >= 0.1.1。
#
# 版本要求：>= 0.1.1（0.1.0 缺少部分数据校验命令，校验链路会失败）。
# 公共索引默认安装最新版；确需锁定版本时通过 $LHM_PLUGIN_VERSION 指定。
#
# 更新策略：每次执行都尝试安装/更新，**不因本地已装版本达标而跳过**，
# 以免长期停留在旧版、拿不到公共索引上的最新能力。
# 仅当在线与离线两条路径均失败、且本地已存在 >= MIN_VERSION 的版本时，
# 才沿用旧版并告警继续（exit 0）—— 避免把网络受限但实际可用的环境误判为失败。
#
# 退出码契约：成功 0；任何一项前置条件不满足（CLI 缺失、在线源不可达且无离线包
# 且本地无可用版本、安装后校验失败）均为 1 —— 调用方（SKILL.md Step 2.1 Hard Stop Gate）据此中断整个 skill。
#
# Usage:
#   bash install_lhm_plugin.sh            # 每次都更新：先走公共索引，失败回落离线包
#   bash install_lhm_plugin.sh --offline  # 直接用离线包（同样每次都装）
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_HOME="$(cd "${SCRIPT_DIR}/.." && pwd)"
PLUGIN_NAME="lhm"
MIN_VERSION="0.1.1"
# 公共索引默认安装最新版；仅在需要锁定版本时设置，例如 LHM_PLUGIN_VERSION=0.1.1
VERSION="${LHM_PLUGIN_VERSION:-}"
VENDOR_DIR="${SKILL_HOME}/vendor"
EVAL_PLUGIN_DIR="/eval/data"

# ---------------------------------------------------------------- aliyun CLI
# 沙箱环境中 aliyun CLI 可能被封装为代理，实际调用需要使用 aliyun_real
if command -v aliyun_real >/dev/null 2>&1; then
  ALIYUN_CLI="aliyun_real"
elif command -v aliyun >/dev/null 2>&1; then
  ALIYUN_CLI="aliyun"
else
  case "$(uname -s)" in Darwin) OS="macosx" ;; *) OS="linux" ;; esac
  case "$(uname -m)" in arm64|aarch64) ARCH="arm64" ;; *) ARCH="amd64" ;; esac
  PKG="aliyun-cli-${OS}-latest-${ARCH}.tgz"
  {
    echo "[ERROR] 未检测到 aliyun CLI，请先安装（要求版本 >= 3.3.8）："
    echo "  当前平台：$(uname -s)/$(uname -m)"
    if [ "${OS}" = "macosx" ]; then
      echo "  方式 A（Homebrew，最简）："
      echo "    brew install aliyun-cli"
      echo "  方式 B（官方 CDN 下载）："
    else
      echo "  方式 A（官方 CDN 下载，适用 ECS）："
    fi
    echo "    curl -o /tmp/${PKG} https://aliyuncli.alicdn.com/${PKG}"
    echo "    tar -xzf /tmp/${PKG} -C /tmp"
    echo "    sudo mv /tmp/aliyun /usr/local/bin/ && aliyun version"
    echo "  完整文档：https://help.aliyun.com/zh/cli/installation-guide"
    echo "  装好后重新执行本脚本安装 lhm 插件。"
  } >&2
  exit 1
fi

# ------------------------------------------------------------ 版本检测工具
plugin_manifest() {
  echo "${HOME}/.aliyun/plugins/aliyun-cli-lhm/manifest.json"
}

plugin_version() {
  [ -f "$(plugin_manifest)" ] || return 1
  python3 - "$(plugin_manifest)" <<'PY' 2>/dev/null
import json, sys
try:
    print(json.load(open(sys.argv[1])).get("version", ""))
except Exception:
    pass
PY
}

# 版本比较：$1 >= $2 返回 0
version_ge() {
  [ "$1" = "$2" ] && return 0
  local sorted
  sorted="$(printf '%s\n%s\n' "$1" "$2" | sort -V | head -n1)"
  [ "${sorted}" = "$2" ]
}

# 当前平台对应的离线包文件名；无法识别的平台返回 1
offline_pkg_name() {
  local os arch
  os="$(uname -s)"; arch="$(uname -m)"
  case "${os}/${arch}" in
    Darwin/arm64)                echo "aliyun-cli-lhm-darwin-arm64.tar.gz" ;;
    Darwin/x86_64)               echo "aliyun-cli-lhm-darwin-amd64.tar.gz" ;;
    Linux/x86_64|Linux/amd64)    echo "aliyun-cli-lhm-linux-amd64.tar.gz" ;;
    Linux/arm64|Linux/aarch64)   echo "aliyun-cli-lhm-linux-arm64.tar.gz" ;;
    *) return 1 ;;
  esac
}

# 按优先级在技能包外部查找离线包，命中则输出其绝对路径
offline_pkg_for_platform() {
  local name dir candidate
  name="$(offline_pkg_name)" || return 1
  if [ -n "${LHM_PLUGIN_PACKAGE:-}" ] && [ -f "${LHM_PLUGIN_PACKAGE}" ]; then
    echo "${LHM_PLUGIN_PACKAGE}"; return 0
  fi
  for dir in "${LHM_PLUGIN_DIR:-}" "${EVAL_PLUGIN_DIR}" "${VENDOR_DIR}"; do
    [ -n "${dir}" ] || continue
    candidate="${dir%/}/${name}"
    if [ -f "${candidate}" ]; then echo "${candidate}"; return 0; fi
  done
  return 1
}

install_offline() {
  local pkg name
  pkg="$(offline_pkg_for_platform)" || {
    name="$(offline_pkg_name 2>/dev/null)" || name="aliyun-cli-lhm-<platform>.tar.gz"
    echo "[ERROR] 未找到当前平台（$(uname -s)/$(uname -m)）的 lhm 离线包，已依次查找：" >&2
    echo "          1. \$LHM_PLUGIN_PACKAGE = ${LHM_PLUGIN_PACKAGE:-<未设置>}" >&2
    echo "          2. \$LHM_PLUGIN_DIR/${name} = ${LHM_PLUGIN_DIR:-<未设置>}" >&2
    echo "          3. ${EVAL_PLUGIN_DIR}/${name}" >&2
    echo "          4. ${VENDOR_DIR}/${name}" >&2
    echo "        请将版本 >= ${MIN_VERSION} 的离线包投放到上述任一位置（技能包内不携带二进制），" >&2
    echo "        或在可访问公共插件索引的网络下在线安装：" >&2
    echo "          ${ALIYUN_CLI} plugin install --names ${PLUGIN_NAME}" >&2
    return 1
  }
  if [ ! -f "${pkg}" ]; then
    echo "[ERROR] 离线包不存在: ${pkg}" >&2
    return 1
  fi
  echo "[INFO] 离线安装: ${pkg}"
  ${ALIYUN_CLI} plugin install --package "${pkg}"
}

install_online() {
  echo "[INFO] 在线安装（公共插件索引）..."
  if [ -n "${VERSION}" ]; then
    echo "[INFO] 锁定版本: ${VERSION}"
    ${ALIYUN_CLI} plugin install --names "${PLUGIN_NAME}" --version "${VERSION}"
  else
    ${ALIYUN_CLI} plugin install --names "${PLUGIN_NAME}"
  fi
}

# ------------------------------------------------------------------ 主流程
# 已装版本只用于"更新失败时的兜底判定"与变更提示，不再作为跳过更新的依据。
installed_version=""
if [ -f "$(plugin_manifest)" ]; then
  installed_version="$(plugin_version)"
  echo "[INFO] 检测到已安装 lhm 插件（版本 ${installed_version:-未知}），仍执行更新以获取最新版本..."
else
  echo "[INFO] 本机未安装 lhm 插件，执行安装..."
fi

install_ok=0
if [ "${1:-}" = "--offline" ]; then
  install_offline && install_ok=1
else
  if install_online; then
    install_ok=1
  else
    echo "[WARN] 在线安装/更新失败（网络受限？），回落到离线包..." >&2
    install_offline && install_ok=1
  fi
fi

# ------------------------------------------------------------------ 结果校验
cur=""
[ -f "$(plugin_manifest)" ] && cur="$(plugin_version)"

if [ "${install_ok}" -eq 1 ]; then
  if [ ! -f "$(plugin_manifest)" ]; then
    echo "[ERROR] 安装后仍未找到 lhm 插件（$(plugin_manifest)）" >&2
    exit 1
  fi
  if ! version_ge "${cur}" "${MIN_VERSION}"; then
    echo "[ERROR] 安装后的插件版本 ${cur:-未知} 仍低于 ${MIN_VERSION}，请检查安装源。" >&2
    exit 1
  fi
  if [ -n "${installed_version}" ] && [ "${installed_version}" != "${cur}" ]; then
    echo "[OK] lhm 插件已更新（${installed_version} -> ${cur}）。"
  else
    echo "[OK] lhm 插件安装完成（版本 ${cur}）。"
  fi
  # 成功路径显式返回 0，与所有失败路径的 exit 1 形成明确契约：
  # 调用方（SKILL.md Step 2.1 Hard Stop Gate）据此判定是否中断整个 skill。
  exit 0
fi

# 在线与离线两条路径均失败：仅当本地已有达标版本时才允许沿用，否则中断。
if [ -n "${cur}" ] && version_ge "${cur}" "${MIN_VERSION}"; then
  echo "[WARN] 更新失败，沿用已安装的 lhm 插件（版本 ${cur} >= ${MIN_VERSION}）继续。" >&2
  echo "[WARN] 上述离线包查找失败信息可忽略；如需获取最新版，请在可访问公共插件索引的网络下重试：" >&2
  echo "        ${ALIYUN_CLI} plugin install --names ${PLUGIN_NAME}" >&2
  exit 0
fi

if [ ! -f "$(plugin_manifest)" ]; then
  echo "[ERROR] 更新失败且本机未安装 lhm 插件（$(plugin_manifest)）" >&2
else
  echo "[ERROR] 更新失败，且已装版本 ${cur:-未知} 低于要求的 ${MIN_VERSION}" >&2
fi
echo "        可在可访问公共插件索引的网络下重试：" >&2
echo "          ${ALIYUN_CLI} plugin install --names ${PLUGIN_NAME}" >&2
exit 1
