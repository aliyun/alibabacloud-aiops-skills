#!/bin/bash

# ====================================================================
# E-HPC Instant - 容器作业创建脚本 (CLI模式)
# 映射自: create_container_job.py
# ====================================================================
# 功能: 使用阿里云CLI创建E-HPC Instant容器作业
# 配置: 支持NAS挂载、环境变量、GPU实例等高级配置
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

# 脚本信息
SCRIPT_NAME="create_container_job.sh"
VERSION="1.0"

# 显示帮助信息
show_help() {
    cat << EOF
${BLUE}E-HPC Instant 容器作业创建工具 v$VERSION${NC}

${YELLOW}功能说明:${NC}
  创建支持NAS挂载、环境变量、GPU实例的容器作业

${YELLOW}环境变量配置:${NC}
  ALIBABA_CLOUD_REGION_ID     - 地域ID (默认: cn-shanghai)
  JOB_NAME                   - 作业名称 (默认: testX)
  JOB_DESCRIPTION            - 作业描述 (默认: container job test)
  CONTAINER_IMAGE            - 容器镜像 (默认: registry-vpc.cn-shanghai.aliyuncs.com/demo/xxx:v1.2)
  VSWITCH_ID                 - 虚拟交换机ID (默认: vsw-xxx)
  SECURITY_GROUP_ID          - 安全组ID (默认: sg-xxx)
  NAS_SERVER                 - NAS服务器地址 (默认: xxx.cn-shanghai.nas.aliyuncs.com)

${YELLOW}示例:${NC}
  # 使用默认配置
  ./$SCRIPT_NAME
  
  # 自定义配置
  JOB_NAME=my-container-job CONTAINER_IMAGE=my-registry/image:tag ./$SCRIPT_NAME

EOF
}

# 参数解析
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo "未知参数: $1"
            show_help
            exit 1
            ;;
    esac
done

echo -e "${BLUE}🚀 E-HPC Instant 容器作业创建工具${NC}"
echo -e "${BLUE}=================================${NC}"

# 验证阿里云CLI
ALIYUN_CLI="aliyun"
if ! command -v "$ALIYUN_CLI" &> /dev/null; then
    echo -e "${RED}❌ 错误: 未找到 aliyun CLI${NC}"
    echo -e "${YELLOW}请先安装并配置阿里云CLI${NC}"
    exit 1
fi

# 获取配置参数
REGION="${ALIBABA_CLOUD_REGION_ID:-cn-shanghai}"
JOB_NAME="${JOB_NAME:-testX-$(date +%Y%m%d-%H%M)}"
JOB_DESCRIPTION="${JOB_DESCRIPTION:-container job test}"
CONTAINER_IMAGE="${CONTAINER_IMAGE:-registry-vpc.cn-shanghai.aliyuncs.com/demo/xxx:v1.2}"
VSWITCH_ID="${VSWITCH_ID:-vsw-xxx}"
SECURITY_GROUP_ID="${SECURITY_GROUP_ID:-sg-xxx}"
NAS_SERVER="${NAS_SERVER:-xxx.cn-shanghai.nas.aliyuncs.com}"

# 输入校验：所有外部输入必须通过白名单校验后才允许拼接进 JSON
validate_region "$REGION"
validate_job_name "$JOB_NAME"
validate_json_safe_text "JOB_DESCRIPTION" "$JOB_DESCRIPTION" 256
validate_container_image "$CONTAINER_IMAGE"
validate_vswitch_id "$VSWITCH_ID"
validate_security_group_id "$SECURITY_GROUP_ID"
validate_hostname "NAS_SERVER" "$NAS_SERVER"

# 构建Tasks JSON (映射自Python SDK)
TASKS_JSON="[{
  \"TaskSpec\": {
    \"TaskExecutor\": [{
      \"Container\": {
        \"Image\": \"$CONTAINER_IMAGE\",
        \"AppId\": \"ci-ctn-xxx\",
        \"Command\": [\"sleep\", \"180000\"],
        \"EnvironmentVars\": [
          {
            \"Name\": \"RUN_PY_PATH\",
            \"Value\": \"/mnt/test.py\"
          },
          {
            \"Name\": \"OUTPUT_PATH\",
            \"Value\": \"/mnt/output/\"
          },
          {
            \"Name\": \"INPUT_PDB_PATH\",
            \"Value\": \"/mnt/input/test.pdb\"
          },
          {
            \"Name\": \"LOG_PATH\",
            \"Value\": \"/mnt/logs\"
          }
        ]
      }
    }],
    \"VolumeMount\": [{
      \"MountPath\": \"/mnt\",
      \"VolumeDriver\": \"alicloud/nas\",
      \"MountOptions\": \"{\\\"server\\\":\\\"$NAS_SERVER\\\",\\\"vers\\\":\\\"3\\\",\\\"path\\\":\\\"/\\\",\\\"options\\\":\\\"nolock,tcp,noresvport\\\"}\"
    }],
    \"Resource\": {
      \"Disks\": [{\"Type\": \"System\", \"Size\": 40}],
      \"Cores\": 8,
      \"Memory\": 32,
      \"InstanceTypes\": [\"ecs.gn6v-c8g1.2xlarge\"]
    }
  },
  \"ExecutorPolicy\": {\"MaxCount\": 1},
  \"TaskSustainable\": false
}]"

# 构建DeploymentPolicy JSON
DEPLOYMENT_POLICY_JSON="{
  \"Network\": {
    \"Vswitch\": [\"$VSWITCH_ID\"],
    \"EnableExternalIpAddress\": false
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

# 显示配置摘要
echo -e "${YELLOW}📋 作业配置摘要:${NC}"
echo -e "  ${BLUE}作业名称:${NC}      $JOB_NAME"
echo -e "  ${BLUE}作业描述:${NC}      $JOB_DESCRIPTION"
echo -e "  ${BLUE}地域:${NC}          $REGION"
echo -e "  ${BLUE}容器镜像:${NC}      $CONTAINER_IMAGE"
echo -e "  ${BLUE}实例规格:${NC}      ecs.gn6v-c8g1.2xlarge (V100 GPU, 8核32GB)"
echo -e "  ${BLUE}网络配置:${NC}      vSwitch=$VSWITCH_ID"
echo -e "  ${BLUE}安全组:${NC}        $SECURITY_GROUP_ID"
echo -e "  ${BLUE}NAS挂载:${NC}       $NAS_SERVER"

# 用户确认
echo ""
read -p "$(echo -e "${YELLOW}❓ 确认提交作业? (y/N): ${NC}")" -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}❌ 操作已取消${NC}"
    exit 0
fi

# 提交作业
echo -e "${BLUE}📤 正在提交作业...${NC}"

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
    
    echo -e "${GREEN}✅ 容器作业提交成功！${NC}"
    echo -e "${GREEN}💡 后续操作建议:${NC}"
    echo -e "  • 查看作业状态: ./list_jobs.sh"
    echo -e "  • 获取详细信息: ./get_job.sh <JobId>"
else
    echo -e "${RED}❌ 作业提交失败！${NC}"
    exit 1
fi
