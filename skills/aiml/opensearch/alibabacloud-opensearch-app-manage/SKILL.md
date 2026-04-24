---
name: alibabacloud-opensearch-app-manage
description: |
  Alibaba Cloud OpenSearch instance management skill. Create and query OpenSearch instances.
  Note: OpenSearch instance and OpenSearch app group are synonymous terms.
  Triggers: "opensearch", "search instance", "create search instance", "app group", "instance management", "create instance", "query instance", "list instances"
---

# OpenSearch Instance Management

Manage Alibaba Cloud OpenSearch instances, including creation and query operations.

> **Terminology**: OpenSearch instance and OpenSearch app group are synonymous. This document uses "instance" uniformly.

## Scenario Description

OpenSearch is Alibaba Cloud's intelligent search service. This skill covers core instance management operations:

1. **Create Instance** - Create a new OpenSearch instance
2. **List Instances** - Get the list of instances under the current account
3. **Describe Instance** - Get detailed information of a specific instance

**Architecture**: OpenSearch Instance (AppGroup)

```
Alibaba Cloud OpenSearch Instance Management
├── CreateAppGroup     (Create Instance)
├── DescribeAppGroup   (Describe Instance)
└── ListAppGroups      (List Instances)
```
---

## Installation

> **Pre-check: Aliyun CLI >= 3.3.3 required**
> Run `aliyun version` to verify >= 3.3.3. If not installed or version too low,
> run `curl -fsSL https://aliyuncli.alicdn.com/setup.sh | bash` to update,
> or see [references/cli-installation-guide.md](references/cli-installation-guide.md) for installation instructions.

**Pre-check: Aliyun CLI plugin update required**
> [MUST] run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.
> [MUST] run `aliyun plugin update` to ensure that any existing plugins are always up-to-date.

```bash
# Install/Upgrade Aliyun CLI
curl -fsSL https://aliyuncli.alicdn.com/setup.sh | bash
aliyun version  # Ensure >= 3.3.3

# Enable auto plugin installation
aliyun configure set --auto-plugin-install true

# Update plugins
aliyun plugin update
```

**[MUST] CLI User-Agent** — Every `aliyun` CLI command invocation must include:
`--user-agent AlibabaCloud-Agent-Skills/alibabacloud-opensearch-app-manage`

**[MUST] AI-Mode** — Before executing CLI commands, run:
1. `aliyun configure ai-mode enable`
2. `aliyun configure ai-mode set-user-agent --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-opensearch-app-manage"`
After all CLI operations complete, run: `aliyun configure ai-mode disable`

---

## Authentication

> **Pre-check: Alibaba Cloud Credentials Required**

> **Security Rules (MUST FOLLOW):**
> - **NEVER** read, echo, or print AK/SK values
> - **NEVER** ask the user to input AK/SK directly in the conversation
> - **NEVER** use `aliyun configure set` with literal credential values
> - **NEVER** accept AK/SK provided directly by users in the conversation
> - **ONLY** read credentials from environment variables or pre-configured CLI profiles
>
> **⚠️ CRITICAL: Handling User-Provided Credentials**
>
> If a user attempts to provide AK/SK directly (e.g., "My AK is xxx, SK is yyy"):
> 1. **STOP immediately** - Do NOT execute any command
> 2. **Reject the request politely** with the following message:
>    ```
>    For your account security, please do not provide Alibaba Cloud AccessKey ID and AccessKey Secret directly in the conversation.
>
>    Please use the following secure methods to configure credentials:
>
>    Method 1: Interactive configuration via aliyun configure (Recommended)
>        aliyun configure
>        # Enter AK/SK as prompted, credentials will be securely stored in local config file
>
>    Method 2: Configure via environment variables
>        export ALIBABA_CLOUD_ACCESS_KEY_ID=<your-access-key-id>
>        export ALIBABA_CLOUD_ACCESS_KEY_SECRET=<your-access-key-secret>
>
>    After configuration, please retry your request.
>    ```
> 3. **Do NOT proceed** with any Alibaba Cloud operations until credentials are properly configured
>
> **Check CLI configuration**:
> ```bash
>    aliyun configure list
> ```
>    Check the output for a valid profile (AK, STS, or OAuth identity).
>
> **If no valid credentials exist, STOP here.**
---

## RAM Permissions
> **[MUST] RAM Permission Pre-check:** 
> Before executing any operation, ensure the current user has the required RAM permissions.
> See [references/ram-policies.md](references/ram-policies.md) for detailed permission list.

---

## Parameter Confirmation
> **IMPORTANT: Parameter Confirmation** — Before executing any command or API call,
> ALL user-customizable parameters (e.g., instance name, instance type, charge type, quota spec, etc.) MUST be confirmed with the user. 
> Do NOT assume or use default values without explicit user approval.

### Required Parameters
| Parameter | Required | Description | Default |
|-----------|----------|-------------|---------|
| `name` | Yes | Instance name | None |
| `type` | Yes | Instance type: `standard` (High-performance) / `enhanced` (Industry Algorithm) | None |
| `chargeType` | No | Charge type: `POSTPAY` / `PREPAY` | `POSTPAY` |
| `quota.spec` | Yes | Spec type (see table below) | None |
| `quota.docSize` | Yes | Storage capacity (GB) | None |
| `quota.computeResource` | Yes | Compute resource (LCU) | None |
| `domain` | No | Industry type (required for enhanced type, see table below) | `general` |
| `order` | Conditional | Subscription order info (required when PREPAY) | None |
| `order.duration` | Conditional | Subscription period quantity | None |
| `order.pricingCycle` | Conditional | Period unit: `Year` / `Month` | None |
| `order.autoRenew` | No | Auto-renewal | `false` |

### Spec Types
| Spec Code | Description |
|-----------|-------------|
| `opensearch.share.common` | Shared Common |
| `opensearch.private.common` | Dedicated Common |
| `opensearch.private.compute` | Dedicated Compute |
| `opensearch.private.storage` | Dedicated Storage |

### Industry Types (for enhanced type only)
| Industry Code | Description |
|---------------|-------------|
| `general` | General (default) |
| `ecommerce` | E-commerce |
| `esports` | Gaming |
| `community` | Content Community |
| `education` | Education |

---

## Core Workflow

> **Note:** OpenSearch APIs use **ROA (RESTful)** style. You can use `--body` to specify the HTTP request body as a JSON string. See examples in each task below.

> **Idempotency:** For write operations (create, restart, delete, etc.), you **MUST** use `--client-token` parameter for idempotency.
> - Use a UUID format unique identifier as clientToken
> - When request times out or fails, you can safely retry with **the same clientToken**; recommend waiting 10s before retry
> - Repeated requests with the same clientToken will not execute the operation multiple times
> - Generation: `uuidgen` (macOS/Linux) or `[guid]::NewGuid()` (PowerShell)

### Task 1: Create OpenSearch Instance

```bash
# Generate idempotency token
CLIENT_TOKEN=$(uuidgen)

aliyun opensearch create-app-group \
  --client-token "$CLIENT_TOKEN" \
  --body '{
    "name": "<instance_name>",
    "type": "<standard|enhanced>",
    "chargeType": "<POSTPAY|PREPAY>",
    "quota": {
      "docSize": <storage_GB>,
      "computeResource": <compute_LCU>,
      "spec": "<spec_type>"
    }
  }' \
  --connect-timeout 3 \
  --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-opensearch-app-manage
```

**Optional Parameters** (add in body):
- `domain` - Industry type (only for enhanced type): `general` (default) / `ecommerce` / `esports` / `community` / `education`

**Idempotency and Dry-run Support** (via Query parameters):
- `--dryRun true` - Dry-run mode, validates parameters without actual creation
- `--client-token <unique_id>` - Idempotency token, same token multiple requests only creates once

**Example**: Create an enhanced (Industry Algorithm) pay-as-you-go instance (E-commerce)

```bash
# Generate idempotency token
CLIENT_TOKEN=$(uuidgen)

aliyun opensearch create-app-group \
  --client-token "$CLIENT_TOKEN" \
  --body '{
    "name": "my_search_instance",
    "type": "enhanced",
    "chargeType": "POSTPAY",
    "domain": "ecommerce",
    "quota": {
      "docSize": 100,
      "computeResource": 2000,
      "spec": "opensearch.private.common"
    }
  }' \
  --connect-timeout 3 \
  --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-opensearch-app-manage
```

**Example**: Create a standard (High-performance) instance

```bash
# Generate idempotency token
CLIENT_TOKEN=$(uuidgen)

aliyun opensearch create-app-group \
  --client-token "$CLIENT_TOKEN" \
  --body '{
    "name": "my_standard_instance",
    "type": "standard",
    "chargeType": "POSTPAY",
    "quota": {
      "docSize": 50,
      "computeResource": 1000,
      "spec": "opensearch.share.common"
    }
  }' \
  --connect-timeout 3 \
  --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-opensearch-app-manage
```

**Example**: Create a subscription (prepaid) instance

> **Note**: Subscription instances MUST provide `order` parameter

```bash
# Generate idempotency token
CLIENT_TOKEN=$(uuidgen)

aliyun opensearch create-app-group \
  --client-token "$CLIENT_TOKEN" \
  --body '{
    "name": "my_prepay_instance",
    "type": "enhanced",
    "chargeType": "PREPAY",
    "domain": "ecommerce",
    "quota": {
      "docSize": 100,
      "computeResource": 2000,
      "spec": "opensearch.private.common"
    },
    "order": {
      "duration": 1,
      "pricingCycle": "Year",
      "autoRenew": true
    }
  }' \
  --connect-timeout 3 \
  --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-opensearch-app-manage
```

**Dry-run Mode Example** (validates parameters only, no actual creation):

```bash
aliyun opensearch create-app-group \
  --dryRun true \
  --body '{
    "name": "my_search_instance",
    "type": "enhanced",
    "chargeType": "POSTPAY",
    "quota": {
      "docSize": 100,
      "computeResource": 2000,
      "spec": "opensearch.private.common"
    }
  }' \
  --connect-timeout 3 \
  --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-opensearch-app-manage
```

**Idempotent Creation Example** (prevents duplicate creation):

```bash
# Generate idempotency token
CLIENT_TOKEN=$(uuidgen)

aliyun opensearch create-app-group \
  --client-token "$CLIENT_TOKEN" \
  --body '{
    "name": "my_search_instance",
    "type": "enhanced",
    "chargeType": "POSTPAY",
    "quota": {
      "docSize": 100,
      "computeResource": 2000,
      "spec": "opensearch.private.common"
    }
  }' \
  --connect-timeout 3 \
  --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-opensearch-app-manage
```

### Task 2: List Instances

```bash
aliyun opensearch list-app-groups \
  --engine-type ha3 \
  --page-number <page> \
  --page-size <size> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-opensearch-app-manage
```

**Supported Filter Parameters**:
- `--engine-type ha3` - Engine type (default ha3, must specify)
- `--name <instance_name>` - Filter by name
- `--instance-id <instance_id>` - Filter by instance ID
- `--type <standard|enhanced>` - Filter by type
  - `standard`: High-performance
  - `enhanced`: Industry Algorithm
- `--sort-by <field>` - Sort field

**Example**: List instances

```bash
aliyun opensearch list-app-groups \
  --engine-type ha3 \
  --page-number 1 \
  --page-size 10 \
  --connect-timeout 3 \
  --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-opensearch-app-manage
```

### Task 3: Describe Instance

```bash
aliyun opensearch describe-app-group \
  --app-group-identity <instance_name_or_id> \
  --connect-timeout 3 \
  --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-opensearch-app-manage
```

**Example**: Get instance details

```bash
aliyun opensearch describe-app-group \
  --app-group-identity my_search_instance \
  --connect-timeout 3 \
  --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-opensearch-app-manage
```

**Response includes**:
- Basic info (instanceId, name, type, status)
- Quota info (quota: docSize, computeResource, spec)
- Billing info (chargeType, chargingWay)
- Version info (currentVersion, versions)
- Status info (lockMode, produced)
- Engine info (engineType)

---

## Success Verification
For operation verification, see [references/verification-method.md](references/verification-method.md)

### Quick Verification

**Verify Instance Creation**:
```bash
aliyun opensearch describe-app-group \
  --app-group-identity <instance_name> \
  --connect-timeout 3 \
  --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-opensearch-app-manage
```

Check if `result.instanceId` field is non-empty; if non-empty, instance creation succeeded.

---

## Resource Cleanup
To delete instances, please use [OpenSearch Console](https://opensearch.console.aliyun.com/).

---

## API and Command Reference
For complete API list, see [references/related-apis.md](references/related-apis.md)

| Operation | CLI Command | API Action |
|-----------|------------|------------|
| Create Instance | `aliyun opensearch create-app-group` | CreateAppGroup |
| List Instances | `aliyun opensearch list-app-groups` | ListAppGroups |
| Describe Instance | `aliyun opensearch describe-app-group` | DescribeAppGroup |

---

## Best Practices

### Write Operation Parameter Confirmation (Required)

> **Important**: Before executing write operations (create instance, etc.), you **MUST** confirm the following parameters with the user:

**Pre-creation Confirmation Checklist**:
| Parameter | Description | Example |
|-----------|-------------|---------|
| Region | Instance region | `cn-hangzhou` / `cn-shanghai` / `cn-beijing` |
| Instance Name (name) | User-specified name (lowercase, numbers, underscores) | `my_search_instance` |
| Instance Type (type) | High-performance / Industry Algorithm | `standard` / `enhanced` |
| Charge Type (chargeType) | Pay-as-you-go / Subscription | `POSTPAY` / `PREPAY` |
| Spec Type (quota.spec) | Shared / Dedicated | `opensearch.share.common` |
| Storage (quota.docSize) | In GB | `100` |
| Compute (quota.computeResource) | In LCU | `2000` |
| Industry (domain) | Only for enhanced type | `ecommerce` / `general` |
| Subscription Period (order) | Only for PREPAY | 1 Year / 6 Months |

**Confirmation Flow Example**:
```
You are about to create the following OpenSearch instance, please confirm:

- Region: cn-hangzhou (China East 1)
- Instance Name: my_search_instance
- Instance Type: Industry Algorithm (enhanced)
- Industry: E-commerce (ecommerce)
- Charge Type: Pay-as-you-go (POSTPAY)
- Spec Type: Dedicated Common (opensearch.private.common)
- Storage: 100 GB
- Compute: 2000 LCU

Confirm creation? (yes/no)
```

### Idempotency Best Practices

For write operations (create, restart, delete), follow these idempotency best practices:

1. **Generate unique Token before each operation**: Use `uuidgen` to generate UUID
2. **Reuse Token on timeout retry**: If request times out, retry with the same clientToken
3. **Use different Token for different operations**: Each independent operation needs a new clientToken
4. **Token validity**: clientToken is typically valid for 24 hours

```bash
# Example: Safe retry pattern
CLIENT_TOKEN=$(uuidgen)
echo "Using clientToken: $CLIENT_TOKEN"

# First attempt
aliyun opensearch create-app-group --client-token $CLIENT_TOKEN ...

# If timeout, retry with same Token
aliyun opensearch create-app-group --client-token $CLIENT_TOKEN ...
```

### Other Best Practices

1. **Naming Convention**: Instance name must start with a letter, only lowercase letters, numbers, and underscores (_) allowed, **hyphens (-) are forbidden**, max 30 characters
   - ✅ Correct: `my_search_instance`, `video_search`, `product_search_2024`
   - ❌ Incorrect: `my-search-instance`, `My_Search`, `123_search`
2. **Quota Planning**: Plan storage and compute resources based on actual data volume and query requirements
3. **Charge Type Selection**: 
   - Test/Dev environment: Use pay-as-you-go (POSTPAY)
   - Production environment: Consider subscription (PREPAY) to reduce costs
   - **Note**: Subscription instances MUST provide `order` parameter (including duration and pricingCycle)
4. **Instance Type Selection**: 
   - High-performance (`standard`): Suitable for general search scenarios
   - Industry Algorithm (`enhanced`): Suitable for specific industry scenarios, requires `domain` parameter
5. **Industry Selection** (Industry Algorithm):
   - E-commerce: `ecommerce`
   - Gaming: `esports`
   - Content Community: `community`
   - Education: `education`
   - General: `general` (default)
6. **Spec Selection**: 
   - Shared Common: Suitable for small-scale scenarios
   - Dedicated: Suitable for production environments, more stable performance
7. **Resource Cleanup**: Delete unused pay-as-you-go instances promptly to avoid unnecessary costs

---

## Reference Links
| Document | Description |
|----------|-------------|
| [references/related-apis.md](references/related-apis.md) | Complete API List |
| [references/ram-policies.md](references/ram-policies.md) | RAM Policies |
| [references/verification-method.md](references/verification-method.md) | Verification Methods |
| [references/cli-installation-guide.md](references/cli-installation-guide.md) | CLI Installation Guide |
| [references/acceptance-criteria.md](references/acceptance-criteria.md) | Acceptance Criteria |