# Related APIs

Complete API list for OpenSearch instance management.

> **Terminology**: OpenSearch instance and OpenSearch app group are synonymous.

## Instance Management APIs

| Product | CLI Command | API Action | HTTP Method | Path | Description |
|---------|-------------|------------|-------------|------|-------------|
| OpenSearch | `aliyun opensearch create-app-group` | CreateAppGroup | POST | /v4/openapi/app-groups | Create OpenSearch instance |
| OpenSearch | `aliyun opensearch list-app-groups` | ListAppGroups | GET | /v4/openapi/app-groups | List instances |
| OpenSearch | `aliyun opensearch describe-app-group` | DescribeAppGroup | GET | /v4/openapi/app-groups/{appGroupIdentity} | Describe instance details |

## API Details

### CreateAppGroup - Create Instance

- **API Version**: 2017-12-25
- **API Style**: ROA
- **HTTP Method**: POST
- **Path**: /v4/openapi/app-groups
- **Operation Type**: write
- **Billing**: paid

**Request Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| name | String | Yes | Instance name |
| type | String | Yes | Instance type: `standard` (High-performance) / `enhanced` (Industry Algorithm) |
| chargeType | String | No | Charge type: `POSTPAY` (default) / `PREPAY` |
| quota | Object | Yes | Quota info |
| quota.spec | String | Yes | Spec type |
| quota.docSize | Integer | Yes | Storage capacity (GB) |
| quota.computeResource | String | Yes | Compute resource (LCU) |
| domain | String | No | Industry type (enhanced only): `general` (default) / `ecommerce` / `esports` / `community` / `education` |
| order | Object | Conditional | Subscription order info (required when chargeType=PREPAY) |
| order.duration | Integer | Conditional | Subscription period quantity |
| order.pricingCycle | String | Conditional | Period unit: Year / Month |
| order.autoRenew | Boolean | No | Auto-renewal, default false |

**Query Parameters** (Idempotency and Dry-run):

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| dryRun | Boolean | No | Dry-run mode, true validates parameters without actual creation |
| clientToken | String | No | Idempotency token, same token multiple requests only creates once |

**CLI Example**:

```bash
# Generate idempotency token
CLIENT_TOKEN=$(uuidgen)

aliyun opensearch create-app-group \
  --client-token "$CLIENT_TOKEN" \
  --body '{
    "name": "my_instance",
    "type": "enhanced",
    "chargeType": "POSTPAY",
    "domain": "ecommerce",
    "quota": {
      "docSize": 100,
      "computeResource": 2000,
      "spec": "opensearch.private.common"
    }
  }' \
  --user-agent AlibabaCloud-Agent-Skills
```

---

### ListAppGroups - List Instances

- **API Version**: 2017-12-25
- **API Style**: ROA
- **HTTP Method**: GET
- **Path**: /v4/openapi/app-groups
- **Operation Type**: read
- **Billing**: free

**Request Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| engineType | String | Yes | Engine type, default `ha3` (must specify) |
| pageNumber | Integer | No | Page number, default 1 |
| pageSize | Integer | No | Page size, default 10 |
| name | String | No | Filter by instance name |
| type | String | No | Filter by type: `standard` (High-performance) / `enhanced` (Industry Algorithm) |
| instanceId | String | No | Filter by instance ID |
| sortBy | Integer | No | Sort field |

**CLI Example**:

```bash
aliyun opensearch list-app-groups \
  --engine-type ha3 \
  --page-number 1 \
  --page-size 10 \
  --user-agent AlibabaCloud-Agent-Skills
```

---

### DescribeAppGroup - Describe Instance

- **API Version**: 2017-12-25
- **API Style**: ROA
- **HTTP Method**: GET
- **Path**: /v4/openapi/app-groups/{appGroupIdentity}
- **Operation Type**: read
- **Billing**: free

**Request Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| appGroupIdentity | String | Yes | Instance name or ID (path parameter) |

**Response Parameters**:

| Field | Type | Description |
|-------|------|-------------|
| requestId | String | Request ID |
| result.id | String | Instance ID |
| result.name | String | Instance name |
| result.type | String | Instance type (standard/enhanced) |
| result.status | String | Instance status |
| result.chargeType | String | Charge type (POSTPAY/PREPAY) |
| result.quota | Object | Quota info |
| result.currentVersion | String | Current version |
| result.lockMode | String | Lock status |

**CLI Example**:

```bash
aliyun opensearch describe-app-group \
  --app-group-identity my_app \
  --user-agent AlibabaCloud-Agent-Skills
```

---

## Response Status Codes

| Status Code | Description |
|-------------|-------------|
| 200 | Request successful |
| 400 | Invalid request parameters |
| 401 | Authentication failed |
| 403 | Permission denied |
| 404 | Resource not found |
| 500 | Internal server error |

## Common Response Structure

```json
{
  "requestId": "xxx-xxx-xxx",
  "result": { ... }
}
```

## Error Response Structure

```json
{
  "code": "ErrorCode",
  "message": "Error message",
  "requestId": "xxx-xxx-xxx",
  "httpCode": 400
}
```

## Reference Documentation

- [CreateAppGroup API Doc](https://api.aliyun.com/document/OpenSearch/2017-12-25/CreateAppGroup)
- [ListAppGroups API Doc](https://api.aliyun.com/document/OpenSearch/2017-12-25/ListAppGroups)
- [DescribeAppGroup API Doc](https://api.aliyun.com/document/OpenSearch/2017-12-25/DescribeAppGroup)
