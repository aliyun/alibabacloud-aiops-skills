# Acceptance Criteria: alibabacloud-sas-incident-manage

**Scenario**: Cloud Security Center incident query, trend analysis, and detail retrieval
**Purpose**: Skill testing acceptance criteria

> **CRITICAL**: Use `cloud-siem` product, NOT `sas` (different API!)

> **FORBIDDEN BEHAVIORS** (will cause evaluation failure):
> - ❌ Creating mock/fake API responses when real calls fail
> - ❌ Using `aliyun sas` commands (wrong product)
> - ❌ Generating synthetic incident data
> - ❌ Reporting success without actual API responses

> **REQUIRED Flags**: All commands MUST include:
> - `--user-agent AlibabaCloud-Agent-Skills`
> - `--read-timeout 60`
> - `--connect-timeout 10`

---

## Correct CLI Command Patterns

### 1. list-incidents (API: ListIncidents, Version: 2024-12-12)

#### ✅ CORRECT
```bash
# Basic query
aliyun cloud-siem list-incidents --api-version 2024-12-12 --region cn-shanghai --page-number 1 --page-size 10 --lang zh --user-agent AlibabaCloud-Agent-Skills --read-timeout 60 --connect-timeout 10

# Filter by threat level
aliyun cloud-siem list-incidents --api-version 2024-12-12 --region cn-shanghai --page-number 1 --page-size 10 --threat-level 5,4 --lang zh --user-agent AlibabaCloud-Agent-Skills --read-timeout 60 --connect-timeout 10

# Singapore region
aliyun cloud-siem list-incidents --api-version 2024-12-12 --region ap-southeast-1 --page-number 1 --page-size 10 --lang zh --user-agent AlibabaCloud-Agent-Skills --read-timeout 60 --connect-timeout 10
```

#### ❌ INCORRECT
```bash
# Wrong: Missing --page-number (required!)
aliyun cloud-siem list-incidents --api-version 2024-12-12 --region cn-shanghai --lang zh

# Wrong: Missing --api-version (defaults to 2022-06-16!)
aliyun cloud-siem list-incidents --region cn-shanghai --page-number 1 --lang zh

# Wrong: Using wrong API (DescribeCloudSiemEvents is different API)
aliyun cloud-siem DescribeCloudSiemEvents --CurrentPage 1

# Wrong: Using wrong product
aliyun sas DescribeSecurityEvents --RegionId cn-hangzhou
```

---

### 2. get-incident (API: GetIncident, Version: 2024-12-12)

#### ✅ CORRECT
```bash
# Get incident by UUID (32-char hex string)
aliyun cloud-siem get-incident --api-version 2024-12-12 --region cn-shanghai --incident-uuid b6515eb76b73cd4995a902b6df5a766b --lang zh --user-agent AlibabaCloud-Agent-Skills --read-timeout 60 --connect-timeout 10
```

**UUID Format**: 32-character hexadecimal string (no dashes)

#### ❌ INCORRECT
```bash
# Wrong: UUID with dashes
aliyun cloud-siem get-incident --api-version 2024-12-12 --region cn-shanghai --incident-uuid b6515eb7-6b73-cd49-95a9-02b6df5a766b --lang zh

# Wrong: Missing --api-version
aliyun cloud-siem get-incident --region cn-shanghai --incident-uuid xxx --lang zh
```

---

### 3. DescribeEventCountByThreatLevel (Version: 2022-06-16)

#### ✅ CORRECT
```bash
# Calculate timestamps
START=$(($(date -v-7d +%s) * 1000))  # macOS
END=$(($(date +%s) * 1000))

# 7-day trend
aliyun cloud-siem DescribeEventCountByThreatLevel --RegionId cn-shanghai --StartTime $START --EndTime $END --user-agent AlibabaCloud-Agent-Skills --read-timeout 60 --connect-timeout 10
```

#### ❌ INCORRECT
```bash
# Wrong: Using old SAS CLI (wrong product!)
aliyun sas describe-event-count-by-threat-level --RegionId cn-shanghai

# Wrong: Lowercase parameter names
aliyun cloud-siem DescribeEventCountByThreatLevel --regionId cn-shanghai --startTime $START --endTime $END
```

---

## Response Validation

### list-incidents Response

```json
{
  "RequestId": "xxx-xxx-xxx",
  "TotalCount": 6,
  "PageNumber": 1,
  "PageSize": 10,
  "Incidents": [
    {
      "IncidentUuid": "b6515eb76b73cd4995a902b6df5a766b",
      "IncidentName": "Trojan Program",
      "ThreatLevel": "4",
      "IncidentStatus": 0,
      "CreateTime": 1774337032000
    }
  ]
}
```

### get-incident Response

```json
{
  "RequestId": "xxx-xxx-xxx",
  "Incident": {
    "IncidentUuid": "b6515eb76b73cd4995a902b6df5a766b",
    "IncidentName": "Trojan Program",
    "ThreatLevel": "4",
    "IncidentStatus": 0
  }
}
```

### DescribeEventCountByThreatLevel Response

```json
{
  "RequestId": "xxx-xxx-xxx",
  "Code": 200,
  "Data": {
    "EventNum": 6,
    "UndealEventNum": 6,
    "HighLevelEventNum": 5
  }
}
```

---

## Acceptance Checklist

- [ ] cloud-siem CLI plugin installed (`aliyun plugin install --names cloud-siem`)
- [ ] Credentials configured (`aliyun configure list` shows valid profile)
- [ ] `list-incidents` returns valid JSON with `RequestId` and `Incidents`
- [ ] Pagination parameters work (`--page-number`, `--page-size`)
- [ ] Filter parameters work (`--threat-level`, `--incident-status`)
- [ ] `get-incident` returns valid JSON with `Incident` object
- [ ] `DescribeEventCountByThreatLevel` returns valid JSON with `Data` object
- [ ] Multi-region support works (`cn-shanghai`, `ap-southeast-1`)

> **For parameter values (threat levels, status, regions)**, see [related-commands.md](related-commands.md).

## References

- [SKILL.md](../SKILL.md) - Main skill documentation
- [ram-policies.md](ram-policies.md) - RAM permission policy
- [verification-method.md](verification-method.md) - Verification methods
- [related-commands.md](related-commands.md) - Command and parameter reference
