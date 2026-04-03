---
name: alibabacloud-waf-quick-showcase
description: |
  Solution skill for using WAF to protect web applications on ECS. Used for quickly deploying network environments including VPC, security groups, and ECS instances, and integrating WAF for web application protection.
  Trigger words: "WAF protection", "ECS web protection", "Web Application Firewall", "website security"
---

# Using WAF to Protect Web Applications on ECS

With this skill, you can quickly deploy a complete web application protection solution, including network environment setup, ECS instance creation, sample application deployment, and WAF integration.

## Supported Scenarios

> **This skill supports two usage scenarios**:
> 
> 1. **Quick WAF Protection Experience**: Create VPC, ECS, and WAF from scratch for a complete protection experience
> 2. **Existing WAF Protection Experience**: User already has WAF, create new VPC and ECS to integrate with existing WAF
> 
> **Prohibited Scenario**:
> - **Existing ECS Integration**: Does not support integrating user's existing ECS into WAF
> 
> If the user indicates they have existing ECS and want to integrate it into WAF, respond:
> "This skill is designed for experiencing the complete WAF protection workflow and requires creating new ECS instances. If you want to integrate your existing ECS into WAF, please refer to the Cloud Product Integration feature in the WAF console."

> **CRITICAL: Scenario 1 Resource Creation Rules**
> 
> If the user requests "Quick Experience" (Scenario 1):
> - **VPC**: Create new if quota is sufficient; use existing VPC if quota is full
> - **Must Create New**: VSwitch, Security Group, ECS
> - **WAF Reusable**: If WAF already exists, skip creation and use existing WAF to integrate ECS
> - If creation fails, must stop and inform the user

> **MUST: Scenario 1 Must Check for Existing WAF Instance**
>
> After authentication confirmation and before parameter confirmation, must execute:
> ```bash
> aliyun waf-openapi describe-instance --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills
> ```
>
> - **If valid InstanceId is returned**: Skip WAF creation steps and use this WAF directly to integrate ECS
> - **Prompt**: "Detected that your account already has a WAF instance (InstanceId: [xxx]), will use this instance for protection experience."
> - **If no WAF instance**: Execute Step 4 to create new WAF

### Scenario 2: Existing WAF Protection Experience (Detailed)

> **CRITICAL: Handling Process When User Already Has WAF**
> 
> When the user indicates they have a WAF instance:
> 1. **Ask for WAF Instance ID**: Must first ask for the user's existing WAF instance ID
> 2. **Skip WAF Creation**: **Prohibit** executing `create-postpaid-instance`, directly use the WAF instance ID provided by the user
> 3. **Create New Network and ECS**: Still need to create VPC, VSwitch, Security Group, ECS
> 4. **Integrate Existing WAF**: Use the user's WAF instance ID to execute `sync-product-instance` and `create-cloud-resource`
>
> **Inquiry Prompt**:
> "You already have a WAF instance. Please provide your WAF instance ID (format: waf-cn-xxx), and I will create a new ECS for you and integrate it with your existing WAF for experience."

## Pre-flight Checks (Must Remind Users Before Each Run)

> **IMPORTANT: Must proactively ask and help users complete the following checks before running**
> 
> 1. **CLI Version**: Run `aliyun version` to confirm version >= 3.3.1
> 2. **Authentication Configuration**: Run `aliyun configure list` to confirm authentication status is Valid
> 3. **Auto Plugin**: Run `aliyun configure set --auto-plugin-install true`
> 4. **Account Balance**: Confirm Alibaba Cloud account balance >= 100 CNY

### Authentication Configuration Check (Must Execute)

```bash
aliyun configure list
```

> **Reminder when authentication is valid**:
> "Detected that your current CLI authentication configuration is valid:
> - Authentication Mode: [OAuth/AK/StsToken] | Account: [Profile Name] | Region: [Region]
> 
> Please confirm whether to use the current account for operations? Operations will incur charges."
>
> **MUST: Wait for user confirmation before continuing**
> - **Prohibit**: Executing any resource creation operations before user confirmation
> - **Prohibit**: Any authentication mode (including StsToken) must wait for user confirmation

> **When authentication is invalid**: Run `aliyun configure --mode OAuth` to complete configuration

> **Security Reminder**: Explicitly handling AK/SK credentials is strictly prohibited. This skill only supports OAuth authentication mode.

## Solution Architecture

**Architecture Components**: VPC + VSwitch + Security Group + ECS + WAF 3.0 (Pay-as-you-go)

**Traffic Path**: User Request → WAF 3.0 (Traffic Filtering and Cleaning) → ECS (Web Application)

## Installation and Configuration

For detailed installation steps, see [references/cli-installation-guide.md](references/cli-installation-guide.md)

**Quick Start**:
```bash
# macOS (Homebrew)
brew install aliyun-cli

# Authentication Configuration (OAuth Mode)
aliyun configure --mode OAuth

# Verify Version (must be >= 3.3.1)
aliyun version
```

> **Security Reminder**: Explicitly handling AK/SK credentials is strictly prohibited. This skill only supports OAuth authentication mode.

## Parameter Confirmation

> **MUST: Must confirm parameters before execution**
> 
> **Prohibit**: Directly using default values to execute commands; must confirm parameters with the user first.
>
> **MUST: Input Validation Rules** (Must verify the following formats)
> - **RegionId**: Must match `^[a-z]{2}-[a-z]+-[a-z]\d*$` format (e.g., cn-hangzhou-j)
> - **CidrBlock**: Must be valid CIDR format and within RFC1918 private network segments (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16)
> - **ZoneId**: Must have RegionId as prefix (e.g., cn-hangzhou-j corresponds to cn-hangzhou)
> - **InstanceType**: Must comply with Alibaba Cloud ECS specification naming convention (ecs.[series]-[spec])
> - **InstancePassword**: 8-30 characters, must contain uppercase letters, lowercase letters, and numbers
> - **Security Requirement**: All parameters are prohibited from containing special characters (such as ; | & $ ` \ etc.)

### Parameter Confirmation Prompt (Must Execute)

> After authentication confirmation and before executing any commands, must confirm the following parameters with the user:
>
> **Confirmation Prompt**:
> "Before starting deployment, please confirm the following parameters:
> 
> 1. **Region**: cn-hangzhou (or other regions you prefer, such as cn-shanghai, cn-beijing)
> 2. **VPC CIDR Block**: 192.168.0.0/16
> 3. **Zone**: cn-hangzhou-j
> 4. **ECS Specification**: ecs.e-c1m2.large
> 5. **ECS Password**: Please provide your ECS login password (8-30 characters, containing uppercase letters, lowercase letters, and numbers)
> 
> Do you want to use the above parameters? Or tell me which ones you want to modify."
>
> **MUST: Wait for user confirmation or modification before continuing**
> - Expected user responses: "Confirm", "Yes", "OK", or provide modifications
> - **Prohibit**: Executing any resource creation operations before user confirms parameters
> - **Prohibit**: Auto-generating ECS passwords; passwords must be provided by the user
> - If the user does not provide a password, must ask again and cannot continue
> - If the user wants to modify parameters, record the modifications and confirm again
>
> **MUST: Must reject execution if parameter validation fails**
> - If user-provided parameters do not meet the format requirements, must clearly inform the user and provide correct examples
> - **Prohibit**: Using invalid parameters to execute commands
> - **Prohibit**: Escaping dangerous characters and continuing execution (should directly reject and require user to provide legal parameters)
>
> **MUST: Return Value and Output Desensitization**
> - **In any scenario**, the `--password` parameter value in commands, logs, and error messages displayed to users must be shown as `***` or `[REDACTED]`
> - **CLI Execution Echo**: If CLI output contains plaintext passwords, must replace and desensitize before displaying to users
> - **Error Message Handling**: If error messages may contain passwords, must desensitize before displaying
> - **Prohibited Behaviors**:
>   - Printing complete commands containing plaintext passwords in terminal
>   - Saving plaintext passwords in history records
>   - Leaking plaintext passwords in error logs
> - **Correct Example**:
>   ```bash
>   # Actually executed command (internal)
>   aliyun ecs run-instances --password MyPass@2024 ...
>   
>   # Command displayed to user (desensitized)
>   aliyun ecs run-instances --password *** ...
>   ```

> **MUST: Must use user-confirmed parameters when executing commands**
> - The `cn-hangzhou`, `192.168.0.0/16`, etc. in the command examples below are reference values only
> - **Prohibit**: Directly copying example commands for execution; must replace with actual values confirmed by the user
> - If the user changes the region to cn-shanghai, then all subsequent commands' `--biz-region-id`, `--region`, `--zone-id` must be modified accordingly

### Parameter Description and Validation Rules

| Parameter | Description | Reference Value | Validation Rule |
|-----------|-------------|-----------------|-----------------|
| `RegionId` | Region ID | cn-hangzhou | Format: `^[a-z]{2}-[a-z]+-[a-z]\d*$`, only lowercase letters, hyphens, and numbers allowed |
| `CidrBlock` | VPC CIDR Block | 192.168.0.0/16 | Must be RFC1918 private network segment (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16), mask range /8-/24 |
| `ZoneId` | Zone ID | cn-hangzhou-j | Must have RegionId as prefix, format: `${RegionId}-${letter}` |
| `InstanceType` | ECS Specification | ecs.e-c1m2.large | Format: `ecs.[series]-[spec]`, series such as e, c, g, r, t, etc. |
| `ImageId` | Image ID | aliyun_3_x64_20G_alibase_20240819.vhd | Must end with `.vhd`, comply with Alibaba Cloud image naming convention |
| `InstancePassword` | ECS Login Password | User Provided | 8-30 characters, must contain uppercase letters, lowercase letters, and numbers simultaneously |

> **SHOULD: Special Character Filtering**
> - All parameters are prohibited from containing: `; | & $ \` " ' < > ( ) { } [ ] ! # ~`
> - If the above characters are detected, must reject execution and prompt the user to re-enter

## Core Workflow

### Step 0: Check VPC Quota

> **CRITICAL: Must check quota before creating VPC** (Each account has a maximum of 10 VPCs per region by default)

```bash
aliyun vpc describe-vpcs --biz-region-id cn-hangzhou --page-size 50 --connect-timeout 5 --read-timeout 30 --user-agent AlibabaCloud-Agent-Skills
# Check TotalCount in the response
```
>
> **Idempotency Protection**: Use `--client-token` parameter to ensure multiple executions won't create duplicate resources.

> **Quota Check Result Handling**:
> 
> - **TotalCount < 10**: Quota is sufficient, create new VPC
> - **TotalCount >= 10**: Quota is full, use existing VPC
> 
> **Handling Process When Quota is Full**:
> 1. Select an existing VPC from the response results (prioritize those with names containing "waf" or "test")
> 2. Prompt the user: "Your VPC quota is full, will use existing VPC (VpcId: [xxx]) to continue deployment."
> 3. Create new VSwitch, Security Group, and ECS under this VPC

### Step 1: Create VPC and VSwitch

> **CRITICAL: Failure Handling and Rollback Mechanism**
> 
> If any resource creation fails:
> 1. **Stop Immediately**: Must not continue executing subsequent steps
> 2. **Inform User**: Clearly explain the failure reason (such as insufficient resources, insufficient permissions, insufficient quota, etc.)
> 3. **Prohibit Substitution**: Must not use existing resources instead
> 
> **Failure Prompt**:
> "Sorry, [VPC/ECS/WAF] creation failed, reason: [error message]. Please check and try again."

```bash
# 1.1 Create VPC (Idempotent Operation)
aliyun vpc create-vpc \
  --biz-region-id cn-hangzhou \
  --cidr-block 192.168.0.0/16 \
  --vpc-name VPC_HZ \
  --description "WAF Protection Solution VPC" \
  --connect-timeout 10 --read-timeout 60 \
  --client-token $(uuidgen) \
  --user-agent AlibabaCloud-Agent-Skills

# Save the returned VpcId, e.g., vpc-bp1234567890abcdef

# 1.2 Query VPC Status, Wait Until Status Becomes Available
aliyun vpc describe-vpcs \
  --biz-region-id cn-hangzhou \
  --vpc-id <VpcId> \
  --connect-timeout 5 --read-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills

# 1.3 Create VSwitch (Idempotent Operation)
aliyun vpc create-vswitch \
  --zone-id cn-hangzhou-j \
  --cidr-block 192.168.1.0/24 \
  --vpc-id <VpcId> \
  --vswitch-name vsw_001 \
  --connect-timeout 10 --read-timeout 60 \
  --client-token $(uuidgen) \
  --user-agent AlibabaCloud-Agent-Skills

# Save the returned VSwitchId
```

### Step 2: Create Security Group and Configure Rules

```bash
# 2.1 Create Security Group (Idempotent Operation)
aliyun ecs create-security-group \
  --biz-region-id cn-hangzhou \
  --vpc-id <VpcId> \
  --security-group-name SecurityGroup_1 \
  --security-group-type normal \
  --description "WAF Protection Solution Security Group" \
  --connect-timeout 10 --read-timeout 60 \
  --client-token $(uuidgen) \
  --user-agent AlibabaCloud-Agent-Skills

# Save the returned SecurityGroupId

# 2.2 Add Inbound Rule - Open Port 80
aliyun ecs authorize-security-group \
  --biz-region-id cn-hangzhou \
  --security-group-id <SecurityGroupId> \
  --permissions '[{"Policy":"Accept","Priority":"1","IpProtocol":"TCP","PortRange":"80/80","SourceCidrIp":"0.0.0.0/0"}]' \
  --connect-timeout 10 --read-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills
```

### Step 3: Create ECS Instance

> **CRITICAL: ABSOLUTELY PROHIBITED - Using Existing ECS Instances**
> - **MUST CREATE NEW**: Always create a new ECS instance using `RunInstances`
> - **PROHIBITED**: Discovering and reusing existing ECS instances (e.g., 'Found multiple existing ECS instances... Selected i-bp1xxx')
> - **PROHIBITED**: Saying "I found an existing ECS instance named 'web-server-waf-demo', will use it"
> - **Security Policy**: Even if user has existing ECS instances, the skill MUST create a new one for the WAF protection experience
> - **Correct Behavior**:
>   - ✅ Always execute `aliyun ecs run-instances` to create a new instance
>   - ✅ Use user-provided password for the new instance
>   - ✅ If user asks to use existing ECS, explain: "This skill creates new resources for a complete WAF protection experience"
>
> **Recommended Image IDs** (Avoid Blind Queries):
> - **Alibaba Cloud Linux 3**: `aliyun_3_x64_20G_alibase_20240819.vhd`
> - **Alternative**: `aliyun_3_x64_20G_alibase_20221102.vhd`
> 
> Directly use the above ImageId, no need to call DescribeImages query.
>
> **MUST: Password Desensitization Processing**
> - **Prohibit**: Displaying plaintext passwords in terminal output, log printing, or commands shown to users
> - **Must**: Replace `--password` parameter value with `***` or `[REDACTED]` before displaying
> - **Example**: `--password ***` instead of `--password MyPass@2024`
> - **Security Requirement**: Password is only used in original form when passing to CLI commands; any echo must be desensitized

```bash
# 3.1 Create ECS Instance (Idempotent Operation)
aliyun ecs run-instances \
  --biz-region-id cn-hangzhou \
  --instance-type ecs.e-c1m2.large \
  --image-id aliyun_3_x64_20G_alibase_20240819.vhd \
  --security-group-id <SecurityGroupId> \
  --vswitch-id <VSwitchId> \
  --instance-name web-server \
  --host-name web-server \
  --internet-charge-type PayByTraffic \
  --internet-max-bandwidth-out 5 \
  --system-disk-size 40 \
  --system-disk-category cloud_essd_entry \
  --password <YourPassword> \
  --amount 1 \
  --connect-timeout 10 --read-timeout 120 \
  --client-token $(uuidgen) \
  --user-agent AlibabaCloud-Agent-Skills

# Save the returned InstanceId

# 3.2 Query ECS Status, Wait Until Status Becomes Running
aliyun ecs describe-instances \
  --biz-region-id cn-hangzhou \
  --instance-ids '["<InstanceId>"]' \
  --connect-timeout 5 --read-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills
```

### Step 4: Enable WAF and Integrate ECS

> **⚠️ Integration Reminder**: When integrating WAF, web services may experience brief second-level connection interruptions. It is recommended to perform operations during off-peak business hours.

#### 4.1 Create WAF Pay-as-you-go Instance

```bash
# Create WAF 3.0 Pay-as-you-go Instance (Idempotent Operation)
aliyun waf-openapi create-postpaid-instance \
  --region cn-hangzhou \
  --connect-timeout 10 --read-timeout 60 \
  --client-token $(uuidgen) \
  --user-agent AlibabaCloud-Agent-Skills

# The response result contains InstanceId, please save it
```

> **Idempotency Protection**: Use `--client-token` parameter to ensure multiple executions won't create duplicate resources.

> **Concurrent Scenario Handling**: If creation fails and the error indicates "WAF instance already exists", execute `describe-instance` to query existing instance and use it directly.

> **Authorization Failure Handling**:
> - If HTTP 500 is returned or authorization is required → Prompt user to go to console for authorization
> - **Prompt**: "First-time use of WAF requires completing service linked role authorization in the console. Please visit https://yundun.console.aliyun.com/?p=waf and click 'Create Service Linked Role' to complete authorization."
> - **MUST**: Wait for user to reply "Authorization completed" before retrying creation
> - **Prohibit**: Repeatedly attempting creation before user confirmation

> **Note**: When creating a WAF instance for the first time, you need to complete the service linked role authorization in the console.
> If CLI reports an error indicating authorization is required, please visit [WAF Console](https://yundun.console.aliyun.com/?p=waf) and click "Create Service Linked Role" to complete authorization before trying again.

#### 4.2 Query WAF Instance Information

```bash
# Query WAF Instance Details
aliyun waf-openapi describe-instance \
  --region cn-hangzhou \
  --connect-timeout 5 --read-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills

# Save the returned InstanceId
```

#### 4.3 Sync ECS Assets to WAF

```bash
# Sync ECS, CLB, NLB Assets to WAF
# Note: WAF instance may need to wait about 10 seconds after creation before it can be called normally
aliyun waf-openapi sync-product-instance \
  --instance-id <WAF-InstanceId> \
  --region cn-hangzhou \
  --connect-timeout 10 --read-timeout 60 \
  --user-agent AlibabaCloud-Agent-Skills

# If 503 error is returned, please wait 10 seconds and retry
```

#### 4.4 Integrate ECS into WAF Protection

```bash
# Integrate ECS Instance into WAF, Configure HTTP 80 Port Protection
# Note: Must provide --redirect parameter with ReadTimeout and WriteTimeout
aliyun waf-openapi create-cloud-resource \
  --instance-id <WAF-InstanceId> \
  --biz-region-id cn-hangzhou \
  --listen '{"ResourceProduct":"ecs","ResourceInstanceId":"<ECS-InstanceId>","Port":80,"Protocol":"http"}' \
  --redirect '{"ReadTimeout":120,"WriteTimeout":120}' \
  --connect-timeout 10 --read-timeout 60 \
  --user-agent AlibabaCloud-Agent-Skills
```

#### 4.5 Verify ECS Has Been Integrated into WAF

```bash
# Query Cloud Products List That Have Been Integrated into WAF
aliyun waf-openapi describe-cloud-resources \
  --instance-id <WAF-InstanceId> \
  --resource-product ecs \
  --page-number 1 \
  --page-size 10 \
  --region cn-hangzhou \
  --connect-timeout 5 --read-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills
```

### Completion Prompt

> **IMPORTANT: Must prompt users for next steps after WAF integration is complete**
>
> **Prompt**:
> "WAF has been successfully integrated with ECS! You can proceed with the following operations:
>
> 1. **Deploy Web Application**: Log in to ECS to deploy your web application, or use sample application for testing
> 2. **Verify Protection Effectiveness**: Access ECS public IP to test normal access and attack interception
>
> For detailed verification methods, see [references/verification-method.md](references/verification-method.md)"

## RAM Permission Requirements

For detailed permission list, see [references/ram-policies.md](references/ram-policies.md)

## CLI Support Status

All cloud service operations involved in this skill (VPC, ECS, WAF) support CLI implementation.

**Console Operation Required**: When using WAF for the first time, need to click "Create Service Linked Role" in the console to complete authorization.

For detailed API and CLI command list, see [references/related-apis.md](references/related-apis.md)

## References

- [CLI Installation Guide](references/cli-installation-guide.md) | [RAM Policies](references/ram-policies.md) | [Related APIs](references/related-apis.md)
- [Verification Methods](references/verification-method.md) | [Acceptance Criteria](references/acceptance-criteria.md) | [Official Solution Document](https://www.aliyun.com/solution/tech-solution/web-protection/2714251)
