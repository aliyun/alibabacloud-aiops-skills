# Related Commands — Domain Manage

## CLI Command Standards

| Rule | Correct | Incorrect |
|------|---------|-----------|
| Product code | `domain` | `Domain` |
| Action format | kebab-case: `query-domain-list` | `QueryDomainList` |
| Parameter format | kebab-case: `--domain-name` | `--DomainName` |
| User-Agent | Always `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-domain-manage` | Omitted |
| Region | No `--region-id` (global service) | `--region-id cn-hangzhou` |
| Array params | `.1` `.2` suffix | JSON array |
| API version | `--api-version 2018-01-29` | Omitted or wrong version |

## Domain-specific Notes

| Item | Description |
|------|-------------|
| Region | Domain API is a **global service**, do NOT pass `--region-id` |
| Pagination | List queries use `--page-num` and `--page-size` |
| Array params | Batch domain names use `.1` `.2` suffix indexing |
| JSON parsing | Use jq to parse return values |
| API version | All domain API commands require `--api-version 2018-01-29` |

---

## Domain Query APIs

### query-domain-list

**Description**: Query domain list with pagination support and optional fuzzy search.
**Type**: Synchronous | **Risk**: Read-only

| CLI Command | API Action | Documentation |
|-------------|------------|---------------|
| `aliyun domain query-domain-list` | QueryDomainList | [Doc](https://help.aliyun.com/zh/dws/developer-reference/api-domain-2018-01-29-querydomainlist) |

```bash
aliyun domain query-domain-list \
  --api-version 2018-01-29 \
  --page-num 1 \
  --page-size 20 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-domain-manage
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| --page-num | Integer | Yes | Page number (starting from 1) |
| --page-size | Integer | Yes | Items per page (max 200) |
| --order-by-type | String | No | Sort order: `ASC` or `DESC` |
| --order-key-type | String | No | Sort key: `RegistrationDate` or `ExpirationDate` |
| --group-id | Long | No | Domain group ID filter |
| --domain-name | String | No | Fuzzy domain name filter (partial match) |

**Response**: `Data[].DomainName`, `Data[].InstanceId`, `Data[].ExpirationDate`, `Data[].RegistrationDate`, `Data[].DomainStatus`, `TotalItemNum`, `PageSize`, `CurrentPageNum`, `TotalPageNum`

---

### query-advanced-domain-list

**Description**: Advanced domain list search with multiple filters.
**Type**: Synchronous | **Risk**: Read-only

| CLI Command | API Action | Documentation |
|-------------|------------|---------------|
| `aliyun domain query-advanced-domain-list` | QueryAdvancedDomainList | [Doc](https://help.aliyun.com/zh/dws/developer-reference/api-domain-2018-01-29-queryadvanceddomainlist) |

```bash
aliyun domain query-advanced-domain-list \
  --api-version 2018-01-29 \
  --page-num 1 \
  --page-size 20 \
  --domain-status 1 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-domain-manage
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| --page-num | Integer | Yes | Page number (starting from 1) |
| --page-size | Integer | Yes | Items per page (max 200) |
| --domain-status | Integer | No | Domain status filter (see status codes below) |
| --start-expiration-date | Long | No | Expiration date range start (ms since epoch) |
| --end-expiration-date | Long | No | Expiration date range end (ms since epoch) |
| --start-registration-date | Long | No | Registration date range start (ms since epoch) |
| --end-registration-date | Long | No | Registration date range end (ms since epoch) |
| --domain-name-sort | Boolean | No | Sort by domain name alphabetically |
| --expiration-date-sort | Boolean | No | Sort by expiration date |
| --registration-date-sort | Boolean | No | Sort by registration date |
| --product-domain-type | String | No | Domain type: `gTLD`, `ccTLD`, `New gTLD` |
| --domain-group-id | Long | No | Domain group ID filter |
| --key-word | String | No | Keyword filter for domain name |
| --suffix-name | String | No | Domain suffix filter (e.g., `.com`, `.cn`) |

#### Domain Status Codes

| Code | Status | Description |
|------|--------|-------------|
| 0 | All | All domains (no filter) |
| 1 | Normal | Active and functioning normally |
| 2 | Expired | Past expiration date |
| 3 | Grace Period | In renewal grace period after expiration |
| 4 | Redemption Period | In redemption period (higher cost to recover) |
| 5 | Pending Delete | About to be released/deleted |

#### User Intent Mapping

| User Intent | Parameters |
|-------------|-----------|
| Normal/active domains | `--domain-status 1` |
| Expired domains | `--domain-status 2` |
| Grace period domains | `--domain-status 3` |
| Expiring within N days | `--end-expiration-date <timestamp>` (current time + N days in ms) |
| Filter by domain type | `--product-domain-type gTLD/ccTLD/New gTLD` |
| Filter by suffix | `--suffix-name ".com"` |

---

### query-domain-by-domain-name

**Description**: Query complete domain details by domain name.
**Type**: Synchronous | **Risk**: Read-only

| CLI Command | API Action | Documentation |
|-------------|------------|---------------|
| `aliyun domain query-domain-by-domain-name` | QueryDomainByDomainName | [Doc](https://help.aliyun.com/zh/dws/developer-reference/api-domain-2018-01-29-querydomainbydomainname) |

```bash
aliyun domain query-domain-by-domain-name \
  --api-version 2018-01-29 \
  --domain-name "example.com" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-domain-manage
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| --domain-name | String | Yes | The exact domain name to query |

**Response Key Fields**:

| Field | Type | Description |
|-------|------|-------------|
| DomainName | String | Domain name |
| InstanceId | String | Instance ID |
| RegistrationDate | String | Registration date |
| ExpirationDate | String | Expiration date |
| DomainStatus | String | Domain status |
| DnsList.Dns[] | Array | DNS server list |
| RealNameStatus | String | Real-name verification status |
| RegistrantType | String | Registrant type (individual/enterprise) |
| TransferOutStatus | String | Transfer-out status |
| TransferProhibitionLock | String | Transfer prohibition lock status |
| UpdateProhibitionLock | String | Update prohibition lock status |
| Premium | Boolean | Whether it is a premium domain |
| DomainGroupName | String | Domain group name |
| RegistrantName | String | Registrant name |
| Email | String | Registrant email |

#### Display Format

```
Domain Details:
- Domain Name:       example.com
- Instance ID:       S20241234567890
- Registration Date: 2020-01-01
- Expiration Date:   2025-01-01
- Domain Status:     Normal (1)
- DNS Servers:       ns1.alidns.com, ns2.alidns.com
- Real-name Status:  Verified
- Registrant Type:   Enterprise
- Update Lock:       Enabled
- Transfer Lock:     Enabled
- Transfer-out:      Not in progress
- Premium Domain:    No
- Domain Group:      Default
```

---

### query-domain-by-instance-id

**Description**: Query domain details by instance ID. Returns the same response structure as `query-domain-by-domain-name`.
**Type**: Synchronous | **Risk**: Read-only

| CLI Command | API Action | Documentation |
|-------------|------------|---------------|
| `aliyun domain query-domain-by-instance-id` | QueryDomainByInstanceId | [Doc](https://help.aliyun.com/zh/dws/developer-reference/api-domain-2018-01-29-querydomainbyinstanceid) |

```bash
aliyun domain query-domain-by-instance-id \
  --api-version 2018-01-29 \
  --instance-id "S20241234567890" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-domain-manage
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| --instance-id | String | Yes | The domain instance ID to query |

---

## Information Display Standards

> **[MUST] All information displayed to the user must comply with:**
>
> 1. **No fabricated output**: All displayed information must come from actual API query results
> 2. **Truncation handling**: If API response is truncated, must re-query completely before displaying
> 3. **Count validation**: Displayed count must match `TotalItemNum`/actual count returned by API
> 4. **Pagination handling**: When `TotalItemNum` exceeds `PageSize`, inform the user about remaining pages
> 5. **Date formatting**: Display dates in a user-friendly format (e.g., `2025-01-01`)

---

## Reference Documentation

| Document | Description |
|----------|-------------|
| [QueryDomainList API](https://help.aliyun.com/zh/dws/developer-reference/api-domain-2018-01-29-querydomainlist) | Official API documentation |
| [QueryAdvancedDomainList API](https://help.aliyun.com/zh/dws/developer-reference/api-domain-2018-01-29-queryadvanceddomainlist) | Official API documentation |
| [QueryDomainByDomainName API](https://help.aliyun.com/zh/dws/developer-reference/api-domain-2018-01-29-querydomainbydomainname) | Official API documentation |
| [QueryDomainByInstanceId API](https://help.aliyun.com/zh/dws/developer-reference/api-domain-2018-01-29-querydomainbyinstanceid) | Official API documentation |
| [Aliyun CLI Guide](https://help.aliyun.com/zh/cli/) | Official CLI documentation |
