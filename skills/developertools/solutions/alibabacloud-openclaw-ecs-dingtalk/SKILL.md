---
name: alibabacloud-openclaw-ecs-dingtalk
description: |
  Deploy OpenClaw AI agent platform on Alibaba Cloud ECS and integrate with DingTalk bot. OpenClaw (formerly Clawdbot/Moltbot, 中文名"龙虾") is an open-source AI assistant and automation platform supporting natural language-driven task automation with multi-channel chat integration. This Skill covers the full workflow from ECS instance creation, public network configuration, base environment setup, one-click OpenClaw deployment to DingTalk bot verification. End users can chat with the AI assistant by @mentioning the bot in a DingTalk group.
  Triggers: "OpenClaw", "龙虾", "Clawdbot", "Moltbot", "DingTalk bot", "DingTalk AI", "deploy OpenClaw on ECS", "AI agent platform", "DingTalk integration", "openclaw dingtalk", "openclaw deploy", "DingTalk AI employee", "Alibaba Cloud OpenClaw", "Bailian + DingTalk", "DingTalk group AI", "DingTalk smart assistant", "部署龙虾", "龙虾机器人", "龙虾钉钉"
---

# Deploy OpenClaw on ECS with DingTalk Integration

Deploy OpenClaw AI agent platform on an Alibaba Cloud ECS instance with one click, configure Alibaba Cloud Bailian LLM, and connect to a DingTalk group via a DingTalk bot, enabling users to chat with AI directly in DingTalk.

> Source: This Skill is based on Alibaba Cloud official documentation and OpenClaw open-source project documentation. See reference links at the end.
>
> Version: This Skill is written for OpenClaw March 2026 release and the `@dingtalk-real-ai/dingtalk-connector` plugin, verified on 2026-03-11.

## Parameter Collection

Before execution, prompt the user to provide all required parameters in a single message. Do not proceed until all required parameters are received and confirmed.

### Input Validation

Validate all user inputs before use to prevent command injection. Reject inputs containing shell special characters (`;`, `|`, `&`, `$`, `\`, `'`, `"`, backticks, parentheses, brackets, newlines). Parameters must match expected formats:

- `region`: `cn-[a-z]+`, `ap-[a-z]+`, `us-[a-z]+` etc.
- `instance_type`: `ecs.[a-z0-9]+.[a-z0-9]+`
- `vpc_id/vswitch_id/security_group_id`: `vpc-/vsw-/sg-[a-z0-9]+`
- `dingtalk_client_id`: `ding[a-z0-9]+`
- `dingtalk_client_secret`: 16-64 alphanumeric chars

When passing parameters to Cloud Assistant `RunCommand`, use base64 encoding for sensitive values.

### ECS Instance Parameters

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| `region` | Yes | Deployment region | `cn-hangzhou` |
| `instance_type` | No | ECS instance type (default: `ecs.c6.large`, 2 vCPU 4 GB) | `ecs.c6.large` |
| `image_id` | No | OS image (default: Ubuntu 22.04) | Auto-selected |
| `vpc_id` | No | Existing VPC ID (auto-created if not provided) | `vpc-xxx` |
| `vswitch_id` | No | Existing VSwitch ID (auto-created if not provided) | `vsw-xxx` |
| `security_group_id` | No | Existing Security Group ID (auto-created if not provided) | `sg-xxx` |

### OpenClaw and Bailian Parameters

The Bailian API Key (`bailian_api_key`) is **automatically obtained via CLI** during deployment (see Step 2). No manual console operation is needed. The Skill uses `aliyun maas` commands (ListWorkspaces + ListApiKeys/CreateApiKey) to retrieve or create an API Key programmatically.

> Prerequisites: The user's Alibaba Cloud account must have the Bailian (Model Studio) service activated. If not activated, guide the user to visit [Bailian Console](https://bailian.console.aliyun.com/) to activate it first.

### DingTalk Integration Parameters

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| `dingtalk_client_id` | Yes | DingTalk app Client ID | `dingxxxxxx` |
| `dingtalk_client_secret` | Yes | DingTalk app Client Secret | `xxxxxxxxxxxxx` |

> If the user has not created a DingTalk app, guide them to refer to the [DingTalk App Setup Guide](references/dingtalk-setup-guide.md) to create an app, configure the bot, add permissions, publish the app, and obtain credentials.

## Execution Constraints

- **Sensitive information masking**: Mask middle portion of passwords, keys, tokens, IPs, instance IDs (e.g., `ak****3d`, `i-bp1****7f2z`)
- **Input validation**: Reject shell special characters (`;`, `|`, `&`, `$`, backticks, etc.). Use parameterized API calls
- **Command injection prevention**: Encode sensitive values for Cloud Assistant RunCommand using base64
- **Network timeout**: All curl/wget operations must include `--connect-timeout` and `--max-time` parameters
- Execute steps in order; verify success after each step; inform user of current step
- If any step fails, ask user for confirmation before continuing
- Cloud Assistant `RunCommand` results: poll `DescribeInvocations` every 15+ seconds
- **Destructive operations**: Confirm with user and verify resource state before deletion

---

# Step 1: Create ECS Instance

## 1.1 Verify Alibaba Cloud Account

```bash
aliyun sts GetCallerIdentity \
  --user-agent AlibabaCloud-Agent-Skills
```

## 1.2 Check Zone Availability

Query which availability zones have stock for the target instance type to avoid creating resources in an unavailable zone:

```bash
aliyun ecs DescribeAvailableResource \
  --RegionId ${region} \
  --DestinationResource InstanceType \
  --InstanceChargeType PostPaid \
  --InstanceType ${instance_type} \
  --user-agent AlibabaCloud-Agent-Skills
```

Select a zone where `StatusCategory` is `WithStock` from the result, record as `${zone_id}`.

## 1.3 Create VPC and VSwitch (if not provided by user)

```bash
# Create VPC
aliyun vpc CreateVpc \
  --RegionId ${region} \
  --VpcName openclaw-vpc \
  --CidrBlock 172.16.0.0/16 \
  --user-agent AlibabaCloud-Agent-Skills

# Create VSwitch (use the zone with stock found in the previous step)
aliyun vpc CreateVSwitch \
  --RegionId ${region} \
  --VpcId ${vpc_id} \
  --VSwitchName openclaw-vswitch \
  --CidrBlock 172.16.0.0/24 \
  --ZoneId ${zone_id} \
  --user-agent AlibabaCloud-Agent-Skills
```

## 1.4 Create Security Group and Configure Rules

```bash
# Create security group
aliyun ecs CreateSecurityGroup \
  --RegionId ${region} \
  --VpcId ${vpc_id} \
  --SecurityGroupName openclaw-sg \
  --Description "Security group for OpenClaw" \
  --user-agent AlibabaCloud-Agent-Skills

# Allow SSH (port 22)
aliyun ecs AuthorizeSecurityGroup \
  --RegionId ${region} \
  --SecurityGroupId ${security_group_id} \
  --IpProtocol tcp \
  --PortRange 22/22 \
  --SourceCidrIp 0.0.0.0/0 \
  --user-agent AlibabaCloud-Agent-Skills

# Allow HTTP (port 80) and HTTPS (port 443)
aliyun ecs AuthorizeSecurityGroup \
  --RegionId ${region} \
  --SecurityGroupId ${security_group_id} \
  --IpProtocol tcp \
  --PortRange 80/80 \
  --SourceCidrIp 0.0.0.0/0 \
  --user-agent AlibabaCloud-Agent-Skills

aliyun ecs AuthorizeSecurityGroup \
  --RegionId ${region} \
  --SecurityGroupId ${security_group_id} \
  --IpProtocol tcp \
  --PortRange 443/443 \
  --SourceCidrIp 0.0.0.0/0 \
  --user-agent AlibabaCloud-Agent-Skills
```

## 1.5 Create ECS Instance

First, query the latest Ubuntu 22.04 system image ID in the target region:

```bash
aliyun ecs DescribeImages \
  --RegionId ${region} \
  --OSType linux \
  --ImageOwnerAlias system \
  --ImageName "ubuntu_22_04*" \
  --Status Available \
  --PageSize 1 \
  --user-agent AlibabaCloud-Agent-Skills
```

Get the latest `ImageId` from the result, then create the instance (note: **do not set** `InternetMaxBandwidthOut`; public network access will be configured via EIP later):

```bash
aliyun ecs RunInstances \
  --RegionId ${region} \
  --InstanceType ${instance_type} \
  --ImageId ${image_id} \
  --SecurityGroupId ${security_group_id} \
  --VSwitchId ${vswitch_id} \
  --SystemDisk.Category cloud_essd \
  --SystemDisk.Size 40 \
  --InstanceChargeType PostPaid \
  --InstanceName openclaw-server \
  --Amount 1 \
  --user-agent AlibabaCloud-Agent-Skills
```

## 1.6 Configure Public Network Access (EIP)

Create an Elastic IP Address and bind it to the ECS instance with 100 Mbps bandwidth (OpenClaw installation requires downloading many npm packages):

```bash
# Create EIP (100 Mbps bandwidth)
aliyun vpc AllocateEipAddress \
  --RegionId ${region} \
  --Bandwidth 100 \
  --InternetChargeType PayByTraffic \
  --user-agent AlibabaCloud-Agent-Skills

# Bind EIP to ECS instance
aliyun vpc AssociateEipAddress \
  --RegionId ${region} \
  --AllocationId ${eip_allocation_id} \
  --InstanceId ${instance_id} \
  --InstanceType EcsInstance \
  --user-agent AlibabaCloud-Agent-Skills
```

Record the EIP address for subsequent SSH connections and Cloud Assistant command execution.

## 1.7 Start Instance and Wait for Running State

```bash
# Start instance
aliyun ecs StartInstance \
  --InstanceId ${instance_id} \
  --user-agent AlibabaCloud-Agent-Skills

# Query instance status, confirm it is Running
aliyun ecs DescribeInstances \
  --RegionId ${region} \
  --InstanceIds '["${instance_id}"]' \
  --user-agent AlibabaCloud-Agent-Skills
```

---

# Step 2: Obtain Bailian API Key via CLI

Use the `aliyun maas` CLI plugin to automatically retrieve or create a Bailian API Key, eliminating the need for manual console operations.

## 2.1 Install the MaaS CLI Plugin

The `aliyun maas` commands require the `aliyun-cli-maas` plugin:

```bash
aliyun plugin install --names aliyun-cli-maas \
  --user-agent AlibabaCloud-Agent-Skills
```

## 2.2 List Workspaces (must run first)

**`workspace-id` is a required parameter for ListApiKeys and CreateApiKey**, so you must obtain it via ListWorkspaces first. Every Alibaba Cloud account with Bailian activated has a default workspace:

```bash
aliyun maas list-workspaces \
  --region ${region} \
  --user-agent AlibabaCloud-Agent-Skills
```

Record the `WorkspaceId` from the result as `${workspace_id}`. If the result is empty (no workspaces), the user has not activated the Bailian service yet — guide them to activate it at the [Bailian Console](https://bailian.console.aliyun.com/).

## 2.3 List Existing API Keys (requires workspace_id)

Use the `${workspace_id}` obtained in the previous step to query existing API Keys in that workspace:

```bash
aliyun maas list-api-keys \
  --workspace-id ${workspace_id} \
  --region ${region} \
  --user-agent AlibabaCloud-Agent-Skills
```

If an existing API Key is found, record its `ApiKeyValue` (in `sk-xxx` format) as `${bailian_api_key}` and skip step 2.4.

## 2.4 Create API Key (only if 2.3 returns no results)

Only when no API Key was found in the previous step, create a new one using the same `${workspace_id}`:

```bash
aliyun maas create-api-key \
  --workspace-id ${workspace_id} \
  --description "OpenClaw deployment API Key" \
  --region ${region} \
  --user-agent AlibabaCloud-Agent-Skills
```

Record the `ApiKeyValue` (in `sk-xxx` format) from the response as `${bailian_api_key}`.

> Important: The full API Key value is only visible at creation time. Subsequent queries will only return a masked value. Make sure to record the complete key in this step.

---

# Step 3: Install Base Environment via Cloud Assistant

Use Alibaba Cloud Cloud Assistant to remotely execute commands on the ECS instance without manual SSH connection.

Combine Git installation, Node.js 22.x installation, and npm China mirror configuration into a single command to reduce waiting time:

```bash
aliyun ecs RunCommand \
  --RegionId ${region} \
  --Type RunShellScript \
  --CommandContent "apt-get update -y && apt-get install -y git curl wget && curl -fsSL --connect-timeout 30 --max-time 300 https://deb.nodesource.com/setup_22.x | bash - && apt-get install -y nodejs && npm config set registry https://registry.npmmirror.com && node -v && npm -v" \
  --InstanceId.1 ${instance_id} \
  --Timeout 600 \
  --user-agent AlibabaCloud-Agent-Skills
```

Use `DescribeInvocations` to query the command execution result and confirm success:

```bash
aliyun ecs DescribeInvocations \
  --RegionId ${region} \
  --InvokeId ${invoke_id} \
  --user-agent AlibabaCloud-Agent-Skills
```

Confirm Node.js version is v22.x.x in the output.

> Polling tip: This command typically takes 2-5 minutes to complete. When querying `DescribeInvocations`, poll every 15-30 seconds to avoid excessive polling. The command is finished when `InvocationStatus` changes from `Running` to `Success` or `Failed`.

---

# Step 4: One-Click OpenClaw Installation

Use the installation script to complete OpenClaw setup, Bailian API configuration, and DingTalk plugin installation.

> **Security**: Sensitive parameters are passed via base64 encoding to prevent command injection.

```bash
# Encode sensitive parameters
BAILIAN_KEY_B64=$(echo -n "${bailian_api_key}" | base64)
DINGTALK_ID_B64=$(echo -n "${dingtalk_client_id}" | base64)
DINGTALK_SECRET_B64=$(echo -n "${dingtalk_client_secret}" | base64)

aliyun ecs RunCommand \
  --RegionId ${region} \
  --Type RunShellScript \
  --CommandContent "curl -fsSL --connect-timeout 30 --max-time 300 https://openclaw-install-scripts.oss-cn-hangzhou.aliyuncs.com/install.sh -o /tmp/openclaw-install.sh && BAILIAN_API_KEY=\$(echo '${BAILIAN_KEY_B64}' | base64 -d) DINGTALK_CLIENT_ID=\$(echo '${DINGTALK_ID_B64}' | base64 -d) DINGTALK_CLIENT_SECRET=\$(echo '${DINGTALK_SECRET_B64}' | base64 -d) bash /tmp/openclaw-install.sh --api-key \"\$BAILIAN_API_KEY\" --api-region '${region}' --dingtalk-client-id \"\$DINGTALK_CLIENT_ID\" --dingtalk-client-secret \"\$DINGTALK_CLIENT_SECRET\"" \
  --InstanceId.1 ${instance_id} \
  --Timeout 600 \
  --user-agent AlibabaCloud-Agent-Skills
```

The script auto-completes: OpenClaw npm install, Bailian API config, DingTalk plugin install, gateway startup. Query `DescribeInvocations` to confirm `Gateway started` (poll every 30s, 3-8 min).

---

# Step 5: Acceptance Testing

## 5.1 Verify Gateway Status

```bash
aliyun ecs RunCommand \
  --RegionId ${region} \
  --Type RunShellScript \
  --CommandContent "openclaw gateway status" \
  --InstanceId.1 ${instance_id} \
  --Timeout 60 \
  --user-agent AlibabaCloud-Agent-Skills
```

Confirm the gateway status is `running` and the DingTalk channel plugin is loaded.

## 5.2 Test in DingTalk

Guide the user:
1. Confirm they have completed app creation, permission configuration, publishing, and added the bot to a group per the [DingTalk App Setup Guide](references/dingtalk-setup-guide.md)
2. In the DingTalk group where the bot was added, @mention the bot and send a message (e.g., "Hello, please introduce yourself")
3. Wait for the bot to reply

**Acceptance criteria**: The bot replies normally in the DingTalk group with content generated by the Bailian LLM. This confirms successful deployment.

## 5.3 Deployment Completion Report

After confirming all components are running normally, provide the user with a deployment summary:
- ECS instance ID and EIP public IP
- OpenClaw version and service status
- Bailian model configuration (model name, API endpoint)
- DingTalk app name and bot status
- Cost information

---

## Resource Cleanup

> **Warning**: Resource deletion is irreversible. Always confirm with user before executing.

### Pre-Deletion Checks

Before deletion, prompt user: "The following resources will be permanently deleted: ${instance_id}, ${eip_allocation_id}, ${security_group_id}, ${vswitch_id}, ${vpc_id}. This action is irreversible. Confirm with 'yes' to continue."

Only proceed after explicit "yes" confirmation.

### Deletion Sequence

Delete in dependency order (instance → EIP → security group → VSwitch → VPC):

```bash
# 1. Stop instance if running, then delete
aliyun ecs StopInstance --InstanceId ${instance_id} --user-agent AlibabaCloud-Agent-Skills
# Poll DescribeInstances until Status='Stopped'
aliyun ecs DeleteInstance --InstanceId ${instance_id} --user-agent AlibabaCloud-Agent-Skills

# 2. Release EIP (after confirming unassociated)
aliyun vpc ReleaseEipAddress --RegionId ${region} --AllocationId ${eip_allocation_id} --user-agent AlibabaCloud-Agent-Skills

# 3. Delete security group (after confirming no instances)
aliyun ecs DeleteSecurityGroup --RegionId ${region} --SecurityGroupId ${security_group_id} --user-agent AlibabaCloud-Agent-Skills

# 4. Delete VSwitch then VPC (after confirming empty)
aliyun vpc DeleteVSwitch --VSwitchId ${vswitch_id} --user-agent AlibabaCloud-Agent-Skills
aliyun vpc DeleteVpc --VpcId ${vpc_id} --user-agent AlibabaCloud-Agent-Skills
```

## Cost Impact

- **ECS instance**: 2 vCPU 4 GB (ecs.c6.large) pay-as-you-go, approximately 0.3-0.5 CNY/hour (subject to actual console pricing)
- **EIP bandwidth**: 100 Mbps pay-by-traffic
- **Bailian model calls**: New users have a free quota; charges apply per token usage after exceeding the quota

> Note: The above costs are for reference only. Please refer to the actual pricing and bills shown in the Alibaba Cloud console.

## Common Troubleshooting

| Symptom | Possible Cause | Solution |
|---------|----------------|----------|
| DingTalk bot not responding | Gateway not running | Execute `openclaw gateway status` via Cloud Assistant to check status |
| Reply with "0 characters" empty message | Bailian model config lost | Check if `models.providers` in `~/.openclaw/openclaw.json` contains `alibaba-cloud` |
| 401 error | Gateway Token mismatch | Check if `gateway.auth.token` matches `channels.dingtalk-connector.gatewayToken` |
| AI Card not displaying | Missing card permissions | Add `Card.Streaming.Write` and `Card.Instance.Write` permissions in DingTalk Open Platform |
| npm install timeout | Network issue | Confirm npm China mirror is configured; confirm EIP bandwidth is sufficient |

## Reference Links

| Resource | Link |
|----------|------|
| Bailian API Key Guide | [references/bailian-api-key-guide.md](references/bailian-api-key-guide.md) |
| DingTalk App Setup Guide | [references/dingtalk-setup-guide.md](references/dingtalk-setup-guide.md) |
| Alibaba Cloud Deploy OpenClaw | https://help.aliyun.com/zh/simple-application-server/use-cases/quickly-deploy-and-use-openclaw |
| DingTalk Open Platform ECS Deployment | https://open.dingtalk.com/document/dingstart/deployment-alibaba-cloud-ecs-server |
| OpenClaw Official Website | https://openclaw.ai/ |
| Bailian Console | https://bailian.console.aliyun.com/ |
| DingTalk Open Platform | https://open.dingtalk.com/ |
