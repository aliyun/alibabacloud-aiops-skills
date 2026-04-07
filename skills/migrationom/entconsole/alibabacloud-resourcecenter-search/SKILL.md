---
name: alibabacloud-resourcecenter-search
description: |
  Alibaba Cloud Resource Center - Global Resource Inventory, Search & Statistics Skill.
  Provides cross-region, cross-product, and cross-account resource inventory, search, and statistical analysis capabilities.
  Also supports enabling and disabling Resource Center service.
  Triggers: "resource center", "resource search", "resource inventory", "resource statistics", "cross-account resource", "global resource", "resource count".
---


## 1. Prerequisites

> **Pre-check: Aliyun CLI >= 3.3.1 required**
> Run `aliyun version` to verify >= 3.3.1. If not installed or version too low,
> see `references/cli-installation-guide.md` for installation instructions.
> Then **[MUST]** run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.

> **Pre-check: Alibaba Cloud Credentials Required**
>
> **Security Rules:**
>
> - **NEVER** read, echo, or print AK/SK values (e.g., `echo $ALIBABA_CLOUD_ACCESS_KEY_ID` is FORBIDDEN)
> - **NEVER** ask the user to input AK/SK directly in the conversation or command line
> - **NEVER** use `aliyun configure set` with literal credential values
> - **ONLY** use `aliyun configure list` to check credential status
>
> ```bash
> aliyun configure list
> ```
>
> Check the output for a valid profile (AK, STS, or OAuth identity).
>
> **If no valid profile exists, STOP here.**
>
> 1. Obtain credentials from [Alibaba Cloud Console](https://ram.console.aliyun.com/manage/ak)
> 2. Configure credentials **outside of this session** (via `aliyun configure` in terminal or environment variables in shell profile)
> 3. Return and re-run after `aliyun configure list` shows a valid profile

---

## 2. Parameter Confirmation

> **IMPORTANT: Parameter Confirmation** — Before executing any command or API call,
> ALL user-customizable parameters (e.g., RegionId, instance names, CIDR blocks,
> passwords, domain names, resource specifications, etc.) MUST be confirmed with the
> user. Do NOT assume and use default values without explicit user approval.

| Parameter | Required/Optional | Description | Default Value |
| - | - | - | - |
| `Scope` | Required (cross-account) | Cross-account search scope: Resource Directory ID, Root Folder ID, Folder ID, or Member ID | None |
| `ResourceType` | Optional | Resource type (e.g., `ACS::ECS::Instance`) | None (all types) |
| `RegionId` | Optional | Resource Region ID (e.g., `cn-hangzhou`) | None (all regions) |
| `ResourceId` | Optional | Resource ID | None |
| `ResourceName` | Optional | Resource name  | None |
| `VpcId` | Optional | VPC ID (e.g., `vpc-xxx`) | None |
| `VSwitchId` | Optional | VSwitch (e.g., `vsw-xxx`) | None |
| `IpAddress` | Optional | IP address | None |
| `GroupByKey` | Optional | Statistics grouping dimension: `ResourceType`, `RegionId`, `ResourceGroupId` | None |
| `MaxResults` | Optional | Page size for paginated APIs. | 20 |

---

## 3. RAM Policy

See [references/ram-policies.md](references/ram-policies.md) for full permission lists.

Recommended system policies:

- **Read-only**: `AliyunResourceCenterReadOnlyAccess`
- **Full access**: `AliyunResourceCenterFullAccess`

> Opening Resource Center will auto-create the service-linked role `AliyunServiceRoleForResourceMetaCenter`.

### Resource Visibility Scope

RAM policies (defined in `ram-policies.md`) control whether a user **can call** a Resource Center API. However, for **search APIs** (`SearchResources`, `GetResourceCounts`, `GetResourceConfiguration`, `SearchMultiAccountResources`, `GetMultiAccountResourceCounts`, `GetMultiAccountResourceConfiguration`), the **scope of resources visible** in results is determined by each cloud product's own permissions:

#### Single Account

- **Cloud resource read permissions**: A RAM user can only see resources in Resource Center for which they have read-only access on the corresponding cloud product. For example, granting `ReadOnlyAccess` lets the user see all resources they have access to; granting only `AliyunVPCReadOnlyAccess` limits visibility to VPC resources.
- **Resource group scoped permissions**: If resources are organized by resource groups, you can grant a RAM user read access scoped to a specific resource group. The user will only see resources within that group, achieving resource isolation.

#### Cross-Account

- Grant the system policy `AliyunResourceCenterFullAccess` to the RAM user of the **Resource Directory management account** to enable cross-account resource search.

---

## 4. Core Workflow

### Step 1: Identify APIs Based on User Requirements

Determine which APIs are needed based on the user's specific scenario. Refer to the scenario cards below.

### Step 2: **[MUST]** Read API Documentation Before Every CLI Call

> **CRITICAL WARNING**: DO NOT execute any `aliyun resourcecenter` command without first reading the exact parameter format in `references/related-apis.md`.
>
> **Failure Pattern**: Guessing parameters like `--filter` format will cause errors. The correct JSON structure MUST be copied from the documentation.
>
> **Mandatory Action**: Open and read the specific API section in [references/related-apis.md](references/related-apis.md) BEFORE constructing any CLI command.

---

### Scenario Cards

#### Scenario 1: Service Activation

| Requirement | Account Type | API | Description |
| - | - | - | - |
| Check if enabled | Single-account | `get-resource-center-service-status` | Returns service status |
| Enable service | Single-account | `enable-resource-center` | Required for first-time use |
| Check cross-account status | Resource Directory | `get-multi-account-resource-center-service-status` | Multi-account scenario |
| Enable cross-account service | Resource Directory | `enable-multi-account-resource-center` | Requires management account or delegated admin |

---

#### Scenario 2: ResourceType Discovery

| Requirement | Account Type | Script | Description |
| - | - | - | - |
| Find resource type codes by keyword | Single-account | `scripts/query-resource-types.py` | Search across ResourceType, ProductName, and ResourceTypeName fields |

**Decision Logic**:

- When you needs to filter by resource type but doesn't know the exact code -> Use this script first
- After discovering the correct `ResourceType` code -> Use it in search or count API with `--filter` parameter

---

#### Scenario 3: Resource Search

| Requirement | Account Scope | API | Key Parameters |
| - | - | - | - |
| Search resources by criteria | Current account | `search-resources` | `--filter` |
| Cross-account resource search | Resource Directory | `search-multi-account-resources` | `--scope` + `--filter` |
| Search including deleted resources | Current account | `search-resources` | `--include-deleted-resources=true` |

---

#### Scenario 4: View Resource Details

| Requirement | Account Scope | API | Use Case |
| - | - | - | - |
| Get single resource configuration | Current account | `get-resource-configuration` | Get complete configuration details |
| Batch get multiple resource configurations | Current account | `batch-get-resource-configurations` | Get multiple resources at once |
| Get resource configuration from another account | Resource Directory | `get-multi-account-resource-configuration` | Cross-account view |

---

#### Scenario 5: Statistics and Analysis

| Requirement | Account Scope | API | Grouping Dimensions |
| - | - | - | - |
| Count resources | Current account | `get-resource-counts` | `ResourceType`, `RegionId`, `ResourceGroupId` |
| Cross-account statistics | Resource Directory | `get-multi-account-resource-counts` | `ResourceType`, `RegionId`, `ResourceGroupId` |

---

#### Scenario 6: Tag Discovery

| Requirement | Account Scope | API | Description |
| - | - | - | - |
| List all tag keys | Current account | `list-tag-keys` | Browse tag catalog |
| List values for a specific tag key | Current account | `list-tag-values` | e.g., list all values for `env` |
| Cross-account tag keys | Resource Directory | `list-multi-account-tag-keys` | Multi-account scenario |
| Cross-account tag values | Resource Directory | `list-multi-account-tag-values` | Multi-account scenario |

---

## 5. Success Verification

See [references/verification-method.md](references/verification-method.md) for detailed verification steps and commands for each workflow step.

---

## 6. Precautions

> **[MUST] High-Risk Operation Confirmation** — Before executing `disable-resource-center` or `disable-multi-account-resource-center`:
>
> 1. **MUST explicitly inform the user** of the impacts:
>   - **Disable Impact**
>     - After disabling Resource Center, resource data will no longer be viewable in Resource Center. Specifically:
>       - For a single Alibaba Cloud account, after disabling Resource Center, resource data in the current account will no longer be viewable.
>       - For the management account of a Resource Directory and the delegated administrator account of Resource Center, disabling Resource Center will also disable the cross-account resource search feature. Resource data in the current account and members of the Resource Directory will no longer be viewable. Additionally, members will not be able to view resource data in their own accounts.
>       - After disabling Resource Center, the resource management module on the console homepage, Config Audit service, and other related scenarios will also be unable to view resource data.
>   - **Disable Restrictions**
>     - If the management account of a Resource Directory or the delegated administrator account of Resource Center has cross-account resource features enabled by another account, Resource Center cannot be disabled.
>     - If there are cloud products or features that have strong dependencies on Resource Center, such as Config Audit and associated resource transfer, you must first disable those cloud products or features before you can disable Resource Center.
> 2. **MUST obtain explicit user confirmation** (e.g., user types "confirm disable" or similar clear affirmation)
> 3. **DO NOT proceed** without user's explicit acknowledgment

#### Disable Resource Center

> **Warning:** Disabling will remove all resource data and affect dependent services (e.g., Config Audit). Must first disable cross-account if enabled.

```bash
aliyun resourcecenter disable-resource-center \
  --user-agent AlibabaCloud-Agent-Skills
```

#### Disable Cross-Account Resource Center

> Must be done before disabling single-account resource center (if cross-account is enabled). Requires management account or delegated admin.

```bash
aliyun resourcecenter disable-multi-account-resource-center \
  --user-agent AlibabaCloud-Agent-Skills
```

---

## 7. Best Practices

1. **`--user-agent` on every Resource Center CLI call** — All `aliyun resourcecenter` examples in this skill include `--user-agent AlibabaCloud-Agent-Skills`. When executing commands for this skill, **always** pass the same flag so usage is consistent with verification, maintainers’ expectations, and any automated checks.
2. **Use filters for targeted search** — Combining `ResourceType`, `RegionId`, and `Tag` filters improves search efficiency
3. **Use `GroupByKey` for quick statistics** — Get resource distribution by type, region, or resource group without iterating
4. **Cross-account scope selection** — Use the most specific scope (member ID > folder ID > root folder ID > directory ID) to narrow search results
5. **Wait after enabling** — Resource Center needs a few minutes to build data after activation; large accounts may take longer
6. **Prefer read-only policies** — For daily search and statistics operations, use `AliyunResourceCenterReadOnlyAccess` for security
7. **ResourceType discovery** — When the exact resource type code is unknown, use the helper script documented in **Section 8** (run from the skill root directory).
8. **Tag discovery vs tag-filtered search** — For “what tag keys/values exist”, use `list-tag-keys` / `list-tag-values` (and multi-account variants with `--scope`). Reserve `search-resources` for finding **resources** that match tag conditions.

---

## 8. Available scripts

| Script | Purpose | Usage |
| - | - | - |
| `scripts/query-resource-types.py` | Queries resource types by keyword from Alibaba Cloud Resource Center; **stdout is JSON** (`resourceTypes`, `count`, `keyword`, `language`; failures use `success: false` and `error`) | `python3 scripts/query-resource-types.py <keyword> [--language LANGUAGE]` |

---

## 9. Troubleshooting

When a Resource Center API call or `aliyun resourcecenter` command fails, read the response’s **HTTP status**, **Code** (error code), and **Message**, then match them against the catalog.

**Full error list:** [references/error-codes.md](references/error-codes.md)

---

## 10. Reference Links

| Reference | Description |
| - | - |
| [references/related-apis.md](references/related-apis.md) | All CLI commands list |
| [references/ram-policies.md](references/ram-policies.md) | RAM permission policies |
| [references/verification-method.md](references/verification-method.md) | Verification steps for each workflow |
| [references/error-codes.md](references/error-codes.md) | Deduplicated Resource Center API error code catalog (HTTP, Code, Message) and lookup hints |
| [references/cli-installation-guide.md](references/cli-installation-guide.md) | Aliyun CLI installation guide |
| [references/acceptance-criteria.md](references/acceptance-criteria.md) | **For maintainers/CI only**: Skill testing acceptance criteria, correct CLI command patterns, parameter validation rules. **Note:** This document is intended for human maintainers and automated testing, not required reading for end users. |