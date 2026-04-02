---
name: alibabacloud-tair-devtoolset
description: |
  Alicloud Service Scenario-Based Skill. Create Tair Enterprise Edition instance and configure public network access using Aliyun CLI.
  Triggers: "tair", "create tair instance", "tair instance".
---

# Tair DevToolset — Instance Creation and Public Network Configuration

Automate Tair Enterprise Edition cloud-native instance creation, public network access configuration, and IP whitelist setup using Aliyun CLI.

**Architecture**: `VPC + VSwitch + Tair Enterprise Instance + Public Endpoint`

---

## 1. Installation

> **Pre-check: Aliyun CLI >= 3.3.1 required**
> Run `aliyun version` to verify >= 3.3.1. If not installed or version too low,
> see `references/cli-installation-guide.md` for installation instructions.
> Then [MUST] run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.

```bash
# Verify CLI version
aliyun version

# Enable automatic plugin installation
aliyun configure set --auto-plugin-install true

# Verify jq
jq --version
```

If jq is not installed:
```bash
brew install jq   # macOS
```

---

## 2. Authentication

> **Pre-check: Alibaba Cloud Credentials Required**
>
> All credential configurations follow existing aliyun CLI settings, no separate configuration needed in scripts.
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
> **If no valid profile exists, STOP here.**
> 1. Obtain credentials from [Alibaba Cloud Console](https://ram.console.aliyun.com/manage/ak)
> 2. Configure credentials **outside of this session** (via `aliyun configure` in terminal or environment variables in shell profile)
> 3. Return and re-run after `aliyun configure list` shows a valid profile

---

## 3. RAM Policy

See [references/ram-policies.md](references/ram-policies.md) for RAM permissions required by this Skill.

Core permissions:

| RAM Action | Description |
|-----------|-------------|
| `r-kvstore:CreateTairInstance` | Create Tair instance |
| `r-kvstore:DescribeInstanceAttribute` | Query instance status |
| `r-kvstore:ModifySecurityIps` | Modify IP whitelist |
| `r-kvstore:AllocateInstancePublicConnection` | Allocate public endpoint |
| `r-kvstore:DescribeDBInstanceNetInfo` | Query network info |

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `references/ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

---

## 4. Parameter Confirmation

> **IMPORTANT: Parameter Confirmation** — Before executing any command or API call,
> ALL user-customizable parameters (e.g., RegionId, instance names, CIDR blocks,
> passwords, domain names, resource specifications, etc.) MUST be confirmed with the
> user. Do NOT assume or use default values without explicit user approval.

| Parameter | Required | Description | Default |
|-----------|----------|-------------|---------|
| VPC_ID | **Yes** | VPC ID, e.g. `vpc-bp1xxx` | — |
| VSWITCH_ID | **Yes** | VSwitch ID, e.g. `vsw-bp1xxx` | — |
| REGION_ID | No | Region ID | `cn-hangzhou` |
| ZONE_ID | No | Zone ID | `cn-hangzhou-h` |
| INSTANCE_TYPE | No | Instance series | `tair_rdb` |
| INSTANCE_CLASS | No | Instance specification | `tair.rdb.1g` |
| INSTANCE_NAME | No | Instance name | `tair-benchmark-<timestamp>` |

### Common Specifications

#### Standard Architecture

| InstanceClass | Memory | Bandwidth | Max Connections | QPS Reference |
|---------------|--------|-----------|-----------------|---------------|
| tair.rdb.1g | 1 GB | 768 Mbps | 30,000 | 300,000 |
| tair.rdb.2g | 2 GB | 768 Mbps | 30,000 | 300,000 |
| tair.rdb.4g | 4 GB | 768 Mbps | 40,000 | 300,000 |
| tair.rdb.8g | 8 GB | 768 Mbps | 40,000 | 300,000 |
| tair.rdb.16g | 16 GB | 768 Mbps | 40,000 | 300,000 |
| tair.rdb.24g | 24 GB | 768 Mbps | 50,000 | 300,000 |
| tair.rdb.32g | 32 GB | 768 Mbps | 50,000 | 300,000 |
| tair.rdb.64g | 64 GB | 768 Mbps | 50,000 | 300,000 |

## 5. Core Workflow

> **[MUST] Execution Constraints**
> - **MUST and ONLY** use `scripts/create-and-connect-test.sh` script to complete instance creation, whitelist configuration, public endpoint allocation, etc.
> - **DO NOT** bypass the script to directly call `aliyun r-kvstore` CLI commands for the above operations
> - **DO NOT** write or concatenate aliyun CLI commands to replace script functionality
> - Model's responsibility is: collect parameters → set environment variables → run script. No improvisation allowed.

Set environment variables with collected parameters and run the all-in-one script:

```bash
export VPC_ID="<user-confirmed VPC_ID>"
export VSWITCH_ID="<user-confirmed VSWITCH_ID>"

# Optional parameters
export REGION_ID="cn-hangzhou"
export ZONE_ID="cn-hangzhou-h"
export INSTANCE_TYPE="tair_rdb"
export INSTANCE_CLASS="tair.rdb.1g"
# For NAT environment, manually set public IP
# export MY_PUBLIC_IP="your-public-ip"

bash scripts/create-and-connect-test.sh
```

The script will automatically complete: Create instance → Wait for ready → Configure whitelist → Allocate public endpoint → Get public connection info.

---

## 6. Success Verification

See [references/verification-method.md](references/verification-method.md) for detailed verification steps.

Quick instance status verification:
```bash
aliyun r-kvstore describe-instance-attribute \
  --instance-id "${INSTANCE_ID}" \
  --user-agent AlibabaCloud-Agent-Skills
```

Confirm `InstanceStatus` is `Normal` and public endpoint is allocated.

---

## 7. Troubleshooting

| Issue | Solution |
|-------|----------|
| Connection timeout | Check if whitelist includes current public IP (must be IPv4) |
| Public endpoint empty | Confirm `allocate-instance-public-connection` executed successfully and wait for instance to recover to Normal |

---

## 8. Best Practices

1. Use pay-as-you-go (PostPaid) for testing
2. Only add test machine's public IP to whitelist, follow least privilege principle

---

## 9. Reference Links

| Reference | Description |
|-----------|-------------|
| [references/cli-installation-guide.md](references/cli-installation-guide.md) | Aliyun CLI Installation and Configuration Guide |
| [references/ram-policies.md](references/ram-policies.md) | RAM Permission Policy Document |
| [references/related-commands.md](references/related-commands.md) | Related CLI Commands and Parameters |
| [references/verification-method.md](references/verification-method.md) | Success Verification Method |
| [references/acceptance-criteria.md](references/acceptance-criteria.md) | Acceptance Criteria |
