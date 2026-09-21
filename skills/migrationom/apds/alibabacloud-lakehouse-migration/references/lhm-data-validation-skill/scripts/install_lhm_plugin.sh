#!/usr/bin/env bash
# 安装 aliyun CLI 的 lhm 插件（本项目网络层依赖，所有 LHM 接口经它调用）。
#
# lhm 插件已公开，直接走公共插件索引在线安装即可，无需内部源、无需申请权限：
#   aliyun plugin install --names lhm
#
# 始终安装最新版：不再支持离线包安装，也不再支持锁定版本，插件来源唯一——公共插件索引。
#
# 更新策略：每次执行都尝试安装/更新，**不因本地已装版本达标而跳过**，
# 以免长期停留在旧版、拿不到公共索引上的最新能力。
# 仅当在线安装失败、且本地已存在 >= MIN_VERSION 的版本时，才沿用旧版并告警继续
# （exit 0）—— 避免把网络抖动但实际可用的环境误判为失败。
#
# 退出码契约：成功 0；任何一项前置条件不满足（CLI 缺失、在线源不可达且本地无
# 可用版本、安装后校验失败）均为 1 —— 调用方（SKILL.md Step 2.1 Hard Stop Gate）据此中断整个 skill。
#
# Usage:
#   bash install_lhm_plugin.sh            # 每次都更新：走公共插件索引在线安装最新版
set -uo pipefail

PLUGIN_NAME="lhm"
MIN_VERSION="0.1.1"
# aliyun CLI 插件仓库地址（公共插件索引）
PLUGIN_SOURCE_BASE="https://aliyuncli.alicdn.com/plugins"

# ---------------------------------------------- LHM API 版本环境变量
# lhm 插件调用 LHM 接口时需固定 API 版本：已设置则沿用，未设置则导入默认值。
# export 后本脚本内发起的所有 aliyun CLI 调用（子进程）都会继承该变量。
if [ -n "${ALIBABA_CLOUD_LHM_API_VERSION:-}" ]; then
  echo "[INFO] 沿用已设置的环境变量 ALIBABA_CLOUD_LHM_API_VERSION=${ALIBABA_CLOUD_LHM_API_VERSION}"
else
  export ALIBABA_CLOUD_LHM_API_VERSION="2025-01-16"
  echo "[INFO] 未检测到 ALIBABA_CLOUD_LHM_API_VERSION，已导入默认值：${ALIBABA_CLOUD_LHM_API_VERSION}"
fi

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

# ---------------------------------------------- 配置插件仓库地址
# aliyun CLI 存在时，将插件仓库地址指向公共插件索引，保证后续在线安装走该源。
echo "[INFO] 配置插件仓库地址: ${PLUGIN_SOURCE_BASE}"
if ${ALIYUN_CLI} configure plugin-settings set --source-base "${PLUGIN_SOURCE_BASE}"; then
  echo "[OK] 插件仓库地址配置成功。"
else
  echo "[WARN] 插件仓库地址配置失败，将沿用 aliyun CLI 现有配置继续。" >&2
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

install_online() {
  echo "[INFO] 在线安装最新版（公共插件索引）..."
  ${ALIYUN_CLI} plugin install --names "${PLUGIN_NAME}"
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
if install_online; then
  install_ok=1
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

# 在线安装失败：仅当本地已有达标版本时才允许沿用，否则中断。
if [ -n "${cur}" ] && version_ge "${cur}" "${MIN_VERSION}"; then
  echo "[WARN] 在线安装/更新失败（网络受限？），沿用已安装的 lhm 插件（版本 ${cur} >= ${MIN_VERSION}）继续。" >&2
  echo "[WARN] 如需获取最新版，请在可访问公共插件索引的网络下重试：" >&2
  echo "        ${ALIYUN_CLI} plugin install --names ${PLUGIN_NAME}" >&2
  exit 0
fi

if [ ! -f "$(plugin_manifest)" ]; then
  echo "[ERROR] 在线安装失败且本机未安装 lhm 插件（$(plugin_manifest)）" >&2
else
  echo "[ERROR] 在线安装失败，且已装版本 ${cur:-未知} 低于要求的 ${MIN_VERSION}" >&2
fi
echo "        请在可访问公共插件索引的网络下重试：" >&2
echo "          ${ALIYUN_CLI} plugin install --names ${PLUGIN_NAME}" >&2
exit 1
