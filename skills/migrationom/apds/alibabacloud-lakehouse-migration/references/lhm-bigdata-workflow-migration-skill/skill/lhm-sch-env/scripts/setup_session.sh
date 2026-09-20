#!/usr/bin/env bash
# ============================================================
# LHM 调度迁移会话准备
# ------------------------------------------------------------
# 三件事：
#   1. 按需安装 lhm-sch-* CLI（含本技能自身的 lhm-sch-env）
#   2. 把用户填写的配置转写为本次会话的临时配置文件，供子 agent 加载
#      （凭证不在其中：由 aliyun CLI 默认凭证链在调用时解析）
#   3. 自动执行环境检测： lhm-sch-env check --profile full
#      （网络连通性 / 资源组状态 / Agent 在线状态）
#
# 用法：
#   ./setup_session.sh                       # 全阶段：装 CLI + 转写会话配置 + 环境检测
#   ./setup_session.sh --stage ds            # 只保证阶段① 所需 CLI，且不校验迁移源/目标数据源名称
#   ./setup_session.sh --from <路径>          # 显式指定用户配置文件
#   ./setup_session.sh --check-only          # 只校验，不写会话文件、不装 CLI、不检测
#   ./setup_session.sh --skip-env-check      # 跳过环境检测（不推荐）
#   ./setup_session.sh --print-path          # 输出会话配置文件路径
#   ./setup_session.sh --cleanup             # 会话结束后删除会话配置文件
#   ./setup_session.sh --json                # 输出机器可读结果
#
# 退出码：
#   0 = 会话就绪   1 = 存在阻塞项（缺 CLI、缺必填配置或环境检测未通过）
#
# 安全：脚本不解析、不打印任何密钥；凭证由 aliyun CLI 默认凭证链解析。
# ============================================================

# bash 3.2（macOS 默认）在 set -u 下展开空数组会报错，故不开 -u。
set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WRITER="${SCRIPT_DIR}/session_writer.py"
SKILL_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

STAGE="all"
OUTPUT="text"
FROM_PATH=""
CHECK_ONLY=0
CLEANUP=0
PRINT_PATH=0
AUTO_INSTALL=0
SKIP_ENV_CHECK=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --stage)       STAGE="${2:-all}"; shift 2 ;;
        --from)        FROM_PATH="${2:-}"; shift 2 ;;
        --json)        OUTPUT="json"; shift ;;
        --check-only)  CHECK_ONLY=1; shift ;;
        --cleanup)     CLEANUP=1; shift ;;
        --print-path)  PRINT_PATH=1; shift ;;
        --auto-install) AUTO_INSTALL=1; shift ;;
        --skip-env-check) SKIP_ENV_CHECK=1; shift ;;
        -h|--help)     sed -n '2,26p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *) echo "未知参数：$1" >&2; exit 2 ;;
    esac
done

if [[ -t 1 && "${OUTPUT}" == "text" ]]; then
    RED='\033[0;31m'; GRN='\033[0;32m'; YLW='\033[0;33m'; NC='\033[0m'
else
    RED=''; GRN=''; YLW=''; NC=''
fi

if [[ ! -f "${WRITER}" ]]; then
    echo "转写脚本缺失：${WRITER}" >&2
    exit 2
fi

# ---------- 快捷分支 ----------
if [[ ${PRINT_PATH} -eq 1 ]]; then
    exec python3 "${WRITER}" --print-path
fi

if [[ ${CLEANUP} -eq 1 ]]; then
    python3 "${WRITER}" --cleanup
    exit $?
fi

# ---------- Step 1: CLI 安装 ----------
case "${STAGE}" in
    ds)        REQUIRED_CLI="lhm-sch-ds" ;;
    read-exec) REQUIRED_CLI="lhm-sch-read-exec" ;;
    deploy)    REQUIRED_CLI="lhm-sch-deploy" ;;
    all)       REQUIRED_CLI="lhm-sch-ds lhm-sch-read-exec lhm-sch-deploy" ;;
    *) echo "未知阶段：${STAGE}（可选 ds / read-exec / deploy / all）" >&2; exit 2 ;;
esac

# 环境检测由本技能自身的 CLI 执行，所有阶段都需要
[[ ${SKIP_ENV_CHECK} -eq 0 ]] && REQUIRED_CLI="lhm-sch-env ${REQUIRED_CLI}"

MISSING_CLI=()
for cli in ${REQUIRED_CLI}; do
    command -v "${cli}" >/dev/null 2>&1 || MISSING_CLI+=("${cli}")
done

# 目录名与命令名一致，可直接由命令名推出安装目录
INSTALL_HINTS=()
if [[ ${#MISSING_CLI[@]} -gt 0 && ${CHECK_ONLY} -eq 0 && ${AUTO_INSTALL} -eq 1 ]]; then
    for cli in "${MISSING_CLI[@]}"; do
        cli_dir="${SKILL_DIR}/../${cli}"
        if [[ -f "${cli_dir}/install.sh" ]]; then
            [[ "${OUTPUT}" == "text" ]] && echo "正在安装 ${cli} ..."
            (cd "${cli_dir}" && bash install.sh >/dev/null 2>&1) \
                || INSTALL_HINTS+=("${cli} 自动安装失败，请手动执行：cd ${cli_dir} && bash install.sh")
        else
            INSTALL_HINTS+=("未找到 ${cli} 的 install.sh（预期位于 ${cli_dir}）")
        fi
    done
    # 重新探测
    MISSING_CLI=()
    for cli in ${REQUIRED_CLI}; do
        command -v "${cli}" >/dev/null 2>&1 || MISSING_CLI+=("${cli}")
    done
elif [[ ${#MISSING_CLI[@]} -gt 0 ]]; then
    for cli in "${MISSING_CLI[@]}"; do
        INSTALL_HINTS+=("cd ${SKILL_DIR}/../${cli} && bash install.sh")
    done
fi

# ---------- Step 2: 转写会话配置 ----------
# 阶段一并传给转写脚本：--stage ds 是纯数据源管理会话，迁移链路不会执行，
# 因此不能因为缺 source/target_data_source_name 就判定“会话未就绪”——
# 那会把“建数据源”误报成“卡在迁移参数上”，诱导上层去追问无关的迁移参数。
WRITER_ARGS=(--stage "${STAGE}")
[[ -n "${FROM_PATH}" ]] && WRITER_ARGS+=(--from "${FROM_PATH}")
[[ ${CHECK_ONLY} -eq 1 ]] && WRITER_ARGS+=(--check-only)

WRITER_OUT="$(python3 "${WRITER}" "${WRITER_ARGS[@]}" 2>&1)"
WRITER_RC=$?

read_field() {
    printf '%s' "${WRITER_OUT}" | python3 -c "
import json, sys
try:
    data = json.loads(sys.stdin.read())
except Exception:
    print('')
    sys.exit(0)
value = data.get('$1', '')
if isinstance(value, list):
    print('\n'.join(str(v) for v in value))
else:
    print(value)
"
}

SESSION_FILE="$(read_field session_file)"
USER_CONFIG="$(read_field user_config)"
ENDPOINT="$(read_field endpoint)"
REGION="$(read_field region_id)"
SOURCE_DS="$(read_field source_data_source_name)"
TARGET_DS="$(read_field target_data_source_name)"
WRITER_BLOCKERS="$(read_field blockers)"
WRITER_WARNINGS="$(read_field warnings)"

case "${ENDPOINT}" in
    lhm-pre.*) ENV_LABEL="预发" ;;
    lhm.*)     ENV_LABEL="生产" ;;
    *)         ENV_LABEL="自定义" ;;
esac

# ---------- Step 3: 环境检测（lhm-sch-env check --profile full） ----------
ENV_CHECK_OUT=""
ENV_CHECK_RC=0
ENV_CHECK_RAN=0
if [[ ${SKIP_ENV_CHECK} -eq 0 && ${CHECK_ONLY} -eq 0 && ${WRITER_RC} -eq 0 \
      && -n "${SESSION_FILE}" ]] && command -v lhm-sch-env >/dev/null 2>&1; then
    [[ "${OUTPUT}" == "text" ]] && echo "正在执行环境检测（lhm-sch-env check --profile full）..."
    ENV_CHECK_RAN=1
    ENV_CHECK_OUT="$(lhm-sch-env check --profile full --session-file "${SESSION_FILE}" --json 2>/dev/null)"
    ENV_CHECK_RC=$?
fi

READY=true
[[ ${WRITER_RC} -ne 0 || ${#MISSING_CLI[@]} -gt 0 || ${ENV_CHECK_RC} -ne 0 ]] && READY=false

# ---------- 输出 ----------
if [[ "${OUTPUT}" == "json" ]]; then
    printf '%s' "${WRITER_OUT}" | MISSING="${MISSING_CLI[*]}" HINTS="$(printf '%s\n' "${INSTALL_HINTS[@]}")" \
        ENVCHK="${ENV_CHECK_OUT}" ENVRAN="${ENV_CHECK_RAN}" python3 -c "
import json, os, sys
try:
    data = json.loads(sys.stdin.read())
except Exception:
    data = {'blockers': ['转写脚本输出无法解析'], 'warnings': []}
missing = [item for item in os.environ.get('MISSING', '').split() if item]
hints = [line for line in os.environ.get('HINTS', '').splitlines() if line.strip()]
data['missing_cli'] = missing
data['install_hints'] = hints
if missing:
    data.setdefault('blockers', []).append('CLI 未安装：' + ', '.join(missing))
if os.environ.get('ENVRAN') == '1':
    try:
        env_check = json.loads(os.environ.get('ENVCHK', ''))
    except Exception:
        env_check = {'error': '环境检测输出无法解析'}
    data['env_check'] = env_check
    for name in env_check.get('blocking_items', []):
        data.setdefault('blockers', []).append('环境检测未通过：' + name)
data['ready'] = not data.get('blockers')
print(json.dumps(data, ensure_ascii=False, indent=2))
"
else
    echo "LHM 会话准备（阶段：${STAGE}）"
    echo "------------------------------------------------------------"
    if [[ ${#MISSING_CLI[@]} -eq 0 ]]; then
        printf "${GRN}✓${NC} CLI 已就绪：%s\n" "${REQUIRED_CLI}"
    else
        printf "${RED}✗${NC} CLI 未安装：%s\n" "${MISSING_CLI[*]}"
    fi

    if [[ -n "${USER_CONFIG}" ]]; then
        printf "${GRN}✓${NC} 用户配置：%s\n" "${USER_CONFIG}"
    else
        printf "${YLW}⚠${NC}  未找到用户配置文件\n"
    fi

    if [[ ${WRITER_RC} -eq 0 ]]; then
        if [[ ${CHECK_ONLY} -eq 1 ]]; then
            printf "${GRN}✓${NC} 配置校验通过（--check-only，未写会话文件）\n"
        else
            printf "${GRN}✓${NC} 会话配置已生成：%s\n" "${SESSION_FILE}"
        fi
        printf "${GRN}✓${NC} 环境：%s（%s / %s）\n" "${ENV_LABEL}" "${ENDPOINT}" "${REGION}"
        if [[ -n "${SOURCE_DS}" || -n "${TARGET_DS}" ]]; then
            printf "${GRN}✓${NC} 数据源：源=%s 目标=%s\n" \
                "${SOURCE_DS:-<未填>}" "${TARGET_DS:-<未填>}"
        fi
        if [[ ${ENV_CHECK_RAN} -eq 1 ]]; then
            printf '%s' "${ENV_CHECK_OUT}" | python3 -c "
import json, sys
try:
    data = json.loads(sys.stdin.read())
except Exception:
    print('⚠  环境检测输出无法解析')
    sys.exit(0)
icons = {'pass': '✓', 'fail': '✗', 'skip': '⊘'}
for item in data.get('checks', []):
    icon = icons.get(item.get('status'), '?')
    print(f\"{icon} 环境检测 {item.get('name')}: {item.get('message')}\")
    if item.get('status') == 'fail' and item.get('fix_guide'):
        for line in item['fix_guide'].splitlines():
            print(f'    {line}')
"
        elif [[ ${SKIP_ENV_CHECK} -eq 1 ]]; then
            printf "${YLW}⚠${NC}  已跳过环境检测（--skip-env-check）\n"
        fi
    fi

    while IFS= read -r line; do
        [[ -n "${line}" ]] && printf "${YLW}⚠${NC}  %s\n" "${line}"
    done <<< "${WRITER_WARNINGS}"

    echo "------------------------------------------------------------"
    if [[ "${READY}" == "true" ]]; then
        printf "${GRN}会话就绪${NC}\n"
        [[ ${CHECK_ONLY} -eq 0 ]] && echo "子 agent 将自动加载该会话配置，无需再传凭证参数。"
    else
        printf "${RED}会话未就绪：${NC}\n"
        while IFS= read -r line; do
            [[ -n "${line}" ]] && echo "  • ${line}"
        done <<< "${WRITER_BLOCKERS}"
        for hint in "${INSTALL_HINTS[@]}"; do
            echo "  • ${hint}"
        done
        if [[ ${ENV_CHECK_RAN} -eq 1 && ${ENV_CHECK_RC} -ne 0 ]]; then
            printf '%s' "${ENV_CHECK_OUT}" | python3 -c "
import json, sys
try:
    data = json.loads(sys.stdin.read())
except Exception:
    sys.exit(0)
for name in data.get('blocking_items', []):
    print('  • 环境检测未通过：' + name)
"
        fi
        echo "修复指引见 SKILL.md。"
    fi
fi

[[ "${READY}" == "true" ]] && exit 0 || exit 1
