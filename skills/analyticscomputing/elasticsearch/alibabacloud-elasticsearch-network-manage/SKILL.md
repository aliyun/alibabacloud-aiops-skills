---
name: alibabacloud-elasticsearch-network-manage
description: |
  Alibaba Cloud Elasticsearch Instance Network Management Skill. Use for managing ES instance network configurations including triggering network, Kibana PVL network, white IP list, and HTTPS settings.
  Triggers: "elasticsearch network", "ES network", "kibana pvl", "white ip", "https", "trigger network", "modify white ips".
---

# Elasticsearch Instance Network Management

A skill for managing Alibaba Cloud Elasticsearch instance network configurations, including network triggering, Kibana PVL network, white IP list, and HTTPS settings.

## Architecture

```
Alibaba Cloud Account → Elasticsearch Service → ES Instance(s) → Network Configuration
                                                        ├── Public Network Access
                                                        ├── Kibana PVL Network
                                                        ├── White IP List
                                                        └── HTTPS Settings
```

---

## Installation

> **Pre-check: Aliyun CLI >= 3.3.1 required**
> Run `aliyun version` to verify >= 3.3.1. If not installed or version too low,
> see `references/cli-installation-guide.md` for installation instructions.
> Then [MUST] run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.

```bash
# Install Aliyun CLI
curl -fsSL --connect-timeout 10 --max-time 60 https://aliyuncli.alicdn.com/install.sh | bash

# Verify installation
aliyun version
```

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ALIBABA_CLOUD_ACCESS_KEY_ID` | Yes | Alibaba Cloud AccessKey ID |
| `ALIBABA_CLOUD_ACCESS_KEY_SECRET` | Yes | Alibaba Cloud AccessKey Secret |
| `ALIBABA_CLOUD_REGION_ID` | No | Default Region ID (e.g., cn-hangzhou) |

---

## Parameter Confirmation

> **IMPORTANT: Parameter Confirmation** — Before executing any command or API call,
> ALL user-customizable parameters (e.g., RegionId, instance names, white IPs,
> VPC IDs, security groups, etc.) MUST be confirmed with the user.
> Do NOT assume or use default values without explicit user approval.

| Parameter Name | Required/Optional | Description | Default Value |
|---------------|-------------------|-------------|---------------|
| `InstanceId` | Required (for all operations) | Elasticsearch Instance ID | - |
| `RegionId` | Optional | Region ID | cn-hangzhou |
| `nodeType` | Required (TriggerNetwork) | Instance Type: KIBANA/WORKER | - |
| `networkType` | Required (TriggerNetwork) | Network Type: PUBLIC/PRIVATE | - |
| `actionType` | Required (TriggerNetwork) | Action Type: OPEN/CLOSE | - |
| `resourceGroupId` | Optional | Resource Group ID | - |
| `whiteIpGroup` | Required (ModifyWhiteIps) | White IP Group Configuration | - |
| `whiteIpType` | Optional (ModifyWhiteIps) | White IP Type: PRIVATE_ES/PUBLIC_KIBANA | PRIVATE_ES |

---

## Authentication

> **Pre-check: Alibaba Cloud Credentials Required**
>
> **Security Rules:**
> - **NEVER** read, echo, or print AK/SK values (e.g., `echo $ALIBABA_CLOUD_ACCESS_KEY_ID` is FORBIDDEN)
> - **NEVER** ask the user to input AK/SK directly in the conversation or command line
> - **NEVER** use `aliyun configure set` with literal credential values
> - **ONLY** use `aliyun configure list` to check credential status
>
> ```bash
> aliyun configure list
> ```
> Check the output for a valid profile (AK, STS, or OAuth identity).
>
> **Credential Issue Handling:**
>
> If `aliyun configure list` shows no valid credentials or incorrect configuration:
>
> 1. **Identify the issue**: Inform the user that credentials are not configured or misconfigured
> 2. **Guide proper configuration**: Direct the user to configure credentials **in the terminal** (not in the chat dialog):
>    - Run `aliyun configure` for interactive configuration
>    - Or set environment variables in shell profile
> 3. **Prohibit plaintext input**: **Absolutely forbidden** to let user input AK/SK in plaintext in the chat dialog
> 4. **Wait for re-verification**: After configuration, re-run `aliyun configure list` to verify
>
> Credential portal: [Alibaba Cloud RAM Console](https://ram.console.aliyun.com/manage/ak)

---

## RAM Policy

RAM permissions required for Elasticsearch instance network configuration operations. See [references/ram-policies.md](references/ram-policies.md) for details.

---

## Core Workflow

> **Prerequisite: Instance Status Check**
>
> Before executing any network configuration operation, verify that the instance status is `active`.
> Network configuration changes **cannot be executed** when instance status is `activating`, `invalid`, or `inactive`.
>
> ```bash
> # Check instance status
> aliyun elasticsearch describe-instance \
>   --instance-id <InstanceId> \
>   --read-timeout 30 \
>   --user-agent AlibabaCloud-Agent-Skills | jq -r '.Result.status'
> ```
> If the return value is not `active`, wait until the instance status becomes `active` before proceeding.

### Task 1: Trigger Network (Enable/Disable Public/Private Network Access)

Enable or disable public or private network access for Elasticsearch or Kibana clusters.

> **Scope**: Supports enabling/disabling public/private network for both cluster and Kibana on basic management instances. Supports enabling/disabling public and private network for cluster on cloud-native instances. Supports enabling/disabling Kibana public network on cloud-native instances. For Kibana private network on cloud-native instances, use:
> - EnableKibanaPvlNetwork to enable Kibana private link
> - DisableKibanaPvlNetwork to disable Kibana private link

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `nodeType` | String | Yes | Instance Type: KIBANA (Kibana cluster) / WORKER (Elasticsearch cluster) |
| `networkType` | String | Yes | Network Type: PUBLIC / PRIVATE |
| `actionType` | String | Yes | Action Type: OPEN (enable) / CLOSE (disable) |

```bash
# Enable Kibana public network access (timeout 30s)
aliyun elasticsearch trigger-network \
  --instance-id <InstanceId> \
  --read-timeout 30 \
  --body '{
    "nodeType": "KIBANA",
    "networkType": "PUBLIC",
    "actionType": "OPEN"
  }' \
  --user-agent AlibabaCloud-Agent-Skills

# Disable Kibana public network access
aliyun elasticsearch trigger-network \
  --instance-id <InstanceId> \
  --read-timeout 30 \
  --body '{
    "nodeType": "KIBANA",
    "networkType": "PUBLIC",
    "actionType": "CLOSE"
  }' \
  --user-agent AlibabaCloud-Agent-Skills

# Enable Elasticsearch private network access
aliyun elasticsearch trigger-network \
  --instance-id <InstanceId> \
  --read-timeout 30 \
  --body '{
    "nodeType": "WORKER",
    "networkType": "PRIVATE",
    "actionType": "OPEN"
  }' \
  --user-agent AlibabaCloud-Agent-Skills

# Disable Elasticsearch public network access
aliyun elasticsearch trigger-network \
  --instance-id <InstanceId> \
  --read-timeout 30 \
  --body '{
    "nodeType": "WORKER",
    "networkType": "PUBLIC",
    "actionType": "CLOSE"
  }' \
  --user-agent AlibabaCloud-Agent-Skills
```

**Pre-check (Required):**

```bash
# 1. Check instance architecture type (timeout 30s)
arch_type=$(aliyun elasticsearch describe-instance \
  --instance-id <InstanceId> \
  --read-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills | jq -r '.Result.archType')

echo "Instance architecture type: $arch_type"

# 2. If cloud-native (public) and trying to open/close Kibana private network, TriggerNetwork is not supported
if [ "$arch_type" == "public" ] && [ "$node_type" == "KIBANA" ] && [ "$network_type" == "PRIVATE" ]; then
  echo "❌ Cloud-native instances do not support TriggerNetwork for Kibana private network, use EnableKibanaPvlNetwork/DisableKibanaPvlNetwork instead"
  exit 1
fi
```

---

### Task 2: Enable Kibana PVL Network (Enable Kibana Private Network Access)

Enable Kibana private network access (PrivateLink) for an Elasticsearch instance.

> **Prerequisites**: Only supports cloud-native instances (archType=public), Kibana spec must be > 1 core 2GB. For basic management instances, use TriggerNetwork.

**Request Parameters (Body):**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `endpointName` | String | Yes | Endpoint name, recommended format: `{InstanceId}-kibana-endpoint` |
| `securityGroups` | Array | Yes | Security group ID array |
| `vSwitchIdsZone` | Array | Yes | VSwitch and availability zone information |
| `vSwitchIdsZone[].vswitchId` | String | Yes | Virtual switch ID |
| `vSwitchIdsZone[].zoneId` | String | Yes | Availability zone ID |
| `vpcId` | String | Yes | VPC instance ID |

> **Pre-check**: Call DescribeInstance first to check `Result.enableKibanaPrivateNetwork`. If already enabled, compare current config (vpcId, vswitchId, securityGroups) with user requirements. If they match, skip and inform user config is already correct.

```bash
# Check current Kibana PVL status and config
instance_info=$(aliyun elasticsearch describe-instance \
  --instance-id <InstanceId> \
  --read-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills)

pvl_enabled=$(echo "$instance_info" | jq -r '.Result.enableKibanaPrivateNetwork')
current_vpc=$(echo "$instance_info" | jq -r '.Result.networkConfig.vpcId')
current_vswitch=$(echo "$instance_info" | jq -r '.Result.networkConfig.vswitchId')

if [ "$pvl_enabled" == "true" ]; then
  # Check if current config matches user requirements
  if [ "$current_vpc" == "<VpcId>" ] && [ "$current_vswitch" == "<VswitchId>" ]; then
    echo "✅ Kibana private network already enabled with matching config, no action needed"
    exit 0
  fi
fi

# Enable Kibana private network access
aliyun elasticsearch enable-kibana-pvl-network \
  --instance-id <InstanceId> \
  --body '{
    "endpointName": "<InstanceId>-kibana-endpoint",
    "securityGroups": ["<SecurityGroupId>"],
    "vSwitchIdsZone": [{"vswitchId": "<VswitchId>", "zoneId": "<ZoneId>"}],
    "vpcId": "<VpcId>"
  }' \
  --read-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills
```
---

### Task 3: Disable Kibana PVL Network (Disable Kibana Private Network Access)

Disable Kibana private network access for an Elasticsearch instance.

> **Prerequisites**: This API **only supports cloud-native instances** (archType=public). For basic management instances, use TriggerNetwork.

```bash
aliyun elasticsearch disable-kibana-pvl-network \
  --instance-id <InstanceId> \
  --read-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills
```

---

### Task 4: Modify White IPs (Modify White IP List)

Update the access white IP list for the specified instance. Two update methods are supported (cannot be used simultaneously):

1. **IP White List Method**: Use `whiteIpList` + `nodeType` + `networkType`
2. **IP White Group Method**: Use `modifyMode` + `whiteIpGroup`

> **Notes**: 
> - Cannot update when instance status is activating, invalid, or inactive
> - Public network white list does not support private IPs; private network white list does not support public IPs
> - **Kibana private network white list for cloud-native instances (archType=public) cannot be modified via this API**. Use UpdateKibanaPvlNetwork API to modify security groups instead (see Task 7)

**Method 1: IP White List (Update Default Group)**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `whiteIpList` | Array | Yes | IP white list, will overwrite Default group |
| `nodeType` | String | Yes | Node Type: WORKER (ES cluster) / KIBANA |
| `networkType` | String | Yes | Network Type: PUBLIC / PRIVATE |

```bash
# Modify ES public network white list (overwrite Default group)
aliyun elasticsearch modify-white-ips \
  --instance-id <InstanceId> \
  --body '{"nodeType":"WORKER","networkType":"PUBLIC","whiteIpList":["59.0.0.0/8","120.0.0.0/8"]}' \
  --read-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills

# Modify ES private network white list
aliyun elasticsearch modify-white-ips \
  --instance-id <InstanceId> \
  --body '{"nodeType":"WORKER","networkType":"PRIVATE","whiteIpList":["192.168.1.0/24","10.0.0.0/8"]}' \
  --read-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills

# Modify Kibana public network white list
aliyun elasticsearch modify-white-ips \
  --instance-id <InstanceId> \
  --body '{"nodeType":"KIBANA","networkType":"PUBLIC","whiteIpList":["0.0.0.0/0"]}' \
  --read-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills
```

**Method 2: IP White Group (Supports Incremental/Overwrite/Delete)**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `modifyMode` | String | No | Modify mode: Cover (overwrite, default) / Append / Delete |
| `whiteIpGroup.groupName` | String | Yes | White IP group name |
| `whiteIpGroup.ips` | Array | Yes | IP address list |
| `whiteIpGroup.whiteIpType` | String | No | White IP type (see table below) |

**whiteIpType Values:**

| Value | Description |
|-------|-------------|
| `PRIVATE_ES` | Elasticsearch private network white list |
| `PUBLIC_ES` | Elasticsearch public network white list |
| `PRIVATE_KIBANA` | Kibana private network white list |
| `PUBLIC_KIBANA` | Kibana public network white list |

```bash
# Overwrite specified white group (Cover mode)
aliyun elasticsearch modify-white-ips \
  --instance-id <InstanceId> \
  --body '{"modifyMode":"Cover","whiteIpGroup":{"groupName":"default","ips":["59.0.0.0/8","120.0.0.0/8"],"whiteIpType":"PUBLIC_ES"}}' \
  --read-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills

# Append IPs to white group (Append mode, group must exist)
aliyun elasticsearch modify-white-ips \
  --instance-id <InstanceId> \
  --body '{"modifyMode":"Append","whiteIpGroup":{"groupName":"default","ips":["172.16.0.0/12"],"whiteIpType":"PRIVATE_ES"}}' \
  --read-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills

# Delete IPs from white group (Delete mode, at least one IP must remain)
aliyun elasticsearch modify-white-ips \
  --instance-id <InstanceId> \
  --body '{"modifyMode":"Delete","whiteIpGroup":{"groupName":"default","ips":["192.168.1.100"],"whiteIpType":"PRIVATE_ES"}}' \
  --read-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills

# Create new white group (Cover mode + new group name)
aliyun elasticsearch modify-white-ips \
  --instance-id <InstanceId> \
  --body '{"modifyMode":"Cover","whiteIpGroup":{"groupName":"new_group","ips":["10.0.0.0/8"],"whiteIpType":"PRIVATE_ES"}}' \
  --read-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills

# Delete white group (Cover mode + empty ips)
aliyun elasticsearch modify-white-ips \
  --instance-id <InstanceId> \
  --body '{"modifyMode":"Cover","whiteIpGroup":{"groupName":"group_to_delete","ips":[],"whiteIpType":"PRIVATE_ES"}}' \
  --read-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills
```

**modifyMode Description:**

| Mode | Description |
|------|-------------|
| `Cover` | Overwrite mode (default). Empty ips deletes the group; non-existent groupName creates new group |
| `Append` | Append mode. Group must exist, otherwise NotFound error |
| `Delete` | Delete mode. Delete specified IPs, at least one IP must remain |

---

### Task 5: Open HTTPS (Enable HTTPS)

Enable HTTPS access for an Elasticsearch instance.

> **Pre-check**: Call DescribeInstance first to check `Result.protocol`. If already `HTTPS`, skip OpenHttps and inform user HTTPS is already enabled.

```bash
# Check current HTTPS status
protocol=$(aliyun elasticsearch describe-instance \
  --instance-id <InstanceId> \
  --read-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills | jq -r '.Result.protocol')

if [ "$protocol" == "HTTPS" ]; then
  echo "✅ HTTPS is already enabled, no action needed"
else
  # Enable HTTPS
  aliyun elasticsearch open-https \
    --instance-id <InstanceId> \
    --read-timeout 30 \
    --user-agent AlibabaCloud-Agent-Skills
fi
```

---

### Task 6: Close HTTPS (Disable HTTPS)

Disable HTTPS access for an Elasticsearch instance.

> **Pre-check**: Call DescribeInstance first to check `Result.protocol`. If already `HTTP`, skip CloseHttps and inform user HTTPS is already disabled.

```bash
# Check current HTTPS status
protocol=$(aliyun elasticsearch describe-instance \
  --instance-id <InstanceId> \
  --read-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills | jq -r '.Result.protocol')

if [ "$protocol" == "HTTP" ]; then
  echo "✅ HTTPS is already disabled, no action needed"
else
  # Disable HTTPS
  aliyun elasticsearch close-https \
    --instance-id <InstanceId> \
    --read-timeout 30 \
    --user-agent AlibabaCloud-Agent-Skills
fi
```

---

### Task 7: Update Kibana PVL Network (Update Kibana Private Network Configuration)

Update Kibana private network access configuration, primarily used for modifying security groups.

> **Prerequisites**:
> 1. This API **only supports cloud-native instances** (archType=public). For basic management instances, use TriggerNetwork.
> 2. Kibana specification must be **greater than 1 core 2GB**.
> 3. Instance must have Kibana private network access enabled.

**Use Case**: Use this API when cloud-native instances need to modify Kibana private network access security groups (whitelist control).

**Request Parameters:**

| Parameter | Type | Location | Required | Description |
|-----------|------|----------|----------|-------------|
| `InstanceId` | String | Path | Yes | Instance ID |
| `pvlId` | String | Query | Yes | Kibana private link ID, format: `{InstanceId}-kibana-internal-internal` |
| `endpointName` | String | Body | No | Endpoint name |
| `securityGroups` | Array | Body | No | Security group ID array |

```bash
# Update Kibana private network security group
aliyun elasticsearch update-kibana-pvl-network \
  --instance-id <InstanceId> \
  --pvl-id <InstanceId>-kibana-internal-internal \
  --body '{"securityGroups": ["<NewSecurityGroupId>"]}' \
  --read-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills
```

---

## Success Verification Method

For detailed verification steps, see [references/verification-method.md](references/verification-method.md)

**Quick Verification:**

1. **TriggerNetwork**: Check `RequestId`, use DescribeInstance to confirm network config changes
2. **EnableKibanaPvlNetwork/DisableKibanaPvlNetwork**: Check return status, use DescribeInstance to confirm PVL status
3. **ModifyWhiteIps**: Check return status, use DescribeInstance to confirm whitelist updated
4. **OpenHttps/CloseHttps**: Check return status, use DescribeInstance to confirm HTTPS status

---

## Best Practices

1. **Check architecture type for Kibana private network**: For cloud-native instances (archType=public), TriggerNetwork does not support Kibana private network (nodeType=KIBANA, networkType=PRIVATE). Use EnableKibanaPvlNetwork/DisableKibanaPvlNetwork instead.
2. **Kibana private network whitelist for cloud-native instances**: For cloud-native instances (archType=public), Kibana private network access control should be done via UpdateKibanaPvlNetwork to modify security groups, not ModifyWhiteIps
3. **Backup whitelist**: Record existing configuration before modifying whitelist
4. **Use 0.0.0.0/0 with caution**: Opening access to all IPs poses security risks; only open necessary IP ranges
5. **HTTPS recommendation**: Enable HTTPS in production environments to ensure data transmission security
6. **Network change impact**: TriggerNetwork operations may cause brief service interruptions; execute during off-peak hours
7. **Use clientToken**: Use clientToken for write operations to ensure idempotency
8. **Retry on instance status errors**: If API calls fail with `InstanceStatusNotSupportCurrentAction`, `TargetInstanceStatusNotSupportCurrentAction`, or `ConcurrencyUpdateInstanceConflict`, wait 30-60 seconds and retry. See `references/verification-method.md` for details.
9. **Idempotent operations**: Check current state before making changes. Skip API calls if desired state is already achieved.

---

## Reference Links

| Reference | Description |
|-----------|-------------|
| [references/related-apis.md](references/related-apis.md) | API and CLI command reference table |
| [references/ram-policies.md](references/ram-policies.md) | RAM permission policies |
| [references/cli-installation-guide.md](references/cli-installation-guide.md) | CLI installation guide |
| [references/verification-method.md](references/verification-method.md) | Verification methods |
| [references/acceptance-criteria.md](references/acceptance-criteria.md) | Acceptance criteria |