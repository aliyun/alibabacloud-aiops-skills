#!/bin/bash
# Skill文件夹ZIP打包脚本（带大小验证）
# Author: risk-console
# Date: 2026-03-27
# Description: 压缩skill文件夹，验证单个skill不超过10MB，最终ZIP不超过20MB
#
# 跨平台支持:
#   - Linux/macOS: 使用 zip 和 du 命令
#   - Windows: 支持以下压缩工具（按优先级）:
#     1. 7-Zip (推荐，下载地址: https://www.7-zip.org/)
#     2. PowerShell Compress-Archive (Windows 自带)
#
# Windows 使用注意:
#   - 建议在 Git Bash 中运行此脚本
#   - 如果使用 7-Zip，确保已安装到默认路径或添加到 PATH 环境变量

set -e
set -o pipefail

# ==================== 配置部分 ====================

# 大小限制（字节）
MAX_SINGLE_SKILL_SIZE=$((10 * 1024 * 1024))  # 10MB
MAX_FINAL_ZIP_SIZE=$((20 * 1024 * 1024))      # 20MB

# 全局变量（由 parse_args 设置）
OUTPUT_ZIP=""
SKILL_PATHS=()

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 检测操作系统
OS_TYPE="unknown"
ZIP_TOOL=""

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

# ==================== 依赖检查 ====================

check_dependencies() {
    detect_os

    if [ "$OS_TYPE" = "windows" ]; then
        # Windows环境检查
        # 优先检查7-Zip
        if command -v 7z &> /dev/null; then
            ZIP_TOOL="7z"
            echo -e "${GREEN}✓ Found 7-Zip (7z command)${NC}"
        elif [ -f "/c/Program Files/7-Zip/7z.exe" ]; then
            ZIP_TOOL="7z_full"
            echo -e "${GREEN}✓ Found 7-Zip at C:\\Program Files\\7-Zip\\7z.exe${NC}"
        elif [ -f "/c/Program Files (x86)/7-Zip/7z.exe" ]; then
            ZIP_TOOL="7z_x86"
            echo -e "${GREEN}✓ Found 7-Zip at C:\\Program Files (x86)\\7-Zip\\7z.exe${NC}"
        # 检查PowerShell（Windows自带）
        elif command -v powershell &> /dev/null || command -v pwsh &> /dev/null; then
            ZIP_TOOL="powershell"
            echo -e "${GREEN}✓ Found PowerShell (using Compress-Archive)${NC}"
        else
            echo -e "${RED}Error: No compression tool found on Windows${NC}" >&2
            echo "Please install one of the following:" >&2
            echo "  - 7-Zip: https://www.7-zip.org/" >&2
            echo "  - PowerShell (should be pre-installed)" >&2
            exit 1
        fi
    else
        # Linux/macOS环境检查
        local missing_deps=()
        command -v zip &> /dev/null || missing_deps+=("zip")
        command -v du &> /dev/null || missing_deps+=("du")

        if [ ${#missing_deps[@]} -gt 0 ]; then
            echo -e "${RED}Error: Missing required dependencies: ${missing_deps[*]}${NC}" >&2
            echo "Please install them using your package manager:" >&2
            exit 1
        fi
        ZIP_TOOL="zip"
    fi
}

# ==================== 工具函数 ====================

# 计算文件夹大小（字节）
get_folder_size() {
    local folder="$1"

    if [ "$OS_TYPE" = "windows" ]; then
        # Windows环境：使用PowerShell计算
        if command -v powershell &> /dev/null; then
            powershell -NoProfile -Command "(Get-ChildItem -Path '$folder' -Recurse -File | Measure-Object -Property Length -Sum).Sum" 2>/dev/null || echo "0"
        elif command -v pwsh &> /dev/null; then
            pwsh -NoProfile -Command "(Get-ChildItem -Path '$folder' -Recurse -File | Measure-Object -Property Length -Sum).Sum" 2>/dev/null || echo "0"
        else
            # 回退：尝试使用du（如果通过Git Bash可用）
            du -sb "$folder" 2>/dev/null | awk '{print $1}' || echo "0"
        fi
    else
        # 使用du命令，兼容Linux和macOS
        if du --version &>/dev/null 2>&1; then
            # GNU du (Linux)
            du -sb "$folder" 2>/dev/null | awk '{print $1}'
        else
            # BSD du (macOS)
            du -sk "$folder" 2>/dev/null | awk '{print $1 * 1024}'
        fi
    fi
}

# 字节转人类可读格式
bytes_to_human() {
    local bytes=$1

    if [ $bytes -lt 1024 ]; then
        echo "${bytes}B"
    elif [ $bytes -lt $((1024 * 1024)) ]; then
        # Use bc for calculation or fallback to integer division
        if command -v bc &> /dev/null; then
            echo "$(echo "scale=2; $bytes/1024" | bc)KB"
        else
            echo "$((bytes / 1024))KB"
        fi
    else
        # Use bc for calculation or fallback to integer division
        if command -v bc &> /dev/null; then
            echo "$(echo "scale=2; $bytes/1024/1024" | bc)MB"
        else
            echo "$((bytes / 1024 / 1024))MB"
        fi
    fi
}

# ==================== 核心功能函数 ====================

# 验证单个skill文件夹大小
validate_skill_size() {
    local skill_path="$1"
    local skill_name=$(basename "$skill_path")

    if [ ! -d "$skill_path" ]; then
        echo -e "${RED}Error: Skill folder not found: $skill_path${NC}" >&2
        return 1
    fi

    local size=$(get_folder_size "$skill_path")
    local size_human=$(bytes_to_human $size)

    if [ $size -gt $MAX_SINGLE_SKILL_SIZE ]; then
        echo -e "  ${YELLOW}⚠ Skipped: $skill_name ($size_human > 10MB)${NC}" >&2
        return 1
    fi

    echo -e "  ${GREEN}✓ Valid: $skill_name ($size_human)${NC}" >&2
    return 0
}

# 创建skill ZIP包
create_skills_zip() {
    local output_zip="$1"
    shift
    local skill_folders=("$@")

    echo -e "${BLUE}[Step 1] Validating skill folder sizes...${NC}"

    # 验证每个skill文件夹大小
    local valid_skills=()
    local total_size=0

    for skill_path in "${skill_folders[@]}"; do
        if validate_skill_size "$skill_path"; then
            valid_skills+=("$skill_path")
            local size=$(get_folder_size "$skill_path")
            total_size=$((total_size + size))
        fi
    done

    # 检查是否有有效的skill
    if [ ${#valid_skills[@]} -eq 0 ]; then
        echo -e "${RED}Error: No valid skills to pack (all exceeded 10MB limit)${NC}" >&2
        return 1
    fi

    echo ""
    echo -e "${BLUE}[Step 2] Packing ${#valid_skills[@]} skill folders into ZIP...${NC}"

    # 创建临时目录
    local temp_dir=$(mktemp -d)
    local original_dir=$(pwd)

    echo "  Temp directory: $temp_dir" >&2
    echo "  Original directory: $original_dir" >&2

    # 复制有效的skill文件夹到临时目录
    for skill_path in "${valid_skills[@]}"; do
        local skill_name=$(basename "$skill_path")
        echo "  Copying: $skill_name"
        cp -r "$skill_path" "$temp_dir/$skill_name/"
    done

    # 将所有文件时间戳设为固定值，确保相同内容产生相同的ZIP和MD5
    # 时间戳格式: YYYYMMDDhhmm.ss (2026-01-01 00:00:00)
    local fixed_timestamp="202601010000.00"
    echo "  Setting fixed timestamp: $fixed_timestamp" >&2

    local touch_count=0
    if find "$temp_dir" -exec touch -t "$fixed_timestamp" {} + 2>/dev/null; then
        touch_count=$(find "$temp_dir" -type f 2>/dev/null | wc -l | tr -d ' ')
        echo "  ✓ Fixed timestamp set for $touch_count files" >&2
    else
        echo "  ⚠ Warning: Failed to set fixed timestamp (may cause MD5 variation)" >&2
    fi

    echo "  Output ZIP path: $output_zip" >&2

    # 转换输出路径为绝对路径
    if [[ ! "$output_zip" = /* ]]; then
        output_zip="$original_dir/$output_zip"
    fi

    echo "  Absolute output path: $output_zip" >&2

    # 进入临时目录创建ZIP（确保第一层子目录为skill文件夹）
    cd "$temp_dir"

    # 调试：显示临时目录内容
    echo "  Temp directory contents:" >&2
    ls -la "$temp_dir" >&2 || true

    echo "  Creating ZIP archive..." >&2

    # 根据不同工具创建ZIP
    local zip_result=0
    case "$ZIP_TOOL" in
        "7z")
            echo "  Using 7z command..." >&2
            # 使用 . 避免通配符展开问题
            # -mtc=off 禁用创建时间，-mta=off 禁用访问时间（确保MD5一致性）
            7z a -tzip -mtc=off -mta=off "$output_zip" . 2>&1
            zip_result=$?
            ;;
        "7z_full")
            echo "  Using 7-Zip (64-bit)..." >&2
            # 7-Zip在Windows上需要Windows格式的路径
            local win_output_zip="$output_zip"
            if command -v cygpath &> /dev/null; then
                win_output_zip=$(cygpath -w "$output_zip" 2>/dev/null || echo "$output_zip")
            fi
            echo "  Windows path: $win_output_zip" >&2
            # 使用 . 避免通配符展开问题
            # -mtc=off 禁用创建时间，-mta=off 禁用访问时间（确保MD5一致性）
            "/c/Program Files/7-Zip/7z.exe" a -tzip -mtc=off -mta=off "$win_output_zip" . 2>&1
            zip_result=$?
            ;;
        "7z_x86")
            echo "  Using 7-Zip (32-bit)..." >&2
            local win_output_zip="$output_zip"
            if command -v cygpath &> /dev/null; then
                win_output_zip=$(cygpath -w "$output_zip" 2>/dev/null || echo "$output_zip")
            fi
            echo "  Windows path: $win_output_zip" >&2
            # 使用 . 避免通配符展开问题
            # -mtc=off 禁用创建时间，-mta=off 禁用访问时间（确保MD5一致性）
            "/c/Program Files (x86)/7-Zip/7z.exe" a -tzip -mtc=off -mta=off "$win_output_zip" . 2>&1
            zip_result=$?
            ;;
        "powershell")
            # PowerShell Compress-Archive需要绝对路径
            local ps_output_zip
            local ps_temp_dir

            if command -v cygpath &> /dev/null; then
                ps_output_zip=$(cygpath -w "$output_zip" 2>/dev/null)
                ps_temp_dir=$(cygpath -w "$temp_dir" 2>/dev/null)
            else
                # 手动转换路径（Git Bash格式转Windows格式）
                ps_output_zip=$(echo "$output_zip" | sed 's|^/\([a-z]\)/|\1:/|' | sed 's|/|\\|g')
                ps_temp_dir=$(echo "$temp_dir" | sed 's|^/\([a-z]\)/|\1:/|' | sed 's|/|\\|g')
            fi

            if command -v powershell &> /dev/null; then
                powershell -NoProfile -Command "Compress-Archive -Path '$ps_temp_dir\\*' -DestinationPath '$ps_output_zip' -Force" 2>&1 >&2
                zip_result=$?
            else
                pwsh -NoProfile -Command "Compress-Archive -Path '$ps_temp_dir\\*' -DestinationPath '$ps_output_zip' -Force" 2>&1 >&2
                zip_result=$?
            fi
            ;;
        *)
            # 默认使用zip命令（Linux/macOS）
            # 使用 . 代替 * 避免通配符展开和空格问题
            # -r 递归打包，-q 静默模式，-X 排除额外文件属性（确保MD5一致性）
            echo "  Using zip command on current directory contents..." >&2
            zip -r -q -X "$output_zip" . 2>&1
            zip_result=$?

            # 如果失败，尝试显式列出文件
            if [ $zip_result -ne 0 ]; then
                echo "  First attempt failed, trying explicit file list..." >&2
                # 使用find列出所有文件，避免通配符问题
                find . -mindepth 1 -maxdepth 1 -print0 | xargs -0 zip -r -q -X "$output_zip" 2>&1
                zip_result=$?
            fi
            ;;
    esac

    cd "$original_dir"
    rm -rf "$temp_dir"

    # 检查ZIP创建是否成功
    if [ $zip_result -ne 0 ]; then
        echo -e "${RED}Error: ZIP creation command failed (exit code: $zip_result)${NC}" >&2
        return 1
    fi

    if [ ! -f "$output_zip" ]; then
        echo -e "${RED}Error: Failed to create ZIP file${NC}" >&2
        return 1
    fi

    # 验证最终ZIP大小
    local zip_size=0
    if [ "$OS_TYPE" = "windows" ]; then
        # Windows环境：使用PowerShell获取文件大小
        if command -v powershell &> /dev/null; then
            zip_size=$(powershell -NoProfile -Command "(Get-Item '$output_zip').Length" 2>/dev/null || echo "0")
        elif command -v pwsh &> /dev/null; then
            zip_size=$(pwsh -NoProfile -Command "(Get-Item '$output_zip').Length" 2>/dev/null || echo "0")
        else
            # 回退：尝试使用stat
            zip_size=$(stat -c%s "$output_zip" 2>/dev/null || stat -f%z "$output_zip" 2>/dev/null || echo "0")
        fi
    else
        # Linux/macOS
        zip_size=$(stat -c%s "$output_zip" 2>/dev/null || stat -f%z "$output_zip" 2>/dev/null || echo "0")
    fi
    local zip_size_human=$(bytes_to_human $zip_size)

    if [ $zip_size -gt $MAX_FINAL_ZIP_SIZE ]; then
        echo -e "${RED}Error: Final ZIP size ($zip_size_human) exceeds 20MB limit${NC}" >&2
        rm -f "$output_zip"
        return 1
    fi

    echo -e "  ${GREEN}✓ ZIP created: $output_zip ($zip_size_human)${NC}"
    echo -e "  ${GREEN}✓ Packed ${#valid_skills[@]} skills (skipped ${#skill_folders[@]}-${#valid_skills[@]} large folders)${NC}"

    return 0
}

# ==================== 参数解析 ====================

usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Skill文件夹ZIP打包脚本 - 带大小验证

OPTIONS:
    --skill-paths PATHS     Skill文件夹路径列表（空格分隔）
    --output FILE           输出ZIP文件路径
    --max-skill-size SIZE   单个skill最大大小（MB，默认10）
    --max-zip-size SIZE     最终ZIP最大大小（MB，默认20）
    --help                  显示帮助信息

SIZE LIMITS:
    - 单个skill文件夹: 最大 10MB
    - 最终ZIP文件: 最大 20MB
    - 超过限制的skill文件夹将被自动跳过

EXAMPLES:
    # 基本用法（注意：--skill-paths 在 --output 之前）
    $0 --skill-paths ./test-stealth-risk --output ./test-stealth-risk.zip

    # 多个skill文件夹
    $0 --skill-paths /path/skill1 /path/skill2 /path/skill3 --output /tmp/skills.zip

    # 自定义大小限制
    $0 --skill-paths /path/skill1 /path/skill2 --output /tmp/skills.zip \\
       --max-skill-size 15 \\
       --max-zip-size 30

EXIT CODES:
    0 - 成功创建ZIP
    1 - 失败（没有有效skill或ZIP超过大小限制）

EOF
}

parse_args() {
    OUTPUT_ZIP=""
    SKILL_PATHS=()

    while [[ $# -gt 0 ]]; do
        case $1 in
            --output)
                OUTPUT_ZIP="$2"
                shift 2
                ;;
            --skill-paths)
                shift
                while [[ $# -gt 0 && ! "$1" =~ ^-- ]]; do
                    SKILL_PATHS+=("$1")
                    shift
                done
                ;;
            --max-skill-size)
                MAX_SINGLE_SKILL_SIZE=$(($2 * 1024 * 1024))
                shift 2
                ;;
            --max-zip-size)
                MAX_FINAL_ZIP_SIZE=$(($2 * 1024 * 1024))
                shift 2
                ;;
            --help)
                usage
                exit 0
                ;;
            *)
                echo -e "${RED}Error: Unknown option: $1${NC}" >&2
                usage >&2
                exit 1
                ;;
        esac
    done

    # 验证必需参数
    if [ -z "$OUTPUT_ZIP" ]; then
        echo -e "${RED}Error: Output file is required (--output)${NC}" >&2
        usage >&2
        exit 1
    fi

    if [ ${#SKILL_PATHS[@]} -eq 0 ]; then
        echo -e "${RED}Error: At least one skill path is required (--skill-paths)${NC}" >&2
        usage >&2
        exit 1
    fi
}

# ==================== 主函数 ====================

main() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}Skill ZIP Packager (Size Validation)${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""

    # 检查依赖
    check_dependencies

    # 解析命令行参数 (使用全局变量 OUTPUT_ZIP 和 SKILL_PATHS)
    parse_args "$@"

    echo "Configuration:"
    echo "  Output: $OUTPUT_ZIP"
    echo "  Skill Count: ${#SKILL_PATHS[@]}"
    echo "  Max Single Skill: $(bytes_to_human $MAX_SINGLE_SKILL_SIZE)"
    echo "  Max Final ZIP: $(bytes_to_human $MAX_FINAL_ZIP_SIZE)"
    echo ""

    # 创建ZIP
    if ! create_skills_zip "$OUTPUT_ZIP" "${SKILL_PATHS[@]}"; then
        echo ""
        echo -e "${RED}========================================${NC}"
        echo -e "${RED}Packaging failed!${NC}"
        echo -e "${RED}========================================${NC}"
        exit 1
    fi

    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}Packaging completed successfully!${NC}"
    echo -e "${GREEN}========================================${NC}"
}

# 执行主函数
main "$@"

