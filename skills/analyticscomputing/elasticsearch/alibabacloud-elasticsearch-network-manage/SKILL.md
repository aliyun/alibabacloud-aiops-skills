---
name: alibabacloud-elasticsearch-network-manage
description: |
  Alibaba Cloud Elasticsearch Instance Network Management Skill. Use for managing ES instance network configurations including triggering network, Kibana PVL network, white IP list, HTTPS settings, and Kibana SSO authentication.
  Triggers: "elasticsearch network", "ES network", "kibana pvl", "white ip", "https", "trigger network", "modify white ips", "kibana sso", "kibana authentication".
---

# Elasticsearch Instance Network Management

A skill for managing Alibaba Cloud Elasticsearch instance network configurations, including network triggering, Kibana PVL network, white IP list, HTTPS settings, and Kibana SSO authentication.

## Architecture

```
Alibaba Cloud Account → Elasticsearch Service → ES Instance(s) → Network Configuration
                                                        ├── Public Network Access
                                                        ├── Kibana PVL Network
                                                        ├── White IP List
                                                        ├── HTTPS Settings
                                                        └── Kibana SSO Authentication
```

---

## Installation

> **Pre-check: Aliyun CLI >= 3.3.3 required**
> Run `aliyun version` to verify >= 3.3.3. If not installed or version too low,
> run `curl -fsSL https://aliyuncli.alicdn.com/setup.sh | bash` to update,
> or see `references/cli-installation-guide.md` for installation instructions.

**[MUST] AI-Mode Configuration**

Before executing any CLI commands, enable AI-Mode and set User-Agent. After the workflow completes, disable AI-Mode.

```bash
# Step 1: Enable AI-Mode (before CLI operations)
aliyun configure ai-mode enable

# Step 2: Set User-Agent for traceability
aliyun configure ai-mode set-user-agent --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-network-manage"
```

After all CLI operations are complete:

```bash
# Step 3: Disable AI-Mode (after workflow ends)
aliyun configure ai-mode disable
```

**[MUST] Plugin Update**

```bash
aliyun configure set --auto-plugin-install true
aliyun plugin update
```

**[MUST] CLI Installation** (if not already installed or version < 3.3.3):

```bash
curl -fsSL https://aliyuncli.alicdn.com/setup.sh | bash
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

## CLI User-Agent Requirement

**[MUST] CLI User-Agent** — The user-agent is set globally via `aliyun configure ai-mode set-user-agent` during installation.
As a fallback, every `aliyun` CLI command invocation must also include:
`--user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-network-manage`

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
> - **NEVER** read, echo, or print AK/SK values
> - **NEVER** ask user to input AK/SK in conversation or command line
> - **ONLY** use `aliyun configure list` to check credential status
>
> ```bash
> aliyun configure list
> ```
>
> If no valid credentials, guide user to run `aliyun configure` in terminal (never accept plaintext AK/SK in chat).
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
> # Check instance status with retry logic
> max_retries=10
> retry_count=0
> while [ $retry_count -lt $max_retries ]; do
>   status=$(aliyun elasticsearch describe-instance \
>     --instance-id <InstanceId> \
>     --read-timeout 30 \
>     --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-network-manage | jq -r '.Result.status')
>
>   if [ "$status" == "active" ]; then
>     echo "✅ Instance status is active, proceeding..."
>     break
>   else
>     echo "⚠️ Instance status is $status, waiting 30s before retry..."
>     sleep 30
>     retry_count=$((retry_count + 1))
>   fi
> done
>
> if [ $retry_count -eq $max_retries ]; then
>   echo "❌ Instance did not become active after $max_retries retries, aborting"
>   exit 1
> fi
> ```

### Task 1: Trigger Network (Enable/Disable Public/Private Network Access)

Enable or disable public or private network access for Elasticsearch or Kibana clusters.

> **Scope**: Supports all network types on basic management instances. On cloud-native instances, supports cluster public/private network and Kibana public network. For **Kibana private network on cloud-native instances**, use EnableKibanaPvlNetwork / DisableKibanaPvlNetwork instead.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `nodeType` | String | Yes | Instance Type: KIBANA (Kibana cluster) / WORKER (Elasticsearch cluster) |
| `networkType` | String | Yes | Network Type: PUBLIC / PRIVATE |
| `actionType` | String | Yes | Action Type: OPEN (enable) / CLOSE (disable) |

```bash
# Example: Enable Kibana public network access
aliyun elasticsearch trigger-network \
  --instance-id <InstanceId> --read-timeout 30 \
  --body '{"nodeType":"KIBANA","networkType":"PUBLIC","actionType":"OPEN"}' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-network-manage

# Example: Disable Elasticsearch public network access
aliyun elasticsearch trigger-network \
  --instance-id <InstanceId> --read-timeout 30 \
  --body '{"nodeType":"WORKER","networkType":"PUBLIC","actionType":"CLOSE"}' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-network-manage
```

**Pre-check (Required):**

> **Network Status Fields** (via DescribeInstance):
> - `Result.enablePublic`: ES public network (private network is always on, cannot be disabled)
> - `Result.enableKibanaPublicNetwork`: Kibana public network
> - `Result.enableKibanaPrivateNetwork`: Kibana private network
>
> If the target network is already in the desired state, **skip the TriggerNetwork call** and inform the user.

```bash
# Pre-check: architecture + current network status
instance_info=$(aliyun elasticsearch describe-instance \
  --instance-id <InstanceId> --read-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-network-manage)

arch_type=$(echo "$instance_info" | jq -r '.Result.archType')

# Cloud-native Kibana private network: use EnableKibanaPvlNetwork/DisableKibanaPvlNetwork instead
if [ "$arch_type" == "public" ] && [ "$node_type" == "KIBANA" ] && [ "$network_type" == "PRIVATE" ]; then
  echo "❌ Use EnableKibanaPvlNetwork/DisableKibanaPvlNetwork for cloud-native Kibana private network"
  exit 1
fi

# Check if target network already in desired state
enable_public=$(echo "$instance_info" | jq -r '.Result.enablePublic')
enable_kibana_public=$(echo "$instance_info" | jq -r '.Result.enableKibanaPublicNetwork')
enable_kibana_private=$(echo "$instance_info" | jq -r '.Result.enableKibanaPrivateNetwork')

# Map nodeType+networkType to status field (ES private is always on)
# WORKER+PUBLIC -> enablePublic | KIBANA+PUBLIC -> enableKibanaPublicNetwork | KIBANA+PRIVATE -> enableKibanaPrivateNetwork
# If actionType=OPEN and already true, or actionType=CLOSE and already false, skip
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
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-network-manage)

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
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-network-manage
```
---

### Task 3: Disable Kibana PVL Network (Disable Kibana Private Network Access)

Disable Kibana private network access for an Elasticsearch instance.

> **Prerequisites**: This API **only supports cloud-native instances** (archType=public). For basic management instances, use TriggerNetwork.

```bash
aliyun elasticsearch disable-kibana-pvl-network \
  --instance-id <InstanceId> \
  --read-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-network-manage
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
  --instance-id <InstanceId> --read-timeout 30 \
  --body '{"nodeType":"WORKER","networkType":"PUBLIC","whiteIpList":["59.0.0.0/8","120.0.0.0/8"]}' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-network-manage
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
  --instance-id <InstanceId> --read-timeout 30 \
  --body '{"modifyMode":"Cover","whiteIpGroup":{"groupName":"default","ips":["59.0.0.0/8","120.0.0.0/8"],"whiteIpType":"PUBLIC_ES"}}' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-network-manage

# Append IPs to white group (Append mode, group must exist)
aliyun elasticsearch modify-white-ips \
  --instance-id <InstanceId> --read-timeout 30 \
  --body '{"modifyMode":"Append","whiteIpGroup":{"groupName":"default","ips":["172.16.0.0/12"],"whiteIpType":"PRIVATE_ES"}}' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-network-manage
```

**modifyMode Description:**

| Mode | Description |
|------|-------------|
| `Cover` | Overwrite mode (default). Empty ips deletes group; non-existent groupName creates new |
| `Append` | Append mode. Group must exist, otherwise NotFound error |
| `Delete` | Delete mode. Remove specified IPs, at least one IP must remain |

> **IMPORTANT: modifyMode Selection Guidelines**
> - Use `Append` for incremental addition, `Cover` for full replacement, `Delete` for removal
> - **If user intent is unclear, MUST ask user** which mode to use before executing
> - If Append fails with NotFound: inform user, suggest Cover mode to create group. Do NOT silently switch modes.

---

### Task 5: Open HTTPS (Enable HTTPS)

Enable HTTPS access for an Elasticsearch instance.

> **Pre-check**: Call DescribeInstance first to check `Result.protocol`. If already `HTTPS`, skip OpenHttps and inform user HTTPS is already enabled.

```bash
# Check current HTTPS status
protocol=$(aliyun elasticsearch describe-instance \
  --instance-id <InstanceId> \
  --read-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-network-manage | jq -r '.Result.protocol')

if [ "$protocol" == "HTTPS" ]; then
  echo "✅ HTTPS is already enabled, no action needed"
else
  # Enable HTTPS
  aliyun elasticsearch open-https \
    --instance-id <InstanceId> \
    --read-timeout 30 \
    --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-network-manage
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
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-network-manage | jq -r '.Result.protocol')

if [ "$protocol" == "HTTP" ]; then
  echo "✅ HTTPS is already disabled, no action needed"
else
  # Disable HTTPS
  aliyun elasticsearch close-https \
    --instance-id <InstanceId> \
    --read-timeout 30 \
    --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-network-manage
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
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-network-manage
```

---

### Task 8: Update Kibana SSO (Enable/Disable Kibana Alibaba Cloud Account Authentication)

Enable or disable Kibana Alibaba Cloud account SSO authentication. When enabled, users must log in with their Alibaba Cloud account before using Kibana.

> **Prerequisites**: This API **only supports cloud-native instances** (archType=public).

> **Pre-check**: Call DescribeInstance to check `Result.enableKibanaPublicSSO` / `Result.enableKibanaPrivateSSO`. If desired state already achieved, skip the call.

**Parameters:** See [references/related-apis.md](references/related-apis.md) for full details.

```bash
# Enable Kibana SSO for public network
aliyun elasticsearch update-kibana-sso \
  --instance-id <InstanceId> \
  --body '{"enable":true,"networkType":"PUBLIC"}' \
  --read-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-network-manage

# Disable Kibana SSO for private network
aliyun elasticsearch update-kibana-sso \
  --instance-id <InstanceId> \
  --body '{"enable":false,"networkType":"PRIVATE"}' \
  --read-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-network-manage
```

---

## Success Verification Method

For detailed verification steps, see [references/verification-method.md](references/verification-method.md). After each operation, check `RequestId` in response and call DescribeInstance to confirm changes.

---

## Best Practices

1. **Cloud-native Kibana**: Private network uses EnableKibanaPvlNetwork/DisableKibanaPvlNetwork. Whitelist via UpdateKibanaPvlNetwork. SSO via UpdateKibanaSso (archType=public only).
2. **Security**: Use 0.0.0.0/0 with caution. Enable HTTPS in production.
3. **Reliability**: Use clientToken for idempotency. Retry on `InstanceStatusNotSupportCurrentAction`/`ConcurrencyUpdateInstanceConflict` (wait 30-60s). Check current state before changes, skip if desired state already achieved.
---
## Reference Links

| Reference | Description |
|-----------|-------------|
| [references/related-apis.md](references/related-apis.md) | API and CLI command reference table |
| [references/ram-policies.md](references/ram-policies.md) | RAM permission policies |
| [references/cli-installation-guide.md](references/cli-installation-guide.md) | CLI installation guide |
| [references/verification-method.md](references/verification-method.md) | Verification methods |
| [references/acceptance-criteria.md](references/acceptance-criteria.md) | Acceptance criteria |