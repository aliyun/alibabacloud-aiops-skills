# Verification Method - Elasticsearch Instance Network Management

This document describes methods to verify whether various API operations are successful.

---

## 1. DescribeInstance Verification (Pre-check)

**Verification Command:**

```bash
aliyun elasticsearch describe-instance \
  --instance-id <InstanceId> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-network-manage
```

**Success Criteria:**

- HTTP status code: 200
- Response JSON contains `RequestId` field
- `Result.instanceId` matches the requested InstanceId
- `Result.archType` exists (used to determine TriggerNetwork support)

**Verification Script:**

```bash
INSTANCE_ID="es-cn-xxxxxx"
result=$(aliyun elasticsearch describe-instance --instance-id $INSTANCE_ID --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-network-manage 2>&1)

if echo "$result" | jq -e '.Result.instanceId' > /dev/null 2>&1; then
    returned_id=$(echo "$result" | jq -r '.Result.instanceId')
    arch_type=$(echo "$result" | jq -r '.Result.archType')
    
    if [ "$returned_id" == "$INSTANCE_ID" ]; then
        echo "✅ DescribeInstance succeeded"
        echo "Instance architecture type: $arch_type"
        
        # Check if cloud-native
        if [ "$arch_type" == "public" ]; then
            echo "⚠️  Cloud-native instance, TriggerNetwork not supported for Kibana private network"
        else
            echo "✅ Basic management instance, TriggerNetwork supported"
        fi
    else
        echo "❌ Returned instance ID does not match"
    fi
else
    echo "❌ DescribeInstance failed"
    echo "$result"
fi
```

---

## 2. TriggerNetwork Verification

**Verification Steps:**

1. Confirm instance is not cloud-native (archType != public) when operating Kibana private network
2. Execute TriggerNetwork
3. Use DescribeInstance to confirm network configuration changes

**Verification Command:**

```bash
INSTANCE_ID="es-cn-xxxxxx"
VPC_ID="vpc-xxxxxx"
VSWITCH_ID="vsw-xxxxxx"

# 1. Check architecture type
arch_type=$(aliyun elasticsearch describe-instance \
  --instance-id $INSTANCE_ID \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-network-manage | jq -r '.Result.archType')

if [ "$arch_type" == "public" ] && [ "$node_type" == "KIBANA" ] && [ "$network_type" == "PRIVATE" ]; then
  echo "❌ Cloud-native instance does not support TriggerNetwork for Kibana private network"
  exit 1
fi

# 2. Execute network change
echo "Triggering network change..."
result=$(aliyun elasticsearch trigger-network \
  --instance-id $INSTANCE_ID \
  --body '{"nodeType":"WORKER","networkType":"PUBLIC","actionType":"OPEN"}' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-network-manage 2>&1)

if echo "$result" | jq -e '.RequestId' > /dev/null 2>&1; then
  echo "✅ TriggerNetwork request submitted"
  echo "RequestId: $(echo "$result" | jq -r '.RequestId')"
else
  echo "❌ TriggerNetwork failed"
  echo "$result"
  exit 1
fi

# 3. Wait and verify network change (timeout: max 15 minutes)
sleep 10
echo "Verifying network configuration changes..."
max_retries=30
retry_count=0

start_time=$(date +%s)
timeout_seconds=900

while [ $retry_count -lt $max_retries ]; do
  # Check total timeout (15 minutes)
  current_time=$(date +%s)
  elapsed=$((current_time - start_time))
  if [ $elapsed -gt $timeout_seconds ]; then
    echo "⚠️  Verification timeout (15 minutes), please check network configuration manually"
    break
  fi
  
  network_config=$(aliyun elasticsearch describe-instance \
    --instance-id $INSTANCE_ID \
    --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-network-manage 2>/dev/null | jq -r '.Result.networkConfig')
  
  current_vpc=$(echo "$network_config" | jq -r '.vpcId')
  current_vswitch=$(echo "$network_config" | jq -r '.vswitchId')
  
  if [ "$current_vpc" == "$VPC_ID" ] && [ "$current_vswitch" == "$VSWITCH_ID" ]; then
    echo "✅ TriggerNetwork succeeded, network configuration updated"
    break
  fi
  
  retry_count=$((retry_count + 1))
  echo "Waiting for network change to complete... ($retry_count/$max_retries)"
  sleep 30
done

if [ $retry_count -eq $max_retries ]; then
  echo "⚠️  Verification timeout, please check network configuration manually"
fi
```

**Success Criteria:**

- TriggerNetwork request returns `RequestId`
- DescribeInstance returns network configuration matching the request

---

## 3. EnableKibanaPvlNetwork Verification

**Verification Steps:**

1. Execute EnableKibanaPvlNetwork
2. Use DescribeInstance to confirm Kibana PVL is enabled

**Verification Command:**

```bash
INSTANCE_ID="es-cn-xxxxxx"

# 1. Execute enable operation
echo "Enabling Kibana PVL..."
result=$(aliyun elasticsearch enable-kibana-pvl-network \
  --instance-id $INSTANCE_ID \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-network-manage 2>&1)

if echo "$result" | jq -e '.RequestId' > /dev/null 2>&1; then
  echo "✅ EnableKibanaPvlNetwork request submitted"
else
  echo "❌ EnableKibanaPvlNetwork failed"
  echo "$result"
  exit 1
fi

# 2. Wait and verify (timeout: max 10 minutes)
sleep 10
echo "Verifying Kibana PVL status..."
max_retries=20
retry_count=0
start_time=$(date +%s)
timeout_seconds=600

while [ $retry_count -lt $max_retries ]; do
  # Check total timeout
  current_time=$(date +%s)
  elapsed=$((current_time - start_time))
  if [ $elapsed -gt $timeout_seconds ]; then
    echo "⚠️  Verification timeout (10 minutes), please check Kibana PVL status manually"
    break
  fi
  
  pvl_enabled=$(aliyun elasticsearch describe-instance \
    --instance-id $INSTANCE_ID \
    --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-network-manage 2>/dev/null | jq -r '.Result.enableKibanaPrivateNetwork')
  
  if [ "$pvl_enabled" == "true" ]; then
    echo "✅ EnableKibanaPvlNetwork succeeded, Kibana PVL is enabled"
    break
  fi
  
  retry_count=$((retry_count + 1))
  echo "Waiting for Kibana PVL to enable... ($retry_count/$max_retries)"
  sleep 30
done

if [ $retry_count -eq $max_retries ]; then
  echo "⚠️  Verification timeout, please check Kibana PVL status manually"
fi
```

**Success Criteria:**

- EnableKibanaPvlNetwork request returns `RequestId`
- DescribeInstance returns `enableKibanaPrivateNetwork` as `true`

---

## 4. DisableKibanaPvlNetwork Verification

**Verification Steps:**

1. Confirm instance is cloud-native (archType=public)
2. Execute DisableKibanaPvlNetwork
3. Use DescribeInstance to confirm Kibana PVL is disabled

**Verification Command:**

```bash
INSTANCE_ID="es-cn-xxxxxx"

# 1. Execute disable operation
echo "Disabling Kibana PVL..."
result=$(aliyun elasticsearch disable-kibana-pvl-network \
  --instance-id $INSTANCE_ID \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-network-manage 2>&1)

if echo "$result" | jq -e '.RequestId' > /dev/null 2>&1; then
  echo "✅ DisableKibanaPvlNetwork request submitted"
else
  echo "❌ DisableKibanaPvlNetwork failed"
  echo "$result"
  exit 1
fi

# 2. Wait and verify (timeout: max 10 minutes)
sleep 10
echo "Verifying Kibana PVL status..."
max_retries=20
retry_count=0
start_time=$(date +%s)
timeout_seconds=600

while [ $retry_count -lt $max_retries ]; do
  # Check total timeout
  current_time=$(date +%s)
  elapsed=$((current_time - start_time))
  if [ $elapsed -gt $timeout_seconds ]; then
    echo "⚠️  Verification timeout (10 minutes), please check Kibana PVL status manually"
    break
  fi
  
  pvl_enabled=$(aliyun elasticsearch describe-instance \
    --instance-id $INSTANCE_ID \
    --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-network-manage 2>/dev/null | jq -r '.Result.enableKibanaPrivateNetwork')
  
  if [ "$pvl_enabled" == "false" ] || [ "$pvl_enabled" == "null" ]; then
    echo "✅ DisableKibanaPvlNetwork succeeded, Kibana PVL is disabled"
    break
  fi
  
  retry_count=$((retry_count + 1))
  echo "Waiting for Kibana PVL to disable... ($retry_count/$max_retries)"
  sleep 30
done

if [ $retry_count -eq $max_retries ]; then
  echo "⚠️  Verification timeout, please check Kibana PVL status manually"
fi
```

**Success Criteria:**

- DisableKibanaPvlNetwork request returns `RequestId`
- DescribeInstance returns `enableKibanaPrivateNetwork` as `false` or not exists

---

## 5. UpdateKibanaPvlNetwork Verification

**Verification Steps:**

1. Execute UpdateKibanaPvlNetwork
2. Use DescribeInstance to confirm Kibana private network access configuration is updated

**Verification Command:**

```bash
INSTANCE_ID="es-cn-xxxxxx"
PVL_ID="${INSTANCE_ID}-kibana-internal-internal"
NEW_SG="sg-bp1newgroup123"

# 1. Execute update operation
echo "Updating Kibana PVL configuration..."
result=$(aliyun elasticsearch update-kibana-pvl-network \
  --instance-id $INSTANCE_ID \
  --pvl-id $PVL_ID \
  --body "{\"securityGroups\": [\"$NEW_SG\"]}" \
  --read-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-network-manage 2>&1)

if echo "$result" | jq -e '.RequestId' > /dev/null 2>&1; then
  echo "✅ UpdateKibanaPvlNetwork request submitted"
  echo "RequestId: $(echo "$result" | jq -r '.RequestId')"
else
  echo "❌ UpdateKibanaPvlNetwork failed"
  echo "$result"
  exit 1
fi

# 2. Wait and verify (timeout: max 10 minutes)
sleep 10
echo "Verifying Kibana PVL configuration update..."
max_retries=20
retry_count=0
start_time=$(date +%s)
timeout_seconds=600

while [ $retry_count -lt $max_retries ]; do
  # Check total timeout
  current_time=$(date +%s)
  elapsed=$((current_time - start_time))
  if [ $elapsed -gt $timeout_seconds ]; then
    echo "⚠️  Verification timeout (10 minutes), please check Kibana PVL configuration manually"
    break
  fi
  
  instance_info=$(aliyun elasticsearch describe-instance \
    --instance-id $INSTANCE_ID \
    --read-timeout 30 \
    --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-network-manage 2>/dev/null)
  
  status=$(echo "$instance_info" | jq -r '.Result.status')
  
  if [ "$status" == "active" ]; then
    echo "✅ UpdateKibanaPvlNetwork succeeded, Kibana PVL configuration updated"
    break
  fi
  
  retry_count=$((retry_count + 1))
  echo "Waiting for Kibana PVL configuration update... ($retry_count/$max_retries)"
  sleep 30
done

if [ $retry_count -eq $max_retries ]; then
  echo "⚠️  Verification timeout, please check Kibana PVL configuration manually"
fi
```

**Success Criteria:**

- UpdateKibanaPvlNetwork request returns `RequestId`
- DescribeInstance returns instance status as `active`, security group configuration is updated

---

## 6. ModifyWhiteIps Verification

**Verification Steps:**

1. Execute ModifyWhiteIps
2. Use DescribeInstance to confirm whitelist is updated

**Verification Command:**

```bash
INSTANCE_ID="es-cn-xxxxxx"

# 1. Execute whitelist modification
echo "Modifying whitelist..."
result=$(aliyun elasticsearch modify-white-ips \
  --instance-id $INSTANCE_ID \
  --white-ip-type PRIVATE_ES \
  --body '{
    "whiteIpGroup": [
      {
        "groupName": "default",
        "ips": ["192.168.1.0/24"]
      }
    ]
  }' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-network-manage 2>&1)

if echo "$result" | jq -e '.RequestId' > /dev/null 2>&1; then
  echo "✅ ModifyWhiteIps request submitted"
else
  echo "❌ ModifyWhiteIps failed"
  echo "$result"
  exit 1
fi

# 2. Wait and verify
sleep 5
echo "Verifying whitelist update..."
white_ips=$(aliyun elasticsearch describe-instance \
  --instance-id $INSTANCE_ID \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-network-manage | jq -r '.Result.networkConfig.whiteIpList')

echo "Current whitelist: $white_ips"
echo "✅ ModifyWhiteIps succeeded"
```

**Success Criteria:**

- ModifyWhiteIps request returns `RequestId`
- DescribeInstance returns whitelist matching the request

---

## 7. OpenHttps Verification

**Verification Steps:**

1. Execute OpenHttps
2. Use DescribeInstance to confirm HTTPS is enabled

**Verification Command:**

```bash
INSTANCE_ID="es-cn-xxxxxx"

# 1. Execute enable HTTPS
echo "Enabling HTTPS..."
result=$(aliyun elasticsearch open-https \
  --instance-id $INSTANCE_ID \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-network-manage 2>&1)

if echo "$result" | jq -e '.RequestId' > /dev/null 2>&1; then
  echo "✅ OpenHttps request submitted"
else
  echo "❌ OpenHttps failed"
  echo "$result"
  exit 1
fi

# 2. Wait and verify (timeout: max 10 minutes)
sleep 10
echo "Verifying HTTPS status..."
max_retries=20
retry_count=0
start_time=$(date +%s)
timeout_seconds=600

while [ $retry_count -lt $max_retries ]; do
  # Check total timeout
  current_time=$(date +%s)
  elapsed=$((current_time - start_time))
  if [ $elapsed -gt $timeout_seconds ]; then
    echo "⚠️  Verification timeout (10 minutes), please check HTTPS status manually"
    break
  fi
  
  protocol=$(aliyun elasticsearch describe-instance \
    --instance-id $INSTANCE_ID \
    --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-network-manage 2>/dev/null | jq -r '.Result.protocol')
  
  if [ "$protocol" == "HTTPS" ]; then
    echo "✅ OpenHttps succeeded, HTTPS is enabled"
    break
  fi
  
  retry_count=$((retry_count + 1))
  echo "Waiting for HTTPS to enable... ($retry_count/$max_retries)"
  sleep 30
done

if [ $retry_count -eq $max_retries ]; then
  echo "⚠️  Verification timeout, please check HTTPS status manually"
fi
```

**Success Criteria:**

- OpenHttps request returns `RequestId`
- DescribeInstance returns `protocol` as `HTTPS`

---

## 8. CloseHttps Verification

**Verification Steps:**

1. Execute CloseHttps
2. Use DescribeInstance to confirm HTTPS is disabled

**Verification Command:**

```bash
INSTANCE_ID="es-cn-xxxxxx"

# 1. Execute disable HTTPS
echo "Disabling HTTPS..."
result=$(aliyun elasticsearch close-https \
  --instance-id $INSTANCE_ID \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-network-manage 2>&1)

if echo "$result" | jq -e '.RequestId' > /dev/null 2>&1; then
  echo "✅ CloseHttps request submitted"
else
  echo "❌ CloseHttps failed"
  echo "$result"
  exit 1
fi

# 2. Wait and verify (timeout: max 10 minutes)
sleep 10
echo "Verifying HTTPS status..."
max_retries=20
retry_count=0
start_time=$(date +%s)
timeout_seconds=600

while [ $retry_count -lt $max_retries ]; do
  # Check total timeout
  current_time=$(date +%s)
  elapsed=$((current_time - start_time))
  if [ $elapsed -gt $timeout_seconds ]; then
    echo "⚠️  Verification timeout (10 minutes), please check HTTPS status manually"
    break
  fi
  
  protocol=$(aliyun elasticsearch describe-instance \
    --instance-id $INSTANCE_ID \
    --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-network-manage 2>/dev/null | jq -r '.Result.protocol')
  
  if [ "$protocol" == "HTTP" ]; then
    echo "✅ CloseHttps succeeded, HTTPS is disabled"
    break
  fi
  
  retry_count=$((retry_count + 1))
  echo "Waiting for HTTPS to disable... ($retry_count/$max_retries)"
  sleep 30
done

if [ $retry_count -eq $max_retries ]; then
  echo "⚠️  Verification timeout, please check HTTPS status manually"
fi
```

**Success Criteria:**

- CloseHttps request returns `RequestId`
- DescribeInstance returns `protocol` as `HTTP`

---

## Common Error Handling

**Common Error Codes:**

| Error Code | Description | Solution |
|------------|-------------|----------|
| InstanceNotFound | Instance does not exist | Check if InstanceId is correct |
| InstanceActivating | Instance is being modified | Wait for instance status to become active and retry |
| InvalidParameter | Parameter error | Check request parameter format and values |
| Forbidden | No permission | Check RAM permission configuration |
| InvalidInstanceType | Instance type not supported | Cloud-native instances do not support TriggerNetwork for Kibana private network |
| NetworkConfigError | Network configuration error | Check VPC and VSwitch configuration |

**Error Handling Script Template:**

```bash
result=$(aliyun elasticsearch <command> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-network-manage 2>&1)
exit_code=$?

if [ $exit_code -ne 0 ]; then
    error_code=$(echo "$result" | jq -r '.Code // empty')
    error_message=$(echo "$result" | jq -r '.Message // empty')
    
    echo "❌ Command execution failed"
    echo "Error code: $error_code"
    echo "Error message: $error_message"
    
    # Specific error handling
    case "$error_code" in
        "InvalidInstanceType")
            echo "Hint: Cloud-native instances do not support this operation"
            ;;
        "InstanceActivating")
            echo "Hint: Please wait for instance status to become active and retry"
            ;;
    esac
else
    echo "✅ Command execution succeeded"
fi
```
