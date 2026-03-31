#!/bin/bash
# Tair 自动化脚本
# 创建阿里云 Tair 企业版实例，配置公网访问并验证连通性

set -e

# 清除代理设置，避免 Bad file descriptor 错误
unset HTTP_PROXY HTTPS_PROXY http_proxy https_proxy ALL_PROXY all_proxy

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 检测包管理器，返回安装提示
get_install_hint() {
    local pkg_name="$1"
    if [[ "$(uname -s)" == "Darwin" ]]; then
        echo "brew install $pkg_name"
    elif command -v apt-get &> /dev/null; then
        echo "sudo apt-get install -y $pkg_name"
    elif command -v yum &> /dev/null; then
        echo "sudo yum install -y $pkg_name"
    else
        echo "请通过系统包管理器安装 $pkg_name"
    fi
}

# 检查依赖
check_dependencies() {
    log_info "检查依赖..."
    
    if ! command -v aliyun &> /dev/null; then
        log_error "aliyun CLI 未安装，请先安装: $(get_install_hint aliyun-cli)"
        exit 1
    fi
    
    if ! command -v jq &> /dev/null; then
        log_error "jq 未安装，请先安装: $(get_install_hint jq)"
        exit 1
    fi
    
    log_success "依赖检查完成"
}

# 参数格式校验
validate_params() {
    local has_error=false
    
    # VPC_ID 格式: vpc-[a-zA-Z0-9]+
    if [[ ! "$VPC_ID" =~ ^vpc-[a-zA-Z0-9]+$ ]]; then
        log_error "VPC_ID 格式错误: $VPC_ID (应为 vpc-xxx 格式)"
        has_error=true
    fi
    
    # VSWITCH_ID 格式: vsw-[a-zA-Z0-9]+
    if [[ ! "$VSWITCH_ID" =~ ^vsw-[a-zA-Z0-9]+$ ]]; then
        log_error "VSWITCH_ID 格式错误: $VSWITCH_ID (应为 vsw-xxx 格式)"
        has_error=true
    fi
    
    # REGION_ID 格式: 小写字母-小写字母数字
    if [[ ! "$REGION_ID" =~ ^[a-z]+-[a-z0-9-]+$ ]]; then
        log_error "REGION_ID 格式错误: $REGION_ID (应为 cn-hangzhou 格式)"
        has_error=true
    fi
    
    # ZONE_ID 格式: 小写字母-小写字母数字-小写字母
    if [[ ! "$ZONE_ID" =~ ^[a-z]+-[a-z0-9-]+$ ]]; then
        log_error "ZONE_ID 格式错误: $ZONE_ID (应为 cn-hangzhou-h 格式)"
        has_error=true
    fi
    
    # INSTANCE_TYPE 格式: tair_xxx
    if [[ ! "$INSTANCE_TYPE" =~ ^tair_[a-z]+$ ]]; then
        log_error "INSTANCE_TYPE 格式错误: $INSTANCE_TYPE (应为 tair_rdb 格式)"
        has_error=true
    fi
    
    # INSTANCE_CLASS 格式: tair.xxx.NNg
    if [[ ! "$INSTANCE_CLASS" =~ ^tair\.[a-z]+\.[0-9]+g$ ]]; then
        log_error "INSTANCE_CLASS 格式错误: $INSTANCE_CLASS (应为 tair.rdb.1g 格式)"
        has_error=true
    fi
    
    # INSTANCE_NAME 格式: 字母数字下划线横杠
    if [[ ! "$INSTANCE_NAME" =~ ^[a-zA-Z0-9_-]+$ ]]; then
        log_error "INSTANCE_NAME 格式错误: $INSTANCE_NAME (仅允许字母数字下划线横杠)"
        has_error=true
    fi
    
    # MY_PUBLIC_IP 格式: IPv4 地址
    if [ -n "$MY_PUBLIC_IP" ] && [[ ! "$MY_PUBLIC_IP" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        log_error "MY_PUBLIC_IP 格式错误: $MY_PUBLIC_IP (应为 IPv4 地址)"
        has_error=true
    fi
    
    if [ "$has_error" = true ]; then
        exit 1
    fi
    
    log_success "参数校验通过"
}

# 获取配置
get_config() {
    log_info "配置参数..."
    
    # 默认值
    REGION_ID="${REGION_ID:-cn-hangzhou}"
    ZONE_ID="${ZONE_ID:-cn-hangzhou-j}"
    INSTANCE_NAME="${INSTANCE_NAME:-tair-benchmark-$(date +%Y%m%d%H%M%S)}"
    INSTANCE_TYPE="${INSTANCE_TYPE:-tair_rdb}"
    INSTANCE_CLASS="${INSTANCE_CLASS:-tair.rdb.1g}"
    CHARGE_TYPE="${CHARGE_TYPE:-PostPaid}"
    
    # 必填参数检查
    if [ -z "$VPC_ID" ]; then
        log_error "缺少必填参数: VPC_ID"
        echo "请设置环境变量: export VPC_ID=\"vpc-xxx\""
        exit 1
    fi
    
    if [ -z "$VSWITCH_ID" ]; then
        log_error "缺少必填参数: VSWITCH_ID"
        echo "请设置环境变量: export VSWITCH_ID=\"vsw-xxx\""
        exit 1
    fi
    
    # 参数格式校验
    validate_params
    
    # 获取本机 IP (通过本地 ifconfig 命令)
    log_info "获取本机 IP..."
    
    if [ -n "$MY_PUBLIC_IP" ]; then
        log_success "使用环境变量 MY_PUBLIC_IP: $MY_PUBLIC_IP"
    else
        if [[ "$(uname -s)" == "Darwin" ]]; then
            MY_PUBLIC_IP=$(ifconfig en0 2>/dev/null | grep 'inet ' | grep -oE '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+' | head -n1)
            [ -z "$MY_PUBLIC_IP" ] && MY_PUBLIC_IP=$(ifconfig en1 2>/dev/null | grep 'inet ' | grep -oE '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+' | head -n1)
        else
            MY_PUBLIC_IP=$(ifconfig eth0 2>/dev/null | grep 'inet ' | grep -oE '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+' | head -n1)
            [ -z "$MY_PUBLIC_IP" ] && MY_PUBLIC_IP=$(ifconfig 2>/dev/null | grep 'inet ' | grep -oE '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+' | grep -v '127.0.0.1' | head -n1)
        fi
        
        if [ -n "$MY_PUBLIC_IP" ]; then
            log_success "本机 IP: $MY_PUBLIC_IP"
        fi
    fi
    
    if [ -z "$MY_PUBLIC_IP" ]; then
        log_error "无法获取本机 IP，请手动设置 MY_PUBLIC_IP 环境变量"
        exit 1
    fi
    log_success "公网 IP: $MY_PUBLIC_IP"
    
    echo ""
    log_info "配置信息:"
    echo "  Region: $REGION_ID"
    echo "  Zone: $ZONE_ID"
    echo "  VPC: $VPC_ID"
    echo "  VSwitch: $VSWITCH_ID"
    echo "  Instance Name: $INSTANCE_NAME"
    echo "  Instance Type: $INSTANCE_TYPE"
    echo "  Instance Class: $INSTANCE_CLASS"
    echo "  Charge Type: $CHARGE_TYPE"
    echo ""
}

# 创建实例
create_instance() {
    log_info "创建 Tair 实例..."
    
    MAX_RETRIES=3
    RETRY_INTERVAL=10
    
    for i in $(seq 1 $MAX_RETRIES); do
        log_info "创建实例尝试 ($i/$MAX_RETRIES)..."
        
        # 生成 ClientToken 确保幂等性
        CLIENT_TOKEN="tair-${INSTANCE_NAME}-$(date +%s)"
        
        RESULT=$(aliyun r-kvstore CreateTairInstance \
            --RegionId "$REGION_ID" \
            --ZoneId "$ZONE_ID" \
            --VpcId "$VPC_ID" \
            --VSwitchId "$VSWITCH_ID" \
            --InstanceName "$INSTANCE_NAME" \
            --InstanceType "$INSTANCE_TYPE" \
            --InstanceClass "$INSTANCE_CLASS" \
            --ChargeType "$CHARGE_TYPE" \
            --ShardType "MASTER_SLAVE" \
            --ClientToken "$CLIENT_TOKEN" \
            --AutoPay true \
            --user-agent AlibabaCloud-Agent-Skills 2>&1 || true)
        
        INSTANCE_ID=$(echo "$RESULT" | jq -r '.InstanceId' 2>/dev/null || true)
        
        if [ -n "$INSTANCE_ID" ] && [ "$INSTANCE_ID" != "null" ]; then
            log_success "实例创建成功: $INSTANCE_ID"
            echo "$INSTANCE_ID" > /tmp/tair_instance_id.txt
            return 0
        fi
        
        log_warn "创建实例失败，${RETRY_INTERVAL}秒后重试..."
        log_warn "错误信息: $(echo "$RESULT" | jq -r '.Message // .message // "未知错误"' 2>/dev/null || echo "$RESULT")"
        
        if [ $i -lt $MAX_RETRIES ]; then
            sleep $RETRY_INTERVAL
        fi
    done
    
    log_error "创建实例失败，已重试 $MAX_RETRIES 次"
    log_error "最后错误: $RESULT"
    exit 1
}

# 等待实例就绪
wait_for_instance() {
    log_info "等待实例就绪 (最多 10 分钟)..."
    
    MAX_RETRIES=20
    RETRY_INTERVAL=30
    
    for i in $(seq 1 $MAX_RETRIES); do
        RESULT=$(aliyun r-kvstore DescribeInstanceAttribute --InstanceId "$INSTANCE_ID" --user-agent AlibabaCloud-Agent-Skills 2>/dev/null || echo '{}')
        
        # 尝试多种可能的 JSON 路径
        STATUS=$(echo "$RESULT" | jq -r '.Instances.DBInstanceAttribute[0].InstanceStatus // .InstanceStatus // empty' 2>/dev/null || true)
        
        # 如果状态为空，设置为 Unknown
        if [ -z "$STATUS" ]; then
            STATUS="Unknown"
        fi
        
        if [ "$STATUS" == "Normal" ] || [ "$STATUS" == "Running" ]; then
            log_success "实例已就绪 (状态: $STATUS)"
            return 0
        fi
        
        log_info "实例状态: $STATUS, 等待中... ($i/$MAX_RETRIES)"
        sleep $RETRY_INTERVAL
    done
    
    log_error "等待超时，实例状态: $STATUS"
    exit 1
}

# 配置白名单
configure_whitelist() {
    log_info "配置白名单..."
    
    if ! aliyun r-kvstore ModifySecurityIps \
        --InstanceId "$INSTANCE_ID" \
        --SecurityIps "$MY_PUBLIC_IP" \
        --SecurityIpGroupName "benchmark" \
        --user-agent AlibabaCloud-Agent-Skills > /dev/null 2>&1; then
        log_error "白名单配置失败"
        exit 1
    fi
    
    log_success "白名单配置完成: $MY_PUBLIC_IP"
}

# 分配公网地址
allocate_public_connection() {
    log_info "分配公网连接地址..."
    
    # 生成连接前缀 (小写字母开头，8-40字符)
    CONNECTION_PREFIX=$(echo "$INSTANCE_ID" | tr '[:upper:]' '[:lower:]' | sed 's/-//g' | cut -c1-20)
    CONNECTION_PREFIX="${CONNECTION_PREFIX}pub"
    
    if ! aliyun r-kvstore AllocateInstancePublicConnection \
        --InstanceId "$INSTANCE_ID" \
        --ConnectionStringPrefix "$CONNECTION_PREFIX" \
        --Port "6379" \
        --user-agent AlibabaCloud-Agent-Skills > /dev/null 2>&1; then
        log_error "公网地址分配失败"
        exit 1
    fi
    
    log_success "公网地址分配请求已提交"
    
    # 等待实例恢复运行状态
    log_info "等待实例恢复运行状态..."
    MAX_RETRIES=20
    RETRY_INTERVAL=30
    
    for i in $(seq 1 $MAX_RETRIES); do
        RESULT=$(aliyun r-kvstore DescribeInstanceAttribute --InstanceId "$INSTANCE_ID" --user-agent AlibabaCloud-Agent-Skills 2>/dev/null || echo '{}')
        
        # 尝试多种可能的 JSON 路径
        STATUS=$(echo "$RESULT" | jq -r '.Instances.DBInstanceAttribute[0].InstanceStatus // .InstanceStatus // empty' 2>/dev/null || true)
        
        # 如果状态为空，设置为 Unknown
        if [ -z "$STATUS" ]; then
            STATUS="Unknown"
        fi
        
        if [ "$STATUS" == "Normal" ] || [ "$STATUS" == "Running" ]; then
            log_success "实例已恢复运行状态 (状态: $STATUS)"
            return 0
        fi
        
        log_info "实例状态: $STATUS, 等待中... ($i/$MAX_RETRIES)"
        sleep $RETRY_INTERVAL
    done
    
    log_error "等待超时，实例状态: $STATUS"
    exit 1
}

# 获取公网地址
get_public_connection() {
    log_info "获取公网连接信息..."
    
    RESULT=$(aliyun r-kvstore DescribeDBInstanceNetInfo --InstanceId "$INSTANCE_ID" --user-agent AlibabaCloud-Agent-Skills 2>&1 || true)
    
    PUBLIC_HOST=$(echo "$RESULT" | jq -r '.NetInfoItems.InstanceNetInfo[] | select(.IPType=="Public") | .ConnectionString' 2>/dev/null | head -n1 || true)
    PUBLIC_PORT=$(echo "$RESULT" | jq -r '.NetInfoItems.InstanceNetInfo[] | select(.IPType=="Public") | .Port' 2>/dev/null | head -n1 || true)
    
    if [ -z "$PUBLIC_HOST" ] || [ "$PUBLIC_HOST" == "null" ]; then
        log_error "获取公网地址失败"
        echo "$RESULT"
        exit 1
    fi
    
    log_success "公网地址: $PUBLIC_HOST:$PUBLIC_PORT"
}


# 主流程
main() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║     Tair DevToolset - 阿里云 Tair 实例创建与连通验证       ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    
    check_dependencies
    get_config
    
    log_info "开始创建实例..."
    
    create_instance
    wait_for_instance
    configure_whitelist
    allocate_public_connection
    get_public_connection
    
    log_success "全部完成!"
}

# 运行
main "$@"
