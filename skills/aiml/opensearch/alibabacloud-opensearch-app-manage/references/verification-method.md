# Verification Method

Success verification methods for OpenSearch instance management operations.

> **Terminology**: OpenSearch instance and OpenSearch app group are synonymous.

## Scenario Verification

### Verify Instance Creation Success

**Expected Result**: OpenSearch instance created successfully, `instanceId` field is non-empty

**Verification Flow**: First call `create-app-group` to create instance, then call `describe-app-group` to check status

**Verification Command**:

```bash
aliyun opensearch describe-app-group \
  --app-group-identity <instance_name> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-opensearch-app-manage
```

**Success Criteria**:
- Response status code is 200
- Response contains `result` object
- `result.instanceId` field is non-empty (key indicator of successful creation)

**Example Response (Success)**:

```json
{
  "requestId": "xxx-xxx-xxx",
  "result": {
    "name": "my_search_instance",
    "instanceId": "ops-cn-xxxxx",
    "status": "normal",
    "produced": 1,
    "type": "enhanced",
    "chargeType": "POSTPAY",
    "lockMode": "Unlock",
    "domain": "ecommerce"
  }
}
```

**Key Fields**:
| Field | Description |
|-------|-------------|
| `instanceId` | Instance ID, non-empty indicates successful creation |
| `status` | Instance status, `normal` means running |
| `produced` | Production status, `1` means production complete |

**Status Values**:
| Status | Description |
|--------|-------------|
| `producing` | Producing |
| `review_pending` | Review pending |
| `config_pending` | Configuration pending |
| `normal` | Normal (success) |
| `frozen` | Frozen |

---

### Verify Dry-run Mode

**Expected Result**: Validates parameters only, does not actually create instance

**Verification Command**:

```bash
aliyun opensearch create-app-group \
  --dryRun true \
  --body '{
    "name": "test_dry_run",
    "type": "enhanced",
    "chargeType": "POSTPAY",
    "domain": "general",
    "quota": {
      "docSize": 100,
      "computeResource": 2000,
      "spec": "opensearch.private.common"
    }
  }' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-opensearch-app-manage
```

**Success Criteria**:
- Response status code is 200
- Request succeeds but does not create instance
- Instance does not exist in list query

---

### Verify Idempotent Creation (clientToken)

**Expected Result**: Same clientToken multiple requests only creates once

**Verification Steps**:

```bash
# Generate idempotency token
CLIENT_TOKEN=$(uuidgen)

# First creation
aliyun opensearch create-app-group \
  --client-token "$CLIENT_TOKEN" \
  --body '{
    "name": "idempotent_test_instance",
    "type": "enhanced",
    "chargeType": "POSTPAY",
    "domain": "ecommerce",
    "quota": {
      "docSize": 100,
      "computeResource": 2000,
      "spec": "opensearch.private.common"
    }
  }' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-opensearch-app-manage

# Second request with same token (using same CLIENT_TOKEN)
aliyun opensearch create-app-group \
  --client-token "$CLIENT_TOKEN" \
  --body '{
    "name": "idempotent_test_instance",
    "type": "enhanced",
    "chargeType": "POSTPAY",
    "domain": "ecommerce",
    "quota": {
      "docSize": 100,
      "computeResource": 2000,
      "spec": "opensearch.private.common"
    }
  }' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-opensearch-app-manage
```

**Success Criteria**:
- Both requests return 200
- Only one instance created (verify with describe-app-group)

---

### Verify List Instances Success

**Expected Result**: Successfully returns instance list

**Verification Command**:

```bash
aliyun opensearch list-app-groups \
  --engine-type ha3 \
  --page-number 1 \
  --page-size 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-opensearch-app-manage
```

**Success Criteria**:
- Response status code is 200
- Response contains `result` array
- `totalCount` field shows correct instance count

---

### Verify Describe Instance Success

**Expected Result**: Successfully returns instance details

**Verification Command**:

```bash
aliyun opensearch describe-app-group \
  --app-group-identity <instance_name> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-opensearch-app-manage
```

**Success Criteria**:
- Response status code is 200
- Response contains `result` object
- `result` contains instance details (id, name, type, status, quota, etc.)

**Example Response (Success)**:

```json
{
  "requestId": "0A6EB64B-B4C8-CF02-810F-E660812972FF",
  "result": {
    "id": "110116134",
    "name": "my_search_instance",
    "instanceId": "ops-cn-xxxxx",
    "type": "enhanced",
    "status": "normal",
    "chargeType": "POSTPAY",
    "domain": "ecommerce",
    "quota": {
      "docSize": 100,
      "computeResource": 2000,
      "spec": "opensearch.private.common"
    },
    "lockMode": "Unlock",
    "produced": 1
  }
}
```

---

## Complete Workflow Verification

### Full Test Script

```bash
#!/bin/bash

APP_NAME="test_instance_$(date +%s)"

# Generate idempotency token
CLIENT_TOKEN=$(uuidgen)

echo "=== 1. Create Instance ==="
aliyun opensearch create-app-group \
  --client-token "$CLIENT_TOKEN" \
  --body "{
    \"name\": \"$APP_NAME\",
    \"type\": \"enhanced\",
    \"chargeType\": \"POSTPAY\",
    \"domain\": \"general\",
    \"quota\": {
      \"docSize\": 100,
      \"computeResource\": 2000,
      \"spec\": \"opensearch.private.common\"
    }
  }" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-opensearch-app-manage

echo ""
echo "=== 2. Wait for Instance Production ==="
sleep 30

echo ""
echo "=== 3. Describe Instance (Verify Creation) ==="
aliyun opensearch describe-app-group \
  --app-group-identity $APP_NAME \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-opensearch-app-manage

echo ""
echo "=== 4. List Instances ==="
aliyun opensearch list-app-groups \
  --engine-type ha3 \
  --page-number 1 \
  --page-size 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-opensearch-app-manage

echo ""
echo "=== Test Complete ==="
echo "Note: To delete test instance, please use OpenSearch Console"
```

---

## Troubleshooting

### Common Errors and Solutions

| Error Message | Possible Cause | Solution |
|---------------|----------------|----------|
| `InvalidAccessKeyId.NotFound` | Invalid Access Key ID | Check credential configuration |
| `Forbidden.RAM` | Insufficient permissions | Check RAM policy |
| `AppGroupNotExist` | Instance does not exist | Verify instance name |
| `InvalidParameter` | Invalid parameter | Check parameter format and values |
| `QuotaExceed` | Quota exceeded | Contact Alibaba Cloud to increase quota |

### Debug Commands

```bash
# Enable debug mode for detailed request/response
aliyun opensearch list-app-groups --log-level=debug --user-agent AlibabaCloud-Agent-Skills/alibabacloud-opensearch-app-manage
```
