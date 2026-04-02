#!/bin/bash
# Tair Automation Script
# Create Alibaba Cloud Tair Enterprise Edition instance and configure public network access

set -e

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Detect package manager and return install hint
get_install_hint() {
    local pkg_name="$1"
    if [[ "$(uname -s)" == "Darwin" ]]; then
        echo "brew install $pkg_name"
    elif command -v apt-get &> /dev/null; then
        echo "sudo apt-get install -y $pkg_name"
    elif command -v yum &> /dev/null; then
        echo "sudo yum install -y $pkg_name"
    else
        echo "Please install $pkg_name via your system package manager"
    fi
}

# Check dependencies
check_dependencies() {
    log_info "Checking dependencies..."
    
    if ! command -v aliyun &> /dev/null; then
        log_error "aliyun CLI not installed, please install: $(get_install_hint aliyun-cli)"
        exit 1
    fi
    
    if ! command -v jq &> /dev/null; then
        log_error "jq not installed, please install: $(get_install_hint jq)"
        exit 1
    fi
    
    log_success "Dependency check completed"
}

# Parameter format validation
validate_params() {
    local has_error=false
    
    # VPC_ID format: vpc-[a-zA-Z0-9]+
    if [[ ! "$VPC_ID" =~ ^vpc-[a-zA-Z0-9]+$ ]]; then
        log_error "VPC_ID format error: $VPC_ID (should be vpc-xxx format)"
        has_error=true
    fi
    
    # VSWITCH_ID format: vsw-[a-zA-Z0-9]+
    if [[ ! "$VSWITCH_ID" =~ ^vsw-[a-zA-Z0-9]+$ ]]; then
        log_error "VSWITCH_ID format error: $VSWITCH_ID (should be vsw-xxx format)"
        has_error=true
    fi
    
    # REGION_ID format: lowercase-alphanumeric
    if [[ ! "$REGION_ID" =~ ^[a-z]+-[a-z0-9-]+$ ]]; then
        log_error "REGION_ID format error: $REGION_ID (should be cn-hangzhou format)"
        has_error=true
    fi
    
    # ZONE_ID format: lowercase-alphanumeric-lowercase
    if [[ ! "$ZONE_ID" =~ ^[a-z]+-[a-z0-9-]+$ ]]; then
        log_error "ZONE_ID format error: $ZONE_ID (should be cn-hangzhou-h format)"
        has_error=true
    fi
    
    # INSTANCE_TYPE format: tair_xxx
    if [[ ! "$INSTANCE_TYPE" =~ ^tair_[a-z]+$ ]]; then
        log_error "INSTANCE_TYPE format error: $INSTANCE_TYPE (should be tair_rdb format)"
        has_error=true
    fi
    
    # INSTANCE_CLASS format: tair.xxx.NNg
    if [[ ! "$INSTANCE_CLASS" =~ ^tair\.[a-z]+\.[0-9]+g$ ]]; then
        log_error "INSTANCE_CLASS format error: $INSTANCE_CLASS (should be tair.rdb.1g format)"
        has_error=true
    fi
    
    # INSTANCE_NAME format: alphanumeric underscore hyphen
    if [[ ! "$INSTANCE_NAME" =~ ^[a-zA-Z0-9_-]+$ ]]; then
        log_error "INSTANCE_NAME format error: $INSTANCE_NAME (only alphanumeric, underscore, hyphen allowed)"
        has_error=true
    fi
    
    # MY_PUBLIC_IP format: IPv4 address
    if [ -n "$MY_PUBLIC_IP" ] && [[ ! "$MY_PUBLIC_IP" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        log_error "MY_PUBLIC_IP format error: $MY_PUBLIC_IP (should be IPv4 address)"
        has_error=true
    fi
    
    if [ "$has_error" = true ]; then
        exit 1
    fi
    
    log_success "Parameter validation passed"
}

# Get configuration
get_config() {
    log_info "Configuring parameters..."
    
    # Default values
    REGION_ID="${REGION_ID:-cn-hangzhou}"
    ZONE_ID="${ZONE_ID:-cn-hangzhou-j}"
    INSTANCE_NAME="${INSTANCE_NAME:-tair-benchmark-$(date +%Y%m%d%H%M%S)}"
    INSTANCE_TYPE="${INSTANCE_TYPE:-tair_rdb}"
    INSTANCE_CLASS="${INSTANCE_CLASS:-tair.rdb.1g}"
    CHARGE_TYPE="${CHARGE_TYPE:-PostPaid}"
    
    # Required parameter check
    if [ -z "$VPC_ID" ]; then
        log_error "Missing required parameter: VPC_ID"
        echo "Please set environment variable: export VPC_ID=\"vpc-xxx\""
        exit 1
    fi
    
    if [ -z "$VSWITCH_ID" ]; then
        log_error "Missing required parameter: VSWITCH_ID"
        echo "Please set environment variable: export VSWITCH_ID=\"vsw-xxx\""
        exit 1
    fi
    
    # Parameter format validation
    validate_params
    
    # Get local IP (via local ifconfig command)
    log_info "Getting local IP..."
    
    if [ -n "$MY_PUBLIC_IP" ]; then
        log_success "Using environment variable MY_PUBLIC_IP: $MY_PUBLIC_IP"
    else
        if [[ "$(uname -s)" == "Darwin" ]]; then
            MY_PUBLIC_IP=$(ifconfig en0 2>/dev/null | grep 'inet ' | grep -oE '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+' | head -n1)
            [ -z "$MY_PUBLIC_IP" ] && MY_PUBLIC_IP=$(ifconfig en1 2>/dev/null | grep 'inet ' | grep -oE '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+' | head -n1)
        else
            MY_PUBLIC_IP=$(ifconfig eth0 2>/dev/null | grep 'inet ' | grep -oE '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+' | head -n1)
            [ -z "$MY_PUBLIC_IP" ] && MY_PUBLIC_IP=$(ifconfig 2>/dev/null | grep 'inet ' | grep -oE '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+' | grep -v '127.0.0.1' | head -n1)
        fi
        
        if [ -n "$MY_PUBLIC_IP" ]; then
            log_success "Local IP: $MY_PUBLIC_IP"
        fi
    fi
    
    if [ -z "$MY_PUBLIC_IP" ]; then
        log_error "Cannot get local IP, please manually set MY_PUBLIC_IP environment variable"
        exit 1
    fi
    log_success "Public IP: $MY_PUBLIC_IP"
    
    echo ""
    log_info "Configuration:"
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

# Create instance
create_instance() {
    log_info "Creating Tair instance..."
    
    MAX_RETRIES=3
    RETRY_INTERVAL=10
    
    for i in $(seq 1 $MAX_RETRIES); do
        log_info "Create instance attempt ($i/$MAX_RETRIES)..."
        
        # Generate ClientToken for idempotency
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
            log_success "Instance created successfully: $INSTANCE_ID"
            echo "$INSTANCE_ID" > /tmp/tair_instance_id.txt
            return 0
        fi
        
        log_warn "Instance creation failed, retrying in ${RETRY_INTERVAL} seconds..."
        log_warn "Error message: $(echo "$RESULT" | jq -r '.Message // .message // "Unknown error"' 2>/dev/null || echo "$RESULT")"
        
        if [ $i -lt $MAX_RETRIES ]; then
            sleep $RETRY_INTERVAL
        fi
    done
    
    log_error "Instance creation failed after $MAX_RETRIES retries"
    log_error "Last error: $RESULT"
    exit 1
}

# Wait for instance ready
wait_for_instance() {
    log_info "Waiting for instance ready (max 10 minutes)..."
    
    MAX_RETRIES=20
    RETRY_INTERVAL=30
    
    for i in $(seq 1 $MAX_RETRIES); do
        RESULT=$(aliyun r-kvstore DescribeInstanceAttribute --InstanceId "$INSTANCE_ID" --user-agent AlibabaCloud-Agent-Skills 2>/dev/null || echo '{}')
        
        # Try multiple possible JSON paths
        STATUS=$(echo "$RESULT" | jq -r '.Instances.DBInstanceAttribute[0].InstanceStatus // .InstanceStatus // empty' 2>/dev/null || true)
        
        # If status is empty, set to Unknown
        if [ -z "$STATUS" ]; then
            STATUS="Unknown"
        fi
        
        if [ "$STATUS" == "Normal" ] || [ "$STATUS" == "Running" ]; then
            log_success "Instance ready (Status: $STATUS)"
            return 0
        fi
        
        log_info "Instance status: $STATUS, waiting... ($i/$MAX_RETRIES)"
        sleep $RETRY_INTERVAL
    done
    
    log_error "Wait timeout, instance status: $STATUS"
    exit 1
}

# Configure whitelist
configure_whitelist() {
    log_info "Configuring whitelist..."
    
    if ! aliyun r-kvstore ModifySecurityIps \
        --InstanceId "$INSTANCE_ID" \
        --SecurityIps "$MY_PUBLIC_IP" \
        --SecurityIpGroupName "benchmark" \
        --user-agent AlibabaCloud-Agent-Skills > /dev/null 2>&1; then
        log_error "Whitelist configuration failed"
        exit 1
    fi
    
    log_success "Whitelist configured: $MY_PUBLIC_IP"
}

# Allocate public connection
allocate_public_connection() {
    log_info "Allocating public connection endpoint..."
    
    # Generate connection prefix (lowercase, 8-40 chars)
    CONNECTION_PREFIX=$(echo "$INSTANCE_ID" | tr '[:upper:]' '[:lower:]' | sed 's/-//g' | cut -c1-20)
    CONNECTION_PREFIX="${CONNECTION_PREFIX}pub"
    
    if ! aliyun r-kvstore AllocateInstancePublicConnection \
        --InstanceId "$INSTANCE_ID" \
        --ConnectionStringPrefix "$CONNECTION_PREFIX" \
        --Port "6379" \
        --user-agent AlibabaCloud-Agent-Skills > /dev/null 2>&1; then
        log_error "Public endpoint allocation failed"
        exit 1
    fi
    
    log_success "Public endpoint allocation request submitted"
    
    # Wait for instance to recover running status
    log_info "Waiting for instance to recover running status..."
    MAX_RETRIES=20
    RETRY_INTERVAL=30
    
    for i in $(seq 1 $MAX_RETRIES); do
        RESULT=$(aliyun r-kvstore DescribeInstanceAttribute --InstanceId "$INSTANCE_ID" --user-agent AlibabaCloud-Agent-Skills 2>/dev/null || echo '{}')
        
        # Try multiple possible JSON paths
        STATUS=$(echo "$RESULT" | jq -r '.Instances.DBInstanceAttribute[0].InstanceStatus // .InstanceStatus // empty' 2>/dev/null || true)
        
        # If status is empty, set to Unknown
        if [ -z "$STATUS" ]; then
            STATUS="Unknown"
        fi
        
        if [ "$STATUS" == "Normal" ] || [ "$STATUS" == "Running" ]; then
            log_success "Instance recovered running status (Status: $STATUS)"
            return 0
        fi
        
        log_info "Instance status: $STATUS, waiting... ($i/$MAX_RETRIES)"
        sleep $RETRY_INTERVAL
    done
    
    log_error "Wait timeout, instance status: $STATUS"
    exit 1
}

# Get public connection
get_public_connection() {
    log_info "Getting public connection info..."
    
    RESULT=$(aliyun r-kvstore DescribeDBInstanceNetInfo --InstanceId "$INSTANCE_ID" --user-agent AlibabaCloud-Agent-Skills 2>&1 || true)
    
    PUBLIC_HOST=$(echo "$RESULT" | jq -r '.NetInfoItems.InstanceNetInfo[] | select(.IPType=="Public") | .ConnectionString' 2>/dev/null | head -n1 || true)
    PUBLIC_PORT=$(echo "$RESULT" | jq -r '.NetInfoItems.InstanceNetInfo[] | select(.IPType=="Public") | .Port' 2>/dev/null | head -n1 || true)
    
    if [ -z "$PUBLIC_HOST" ] || [ "$PUBLIC_HOST" == "null" ]; then
        log_error "Failed to get public endpoint"
        echo "$RESULT"
        exit 1
    fi
    
    log_success "Public endpoint: $PUBLIC_HOST:$PUBLIC_PORT"
}


# Main flow
main() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║     Tair DevToolset - Alibaba Cloud Tair Instance Creator  ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    
    check_dependencies
    get_config
    
    log_info "Starting instance creation..."
    
    create_instance
    wait_for_instance
    configure_whitelist
    allocate_public_connection
    get_public_connection
    
    log_success "All completed!"
}

# Run
main "$@"
