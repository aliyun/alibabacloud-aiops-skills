# OOS Template Generation — CLI Commands Reference

This document provides a comprehensive reference of all Aliyun CLI commands used in the OOS template generation skill.

---

## CLI Command Standards

> **CRITICAL: All CLI commands MUST follow these standards to avoid parameter errors.**

### General Rules

| Rule | Correct | Incorrect |
|------|---------|-----------|
| **OOS command name** | `list-actions` (plugin mode) | `ListActions` (PascalCase) |
| **Region parameter** | `--biz-region-id cn-hangzhou` | `--RegionId cn-hangzhou` |
| **User agent** | Always include `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-oos-template-generation` | Missing user-agent |

---

## OOS Action Query Commands

### list-actions — Search OOS Actions

Query available OOS Action list with optional name-based fuzzy search.

```bash
# Search ECS-related Actions
aliyun oos list-actions \
  --biz-region-id cn-hangzhou \
  --oos-action-name "ACS::ECS" \
  --max-results 50 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-oos-template-generation

# Search Actions containing "Reboot" in name
aliyun oos list-actions \
  --biz-region-id cn-hangzhou \
  --oos-action-name "Reboot" \
  --max-results 50 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-oos-template-generation

# Search RDS-related Actions
aliyun oos list-actions \
  --biz-region-id cn-hangzhou \
  --oos-action-name "ACS::RDS" \
  --max-results 50 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-oos-template-generation

# List all Actions (no filter)
aliyun oos list-actions \
  --biz-region-id cn-hangzhou \
  --max-results 100 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-oos-template-generation
```

**Parameters**:

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--biz-region-id` | Yes | Region ID, e.g., `cn-hangzhou` |
| `--oos-action-name` | No | Action name filter (fuzzy match) |
| `--max-results` | No | Maximum number of results, default 50, range 10-100 |
| `--next-token` | No | Pagination token from previous response |

**Response Fields**:

| Field | Description |
|-------|-------------|
| `Actions[].OOSActionName` | Action name (e.g., `ACS::ECS::RebootInstance`) |
| `Actions[].Description` | Action description |
| `Actions[].ActionType` | Action type (e.g., `Atomic.API`, `Product.ECS`) |
| `Actions[].Properties` | Action property parameter definitions (JSON string) |
| `NextToken` | Pagination token, empty means no more data |

### list-actions (Exact Query) — Get Action Detailed Property Definitions

After selecting an Action, use the exact name to query complete Properties definitions.

```bash
# Get complete property definitions of ACS::ECS::RebootInstance
aliyun oos list-actions \
  --biz-region-id cn-hangzhou \
  --oos-action-name "ACS::ECS::RebootInstance" \
  --max-results 1 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-oos-template-generation

# Get complete property definitions of ACS::ECS::RunCommand
aliyun oos list-actions \
  --biz-region-id cn-hangzhou \
  --oos-action-name "ACS::ECS::RunCommand" \
  --max-results 1 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-oos-template-generation
```

> **CRITICAL**: `Actions[0].Properties` in the response contains property names and types. Property names in the template must **exactly match** this result (case-sensitive), e.g., `regionId` cannot be written as `RegionId`.

---

## OOS Template Validation Commands

### validate-template-content — Validate Template Syntax and Semantics

**Must** call this command after generating a template.

```bash
# Method 1: Pass via file (recommended)
cat > /tmp/oos_template.yaml << 'EOF'
FormatVersion: OOS-2019-06-01
Description:
  en: 'Reboot an ECS instance'
  zh-cn: 'Reboot ECS instance'
Parameters:
  regionId:
    Type: String
    Description: 'Region ID'
    Default: 'cn-hangzhou'
  instanceId:
    Type: String
    Description: 'Instance ID'
Tasks:
  - Name: rebootInstance
    Action: ACS::ECS::RebootInstance
    Description: 'Reboot ECS instance'
    Properties:
      regionId: '{{ regionId }}'
      instanceId: '{{ instanceId }}'
EOF

aliyun oos validate-template-content \
  --biz-region-id cn-hangzhou \
  --content "$(cat /tmp/oos_template.yaml)" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-oos-template-generation

# Method 2: Pass content directly (for short templates)
aliyun oos validate-template-content \
  --biz-region-id cn-hangzhou \
  --content '{"FormatVersion":"OOS-2019-06-01","Description":{"en":"test","zh-cn":"test"},"Tasks":[{"Name":"test","Action":"ACS::Sleep","Properties":{"Duration":"PT1S"}}]}' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-oos-template-generation
```

**Parameters**:

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--biz-region-id` | Yes | Region ID |
| `--content` | Yes | Template content (YAML or JSON string) |

**Response**:
- **Validation passed**: Returns `RequestId` with no error message
- **Validation failed**: Returns error with `Code` and `Message`, fix the template and re-validate

---

## Cloud Product OpenAPI Query (via OpenMeta API)

When using `ACS::ExecuteAPI` to call cloud product APIs, query available APIs and their parameter definitions via the Alibaba Cloud OpenMeta API.

**Base URL**: `https://api.aliyun.com/meta/v1`

### URL Patterns

| Purpose | URL |
|---------|-----|
| Product list | `https://api.aliyun.com/meta/v1/products.json` |
| API overview | `https://api.aliyun.com/meta/v1/products/{Product}/versions/{Version}/overview.json` |
| API detail | `https://api.aliyun.com/meta/v1/products/{Product}/versions/{Version}/apis/{ApiName}/api.json` |
| All API docs | `https://api.aliyun.com/meta/v1/products/{Product}/versions/{Version}/api-docs.json` |

### Common Product Codes and Versions

| Product | Code | Version |
|---------|------|---------|
| ECS | `Ecs` | `2014-05-26` |
| RDS | `Rds` | `2014-08-15` |
| VPC | `Vpc` | `2016-04-28` |
| SLB | `Slb` | `2014-05-15` |
| OOS | `oos` | `2019-06-01` |

### Examples

```bash
# Find product code and version
curl -s --connect-timeout 10 --max-time 30 \
  'https://api.aliyun.com/meta/v1/products.json' | jq '.[] | select(.code=="Ecs")'

# Get API overview (list all available APIs grouped by category)
curl -s --connect-timeout 10 --max-time 30 \
  'https://api.aliyun.com/meta/v1/products/Ecs/versions/2014-05-26/overview.json' | jq '.directories'

# Get detailed API metadata including all parameters
curl -s --connect-timeout 10 --max-time 30 \
  'https://api.aliyun.com/meta/v1/products/Ecs/versions/2014-05-26/apis/DescribeInstances/api.json' | jq '.parameters'

# Get only required parameters for an API
curl -s --connect-timeout 10 --max-time 30 \
  'https://api.aliyun.com/meta/v1/products/Ecs/versions/2014-05-26/apis/DescribeInstances/api.json' \
  | jq '.parameters[] | select(.schema.required==true) | {name, type: .schema.type}'
```

### API Detail Response Key Fields

- `parameters[].name`: Parameter name
- `parameters[].in`: Parameter location (query, body, etc.)
- `parameters[].schema.type`: Parameter type
- `parameters[].schema.required`: Whether required
- `parameters[].schema.description`: Parameter description
- `parameters[].schema.example`: Example value

---

## OOS Template Management Commands

### Template Management

| Operation | CLI Command | Description |
|-----------|------------|-------------|
| Create template | `aliyun oos create-template --template-name <name> --content '<yaml>'` | Create a new OOS template |
| Get template | `aliyun oos get-template --template-name <name>` | View template details |
| Update template | `aliyun oos update-template --template-name <name> --content '<yaml>'` | Update an existing template |
| Delete template | `aliyun oos delete-template --template-name <name>` | Delete a template |
| List templates | `aliyun oos list-templates --max-results 10` | Query template list |

### Execution Management

| Operation | CLI Command | Description |
|-----------|------------|-------------|
| Start execution | `aliyun oos start-execution --template-name <name> --parameters '{"key":"value"}'` | Start template execution |
| Get execution | `aliyun oos get-execution --execution-id <id>` | View execution details |
| List executions | `aliyun oos list-executions --max-results 10` | Query execution list |
| Cancel execution | `aliyun oos cancel-execution --execution-id <id>` | Cancel a running task |

---

## Common Patterns

### Paginated Action Query

When Action count exceeds max-results, use next-token for pagination:

```bash
# First page
aliyun oos list-actions \
  --biz-region-id cn-hangzhou \
  --oos-action-name "ACS::ECS" \
  --max-results 50 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-oos-template-generation

# Subsequent pages (use NextToken from previous response)
aliyun oos list-actions \
  --biz-region-id cn-hangzhou \
  --oos-action-name "ACS::ECS" \
  --max-results 50 \
  --next-token "<NextToken value from previous response>" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-oos-template-generation
```

### Extract Specific Fields (using jq)

```bash
# Extract Action names only
aliyun oos list-actions \
  --biz-region-id cn-hangzhou \
  --oos-action-name "ACS::ECS" \
  --max-results 50 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-oos-template-generation \
  | jq '.Actions[].OOSActionName'

# Extract Properties of a specific Action
aliyun oos list-actions \
  --biz-region-id cn-hangzhou \
  --oos-action-name "ACS::ECS::RebootInstance" \
  --max-results 1 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-oos-template-generation \
  | jq '.Actions[0].Properties'
```

---

## Reference Links

- [OOS API Reference](https://help.aliyun.com/zh/oos/developer-reference/api-overview)
- [OOS Template Syntax](https://help.aliyun.com/zh/oos/user-guide/template-syntax)
- [Aliyun CLI Documentation](https://help.aliyun.com/zh/cli/)
