#!/bin/bash

# ====================================================================
# E-HPC Instant - 长期运行VM作业创建脚本 (CLI模式)
# ====================================================================
# 基于SDK脚本: create_vm_job_longrunning.py
# 功能: 创建长期运行的虚拟机作业，适用于后台服务场景
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
${BLUE}E-HPC Instant 长期运行VM作业创建工具${NC}

${YELLOW}功能说明:${NC}
  创建长期运行的虚拟机作业，适用于后台服务、监控等场景

${YELLOW}环境变量配置:${NC}
  JOB_NAME                        - 作业名称 (默认: create_vm_job)
  JOB_DESCRIPTION                 - 作业描述 (默认: E-HPC Instant VM 后台服务作业提交)
  IMAGE_ID                        - VM镜像ID (默认: m-xxx)
  VSWITCH_ID                      - 虚拟交换机ID (默认: vsw-xxx)
  SECURITY_GROUP_ID               - 安全组ID (默认: sg-xxx)
  REGION                          - 地域 (默认: cn-shanghai)
  VM_PASSWORD                     - VM登录密码 (必填，避免明文硬编码)

${YELLOW}使用方式:${NC}
  ./create_vm_job_longrunning.sh [选项]
  
${YELLOW}选项:${NC}
  -h, --help    显示此帮助信息
  --dry-run     仅显示配置，不实际提交

EOF
}

# 参数解析
DRY_RUN=false
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        *)
            echo "未知参数: $1"
            show_help
            exit 1
            ;;
    esac
done

# 验证阿里云CLI
ALIYUN_CLI="aliyun"
if ! command -v "$ALIYUN_CLI" &> /dev/null; then
    echo -e "${RED}❌ 错误: 未找到 aliyun CLI${NC}"
    echo -e "${YELLOW}请先安装阿里云CLI: https://help.aliyun.com/document_detail/121529.html${NC}"
    exit 1
fi

# 获取配置参数
JOB_NAME="${JOB_NAME:-create_vm_job}"
JOB_DESCRIPTION="${JOB_DESCRIPTION:-E-HPC Instant VM 后台服务作业提交}"
IMAGE_ID="${IMAGE_ID:-m-xxx}"
VSWITCH_ID="${VSWITCH_ID:-vsw-xxx}"
SECURITY_GROUP_ID="${SECURITY_GROUP_ID:-sg-xxx}"
REGION="${REGION:-cn-shanghai}"

# 输入校验：所有外部输入必须通过白名单校验后才允许拼接进 JSON
validate_region "$REGION"
validate_job_name "$JOB_NAME"
validate_json_safe_text "JOB_DESCRIPTION" "$JOB_DESCRIPTION" 256
validate_image_id "$IMAGE_ID"
validate_vswitch_id "$VSWITCH_ID"
validate_security_group_id "$SECURITY_GROUP_ID"
validate_vm_password "$VM_PASSWORD"

# Base64编码的测试脚本
TEST_SCRIPT_BASE64="IyEvYmluL2Jhc2gKCnNsZWVwIDE4MAo="

echo -e "${BLUE}🚀 创建长期运行VM作业${NC}"
echo -e "${BLUE}======================${NC}"

# 显示配置摘要
echo -e "${YELLOW}📋 作业配置:${NC}"
echo -e "  ${BLUE}作业名称:${NC}      $JOB_NAME"
echo -e "  ${BLUE}作业描述:${NC}      $JOB_DESCRIPTION"
echo -e "  ${BLUE}地域:${NC}          $REGION"
echo -e "  ${BLUE}VM镜像:${NC}       $IMAGE_ID"
echo -e "  ${BLUE}vSwitch ID:${NC}   $VSWITCH_ID"
echo -e "  ${BLUE}安全组 ID:${NC}    $SECURITY_GROUP_ID"
echo -e "  ${BLUE}资源配置:${NC}      4 CPU核心, 8GB内存, 40GB系统盘"

if [ "$DRY_RUN" = true ]; then
    echo -e "${YELLOW}📝 模拟模式: 仅显示配置，不提交作业${NC}"
    echo -e "${GREEN}✅ 配置验证通过！${NC}"
    exit 0
fi

# 用户确认
echo ""
read -p "$(echo -e "${YELLOW}❓ 确认提交作业? (y/N): ${NC}")" -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}❌ 操作已取消${NC}"
    exit 0
fi

# 构建Tasks JSON
TASKS_JSON="[{
  \"TaskSpec\": {
    \"TaskExecutor\": [{
      \"VM\": {
        \"Image\": \"$IMAGE_ID\",
        \"Script\": \"$TEST_SCRIPT_BASE64\",
        \"Password\": \"$VM_PASSWORD\"
      }
    }],
    \"VolumeMount\": [{
      \"MountPath\": \"/mnt\",
      \"VolumeDriver\": \"alicloud/nas\",
      \"MountOptions\": \"{\\\"server\\\":\\\"xxx.cn-hangzhou.nas.aliyuncs.com\\\",\\\"vers\\\":\\\"3\\\",\\\"path\\\":\\\"/\\\",\\\"options\\\":\\\"nolock,tcp,noresvport\\\"}\"
    }],
    \"Resource\": {
      \"Disks\": [{
        \"Type\": \"System\",
        \"Size\": 40
      }],
      \"Cores\": 4,
      \"Memory\": 8
    }
  },
  \"ExecutorPolicy\": {
    \"MaxCount\": 1
  },
  \"TaskSustainable\": true
}]"

# 构建DeploymentPolicy JSON
DEPLOYMENT_POLICY_JSON="{
  \"Network\": {
    \"Vswitch\": [\"$VSWITCH_ID\"],
    \"EnableExternalIpAddress\": true
  },
  \"AllocationSpec\": \"Standard\",
  \"Level\": \"General\"
}"

# 构建SecurityPolicy JSON
SECURITY_POLICY_JSON="{
  \"SecurityGroup\": {
    \"SecurityGroupIds\": [\"$SECURITY_GROUP_ID\"]
  }
}"

echo -e "${BLUE}📤 正在提交作业...${NC}"

# 提交作业
if $ALIYUN_CLI ehpcinstant CreateJob \
    --JobName "$JOB_NAME" \
    --JobDescription "$JOB_DESCRIPTION" \
    --Tasks "$TASKS_JSON" \
    --DeploymentPolicy "$DEPLOYMENT_POLICY_JSON" \
    --SecurityPolicy "$SECURITY_POLICY_JSON" \
    --region "$REGION" \
    --connect-timeout 5 \
    --read-timeout 10 \
    --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ehpc-instant-job-skill; then
    
    echo -e "${GREEN}✅ 长期运行VM作业提交成功！${NC}"
    echo -e "${GREEN}💡 后续操作:${NC}"
    echo -e "  • 查看作业状态: ./list_jobs.sh"
    echo -e "  • 获取详情:     ./get_job.sh <JobId>"
else
    echo -e "${RED}❌ 作业提交失败！${NC}"
    exit 1
fi
