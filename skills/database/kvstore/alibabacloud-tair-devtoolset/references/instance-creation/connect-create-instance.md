
## Create Instance And Connect

Use Alibaba Cloud CLI to create a Tair instance, configure network access, and verify connectivity with redis-cli.

### Create Instance

**Prerequisites:**

Install Alibaba Cloud CLI:

```bash
# macOS
brew install aliyun-cli

# Linux (x64)
curl --connect-timeout 10 --max-time 60 -O https://aliyuncli.alicdn.com/aliyun-cli-linux-latest-amd64.tgz
tar xzf aliyun-cli-linux-latest-amd64.tgz
sudo mv aliyun /usr/local/bin/

# Linux (arm64)
curl --connect-timeout 10 --max-time 60 -O https://aliyuncli.alicdn.com/aliyun-cli-linux-latest-arm64.tgz
tar xzf aliyun-cli-linux-latest-arm64.tgz
sudo mv aliyun /usr/local/bin/

# Windows (PowerShell)
Invoke-WebRequest -Uri https://aliyuncli.alicdn.com/aliyun-cli-windows-latest-amd64.zip -OutFile aliyun-cli.zip
Expand-Archive -Path aliyun-cli.zip -DestinationPath C:\aliyun-cli
```

Verify installation and configure credentials (required before any API call):

```bash
aliyun version
aliyun configure                       # interactive: set AccessKey / Region / Language
aliyun configure set --auto-plugin-install true   # required: r-kvstore commands depend on the aliyun-cli-r-kvstore plugin
```

Install redis-cli:

```bash
# macOS
brew install redis

# Ubuntu / Debian
sudo apt-get install redis-tools

# CentOS / RHEL
sudo yum install redis

# Windows
# Download from https://github.com/tporadowski/redis/releases
```

**Required parameters:**

| Parameter | Description | Example |
|-----------|-------------|---------|
| VPC_ID | VPC ID | `vpc-bp1xxx` |
| VSWITCH_ID | VSwitch ID | `vsw-bp1xxx` |
| PASSWORD | Instance password (8-32 chars, must include uppercase, lowercase, digits, special chars) | `YourPass123!` |

**Optional parameters (with defaults):**

| Parameter | Default |
|-----------|---------|
| REGION_ID | cn-hangzhou |
| ZONE_ID | cn-hangzhou-h |
| INSTANCE_TYPE | tair_rdb |
| INSTANCE_CLASS | tair.rdb.1g |
| CHARGE_TYPE | PostPaid |

**Example: Create Tair instance**

```bash
# Set environment variables
export VPC_ID="vpc-xxx"
export VSWITCH_ID="vsw-xxx"
export PASSWORD="YourPass123!"

# Optional parameters
export REGION_ID="cn-hangzhou"
export ZONE_ID="cn-hangzhou-h"
export INSTANCE_NAME="tair-benchmark-$(date +%Y%m%d%H%M%S)"
export INSTANCE_TYPE="tair_rdb"
export INSTANCE_CLASS="tair.rdb.1g"
export CHARGE_TYPE="PostPaid"

# Create instance
aliyun r-kvstore create-tair-instance \
  --biz-region-id "$REGION_ID" \
  --zone-id "$ZONE_ID" \
  --vpc-id "$VPC_ID" \
  --vswitch-id "$VSWITCH_ID" \
  --instance-name "$INSTANCE_NAME" \
  --instance-type "$INSTANCE_TYPE" \
  --instance-class "$INSTANCE_CLASS" \
  --password "$PASSWORD" \
  --charge-type "$CHARGE_TYPE" \
  --shard-type "MASTER_SLAVE" \
  --auto-pay true \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-tair-agent-skills
```

Save the returned `InstanceId` for subsequent steps.

**Example: Wait for instance ready**

```bash
# Replace with your instance ID
export INSTANCE_ID="r-bp1xxxxxxxxxxxx"

# Check instance status (repeat until status is Normal or Running)
aliyun r-kvstore describe-instance-attribute \
  --instance-id "$INSTANCE_ID" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-tair-agent-skills
```

**Example: Configure whitelist**

```bash
# Option 1: Auto-detect your local public IP
MY_PUBLIC_IP=$(curl -4 -s --connect-timeout 5 --max-time 10 ifconfig.me)

# Option 2: Specify IP manually
MY_PUBLIC_IP="1.2.3.4"

# Add IP to whitelist
aliyun r-kvstore modify-security-ips \
  --instance-id "$INSTANCE_ID" \
  --security-ips "$MY_PUBLIC_IP" \
  --security-ip-group-name "benchmark" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-tair-agent-skills
```

**Example: Allocate public connection address**

```bash
# Allocate public endpoint
aliyun r-kvstore allocate-instance-public-connection \
  --instance-id "$INSTANCE_ID" \
  --connection-string-prefix "${INSTANCE_ID}pub" \
  --port "6379" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-tair-agent-skills
```

**Example: Get public connection address**

> Public endpoint allocation is asynchronous — wait ~30s after `allocate-instance-public-connection` before querying or connecting.

```bash
sleep 30
aliyun r-kvstore describe-db-instance-net-info \
  --instance-id "$INSTANCE_ID" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-tair-agent-skills

# Find the connection string where IPType is "Public"
```

**Common instance specifications:**

| InstanceType | InstanceClass | Memory | Max Connections | Use Case |
|--------------|---------------|--------|-----------------|----------|
| tair_rdb | tair.rdb.1g | 1GB | 10000 | Testing/Dev |
| tair_rdb | tair.rdb.2g | 2GB | 10000 | Small apps |
| tair_rdb | tair.rdb.4g | 4GB | 10000 | Medium apps |
| tair_rdb | tair.rdb.8g | 8GB | 10000 | Large apps |

### Connect With redis-cli

After the instance is created and the public connection address is obtained, use redis-cli to connect and verify.

**Example: Connect to the instance**

```bash
# Authentication format for Alibaba Cloud Tair: InstanceID:Password
# Recommended: pass credentials via REDISCLI_AUTH env var (avoids leaking password in shell history / ps output)
export REDISCLI_AUTH='r-bp1xxxxxxxxxxxx:YourPass123!'
redis-cli -h r-bp1xxxxxxxxxxxxpub.redis.rds.aliyuncs.com -p 6379
```

**Example: Execute GET/SET operations**

```bash
# Set a key
127.0.0.1:6379> SET hello world
OK

# Get the key
127.0.0.1:6379> GET hello
"world"

# Set with expiration (seconds)
127.0.0.1:6379> SET session:token abc123 EX 3600
OK

# Get with TTL check
127.0.0.1:6379> GET session:token
"abc123"

127.0.0.1:6379> TTL session:token
(integer) 3599

# Delete a key
127.0.0.1:6379> DEL hello
(integer) 1

# Verify deletion
127.0.0.1:6379> GET hello
(nil)
```

**Troubleshooting:**

| Issue | Solution |
|-------|----------|
| Bad file descriptor | Clear proxy: `unset HTTP_PROXY HTTPS_PROXY http_proxy https_proxy` |
| Connection timeout | Check whitelist contains your public IPv4 address |
| Authentication failed | Use format `InstanceID:Password`, ensure password meets complexity requirements |
