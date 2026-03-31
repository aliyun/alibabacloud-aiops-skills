# Related Commands - Cloud SIEM Incident Management

This document lists all API commands and parameters used by this skill.

> **CRITICAL**: Always use product `cloud-siem`, NOT `sas`.

> **CLI Plugin Required**: Run `aliyun plugin install --names cloud-siem` first.

> **REQUIRED Flags**: All commands MUST include:
> - `--user-agent AlibabaCloud-Agent-Skills`
> - `--read-timeout 120` (use 120 seconds to avoid timeout issues)
> - `--connect-timeout 10`

## Command Reference

| API | Version | CLI Command | Description |
|-----|---------|-------------|-------------|
| ListIncidents | 2024-12-12 | `aliyun cloud-siem list-incidents --api-version 2024-12-12` | Query aggregated security incidents list |
| GetIncident | 2024-12-12 | `aliyun cloud-siem get-incident --api-version 2024-12-12` | Get details of a specific incident |
| DescribeEventCountByThreatLevel | 2022-06-16 | `aliyun cloud-siem DescribeEventCountByThreatLevel` | Query event count trend by threat level |

## API Details

### ListIncidents (v2024-12-12)

Query security incidents with filtering and pagination.

```bash
# Basic query (with required flags)
aliyun cloud-siem list-incidents --api-version 2024-12-12 --region cn-shanghai --page-number 1 --page-size 10 --lang zh --user-agent AlibabaCloud-Agent-Skills --read-timeout 120 --connect-timeout 10

# Filter by threat level and status
aliyun cloud-siem list-incidents --api-version 2024-12-12 --region cn-shanghai --page-number 1 --page-size 10 --threat-level 5,4 --incident-status 0 --lang zh --user-agent AlibabaCloud-Agent-Skills --read-timeout 120 --connect-timeout 10

# Singapore region
aliyun cloud-siem list-incidents --api-version 2024-12-12 --region ap-southeast-1 --page-number 1 --page-size 10 --lang zh --user-agent AlibabaCloud-Agent-Skills --read-timeout 120 --connect-timeout 10
```

**API Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| --region | String | Yes | Service region (cn-shanghai, ap-southeast-1) |
| --page-number | Integer | Yes | Page number (>= 1) |
| --page-size | Integer | Yes | Page size (>= 1) |
| --threat-level | String | No | Comma-separated threat levels (5,4,3,2,1) |
| --incident-status | Integer | No | Incident status (0=unhandled, 10=handled) |
| --lang | String | No | Language ('zh' or 'en') |

---

### GetIncident (v2024-12-12)

Get detailed information of a specific security incident.

```bash
# Get incident details (with required flags)
aliyun cloud-siem get-incident --api-version 2024-12-12 --region cn-shanghai --incident-uuid b6515eb76b73cd4995a902b6df5a766b --lang zh --user-agent AlibabaCloud-Agent-Skills --read-timeout 120 --connect-timeout 10
```

**API Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| IncidentUuid | String | Yes | 32-character hex incident UUID |
| Lang | String | No | Language ('zh' or 'en') |

---

### DescribeEventCountByThreatLevel (v2022-06-16)

Query event count statistics grouped by threat level.

```bash
# Calculate timestamps (milliseconds)
START=$(($(date -v-7d +%s) * 1000))  # macOS
END=$(($(date +%s) * 1000))

# Query 7-day trend (with required flags)
aliyun cloud-siem DescribeEventCountByThreatLevel --RegionId cn-shanghai --StartTime $START --EndTime $END --user-agent AlibabaCloud-Agent-Skills --read-timeout 120 --connect-timeout 10
```

**API Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| RegionId | String | Yes | Region ID (cn-shanghai, ap-southeast-1) |
| StartTime | Long | Yes | Start time in milliseconds |
| EndTime | Long | Yes | End time in milliseconds |

---

## Threat Level Values

| Value | Level | Description |
|-------|-------|-------------|
| 5 | Serious | Critical security threat |
| 4 | High | High-risk threat |
| 3 | Medium | Medium-risk threat |
| 2 | Low | Low-risk threat |
| 1 | Info | Informational event |

## Incident Status Values

| Value | Status | Description |
|-------|--------|-------------|
| 0 | Unhandled | Not processed yet |
| 1 | Processing | Being handled |
| 5 | Failed | Processing failed |
| 10 | Handled | Successfully processed |

## Service Endpoints

| Region | Region ID | Endpoint |
|--------|-----------|----------|
| China (Shanghai) | cn-shanghai | cloud-siem.cn-shanghai.aliyuncs.com |
| Singapore | ap-southeast-1 | cloud-siem.ap-southeast-1.aliyuncs.com |

## References

- [Cloud SIEM API Documentation](https://api.aliyun.com/product/cloud-siem)
- [ListIncidents API](https://api.aliyun.com/api/cloud-siem/2024-12-12/ListIncidents?useCommon=true)
- [GetIncident API](https://api.aliyun.com/api/cloud-siem/2024-12-12/GetIncident?useCommon=true)
- [DescribeEventCountByThreatLevel API](https://api.aliyun.com/api/cloud-siem/2022-06-16/DescribeEventCountByThreatLevel?useCommon=true)
