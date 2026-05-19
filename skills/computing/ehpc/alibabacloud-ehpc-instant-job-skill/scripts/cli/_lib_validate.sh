#!/bin/bash

# ====================================================================
# E-HPC Instant CLI - 通用输入校验库
# ====================================================================
# 目的:
#   防止环境变量/参数中的恶意字符（双引号、反斜杠、控制字符等）
#   被直接拼接进 JSON 字符串后引发 JSON/命令注入。
#
# 用法:
#   在脚本中执行: source "$(dirname "$0")/_lib_validate.sh"
#   然后调用各 validate_* 函数对输入参数进行校验。
#
# 校验失败行为:
#   打印中文错误提示后以非 0 状态退出（exit 1）。
# ====================================================================

# 颜色码（若调用方未定义则提供默认值，避免未绑定变量错误）
: "${RED:=\033[0;31m}"
: "${YELLOW:=\033[1;33m}"
: "${NC:=\033[0m}"

# ---- 内部辅助 ----

# _validate_fail <错误信息> [<提示信息>]
_validate_fail() {
    echo -e "${RED}❌ 错误: $1${NC}" >&2
    if [ -n "${2:-}" ]; then
        echo -e "${YELLOW}$2${NC}" >&2
    fi
    exit 1
}

# 通用：按正则校验
# validate_pattern <字段名> <值> <bash正则> <格式提示>
validate_pattern() {
    local name="$1" value="$2" regex="$3" hint="$4"
    if [[ -z "$value" ]]; then
        _validate_fail "$name 不能为空" "格式: $hint"
    fi
    if [[ ! "$value" =~ $regex ]]; then
        _validate_fail "$name 格式无效: '$value'" "正确格式: $hint"
    fi
}

# ---- 资源 ID 校验（严格白名单字符）----

validate_job_id() {
    validate_pattern "JobId" "$1" '^job-[a-zA-Z0-9]+$' "job- 后跟字母数字"
}

validate_job_name() {
    # 阿里云作业名约束：1-64 位，字母/数字/下划线/连字符，必须以字母或数字开头
    validate_pattern "JobName" "$1" '^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$' "1-64 位字母/数字/下划线/连字符"
}

validate_image_id() {
    validate_pattern "ImageId" "$1" '^m-[a-zA-Z0-9]+$' "m- 后跟字母数字"
}

validate_vswitch_id() {
    validate_pattern "VSwitchId" "$1" '^vsw-[a-zA-Z0-9]+$' "vsw- 后跟字母数字"
}

validate_security_group_id() {
    validate_pattern "SecurityGroupId" "$1" '^sg-[a-zA-Z0-9]+$' "sg- 后跟字母数字"
}

validate_region() {
    validate_pattern "Region" "$1" '^[a-z][a-z0-9-]*[a-z0-9]$' "小写字母/数字/连字符，如 cn-shanghai"
}

# ---- 域名/主机名（NAS Server 等）----

validate_hostname() {
    # 长度 1-253，仅含字母数字、点、连字符；不允许以连字符开头/结尾
    local name="$1" value="$2"
    if [[ -z "$value" ]]; then
        _validate_fail "$name 不能为空"
    fi
    if [[ ${#value} -gt 253 ]]; then
        _validate_fail "$name 长度超过 253"
    fi
    if [[ ! "$value" =~ ^[a-zA-Z0-9]([a-zA-Z0-9.-]*[a-zA-Z0-9])?$ ]]; then
        _validate_fail "$name 格式无效: '$value'" "合法的主机名/域名（字母数字、点、连字符）"
    fi
}

# ---- 容器镜像引用 ----
# 仅允许 registry/repo[:tag][@digest] 中常见字符；拒绝空格、引号、反斜杠等
validate_container_image() {
    local value="$1"
    if [[ -z "$value" ]]; then
        _validate_fail "ContainerImage 不能为空"
    fi
    if [[ ${#value} -gt 512 ]]; then
        _validate_fail "ContainerImage 长度超过 512"
    fi
    if [[ ! "$value" =~ ^[a-zA-Z0-9][a-zA-Z0-9._:/@-]*$ ]]; then
        _validate_fail "ContainerImage 包含非法字符: '$value'" "仅允许 字母数字 . _ : / @ -"
    fi
}

# ---- 自由文本字段（JOB_DESCRIPTION/VM_PASSWORD 等）----
# 拒绝任何控制字符、双引号、反斜杠，避免破坏 JSON 字符串
# 用法: validate_json_safe_text <字段名> <值> [最大长度，默认 256]
validate_json_safe_text() {
    local name="$1" value="$2" maxlen="${3:-256}"
    if [[ -z "$value" ]]; then
        _validate_fail "$name 不能为空"
    fi
    if [[ ${#value} -gt $maxlen ]]; then
        _validate_fail "$name 长度超过 $maxlen"
    fi
    if [[ "$value" == *\"* ]]; then
        _validate_fail "$name 不允许包含双引号 (\")"
    fi
    if [[ "$value" == *\\* ]]; then
        _validate_fail "$name 不允许包含反斜杠 (\\)"
    fi
    # 拒绝任何 ASCII 控制字符 (0x00-0x1F, 0x7F)
    if [[ "$value" =~ [[:cntrl:]] ]]; then
        _validate_fail "$name 包含非法控制字符"
    fi
}

# ---- VM 登录密码 ----
# Aliyun ECS 密码规则：8-30 位，字母/数字/常见符号；禁止双引号与反斜杠
validate_vm_password() {
    local value="$1"
    if [[ -z "$value" ]]; then
        _validate_fail "VM_PASSWORD 不能为空" "请先 export VM_PASSWORD=<your-password>"
    fi
    if [[ ${#value} -lt 8 || ${#value} -gt 30 ]]; then
        _validate_fail "VM_PASSWORD 长度必须为 8-30"
    fi
    if [[ "$value" == *\"* || "$value" == *\\* ]]; then
        _validate_fail "VM_PASSWORD 不允许包含 \" 或 \\"
    fi
    if [[ "$value" =~ [[:cntrl:]] ]]; then
        _validate_fail "VM_PASSWORD 包含非法控制字符"
    fi
}
