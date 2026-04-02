---
name: alibabacloud-hologres-instance-manage
description: |
  Alibaba Cloud Hologres Instance Management Skill. Use for listing and querying Hologres instances.
  Triggers: "hologres", "list instances", "get instance details", "hologres instance", "hologram".
---

# Hologres Instance Management

Skill for managing Alibaba Cloud Hologres instances - list all instances and get instance details.

## Architecture

```
User → Aliyun CLI → Hologres API (hologram) → Instance List / Instance Details
```

## Installation

> **Pre-check: Aliyun CLI >= 3.3.1 required**
> Run `aliyun version` to verify >= 3.3.1. If not installed or version too low,
> see `references/cli-installation-guide.md` for installation instructions.
> Then [MUST] run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.

```bash
curl -fsSL --connect-timeout 4 --max-time 120 https://aliyuncli.alicdn.com/install.sh | bash
aliyun version
```

## Authentication

This skill relies on the **Alibaba Cloud default credential chain**. It never reads, prints, or explicitly handles AK/SK values.

> **Security Rules:**
> - **NEVER** read, echo, or print AK/SK values
> - **NEVER** ask the user to input AK/SK directly
> - **NEVER** use `aliyun configure set` with literal credential values
> - **ONLY** use `aliyun configure list` to verify credential status

```bash
aliyun configure list
```

Check the output for a valid profile (AK, STS, EcsRamRole, or RamRoleArn).

**If no valid profile exists, STOP here.** The user must configure credentials **outside of this session** and return after `aliyun configure list` shows a valid profile.

## RAM Policy

The following RAM permissions are required for this skill:

| Product | RAM Action | Resource Scope | Description |
|---------|-----------|----------------|-------------|
| Hologram | hologram:ListInstances | `acs:hologram:{#regionId}:{#accountId}:instance/*` | List all Hologres instances |
| Hologram | hologram:GetInstance | `acs:hologram:{#regionId}:{#accountId}:instance/{#InstanceId}` | Get instance details |

See [references/ram-policies.md](references/ram-policies.md) for the complete RAM policy document.

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `references/ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

## Parameter Confirmation

> **IMPORTANT: Parameter Confirmation** — Before executing any command or API call,
> ALL user-customizable parameters (e.g., RegionId, instance names, resource group IDs,
> tags, etc.) MUST be confirmed with the user. Do NOT assume or use default values without explicit user approval.

| Parameter Name | Required/Optional | Description | Default Value |
|---------------|-------------------|-------------|---------------|
| RegionId | Optional | Region where instances are located | User's default region |
| InstanceId | Required (for GetInstance) | The ID of the Hologres instance | None |
| resourceGroupId | Optional | Filter by resource group ID | None |
| tag | Optional | Filter by tags (key-value pairs) | None |
| cmsInstanceType | Optional | Cloud Monitor instance type (standard/follower/mc-acceleration/warehouse/high-memory/serverless) | None |

## Core Workflow

### Task 1: List All Hologres Instances

Query all Hologres instances in the specified region.

```bash
# List all instances
aliyun hologram POST /api/v1/instances \
  --header "Content-Type=application/json" --body "{}" \
  --read-timeout 4 --user-agent AlibabaCloud-Agent-Skills

# List instances with resource group filter
aliyun hologram POST /api/v1/instances \
  --header "Content-Type=application/json" \
  --body '{"resourceGroupId":"rg-acfmvscak73zmby"}' \
  --read-timeout 4 --user-agent AlibabaCloud-Agent-Skills

# List instances with tag filter
aliyun hologram POST /api/v1/instances \
  --header "Content-Type=application/json" \
  --body '{"tag":[{"key":"env","value":"production"}]}' \
  --read-timeout 4 --user-agent AlibabaCloud-Agent-Skills

# List instances by CMS instance type
aliyun hologram POST /api/v1/instances \
  --header "Content-Type=application/json" \
  --body '{"cmsInstanceType":"standard"}' \
  --read-timeout 4 --user-agent AlibabaCloud-Agent-Skills
```

**Response Fields:**
- `InstanceId`: Instance ID
- `InstanceName`: Instance name
- `InstanceStatus`: Status (Creating/Running/Suspended/Allocating)
- `InstanceType`: Type (Warehouse/Follower/Standard/Serverless/Shared)
- `InstanceChargeType`: Payment type (PostPaid/PrePaid)
- `RegionId`: Region ID
- `Endpoints`: Network endpoints list

### Task 2: Get Instance Details

Get detailed information about a specific Hologres instance.

```bash
# Get instance details by ID
aliyun hologram GET /api/v1/instances/{instanceId} \
  --read-timeout 4 --user-agent AlibabaCloud-Agent-Skills

# Example with actual instance ID
aliyun hologram GET /api/v1/instances/hgprecn-cn-i7m2v08uu00a \
  --read-timeout 4 --user-agent AlibabaCloud-Agent-Skills
```

**Response Fields:**
- `InstanceId`: Instance ID
- `InstanceName`: Instance name (2-64 characters)
- `InstanceStatus`: Status (Creating/Running/Suspended/Allocating)
- `InstanceType`: Type (Warehouse/Follower/Standard/Serverless/Shared)
- `InstanceChargeType`: Payment type (PostPaid/PrePaid)
- `Cpu`: CPU cores
- `Memory`: Memory in GB
- `Disk`: Standard storage size in GB
- `ColdStorage`: Cold storage capacity in GB
- `Version`: Instance version
- `Endpoints`: Network endpoints with VPC/Internet/Intranet details
- `AutoRenewal`: Whether auto-renewal is enabled
- `EnableHiveAccess`: Whether data lake acceleration is enabled
- `EnableServerless`: Whether serverless computing is enabled
- `EnableSSL`: Whether SSL is enabled
- `StorageType`: Storage type (redundant/local)

## Success Verification Method

See [references/verification-method.md](references/verification-method.md) for detailed verification steps.

### Quick Verification

```bash
# Verify ListInstances
aliyun hologram POST /api/v1/instances \
  --header "Content-Type=application/json" --body "{}" \
  --read-timeout 4 --user-agent AlibabaCloud-Agent-Skills | jq '.InstanceList'

# Verify GetInstance
aliyun hologram GET /api/v1/instances/{your-instance-id} \
  --read-timeout 4 --user-agent AlibabaCloud-Agent-Skills | jq '.Instance.InstanceStatus'
```

**Success Indicators:**
- HTTP status code 200
- `Success` field is `true`
- `InstanceList` or `Instance` field contains valid data

## Cleanup

This skill performs read-only operations. No cleanup is required.

## Command Tables

See [references/related-commands.md](references/related-commands.md) for the complete CLI commands reference.

| Action | CLI Command | Description |
|--------|------------|-------------|
| List Instances | `aliyun hologram POST /api/v1/instances --read-timeout 4 --user-agent AlibabaCloud-Agent-Skills` | Get list of all Hologres instances |
| Get Instance | `aliyun hologram GET /api/v1/instances/{instanceId} --read-timeout 4 --user-agent AlibabaCloud-Agent-Skills` | Get details of a specific instance |

## Best Practices

1. **Always verify credentials** before executing commands using `aliyun configure list`
2. **Use filters** (resourceGroupId, tags) to narrow down results when listing many instances
3. **Check instance status** before performing operations - ensure instance is in `Running` state
4. **Use appropriate network endpoints** - choose VPCSingleTunnel for internal access, Internet for external access
5. **Monitor instance expiration** - check `ExpirationTime` for PrePaid instances to avoid service interruption
6. **Enable SSL** for production environments to ensure secure connections

## Reference Links

| Reference | Description |
|-----------|-------------|
| [references/cli-installation-guide.md](references/cli-installation-guide.md) | Aliyun CLI installation guide |
| [references/ram-policies.md](references/ram-policies.md) | Required RAM permissions |
| [references/related-commands.md](references/related-commands.md) | Complete CLI commands reference |
| [references/verification-method.md](references/verification-method.md) | Success verification steps |
| [Hologres API Documentation](https://api.aliyun.com/api/Hologram/2022-06-01/ListInstances) | Official API documentation |

## Error Handling

| HTTP Status | Error Code | Error Message | Resolution |
|-------------|-----------|---------------|------------|
| 403 | NoPermission | RAM user permission is insufficient | Grant `AliyunHologresReadOnlyAccess` permission |
| 400 | InvalidParameter | Invalid parameter value | Check parameter format and constraints |
| 404 | InstanceNotFound | Instance does not exist | Verify instance ID is correct |

For more error codes, see [Hologres Error Center](https://api.aliyun.com/document/Hologram/2022-06-01/errorCode).
