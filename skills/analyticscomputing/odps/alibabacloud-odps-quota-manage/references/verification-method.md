# MaxCompute Quota Management - Verification Method

## Overview

This document provides step-by-step verification methods to confirm successful execution of MaxCompute Quota management operations.

## API Limitations

| Operation | Verifiable | Notes |
|-----------|------------|-------|
| Create Quota | ✅ Yes | Verify via ListQuotas or QueryQuota |
| Query Quota | ✅ Yes | Direct verification |
| List Quotas | ✅ Yes | Direct verification |
| Delete Quota | ❌ No | **No API available** - Must use Console |

---

## 1. Create Pay-as-you-go Quota Verification

### Step 1: Execute Create Command

```bash
aliyun maxcompute CreateQuota \
  --chargeType payasyougo \
  --commodityCode odps \
  --region cn-hangzhou \
  --user-agent AlibabaCloud-Agent-Skills
```

### Step 2: Check Response

**Success Indicators:**
- Response contains `RequestId`
- Response contains `Data.NickName` (the created quota nickname)

**Expected Response Structure:**
```json
{
  "RequestId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "Data": {
    "NickName": "created-quota-nickname"
  }
}
```

### Step 3: Verify via List

```bash
aliyun maxcompute list-quotas \
  --billing-type payasyougo \
  --region cn-hangzhou \
  --user-agent AlibabaCloud-Agent-Skills
```

**Verification:**
- The newly created quota should appear in `QuotaInfoList`
- Check that `NickName` matches the expected value

---

## 2. Create Subscription Quota Verification

### Step 1: Execute Create Command

```bash
aliyun maxcompute CreateQuota \
  --chargeType subscription \
  --commodityCode odpsplus \
  --partNickName "my-test-quota" \
  --commodityData '{"CU":50,"ord_time":"1:Month","autoRenew":false}' \
  --region cn-hangzhou \
  --user-agent AlibabaCloud-Agent-Skills
```

### Step 2: Check Response

**Success Indicators:**
- Response contains `RequestId`
- Response contains `Data.NickName` matching the specified `partNickName`

### Step 3: Verify via List or Query

**Using QueryQuota (Recommended):**
```bash
aliyun maxcompute query-quota \
  --nickname "my-test-quota" \
  --region cn-hangzhou \
  --user-agent AlibabaCloud-Agent-Skills
```

**Or using ListQuotas:**
```bash
aliyun maxcompute list-quotas \
  --billing-type subscription \
  --region cn-hangzhou \
  --user-agent AlibabaCloud-Agent-Skills
```

**Verification:**
- `NickName` matches `my-test-quota`
- `Status` is `ON` or similar active status
- `Id` is populated

---

## 3. Query Quota Verification

> **⚠️ Note**: GetQuota API is deprecated. Always use QueryQuota (`query-quota`) instead.

### Step 1: Execute Query Command

```bash
aliyun maxcompute query-quota \
  --nickname "quota-nickname" \
  --region cn-hangzhou \
  --user-agent AlibabaCloud-Agent-Skills
```

### Step 2: Check Response

**Success Indicators:**
- Response contains `RequestId`
- Response contains quota details: `NickName`, `Name`, `Id`, `Status`

**Expected Response Structure:**
```json
{
  "RequestId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "NickName": "quota-nickname",
  "Name": "quota-system-name",
  "Id": "quota-unique-id",
  "Status": "ON"
}
```

**Failure Indicators:**
- Error message: `QuotaNotFound` - The specified quota does not exist
- Error message: `InvalidParameter` - Invalid nickname format

---

## 4. List Quotas Verification

### Step 1: Execute List Command

```bash
aliyun maxcompute list-quotas \
  --billing-type payasyougo \
  --max-item 10 \
  --region cn-hangzhou \
  --user-agent AlibabaCloud-Agent-Skills
```

### Step 2: Check Response

**Success Indicators:**
- Response contains `RequestId`
- Response contains `QuotaInfoList` (may be empty if no quotas exist)

**Expected Response Structure:**
```json
{
  "RequestId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "NextToken": "pagination-token-or-empty",
  "QuotaInfoList": [
    {
      "NickName": "quota-nickname-1",
      "Name": "quota-name-1",
      "Id": "quota-id-1"
    },
    {
      "NickName": "quota-nickname-2",
      "Name": "quota-name-2",
      "Id": "quota-id-2"
    }
  ]
}
```

### Step 3: Pagination Verification

If `NextToken` is returned, fetch next page:

```bash
aliyun maxcompute list-quotas \
  --billing-type payasyougo \
  --max-item 10 \
  --marker "<NextToken-value>" \
  --region cn-hangzhou \
  --user-agent AlibabaCloud-Agent-Skills
```

---

## 5. Delete Quota Verification

> **⚠️ LIMITATION**: MaxCompute does **NOT** provide a DeleteQuota API.
>
> Quota deletion cannot be verified programmatically because it must be performed through:
> 1. [Alibaba Cloud MaxCompute Console](https://maxcompute.console.aliyun.com/)
> 2. For subscription quotas, cancel the subscription and wait for expiration

### Manual Verification Steps

1. Log in to [MaxCompute Console](https://maxcompute.console.aliyun.com/)
2. Navigate to **Quota Management**
3. Find the quota you want to delete
4. Click **Delete** or **Unsubscribe** (for subscription quotas)
5. Verify deletion by running:

```bash
aliyun maxcompute query-quota \
  --nickname "deleted-quota-nickname" \
  --region cn-hangzhou \
  --user-agent AlibabaCloud-Agent-Skills
```

**Expected Result**: Should return `QuotaNotFound` error if quota was successfully deleted.

---

## Common Error Codes

| Error Code | Description | Resolution |
|------------|-------------|------------|
| `QuotaNotFound` | Specified quota does not exist | Verify quota nickname is correct |
| `InvalidParameter` | Invalid parameter value | Check parameter format and values |
| `Forbidden` | Insufficient permissions | Attach required RAM policy |
| `InternalError` | Server error | Retry after a short delay |
| `ServiceUnavailable` | Service temporarily unavailable | Retry later |

---

## Quick Verification Script

```bash
#!/bin/bash

# Verify credentials
echo "Checking credentials..."
aliyun configure list

# List all quotas
echo "Listing all quotas..."
aliyun maxcompute list-quotas \
  --region cn-hangzhou \
  --user-agent AlibabaCloud-Agent-Skills

# Query specific quota (using recommended QueryQuota)
echo "Querying specific quota..."
aliyun maxcompute query-quota \
  --nickname "your-quota-nickname" \
  --region cn-hangzhou \
  --user-agent AlibabaCloud-Agent-Skills

echo "Verification complete!"
echo ""
echo "NOTE: Delete quota verification cannot be automated."
echo "      Use MaxCompute Console: https://maxcompute.console.aliyun.com/"
```
