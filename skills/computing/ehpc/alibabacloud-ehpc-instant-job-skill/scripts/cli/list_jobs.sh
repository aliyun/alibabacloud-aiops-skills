#!/bin/bash

# ====================================================================
# E-HPC Instant - 作业列表查询脚本 (CLI模式)
# ====================================================================
# 基于SDK脚本: list_jobs.py
# 功能: 查询E-HPC Instant作业列表，支持过滤条件
# ====================================================================

set -e

# ANSI颜色代码
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 加载共享输入校验库
source "$(dirname "$0")/_lib_validate.sh"

# 显示帮助信息
show_help() {
    cat << EOF
${BLUE}E-HPC Instant 作业列表查询工具${NC}

${YELLOW}功能说明:${NC}
  查询E-HPC Instant作业列表，支持按作业ID或名称过滤

${YELLOW}环境变量配置:${NC}
  JOB_ID                          - 按作业ID过滤 (可选)
  JOB_NAME                        - 按作业名称过滤 (可选)
  REGION                          - 地域 (默认: cn-shanghai)

${YELLOW}使用方式:${NC}
  ./list_jobs.sh [选项]
  
${YELLOW}选项:${NC}
  -h, --help    显示此帮助信息

EOF
}

# 参数解析
if [[ $# -gt 0 ]] && ([[ "$1" == "-h" ]] || [[ "$1" == "--help" ]]); then
    show_help
    exit 0
fi

# 验证阿里云CLI
ALIYUN_CLI="aliyun"
if ! command -v "$ALIYUN_CLI" &> /dev/null; then
    echo -e "${RED}❌ 错误: 未找到 aliyun CLI${NC}"
    echo -e "${YELLOW}请先安装阿里云CLI: https://help.aliyun.com/document_detail/121529.html${NC}"
    exit 1
fi

REGION="${REGION:-cn-shanghai}"

# 输入校验：防止 JSON 注入
validate_region "$REGION"
if [[ -n "$JOB_ID" ]]; then
    validate_job_id "$JOB_ID"
fi
if [[ -n "$JOB_NAME" ]]; then
    validate_job_name "$JOB_NAME"
fi

echo -e "${BLUE}🔍 查询作业列表${NC}"
echo -e "${BLUE}================${NC}"

# 构建过滤条件（输入已通过白名单校验，可安全拼接）
FILTER_JSON=""
if [[ -n "$JOB_ID" ]] || [[ -n "$JOB_NAME" ]]; then
    FILTER_JSON="{"
    if [[ -n "$JOB_ID" ]]; then
        FILTER_JSON+="\"JobId\":\"$JOB_ID\""
        if [[ -n "$JOB_NAME" ]]; then
            FILTER_JSON+=","
        fi
    fi
    if [[ -n "$JOB_NAME" ]]; then
        FILTER_JSON+="\"JobName\":\"$JOB_NAME\""
    fi
    FILTER_JSON+="}"
    
    echo -e "${YELLOW}📋 过滤条件:${NC}"
    if [[ -n "$JOB_ID" ]]; then
        echo -e "  ${BLUE}作业ID:${NC} $JOB_ID"
    fi
    if [[ -n "$JOB_NAME" ]]; then
        echo -e "  ${BLUE}作业名称:${NC} $JOB_NAME"
    fi
fi

echo -e "  ${BLUE}地域:${NC} $REGION"

# 执行查询
echo -e "${BLUE}📤 正在查询...${NC}"

QUERY_ARGS=(--region "$REGION" --connect-timeout 5 --read-timeout 10 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ehpc-instant-job-skill)

if [[ -n "$FILTER_JSON" ]]; then
    QUERY_ARGS+=(--Filter "$FILTER_JSON")
fi

if RESULT=$($ALIYUN_CLI ehpcinstant ListJobs "${QUERY_ARGS[@]}"); then
    echo -e "${GREEN}✅ 查询成功！${NC}"
    echo ""
    echo "$RESULT"
    
    echo -e "${GREEN}💡 提示:${NC}"
    echo -e "  • 获取详情: ./get_job.sh <JobId>"
    echo -e "  • 删除作业: ./delete_jobs.sh <JobId>"
else
    echo -e "${RED}❌ 查询失败！${NC}"
    exit 1
fi
