#!/usr/bin/env bash
# ============================================================
# get_token.sh — 获取 AgentHub AccessToken 并缓存
#
# 用法:
#   ./get_token.sh login CN
#   ./get_token.sh refresh CN
#
# 流程:
#   Step 0: 校验来源锁；未过期且来源已锁定的 Token 可直接复用
#   Step 1: 需要刷新时使用锁定来源；首次初始化要求显式选择来源
#           - 已锁定来源仍可用：继续使用
#           - 首次选择：aliyun CLI 或 AgentHub OAuth，由用户明确指定
#   Step 2: 按来源调用 GenerateAccessToken 并缓存响应
# ============================================================
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ALIYUN_AGENTHUB_DIR="$HOME/.aliyun_agenthub"

TOKEN_EXPIRY_BUFFER=60
CLIENT_ID="4081417976505782102"
AUTH_REQUIRED_EXIT_CODE=20
SCOPE="/internal/agenthub"
SITE="CN"
RAMOAUTH_ENDPOINT="ramoauth.aliyuncs.com"

TOKEN_MARK_BEGIN="===A2A_TOKEN_BEGIN==="
TOKEN_MARK_END="===A2A_TOKEN_END==="

ALIYUN_CLI_CONFIG_FILE="${ALIYUN_CONFIG_FILE:-$HOME/.aliyun/config.json}"
OFFICIAL_ALIYUN_CLI_CONFIG_FILE="$HOME/.aliyun/config.json"
AGENTHUB_CONFIG_FILE="${ALIYUN_AGENTHUB_CONFIG_FILE:-$HOME/.aliyun_agenthub/config.json}"

CMD=""
REQUESTED_CREDENTIAL_SOURCE=""

CREDENTIAL_PROVIDER=""
CREDENTIAL_CONFIG_FILE=""
ALIYUN_PROFILE_NAME=""
PROFILE_MODE=""
SOURCE_LOCKED=false

resolve_cache_file() {
  CACHE_FILE="${ALIYUN_AGENTHUB_DIR}/CN_credential"
}

emit_token() {
  local token="$1"
  printf '\n%s\n%s\n%s\n\n' "$TOKEN_MARK_BEGIN" "$token" "$TOKEN_MARK_END"
}

usage() {
  cat <<'EOF'
用法:
  ./get_token.sh login CN [--credential-source aliyun_cli|agenthub_oauth]
  ./get_token.sh refresh CN [--credential-source aliyun_cli|agenthub_oauth]

命令:
  login     获取 Token（优先复用未过期缓存）
  refresh   跳过 Token 缓存，沿用已锁定凭证来源重新获取 Token

凭证来源:
  首次初始化必须明确选择：
    aliyun_cli     复用 aliyun CLI profile；读取 ALIYUN_AGENTHUB_CLI_PROFILE，未设置时使用 default
    agenthub_oauth 使用 AgentHub 私有 OAuth profile

  第一次成功获取 Token 后锁定来源；后续 login/refresh 可省略 --credential-source。
EOF
  exit 0
}

parse_args() {
  if [[ ${1:-} == "-h" || ${1:-} == "--help" ]]; then
    usage
  fi
  case ${1:-} in
    login|refresh) CMD="$1" ;;
    *) echo "[ERROR] 命令必须是 login 或 refresh。" >&2; exit 2 ;;
  esac
  shift
  if [[ $# -gt 0 ]]; then
    if [[ "$1" != "CN" ]]; then
      echo "[ERROR] 当前版本只支持中国站 CN。" >&2
      exit 2
    fi
    shift
  fi
  if [[ $# -gt 0 ]]; then
    if [[ "$1" != "--credential-source" ]]; then
      echo "[ERROR] 未知参数: $1" >&2
      exit 2
    fi
    if [[ $# -lt 2 ]]; then
      echo "[ERROR] --credential-source 缺少值。" >&2
      exit 2
    fi
    case "$2" in
      aliyun_cli|agenthub_oauth) REQUESTED_CREDENTIAL_SOURCE="$2" ;;
      *) echo "[ERROR] --credential-source 只支持 aliyun_cli 或 agenthub_oauth。" >&2; exit 2 ;;
    esac
    shift 2
  fi
  if [[ $# -gt 0 ]]; then
    echo "[ERROR] 未知参数: $1" >&2
    exit 2
  fi
}

die() {
  echo "ERROR: $*" >&2
  exit 1
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "required command not found: $1"
}

observability_user_agent() {
  local session_id="${SKILL_SESSION_ID:-}"
  if [[ ! "$session_id" =~ ^[0-9a-f]{32}$ ]]; then
    echo "[ERROR] SKILL_SESSION_ID 必须是当前会话首次生成并持续复用的 32 位小写十六进制字符串。" >&2
    return 2
  fi
  printf '%s\n' "AlibabaCloud-Agent-Skills/alibabacloud-remote-skills-connector/$session_id"
}

url_encode() {
  "$AGENTHUB_PYTHON" - "$1" <<'PY'
import sys
from urllib.parse import quote

print(quote(sys.argv[1], safe=""))
PY
}

default_assignment_url() {
  echo "https://ram.console.aliyun.com/applications/$CLIENT_ID?appType=ThirdPartyApp"
}

admin_consent_url() {
  local assignment_url="$1"
  local encoded_callback
  encoded_callback="$(url_encode "$assignment_url")"
  echo "https://signin.aliyun.com/oauth2/v1/adminConsent?clientId=$CLIENT_ID&callback=$encoded_callback"
}

open_url_in_browser() {
  local url="$1"
  case "${ALIYUN_AGENTHUB_AUTO_OPEN_BROWSER:-1}" in
    0|false|False|FALSE|no|No|NO) return 1 ;;
  esac
  if command -v open >/dev/null 2>&1; then
    open "$url" >/dev/null 2>&1 && return 0
  fi
  if command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$url" >/dev/null 2>&1 && return 0
  fi
  "$AGENTHUB_PYTHON" -m webbrowser "$url" >/dev/null 2>&1 && return 0
  return 1
}

is_smart_gateway_oauth_app_error() {
  local text="$1"
  printf '%s' "$text" | grep -Eiq \
    '(^|[[:space:]])ErrorCode:[[:space:]]*consent_required([[:space:]]|$)' || return 1
  printf '%s' "$text" | grep -Eiq \
    '(^|[[:space:]])Message:[[:space:]]*Application is not provisioned, consent required([[:space:]]|$)'
}

print_smart_gateway_admin_consent_guidance() {
  local raw_error="$1"
  local assignment_url consent_url
  assignment_url="$(default_assignment_url)"
  consent_url="$(admin_consent_url "$assignment_url")"
  echo "[提示] AgentHub OAuth 应用还没有完成安装或授权。" >&2
  echo "[提示] 我会尝试打开浏览器，引导管理员安装第三方应用、授权并分配给当前 OAuth 登录身份。" >&2
  if open_url_in_browser "$consent_url"; then
    echo "[提示] 已尝试打开浏览器。" >&2
  else
    echo "[提示] 当前环境未能自动打开浏览器。" >&2
  fi
  echo "[提示] 请在浏览器中按顺序完成：" >&2
  echo "  1. 安装并授权 AgentHub 第三方 OAuth 应用" >&2
  echo "  2. 在应用详情页把它分配给当前 OAuth 登录身份" >&2
  echo "[提示] 如果浏览器没有自动打开，请手动访问安装授权链接：" >&2
  echo "$consent_url" >&2
  echo "[提示] 分配入口：" >&2
  echo "$assignment_url" >&2
  echo "[提示] 分配完成后，回到当前客户端/当前对话里重新发送刚才的请求，或告诉我“已分配，继续”。" >&2
}

is_generate_access_token_permission_error() {
  local text="$1"
  printf '%s' "$text" | grep -Eiq \
    '(^|[[:space:]])ErrorCode:[[:space:]]*NoPermission([[:space:]]|$)' || return 1
  printf '%s' "$text" | grep -Eiq \
    'You are not authorized to perform this action\.'
}

extract_request_id_from_error() {
  local text="$1"
  printf '%s\n' "$text" | sed -nE 's/.*RequestId:[[:space:]]*([^[:space:]]+).*/\1/p' | head -n 1
}

print_generate_access_token_permission_guidance() {
  local raw_error="$1"
  local request_id
  request_id="$(extract_request_id_from_error "$raw_error")"

  echo "[提示] GenerateAccessToken 请求被 NoPermission 拒绝。该 API 默认无需配置 RAM Policy，也无需显式配置 Allow。" >&2
  echo "[提示] 只有适用于当前身份、且覆盖 ram:GenerateAccessToken 的显式 Deny 才会阻止调用。" >&2
  echo "[提示] 请让阿里云账号管理员检查当前 profile 对应身份适用的 RAM Policy，并移除或收窄相关显式 Deny；不要新增 Allow 策略。" >&2
  if [[ -n "$request_id" ]]; then
    echo "[提示] 如需管理员进一步排查，可提供 RequestId: $request_id" >&2
  fi
  echo "[提示] 调整 Deny 后，回到当前客户端/当前对话里重新发送刚才的请求，或告诉我“已调整，继续”。" >&2
}

check_cached_token() {
  if [[ ! -f "$CACHE_FILE" ]] || [[ ! -s "$CACHE_FILE" ]]; then
    echo "expired"
    return
  fi
  "$AGENTHUB_PYTHON" - "$CACHE_FILE" "$TOKEN_EXPIRY_BUFFER" <<'PY' 2>/dev/null
import json
import os
import stat
import sys
import time


def load_private_json(path):
    info = os.lstat(path)
    if (
        not stat.S_ISREG(info.st_mode)
        or info.st_uid != os.getuid()
        or stat.S_IMODE(info.st_mode) != 0o600
        or info.st_nlink != 1
    ):
        raise OSError("unsafe AgentHub token cache")
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags)
    try:
        opened = os.fstat(fd)
        if (
            not stat.S_ISREG(opened.st_mode)
            or opened.st_uid != os.getuid()
            or stat.S_IMODE(opened.st_mode) != 0o600
            or opened.st_nlink != 1
            or (opened.st_dev, opened.st_ino) != (info.st_dev, info.st_ino)
        ):
            raise OSError("unsafe AgentHub token cache")
        with os.fdopen(fd, "r", encoding="utf-8") as stream:
            fd = -1
            return json.load(stream)
    finally:
        if fd >= 0:
            os.close(fd)


try:
    data = load_private_json(sys.argv[1])
    obtained_at = float(data.get("token_obtained_at", 0))
    expires_in = float(data.get("token_expires_in", 0))
    if obtained_at and expires_in and time.time() < obtained_at + expires_in - int(sys.argv[2]):
        print("valid")
    else:
        print("expired")
except Exception:
    print("expired")
PY
}

output_cached_token() {
  "$AGENTHUB_PYTHON" - "$CACHE_FILE" <<'PY' 2>/dev/null
import json
import os
import stat
import time
from datetime import datetime, timezone, timedelta
import sys


def load_private_json(path):
    info = os.lstat(path)
    if (
        not stat.S_ISREG(info.st_mode)
        or info.st_uid != os.getuid()
        or stat.S_IMODE(info.st_mode) != 0o600
        or info.st_nlink != 1
    ):
        raise OSError("unsafe AgentHub token cache")
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags)
    try:
        opened = os.fstat(fd)
        if (
            not stat.S_ISREG(opened.st_mode)
            or opened.st_uid != os.getuid()
            or stat.S_IMODE(opened.st_mode) != 0o600
            or opened.st_nlink != 1
            or (opened.st_dev, opened.st_ino) != (info.st_dev, info.st_ino)
        ):
            raise OSError("unsafe AgentHub token cache")
        with os.fdopen(fd, "r", encoding="utf-8") as stream:
            fd = -1
            return json.load(stream)
    finally:
        if fd >= 0:
            os.close(fd)


cst = timezone(timedelta(hours=8))
data = load_private_json(sys.argv[1])
obtained_at = data["token_obtained_at"]
expires_in = data["token_expires_in"]
remaining = int(obtained_at + expires_in - time.time())
expire_time = datetime.fromtimestamp(obtained_at + expires_in, tz=cst)
token_data = data["token_response"]
payload = token_data.get("Data") or token_data
token = payload.get("AccessToken", payload.get("access_token", ""))
print()
print("===A2A_TOKEN_BEGIN===")
print(token)
print("===A2A_TOKEN_END===")
print()
print("[INFO] Token 来自缓存，过期时间: {}".format(expire_time.strftime("%Y-%m-%d %H:%M:%S CST")))
print("[INFO] 剩余有效期: {}分{}秒".format(remaining // 60, remaining % 60))
PY
}

select_credential_source() {
  local response status fields
  local selector=(
    "$AGENTHUB_PYTHON" "$SCRIPT_DIR/agenthub_credential_source.py" select
    --cache-file "$CACHE_FILE"
    --cli-config-file "$ALIYUN_CLI_CONFIG_FILE"
    --private-config-file "$AGENTHUB_CONFIG_FILE"
  )
  if [[ -n "$REQUESTED_CREDENTIAL_SOURCE" ]]; then
    selector+=(--credential-source "$REQUESTED_CREDENTIAL_SOURCE")
  fi
  response=$("${selector[@]}" 2>&1)
  status=$?
  if [[ $status -ne 0 ]]; then
    echo "$response" >&2
    return "$status"
  fi
  fields=$(printf '%s' "$response" | "$AGENTHUB_PYTHON" -c '
import json, sys
data = json.load(sys.stdin)
print("\t".join([
    str(data.get("provider", "")),
    str(data.get("profile_name", "")),
    str(data.get("mode", "")),
    str(data.get("config_file", "")),
    "true" if data.get("locked") else "false",
]))
')
  IFS=$'\t' read -r CREDENTIAL_PROVIDER ALIYUN_PROFILE_NAME PROFILE_MODE CREDENTIAL_CONFIG_FILE SOURCE_LOCKED <<< "$fields"
  if [[ -z "$CREDENTIAL_PROVIDER" || -z "$ALIYUN_PROFILE_NAME" || -z "$PROFILE_MODE" ]]; then
    echo "[ERROR] AgentHub credential source selector returned an incomplete result." >&2
    return 1
  fi
}

assert_requested_source_lock() {
  local assertion=(
    "$AGENTHUB_PYTHON" "$SCRIPT_DIR/agenthub_credential_source.py" assert-source
    --cache-file "$CACHE_FILE"
  )
  if [[ -n "$REQUESTED_CREDENTIAL_SOURCE" ]]; then
    assertion+=(--credential-source "$REQUESTED_CREDENTIAL_SOURCE")
  fi
  "${assertion[@]}"
}

credential_source_cache_json() {
  "$AGENTHUB_PYTHON" - "$CREDENTIAL_PROVIDER" "$ALIYUN_PROFILE_NAME" "$PROFILE_MODE" "$CREDENTIAL_CONFIG_FILE" <<'PY'
import json
import sys
import time

json.dump(
    {
        "provider": sys.argv[1],
        "profile": sys.argv[2],
        "mode": sys.argv[3],
        "config_file": sys.argv[4],
        "selected_at": int(time.time()),
    },
    sys.stdout,
    ensure_ascii=False,
)
PY
}

cache_token_response() {
  local token_response="$1" now_ts="$2" expires_in="$3" source_json="$4"
  printf '%s' "$token_response" | \
    "$AGENTHUB_PYTHON" -c '
import json
import sys

token_response = json.load(sys.stdin)
json.dump(
    {
        "app_name": "CN",
        "client_id": sys.argv[1],
        "credential_source": json.loads(sys.argv[2]),
        "token_response": token_response,
        "token_obtained_at": int(float(sys.argv[3])),
        "token_expires_in": int(float(sys.argv[4])),
    },
    sys.stdout,
    ensure_ascii=False,
    separators=(",", ":"),
)
' "$CLIENT_ID" "$source_json" "$now_ts" "$expires_in" | \
    "$AGENTHUB_PYTHON" "$SCRIPT_DIR/agenthub_credential_source.py" cache-update \
      --cache-file "$CACHE_FILE"
}

generate_access_token_via_cli() {
  require_cmd aliyun
  local response request_id user_agent
  user_agent="$(observability_user_agent)" || return $?
  if [[ "${CREDENTIAL_CONFIG_FILE:-$ALIYUN_CLI_CONFIG_FILE}" != "$OFFICIAL_ALIYUN_CLI_CONFIG_FILE" ]]; then
    echo "[ERROR] aliyun CLI 只支持官方配置路径 $OFFICIAL_ALIYUN_CLI_CONFIG_FILE；请迁移该 profile，或改用 AgentHub 私有 profile。" >&2
    return "$AUTH_REQUIRED_EXIT_CODE"
  fi
  response=$(aliyun ramoauth GenerateAccessToken \
    --profile "$ALIYUN_PROFILE_NAME" \
    --ClientId "$CLIENT_ID" \
    --endpoint "$RAMOAUTH_ENDPOINT" \
    --version "2026-04-21" \
    --region "cn-hangzhou" \
    --method POST \
    --force \
    --user-agent "$user_agent" \
    --Scope "$SCOPE" 2>&1) || {
    if is_generate_access_token_permission_error "$response"; then
      print_generate_access_token_permission_guidance "$response"
      return "$AUTH_REQUIRED_EXIT_CODE"
    else
      request_id="$(extract_request_id_from_error "$response")"
      echo "[ERROR] aliyun CLI GenerateAccessToken 调用失败。" >&2
      [[ -n "$request_id" ]] && echo "[ERROR] RequestId: $request_id" >&2
    fi
    return 1
  }
  validate_token_response "$response"
}

generate_access_token_direct() {
  local response status request_id
  response=$("$AGENTHUB_PYTHON" "$SCRIPT_DIR/agenthub_token.py" generate \
    --config-file "${CREDENTIAL_CONFIG_FILE:-$AGENTHUB_CONFIG_FILE}" \
    --profile "$ALIYUN_PROFILE_NAME" \
    2>&1)
  status=$?
  if [[ $status -ne 0 ]]; then
    if is_generate_access_token_permission_error "$response"; then
      print_generate_access_token_permission_guidance "$response"
      return "$AUTH_REQUIRED_EXIT_CODE"
    elif is_smart_gateway_oauth_app_error "$response"; then
      print_smart_gateway_admin_consent_guidance "$response"
      return "$AUTH_REQUIRED_EXIT_CODE"
    elif [[ $status -eq $AUTH_REQUIRED_EXIT_CODE ]]; then
      echo "[ERROR] AgentHub 私有 profile 需要在本地终端重新配置或授权。" >&2
      return "$AUTH_REQUIRED_EXIT_CODE"
    else
      request_id="$(extract_request_id_from_error "$response")"
      echo "[ERROR] GenerateAccessToken 直接调用失败。" >&2
      [[ -n "$request_id" ]] && echo "[ERROR] RequestId: $request_id" >&2
    fi
    return "$status"
  fi
  validate_token_response "$response"
}

validate_token_response() {
  local response="$1"
  local access_token
  access_token=$(printf '%s' "$response" | "$AGENTHUB_PYTHON" -c '
import json, sys
data = json.load(sys.stdin)
payload = data.get("Data") or data
print(payload.get("AccessToken", payload.get("access_token", "")))
' 2>/dev/null)
  if [[ -z "$access_token" ]]; then
    echo "[ERROR] GenerateAccessToken 响应结构异常，未找到可用 AccessToken。" >&2
    return 1
  fi
  printf '%s\n' "$response"
}

cache_and_emit_token_response() {
  local token_response="$1"
  local expires_in now_ts access_token source_json
  expires_in=$(printf '%s' "$token_response" | "$AGENTHUB_PYTHON" -c '
import json, sys
data = json.load(sys.stdin)
payload = data.get("Data") or data
print(payload.get("ExpiresIn", payload.get("expires_in", 3600)))
' 2>/dev/null)
  now_ts=$("$AGENTHUB_PYTHON" -c "import time; print(int(time.time()))" 2>/dev/null)
  source_json="$(credential_source_cache_json)"

  if ! cache_token_response "$token_response" "$now_ts" "$expires_in" "$source_json"; then
    echo "[ERROR] 无法安全写入 AgentHub token 缓存。" >&2
    return 1
  fi

  access_token=$(printf '%s' "$token_response" | "$AGENTHUB_PYTHON" -c '
import json, sys
data = json.load(sys.stdin)
payload = data.get("Data") or data
print(payload.get("AccessToken", payload.get("access_token", "")))
' 2>/dev/null)

  emit_token "$access_token"
  "$AGENTHUB_PYTHON" - "$now_ts" "$expires_in" "$CACHE_FILE" <<'PY' 2>/dev/null
import sys
from datetime import datetime, timezone, timedelta

cst = timezone(timedelta(hours=8))
obtained_at = int(float(sys.argv[1]))
expires_in = int(float(sys.argv[2]))
expire_time = datetime.fromtimestamp(obtained_at + expires_in, tz=cst)
print("[INFO] 过期时间: {}".format(expire_time.strftime("%Y-%m-%d %H:%M:%S CST")))
print("[INFO] 有效期: {}秒".format(expires_in))
print("[INFO] Token 已缓存至 {}".format(sys.argv[3]))
PY
}

main() {
  parse_args "$@"
  if [[ -z "${AGENTHUB_PYTHON:-}" || ! -x "$AGENTHUB_PYTHON" ]]; then
    die "AGENTHUB_PYTHON must name the executable interpreter selected by the caller"
  fi
  resolve_cache_file
  "$AGENTHUB_PYTHON" "$SCRIPT_DIR/agenthub_credential_source.py" cache-repair \
    --cache-file "$CACHE_FILE" || die "cannot safely validate or repair the AgentHub token cache"

  assert_requested_source_lock || exit "$?"

  if [[ "$CMD" == "refresh" && -f "$CACHE_FILE" ]]; then
    "$AGENTHUB_PYTHON" "$SCRIPT_DIR/agenthub_credential_source.py" cache-clear-token \
      --cache-file "$CACHE_FILE" || die "cannot safely clear the cached AgentHub token"
    echo "[INFO] refresh: 已清除 Token 缓存，保留已锁定凭证来源"
  fi

  if [[ "$CMD" == "login" ]]; then
    local token_status
    token_status="$(check_cached_token)"
    if [[ "$token_status" == "valid" ]]; then
      if output_cached_token; then
        exit 0
      fi
      echo "[WARN] AgentHub token 缓存无法安全读取，将重新获取 Token。" >&2
    fi
  fi

  select_credential_source || exit "$?"
  if [[ "$CREDENTIAL_PROVIDER" == "aliyun_cli" ]]; then
    echo "[INFO] 使用 aliyun CLI profile '$ALIYUN_PROFILE_NAME'（mode: ${PROFILE_MODE}）"
  else
    echo "[INFO] 使用 AgentHub 私有 profile '$ALIYUN_PROFILE_NAME'（mode: ${PROFILE_MODE}）"
  fi
  if [[ "$SOURCE_LOCKED" == "true" ]]; then
    echo "[INFO] 沿用缓存中锁定的凭证来源；不会因本机环境变化自动切换。"
  fi

  echo "[INFO] 站点: CN, ramoauth endpoint: $RAMOAUTH_ENDPOINT"

  local token_response token_status
  if [[ "$CREDENTIAL_PROVIDER" == "aliyun_cli" ]]; then
    echo "[INFO] 正在通过 aliyun CLI 调用 GenerateAccessToken 获取新 Token..."
    token_response="$(generate_access_token_via_cli)"
  else
    echo "[INFO] 正在直接调用 GenerateAccessToken 获取新 Token..."
    token_response="$(generate_access_token_direct)"
  fi
  token_status=$?
  if [[ $token_status -ne 0 ]]; then
    exit "$token_status"
  fi
  cache_and_emit_token_response "$token_response"
}

main "$@"
