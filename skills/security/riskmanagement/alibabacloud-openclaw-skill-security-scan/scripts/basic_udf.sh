#!/bin/bash
# FileRiskService API客户端脚本 V2（预签名URL模式 - 简化版）
# Author: 阿里云-安全感项目
# Date: 2026-03-31

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# API版本配置
API_VERSION="2024-05-06"

# 操作系统检测
OS_TYPE="unknown"
MD5_TOOL=""

# 检测操作系统
detect_os() {
    case "$(uname -s)" in
        MINGW*|MSYS*|CYGWIN*|Windows_NT)
            OS_TYPE="windows"
            ;;
        Linux*)
            OS_TYPE="linux"
            ;;
        Darwin*)
            OS_TYPE="macos"
            ;;
        *)
            OS_TYPE="unknown"
            ;;
    esac
}

# 检查依赖
check_dependencies() {
    if ! command -v curl &> /dev/null; then
        echo -e "${RED}Error: curl is required but not installed${NC}" >&2
        echo "Please install curl using your package manager" >&2
        exit 1
    fi

    # 检测并设置 MD5 工具
    detect_os

    if [ "$OS_TYPE" = "windows" ]; then
        if command -v powershell &> /dev/null || command -v pwsh &> /dev/null; then
            MD5_TOOL="powershell"
        elif command -v certutil &> /dev/null; then
            MD5_TOOL="certutil"
        elif command -v md5sum &> /dev/null; then
            MD5_TOOL="md5sum"
        else
            echo -e "${YELLOW}Warning: No MD5 tool found (MD5 calculation will be disabled)${NC}" >&2
        fi
    elif [ "$OS_TYPE" = "linux" ]; then
        if command -v md5sum &> /dev/null; then
            MD5_TOOL="md5sum"
        fi
    elif [ "$OS_TYPE" = "macos" ]; then
        if command -v md5 &> /dev/null; then
            MD5_TOOL="md5"
        fi
    fi
}

# 获取当前UTC时间戳（ISO 8601格式）
get_utc_timestamp() {
    local utc_timestamp=$(date +%s)
    date -u -d @${utc_timestamp} +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date -u -r ${utc_timestamp} +"%Y-%m-%dT%H:%M:%SZ"
}

# 生成UUID（用于nonce）
generate_nonce() {
    if command -v uuidgen &> /dev/null; then
        uuidgen | sed 's/-//g'
    else
        cat /dev/urandom | tr -dc 'a-f0-9' | fold -w 32 | head -n 1 2>/dev/null || echo "$(date +%s%N)$(echo $RANDOM)" | md5sum | cut -c1-32
    fi
}

# ==================== JSON转义函数 ====================

# JSON字符串转义（处理特殊字符和空格）
json_escape() {
    local string="$1"
    # 转义反斜杠、双引号、换行符、制表符等
    printf '%s' "$string" | sed 's/\\/\\\\/g; s/"/\\"/g; s/\n/\\n/g; s/\r/\\r/g; s/\t/\\t/g'
}

# 计算文件MD5（支持跨平台）
calculate_file_md5() {
    local file_path="$1"

    if [ ! -f "$file_path" ]; then
        echo -e "${RED}Error: File not found: $file_path${NC}" >&2
        return 1
    fi

    if [ -z "$MD5_TOOL" ]; then
        echo -e "${YELLOW}Warning: No MD5 tool available, skipping MD5 calculation${NC}" >&2
        return 1
    fi

    local md5_value=""

    case "$MD5_TOOL" in
        "powershell")
            # Windows PowerShell
            if command -v powershell &> /dev/null; then
                md5_value=$(powershell -NoProfile -Command "(Get-FileHash -Algorithm MD5 '$file_path').Hash" 2>/dev/null | tr '[:upper:]' '[:lower:]' | tr -d '\r\n')
            else
                md5_value=$(pwsh -NoProfile -Command "(Get-FileHash -Algorithm MD5 '$file_path').Hash" 2>/dev/null | tr '[:upper:]' '[:lower:]' | tr -d '\r\n')
            fi
            ;;
        "certutil")
            # Windows certutil
            md5_value=$(certutil -hashfile "$file_path" MD5 2>/dev/null | sed -n '2p' | tr -d ' \r\n' | tr '[:upper:]' '[:lower:]')
            ;;
        "md5sum")
            # Linux / Git Bash
            md5_value=$(md5sum "$file_path" 2>/dev/null | awk '{print $1}')
            ;;
        "md5")
            # macOS
            md5_value=$(md5 -q "$file_path" 2>/dev/null)
            ;;
        *)
            echo -e "${YELLOW}Warning: Unknown MD5 tool, skipping MD5 calculation${NC}" >&2
            return 1
            ;;
    esac

    # 验证MD5格式（32个小写十六进制字符）
    if [ -z "$md5_value" ] || ! echo "$md5_value" | grep -qE '^[0-9a-f]{32}$'; then
        echo -e "${YELLOW}Warning: Invalid MD5 format: $md5_value${NC}" >&2
        return 1
    fi

    echo "$md5_value"
}

# ==================== API调用函数 ====================

# 1. 获取预签名上传URL（新API：QueryPreSignedUrls）- 支持批量
get_presigned_url() {
    local host="riskpunish.aliyuncs.com"
    local action="QueryPreSignedUrls"
    local version="${API_VERSION}"
    local skill_names=""

    # 解析参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            --host) host="$2"; shift 2 ;;
            --skill-names) skill_names="$2"; shift 2 ;;
            *) echo -e "${RED}Unknown option: $1${NC}"; return 1 ;;
        esac
    done

    if [ -z "$skill_names" ]; then
        echo -e "${RED}Error: --skill-names is required${NC}" >&2
        echo "Usage: --skill-names skill1,skill2,skill3" >&2
        return 1
    fi

    echo -e "${BLUE}======================================${NC}"
    echo -e "${BLUE}[Get Presigned URLs (Batch)]${NC}"
    echo -e "${BLUE}======================================${NC}"
    echo "Action: $action"
    echo "Skill Names: $skill_names"
    echo "Host: $host"
    echo ""

    # 生成请求参数
    local utc_date=$(get_utc_timestamp)
    local nonce=$(generate_nonce)

    # 构造JSON请求体（支持多个skill，逗号分隔）
    # 将逗号分隔的字符串转换为JSON数组
    local json_array=""
    IFS=',' read -ra SKILLS <<< "$skill_names"
    for skill in "${SKILLS[@]}"; do
        skill=$(echo "$skill" | xargs) # trim空格
        # 转义JSON特殊字符
        local escaped_skill=$(json_escape "$skill")
        if [ -z "$json_array" ]; then
            json_array="\"$escaped_skill\""
        else
            json_array="$json_array,\"$escaped_skill\""
        fi
    done
    local request_body="{\"SkillNames\":[$json_array]}"

    # 构造查询参数
    local query_string="Action=${action}&Version=${version}"
    local url="https://${host}/?${query_string}"

    echo "Sending request..."
    echo ""

    # 发送POST请求
    local response=$(curl -s --connect-timeout 10 --max-time 60 -w "\n---HTTP_CODE:%{http_code}---" \
        -X POST \
        "$url" \
        -H "User-Agent: AlibabaCloud-Agent-Skills/alibabacloud-openclaw-skill-security-scan" \
        -H "host: ${host}" \
        -H "x-acs-action: ${action}" \
        -H "x-acs-version: ${version}" \
        -H "x-acs-date: ${utc_date}" \
        -H "x-acs-signature-nonce: ${nonce}" \
        -H "Content-Type: application/json" \
        -d "$request_body")

    # 提取HTTP状态码（使用sed，兼容性更好）
    local http_code=$(echo "$response" | sed -n 's/.*---HTTP_CODE:\([0-9]*\)---.*/\1/p' | tail -1)
    local response_body=$(echo "$response" | sed 's/---HTTP_CODE:[0-9]*---//g')

    echo "HTTP Status: $http_code"
    echo ""
    echo "Response:"
    echo "$response_body"
    echo ""

    return 0
}

# 2. 上传文件到OSS（使用预签名URL）
upload_to_oss() {
    local zip_file=""
    local presigned_url=""

    # 解析参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            --zip-file) zip_file="$2"; shift 2 ;;
            --presigned-url) presigned_url="$2"; shift 2 ;;
            *) echo -e "${RED}Unknown option: $1${NC}"; return 1 ;;
        esac
    done

    if [ -z "$zip_file" ]; then
        echo -e "${RED}Error: --zip-file is required${NC}" >&2
        return 1
    fi

    if [ ! -f "$zip_file" ]; then
        echo -e "${RED}Error: File not found: $zip_file${NC}" >&2
        return 1
    fi

    if [ -z "$presigned_url" ]; then
        echo -e "${RED}Error: --presigned-url is required${NC}" >&2
        return 1
    fi

    echo -e "${BLUE}======================================${NC}"
    echo -e "${BLUE}[Upload to OSS]${NC}"
    echo -e "${BLUE}======================================${NC}"
    echo "ZIP File: $zip_file"
    echo "Size: $(ls -lh "$zip_file" 2>/dev/null | awk '{print $5}')"
    echo ""

    echo "Uploading file to OSS..."
    echo ""

    # 使用 -T 选项上传到预签名URL（专门用于PUT文件上传）
    # -T 选项会自动使用 PUT 方法，并且不会添加额外的 Content-Type 头
    local response=$(curl -s --connect-timeout 10 --max-time 300 -w "\n---HTTP_CODE:%{http_code}---" \
        -T "${zip_file}" \
        "$presigned_url")

    # 提取HTTP状态码（使用sed，兼容性更好）
    local http_code=$(echo "$response" | sed -n 's/.*---HTTP_CODE:\([0-9]*\)---.*/\1/p' | tail -1)
    local response_body=$(echo "$response" | sed 's/---HTTP_CODE:[0-9]*---//g')

    echo "HTTP Status: $http_code"
    echo ""

    if [ -n "$response_body" ]; then
        echo "Response:"
        echo "$response_body"
        echo ""
    fi

    if [ -z "$http_code" ] || [ "$http_code" -ne 200 ]; then
        echo -e "${RED}Upload failed${NC}" >&2
        return 1
    fi

    echo -e "${GREEN}Upload successful${NC}"
    return 0
}

# 3. 触发检测（使用OSS地址）- 支持批量
trigger_detection() {
    local host="riskpunish.aliyuncs.com"
    local action="UploadFiles"
    local version="${API_VERSION}"
    local skills=""

    # 解析参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            --host) host="$2"; shift 2 ;;
            --skills) skills="$2"; shift 2 ;;
            *) echo -e "${RED}Unknown option: $1${NC}"; return 1 ;;
        esac
    done

    if [ -z "$skills" ]; then
        echo -e "${RED}Error: --skills is required${NC}" >&2
        echo "Usage: --skills 'skill1:url1:md5_1,skill2:url2:md5_2'" >&2
        echo "Format: skill:url:md5 (MD5 is REQUIRED, 32 lowercase hex chars)" >&2
        echo "Example: --skills 'my_skill:https://bucket.oss.com/file.zip:a1b2c3d4e5f6789012345678901234ab'" >&2
        return 1
    fi

    echo -e "${BLUE}======================================${NC}"
    echo -e "${BLUE}[Trigger Detection (Batch)]${NC}"
    echo -e "${BLUE}======================================${NC}"
    echo "Action: $action"
    echo "Skills: $skills"
    echo "Host: $host"
    echo ""

    # 生成请求参数
    local utc_date=$(get_utc_timestamp)
    local nonce=$(generate_nonce)

    # 构造JSON请求体（支持多个skill:url:md5对，逗号分隔）
    # 格式: skill1:url1:md5_1,skill2:url2:md5_2（MD5是必须的）
    local json_array=""
    IFS=',' read -ra SKILL_PAIRS <<< "$skills"
    for pair in "${SKILL_PAIRS[@]}"; do
        pair=$(echo "$pair" | xargs) # trim空格

        # 分割第一个冒号获取skill_name
        local skill_name="${pair%%:*}"
        local remainder="${pair#*:}"

        # 从remainder中提取URL和MD5
        # 需要找到最后一个冒号来分割URL和MD5
        local oss_url=""
        local md5_value=""

        # 查找MD5（32位小写十六进制字符）
        if [[ "$remainder" =~ ^(.+):([0-9a-f]{32})$ ]]; then
            # 匹配到了 url:md5 格式
            oss_url="${BASH_REMATCH[1]}"
            md5_value="${BASH_REMATCH[2]}"
        else
            # 没有找到有效的MD5格式
            echo -e "${RED}Error: MD5 is required and must be 32 lowercase hex chars${NC}" >&2
            echo -e "${RED}Invalid format in pair: $pair${NC}" >&2
            echo "Expected format: skill_name:oss_url:md5_value" >&2
            echo "Example: my_skill:https://bucket.oss.com/file.zip:a1b2c3d4e5f6789012345678901234ab" >&2
            return 1
        fi

        if [ -z "$skill_name" ] || [ -z "$oss_url" ] || [ -z "$md5_value" ]; then
            echo -e "${RED}Error: Invalid skill:url:md5 pair: $pair${NC}" >&2
            echo "All three components (skill_name, oss_url, md5) are required" >&2
            return 1
        fi

        # 转义JSON特殊字符
        local escaped_skill_name=$(json_escape "$skill_name")
        local escaped_oss_url=$(json_escape "$oss_url")

        # 构造JSON对象（MD5是必须字段）
        local skill_json="{\"SkillName\":\"$escaped_skill_name\",\"OssUrl\":\"$escaped_oss_url\",\"Md5\":\"$md5_value\"}"
        echo "  - Skill: $skill_name, MD5: $md5_value"

        if [ -z "$json_array" ]; then
            json_array="$skill_json"
        else
            json_array="$json_array,$skill_json"
        fi
    done
    echo ""
    local request_body="{\"Skills\":[$json_array]}"

    # 构造查询参数
    local query_string="Action=${action}&Version=${version}"
    local url="https://${host}/?${query_string}"

    echo "Sending request..."
    echo ""

    # 发送POST请求
    local response=$(curl -s --connect-timeout 10 --max-time 60 -w "\n---HTTP_CODE:%{http_code}---" \
        -X POST \
        "$url" \
        -H "User-Agent: AlibabaCloud-Agent-Skills/alibabacloud-openclaw-skill-security-scan" \
        -H "host: ${host}" \
        -H "x-acs-action: ${action}" \
        -H "x-acs-version: ${version}" \
        -H "x-acs-date: ${utc_date}" \
        -H "x-acs-signature-nonce: ${nonce}" \
        -H "Content-Type: application/json" \
        -d "$request_body")

    # 提取HTTP状态码（使用sed，兼容性更好）
    local http_code=$(echo "$response" | sed -n 's/.*---HTTP_CODE:\([0-9]*\)---.*/\1/p' | tail -1)
    local response_body=$(echo "$response" | sed 's/---HTTP_CODE:[0-9]*---//g')

    echo "HTTP Status: $http_code"
    echo ""
    echo "Response:"
    echo "$response_body"
    echo ""

    if [ -z "$http_code" ] || [ "$http_code" -ne 200 ]; then
        echo -e "${RED}Request failed${NC}" >&2
        return 1
    fi

    return 0
}

# 4. 查询文件风险情报 - 支持批量
query_file_risk() {
    local host="riskpunish.aliyuncs.com"
    local action="QueryFileRisk"
    local version="${API_VERSION}"
    local md5_list=""

    # 解析参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            --host) host="$2"; shift 2 ;;
            --md5-list) md5_list="$2"; shift 2 ;;
            *) echo -e "${RED}Unknown option: $1${NC}"; return 1 ;;
        esac
    done

    if [ -z "$md5_list" ]; then
        echo -e "${RED}Error: --md5-list is required${NC}" >&2
        echo "Usage: --md5-list md5_1,md5_2,md5_3" >&2
        return 1
    fi

    echo -e "${BLUE}======================================${NC}"
    echo -e "${BLUE}[Query File Risk (Batch)]${NC}"
    echo -e "${BLUE}======================================${NC}"
    echo "Action: $action"
    echo "MD5 List: $md5_list"
    echo "Host: $host"
    echo ""

    # 生成请求参数
    local utc_date=$(get_utc_timestamp)
    local nonce=$(generate_nonce)

    # 构造JSON数组格式的Md5List参数
    # 将逗号分隔的字符串转换为JSON数组: ["md5_1","md5_2"]
    local json_array=""
    IFS=',' read -ra MD5S <<< "$md5_list"
    for md5 in "${MD5S[@]}"; do
        md5=$(echo "$md5" | xargs) # trim空格
        if [ -z "$json_array" ]; then
            json_array="\"$md5\""
        else
            json_array="$json_array,\"$md5\""
        fi
    done
    local json_md5s="[$json_array]"

    # URL编码JSON数组（手动编码关键字符）
    local encoded_md5s=$(echo "$json_md5s" | sed 's/\[/%5B/g; s/\]/%5D/g; s/"/%22/g; s/,/%2C/g')
    local query_string="Action=${action}&Version=${version}&Md5List=${encoded_md5s}"
    local url="https://${host}/?${query_string}"

    echo "Sending request..."
    echo ""

    # 发送GET请求
    local response=$(curl -s --connect-timeout 10 --max-time 60 -w "\n---HTTP_CODE:%{http_code}---" \
        -X GET \
        "$url" \
        -H "User-Agent: AlibabaCloud-Agent-Skills/alibabacloud-openclaw-skill-security-scan" \
        -H "host: ${host}" \
        -H "x-acs-action: ${action}" \
        -H "x-acs-version: ${version}" \
        -H "x-acs-date: ${utc_date}" \
        -H "x-acs-signature-nonce: ${nonce}")

    # 提取HTTP状态码（使用sed，兼容性更好）
    local http_code=$(echo "$response" | sed -n 's/.*---HTTP_CODE:\([0-9]*\)---.*/\1/p' | tail -1)
    local response_body=$(echo "$response" | sed 's/---HTTP_CODE:[0-9]*---//g')

    echo "HTTP Status: $http_code"
    echo ""
    echo "Response:"
    echo "$response_body"
    echo ""

    if [ -z "$http_code" ] || [ "$http_code" -ne 200 ]; then
        echo -e "${RED}Request failed${NC}" >&2
        return 1
    fi

    return 0
}

# 5. 查询检测结果 - 支持批量
query_detection_result() {
    local host="riskpunish.aliyuncs.com"
    local action="QueryDetectionResult"
    local version="${API_VERSION}"
    local detection_ids=""

    # 解析参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            --host) host="$2"; shift 2 ;;
            --detection-ids) detection_ids="$2"; shift 2 ;;
            *) echo -e "${RED}Unknown option: $1${NC}"; return 1 ;;
        esac
    done

    if [ -z "$detection_ids" ]; then
        echo -e "${RED}Error: --detection-ids is required${NC}" >&2
        echo "Usage: --detection-ids id1,id2,id3" >&2
        return 1
    fi

    echo -e "${BLUE}======================================${NC}"
    echo -e "${BLUE}[Query Detection Result (Batch)]${NC}"
    echo -e "${BLUE}======================================${NC}"
    echo "Action: $action"
    echo "Detection IDs: $detection_ids"
    echo "Host: $host"
    echo ""

    # 生成请求参数
    local utc_date=$(get_utc_timestamp)
    local nonce=$(generate_nonce)

    # 构造JSON数组格式的DetectionIds参数
    # 将逗号分隔的字符串转换为JSON数组: ["id1","id2"]
    local json_array=""
    IFS=',' read -ra IDS <<< "$detection_ids"
    for id in "${IDS[@]}"; do
        id=$(echo "$id" | xargs) # trim空格
        if [ -z "$json_array" ]; then
            json_array="\"$id\""
        else
            json_array="$json_array,\"$id\""
        fi
    done
    local json_ids="[$json_array]"

    # URL编码JSON数组（手动编码关键字符）
    local encoded_ids=$(echo "$json_ids" | sed 's/\[/%5B/g; s/\]/%5D/g; s/"/%22/g; s/,/%2C/g')
    local query_string="Action=${action}&Version=${version}&DetectionIds=${encoded_ids}"
    local url="https://${host}/?${query_string}"

    echo "Sending request..."
    echo ""

    # 发送GET请求
    local response=$(curl -s --connect-timeout 10 --max-time 60 -w "\n---HTTP_CODE:%{http_code}---" \
        -X GET \
        "$url" \
        -H "User-Agent: AlibabaCloud-Agent-Skills/alibabacloud-openclaw-skill-security-scan" \
        -H "host: ${host}" \
        -H "x-acs-action: ${action}" \
        -H "x-acs-version: ${version}" \
        -H "x-acs-date: ${utc_date}" \
        -H "x-acs-signature-nonce: ${nonce}")

    # 提取HTTP状态码（使用sed，兼容性更好）
    local http_code=$(echo "$response" | sed -n 's/.*---HTTP_CODE:\([0-9]*\)---.*/\1/p' | tail -1)
    local response_body=$(echo "$response" | sed 's/---HTTP_CODE:[0-9]*---//g')

    echo "HTTP Status: $http_code"
    echo ""
    echo "Response:"
    echo "$response_body"
    echo ""

    if [ -z "$http_code" ] || [ "$http_code" -ne 200 ]; then
        echo -e "${RED}Request failed${NC}" >&2
        return 1
    fi

    return 0
}

# 6. 计算ZIP文件MD5
calculate_md5() {
    local zip_file=""

    # 解析参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            --zip-file) zip_file="$2"; shift 2 ;;
            *) echo -e "${RED}Unknown option: $1${NC}"; return 1 ;;
        esac
    done

    if [ -z "$zip_file" ]; then
        echo -e "${RED}Error: --zip-file is required${NC}" >&2
        return 1
    fi

    if [ ! -f "$zip_file" ]; then
        echo -e "${RED}Error: File not found: $zip_file${NC}" >&2
        return 1
    fi

    echo -e "${BLUE}======================================${NC}"
    echo -e "${BLUE}[Calculate MD5]${NC}"
    echo -e "${BLUE}======================================${NC}"
    echo "ZIP File: $zip_file"
    echo "Size: $(ls -lh "$zip_file" 2>/dev/null | awk '{print $5}')"
    echo ""

    echo "Calculating MD5..."
    local md5_value=$(calculate_file_md5 "$zip_file")
    local result=$?

    if [ $result -eq 0 ]; then
        echo ""
        echo -e "${GREEN}MD5: $md5_value${NC}"
        echo ""
        return 0
    else
        echo ""
        echo -e "${RED}Failed to calculate MD5${NC}"
        return 1
    fi
}

# ==================== 使用说明 ====================

show_usage() {
    cat << EOF
${BLUE}FileRiskService API Client V2 (Batch Support)${NC}

${YELLOW}Usage:${NC}
  $0 <command> [options]

${YELLOW}Commands:${NC}
  calculate-md5           Calculate MD5 of a ZIP file
  get-presigned-url       Get presigned URLs for file upload (supports batch)
  upload-to-oss           Upload file to OSS using presigned URL
  trigger-detection       Trigger detection for uploaded files (supports batch, MD5 required)
  query-file-risk         Query file risk intelligence by MD5 (supports batch)
  query-detection         Query detection results (supports batch)

${YELLOW}Options:${NC}
  --zip-file <path>       Path to ZIP file
                          Used by: calculate-md5, upload-to-oss
  --skill-names <names>   Comma-separated skill names
                          Used by: get-presigned-url
                          Example: skill1,skill2,skill3
  --presigned-url <url>   Presigned URL for upload
                          Used by: upload-to-oss
                          Example: "https://bucket.oss.com/file.zip?..."
  --skills <pairs>        Comma-separated skill:url:md5 triplets
                          Used by: trigger-detection
                          Format: 'skill1:url1:md5_1,skill2:url2:md5_2'
                          ${RED}MD5 is REQUIRED (32 lowercase hex chars)${NC}
  --md5-list <md5s>       Comma-separated MD5 values
                          Used by: query-file-risk
                          Example: md5_1,md5_2,md5_3
  --detection-ids <ids>   Comma-separated detection IDs
                          Used by: query-detection
                          Example: id1,id2,id3
  --host <host>           API host (optional, default: riskpunish.aliyuncs.com)
                          Used by: get-presigned-url, trigger-detection, query-file-risk, query-detection

${YELLOW}Workflow Examples:${NC}

  ${GREEN}[Optional] Calculate MD5 of your ZIP file:${NC}
  $0 calculate-md5 --zip-file ./my_skill.zip
  ${BLUE}# Output: MD5: a1b2c3d4e5f6789012345678901234ab${NC}

  ${GREEN}Step 1: Get presigned upload URL${NC}
  $0 get-presigned-url --skill-names my_skill
  ${BLUE}# Extract OssUrl from response for next step${NC}

  ${GREEN}Step 2: Upload file to OSS${NC}
  $0 upload-to-oss --zip-file ./my_skill.zip --presigned-url "https://bucket.oss.com/path/file.zip?..."
  ${BLUE}# Use the OssUrl from Step 1${NC}

  ${GREEN}Step 3: Trigger detection${NC}
  $0 trigger-detection --skills 'my_skill:https://bucket.oss.com/path/file.zip:a1b2c3d4e5f6789012345678901234ab'
  ${BLUE}# Use OssUrl from Step 1 and MD5 from calculate-md5${NC}
  ${BLUE}# Extract DetectionId from response for next step${NC}

  ${GREEN}Step 4: Query detection result${NC}
  $0 query-detection --detection-ids "7ecfb680e0aa4118b3892a2d98c30d1f"
  ${BLUE}# Use DetectionId from Step 3${NC}

${YELLOW}Batch Operation Examples:${NC}

  ${GREEN}Batch: Query file risk intelligence${NC}
  $0 query-file-risk --md5-list md5_1,md5_2,md5_3

  ${GREEN}Batch: Get presigned URLs for multiple skills${NC}
  $0 get-presigned-url --skill-names skill1,skill2,skill3

  ${GREEN}Batch: Trigger detection for multiple files${NC}
  $0 trigger-detection --skills 'skill1:url1:md5_1,skill2:url2:md5_2,skill3:url3:md5_3'

  ${GREEN}Batch: Query multiple detection results${NC}
  $0 query-detection --detection-ids id1,id2,id3

${YELLOW}Important Notes:${NC}
  - ${RED}Always quote parameters containing special characters (URLs, comma-separated values)${NC}
  - MD5 calculation supports: Windows (PowerShell/certutil), Linux (md5sum), macOS (md5)
  - MD5 must be exactly 32 lowercase hexadecimal characters (a-f, 0-9)
  - ${RED}MD5 is REQUIRED in trigger-detection${NC}
  - All API responses are output directly without parsing
  - Extract values from responses manually for subsequent steps

${YELLOW}MD5 Format:${NC}
  - Length: 32 characters
  - Characters: lowercase hexadecimal (a-f, 0-9)
  - Example: ${BLUE}a1b2c3d4e5f6789012345678901234ab${NC}

${YELLOW}Parameter Format:${NC}
  - skill-names: ${BLUE}skill1,skill2,skill3${NC}
  - skills: ${BLUE}'skill1:url1:md5_1,skill2:url2:md5_2'${NC}
  - detection-ids: ${BLUE}id1,id2,id3${NC}

EOF
}

# ==================== 主程序入口 ====================

main() {
    check_dependencies

    if [ $# -eq 0 ]; then
        show_usage
        exit 1
    fi

    local command="$1"
    shift

    case "$command" in
        calculate-md5)
            calculate_md5 "$@"
            ;;
        get-presigned-url)
            get_presigned_url "$@"
            ;;
        upload-to-oss)
            upload_to_oss "$@"
            ;;
        trigger-detection)
            trigger_detection "$@"
            ;;
        query-file-risk)
            query_file_risk "$@"
            ;;
        query-detection-result|query-detection)
            query_detection_result "$@"
            ;;
        help|--help|-h)
            show_usage
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown command: $command${NC}" >&2
            echo ""
            show_usage
            exit 1
            ;;
    esac
}

# Only execute main if script is run directly (not sourced)
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    main "$@"
fi



