# Acceptance Criteria: MaxCompute Quota Management

**Scenario**: MaxCompute Quota Management
**Purpose**: Skill testing acceptance criteria

---

## API Coverage and Limitations

| Operation | Testable via CLI/SDK | Notes |
|-----------|---------------------|-------|
| Create Pay-as-you-go Quota | ✅ Yes | Full support |
| Create Subscription Quota | ✅ Yes | **Will incur charges** |
| Query Quota (QueryQuota) | ✅ Yes | Recommended |
| Query Quota (GetQuota) | ⚠️ Yes | Deprecated, use QueryQuota |
| List Quotas | ✅ Yes | Full support |
| Delete Quota | ❌ No | **No API available** |

---

## Correct CLI Command Patterns

### 1. Product Name Verification

✅ **CORRECT** — Use `maxcompute` as product name:
```bash
aliyun maxcompute list-quotas
aliyun maxcompute query-quota --nickname xxx
aliyun maxcompute create-quota --charge-type payasyougo
```

❌ **INCORRECT** — Wrong product names:
```bash
aliyun odps list-quotas           # Wrong: use maxcompute, not odps
aliyun MaxCompute list-quotas     # Wrong: must be lowercase
aliyun mc list-quotas             # Wrong: no abbreviation
```

### 2. Command Name Verification

✅ **CORRECT** — Use kebab-case (plugin mode) for all commands:
```bash
aliyun maxcompute create-quota     # Plugin mode
aliyun maxcompute get-quota       # Deprecated
aliyun maxcompute query-quota     # Recommended
aliyun maxcompute list-quotas
```

❌ **INCORRECT** — Wrong command formats:
```bash
aliyun maxcompute createQuota     # Wrong: camelCase
aliyun maxcompute create_quota    # Wrong: underscore
aliyun maxcompute delete-quota    # Wrong: No such API exists
```

### 3. Parameter Name Verification

✅ **CORRECT** — Use kebab-case for all parameters:
```bash
aliyun maxcompute create-quota \
  --charge-type payasyougo \
  --commodity-code odps \
  --part-nick-name "myQuotaNick"    # Only letters and numbers allowed

aliyun maxcompute list-quotas \
  --billing-type payasyougo \
  --max-item 10

aliyun maxcompute query-quota \      # Recommended
  --nickname "quota-name"

aliyun maxcompute get-quota \        # Deprecated
  --nickname "quota-name"
```

❌ **INCORRECT** — Wrong parameter formats:
```bash
aliyun maxcompute create-quota --chargeType payasyougo    # Wrong: camelCase
aliyun maxcompute create-quota --charge_type payasyougo   # Wrong: underscore
aliyun maxcompute create-quota --ChargeType payasyougo    # Wrong: PascalCase
```

### 4. User-Agent Verification

✅ **CORRECT** — Every command includes user-agent:
```bash
aliyun maxcompute list-quotas --user-agent AlibabaCloud-Agent-Skills
```

❌ **INCORRECT** — Missing user-agent:
```bash
aliyun maxcompute list-quotas    # Wrong: missing --user-agent
```

### 5. Region Parameter Verification

✅ **CORRECT** — Include region when needed:
```bash
aliyun maxcompute list-quotas --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills
aliyun maxcompute query-quota --nickname xxx --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills
```

### 6. Charge Type Values Verification

✅ **CORRECT** — Valid charge type values (for CreateQuota):
```bash
--chargeType payasyougo     # Pay-as-you-go
--chargeType subscription   # Subscription
```

❌ **INCORRECT** — Invalid charge type values:
```bash
--chargeType PayAsYouGo      # Wrong: must be lowercase
--chargeType pay-as-you-go   # Wrong: no hyphens
--chargeType postpaid        # Wrong: not the correct value
--chargeType prepaid         # Wrong: not the correct value
```

### 7. Billing Type Values Verification (for list-quotas)

✅ **CORRECT** — Valid billing type values:
```bash
--billing-type payasyougo    # Filter pay-as-you-go quotas
--billing-type subscription  # Filter subscription quotas
```

### 8. Commodity Code Values Verification

✅ **CORRECT** — Valid commodity codes (for CreateQuota):
```bash
# China site
--commodityCode odps        # Pay-as-you-go
--commodityCode odpsplus    # Subscription

# International site
--commodityCode odps_intl       # Pay-as-you-go
--commodityCode odpsplus_intl   # Subscription
```

❌ **INCORRECT** — Invalid commodity codes:
```bash
--commodityCode maxcompute      # Wrong: not valid
--commodityCode odps-plus       # Wrong: hyphen instead of no separator
--commodityCode ODPS            # Wrong: must be lowercase
```

### 9. Commodity Data Format Verification (for subscription)

✅ **CORRECT** — Valid JSON format (for CreateQuota):
```bash
--commodityData '{"CU":50,"ord_time":"1:Month","autoRenew":false}'
--commodityData '{"CU":100,"ord_time":"1:Year","autoRenew":true}'
```

❌ **INCORRECT** — Invalid formats:
```bash
--commodity-data '{CU:50}'                    # Wrong: missing quotes around keys
--commodity-data '{"cu":50}'                  # Wrong: CU must be uppercase
--commodity-data '{"CU":"50"}'                # Wrong: CU value must be integer
--commodity-data '{"CU":50,ord_time:"1:Month"}'  # Wrong: missing quotes
```

---

## Authentication Patterns

### 1. Credential Verification

✅ **CORRECT** — Check credentials without exposing values:
```bash
aliyun configure list
```

❌ **INCORRECT** — Never expose credentials:
```bash
echo $ALIBABA_CLOUD_ACCESS_KEY_ID        # Wrong: exposes AK
cat ~/.aliyun/config.json                 # Wrong: may expose credentials
aliyun configure set --access-key-id xxx  # Wrong: hardcoded credentials
```

---

## Response Verification Patterns

### 1. Create Quota Success

✅ **CORRECT** — Check for RequestId and NickName:
```json
{
  "RequestId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "Data": {
    "NickName": "quota-nickname"
  }
}
```

### 2. Get Quota Success

✅ **CORRECT** — Response contains quota details:
```json
{
  "RequestId": "xxxxxxxx",
  "NickName": "quota-nickname",
  "Name": "quota-name",
  "Id": "quota-id",
  "Status": "ON"
}
```

### 3. List Quotas Success

✅ **CORRECT** — Response contains QuotaInfoList:
```json
{
  "RequestId": "xxxxxxxx",
  "QuotaInfoList": [...],
  "NextToken": "..."
}
```

---

## Error Handling Patterns

### 1. Check for Common Errors

| Error Code | Meaning | Action |
|------------|---------|--------|
| `QuotaNotFound` | Quota does not exist | Verify nickname |
| `InvalidParameter` | Bad parameter | Check parameter format |
| `Forbidden` | No permission | Attach RAM policy |

---

## Test Scenarios

### Scenario 1: List Quotas (Read-Only)
```bash
# Should succeed with valid credentials
aliyun maxcompute list-quotas \
  --region cn-hangzhou \
  --user-agent AlibabaCloud-Agent-Skills
```

### Scenario 2: Query Non-Existent Quota
```bash
# Should return QuotaNotFound error
aliyun maxcompute query-quota \
  --nickname "non-existent-quota" \
  --region cn-hangzhou \
  --user-agent AlibabaCloud-Agent-Skills
```

### Scenario 3: Create Pay-as-you-go Quota
```bash
# Should succeed and return NickName
aliyun maxcompute create-quota \
  --charge-type payasyougo \
  --commodity-code odps \
  --region cn-hangzhou \
  --user-agent AlibabaCloud-Agent-Skills
```

### Scenario 4: Delete Quota (NOT TESTABLE)

> **⚠️ LIMITATION**: There is no DeleteQuota API.
>
> This scenario cannot be tested via CLI or SDK.
> Delete operations must be performed through the [MaxCompute Console](https://maxcompute.console.aliyun.com/).
