#!/bin/bash

# ====================================================================
# E-HPC Instant - 作业删除脚本 (CLI模式)
# ====================================================================
# 基于SDK脚本: delete_jobs.py
# 功能: 删除指定的E-HPC Instant作业
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
${BLUE}E-HPC Instant 作业删除工具${NC}

${YELLOW}功能说明:${NC}
  删除指定的E-HPC Instant作业

${YELLOW}环境变量配置:${NC}
  REGION                          - 地域 (默认: cn-shanghai)

${YELLOW}使用方式:${NC}
  ./delete_jobs.sh <JobId>
  
${YELLOW}参数:${NC}
  JobId - 要删除的作业ID (必需)

EOF
}

# 参数验证
if [[ $# -eq 0 ]] || [[ "$1" == "-h" ]] || [[ "$1" == "--help" ]]; then
    if [[ $# -eq 0 ]]; then
        echo -e "${RED}❌ 错误: 请提供作业ID${NC}"
    fi
    show_help
    exit 1
fi

JOB_ID="$1"

# 输入校验
validate_job_id "$JOB_ID"

# 验证阿里云CLI
ALIYUN_CLI="aliyun"
if ! command -v "$ALIYUN_CLI" &> /dev/null; then
    echo -e "${RED}❌ 错误: 未找到 aliyun CLI${NC}"
    echo -e "${YELLOW}请先安装阿里云CLI: https://help.aliyun.com/document_detail/121529.html${NC}"
    exit 1
fi

REGION="${REGION:-cn-shanghai}"
validate_region "$REGION"

echo -e "${BLUE}🗑️  删除作业${NC}"
echo -e "${BLUE}============${NC}"
echo -e "作业ID: ${CYAN}$JOB_ID${NC}"
echo -e "地域:   ${CYAN}$REGION${NC}"
echo ""

# 安全确认
read -p "$(echo -e "${RED}❓ 确认删除作业 $JOB_ID? 此操作不可逆! (y/N): ${NC}")" -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}❌ 操作已取消${NC}"
    exit 0
fi

# 构建JobSpec JSON
JOB_SPEC_JSON="[{\"JobId\":\"$JOB_ID\"}]"

echo -e "${BLUE}📤 正在删除...${NC}"

# 执行删除
if $ALIYUN_CLI ehpcinstant DeleteJobs --JobSpec "$JOB_SPEC_JSON" --region "$REGION" --connect-timeout 5 --read-timeout 10 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ehpc-instant-job-skill; then
    echo -e "${GREEN}✅ 作业删除成功！${NC}"
    echo -e "${GREEN}💡 提示:${NC}"
    echo -e "  • 验证结果: ./list_jobs.sh"
else
    echo -e "${RED}❌ 删除失败！${NC}"
    exit 1
fi
