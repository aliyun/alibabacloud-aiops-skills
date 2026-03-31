---
name: alibabacloud-network-eip-associate
description: |
  Allocate Elastic IP Address (EIP) and bind to existing Alibaba Cloud resources.
  Supports ECS instances, ENI, CLB, NAT Gateway, HAVIP, and IP addresses.
  Focus: EIP product capabilities only - allocation, binding, verification, and cleanup.
  Triggers: "EIP bind", "elastic IP associate", "allocate EIP", "bind EIP to ECS/NAT/CLB"
---

# Allocate and Bind EIP to Existing Cloud Resources
## Scenario Description
Allocate Elastic IP Address (EIP) and bind it to **existing** Alibaba Cloud resources for public internet access. This skill focuses on EIP product capabilities only.
**Supported Resource Types:**
- **EcsInstance**: ECS instance (requires instance ID)
- **NetworkInterface**: Elastic Network Interface/ENI (requires ENI ID + private IP address)
- **SlbInstance**: Classic Load Balancer/CLB (requires CLB instance ID)
- **Nat**: NAT Gateway (requires NAT Gateway ID)
- **HaVip**: High-Availability Virtual IP (requires HaVip ID)
- **IpAddress**: Direct IP address binding (requires VPC ID + IP address)
**Key Principles:**
1. ✅ **Only operate on user-provided resource IDs** - never query or auto-select resources
2. ✅ **Fail fast** - stop immediately on unrecoverable errors
3. ✅ **No resource creation** - only bind to existing resources (no new ECS/NAT/VPC creation)
4. ✅ **User confirmation** - ask for key EIP parameters before allocation
5. ✅ **Cleanup on failure** - release newly allocated EIPs if binding fails

## Pre-checks
### 1. Aliyun CLI version verification (>= 3.3.2)
```bash
aliyun configure set --auto-plugin-install true
CLI_VERSION=$(aliyun version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
[ "$(printf '%s\n' "3.3.2" "$CLI_VERSION" | sort -V | head -n1)" != "3.3.2" ] && echo "❌ CLI < 3.3.2" && exit 1
```
### 2. Authentication credential verification
```bash
aliyun configure list  # Check valid profile (AK/STS/OAuth). NEVER echo AK/SK.
```

## Workflow Overview
**Key rules for ALL commands below:**
- Every `aliyun` product command MUST include `--user-agent AlibabaCloud-Agent-Skills` (NOT on `configure` commands)
- Use plugin mode (kebab-case): `aliyun vpc allocate-eip-address`, NOT `AllocateEipAddress`
- VPC commands require `--biz-region-id <Region>`
- **CRITICAL: `--biz-region-id` only sets the RegionId parameter in the API request body; it does NOT control which API endpoint the CLI connects to.** The API endpoint is determined by the CLI profile's configured region. Before running any VPC command, you MUST set the CLI profile region to match the target region:
  ```bash
  aliyun configure set --region {REGION}
  ```
- `jq` is NOT available — use `grep` to parse JSON output
**Global Variables to Track:**
- `CREATED_EIPS`: Array of EIP AllocationIds created in this session (for user-controlled cleanup on failure)
- `REGION`: Target region (MUST be explicitly provided by user, no default)
- `INSTANCE_TYPE`: Target resource type (EcsInstance/NetworkInterface/SlbInstance/Nat/HaVip/IpAddress)
- `USE_EXISTING_EIP`: Boolean flag (true = use existing EIP, false = create new EIP)
- `ALLOCATION_ID`: EIP instance ID (from existing EIP or newly allocated)
**Workflow Phases:**
1. **Phase 1**: Extract user input, validate resource, choose existing/new EIP
   - Steps 1.1-1.2: Extract parameters, set CLI region
   - Step 1.3: Check if resource already has EIP bound (DescribeEipAddresses)
   - Step 1.3.5: Check if ECS has PIP/Public IP (ECS only, DescribeInstanceAttribute)
   - Step 1.4: User chooses existing EIP or new EIP
   - Step 1.5: Use existing EIP (query available EIPs, let user select)
   - Step 1.6: Create new EIP (confirm parameters)
   - Step 1.7: Pre-allocation validation (only for new EIP)
2. **Phase 2**: Allocate EIP (only if `USE_EXISTING_EIP = false`)
3. **Phase 3**: Bind EIP to target resource (actual execution)
4. **Phase 4**: Verify binding
5. **Phase 5**: Cleanup on failure (ask user to keep or release newly created EIP)

## Phase 1: Extract User Input and Validate Resource
### Step 1.1: Extract required parameters from user message
**Required from user:**
- **Region**: Target region (e.g., `cn-beijing`, `cn-hangzhou`) - **MUST be explicitly provided, no default**
- **Resource Type**: One of: ECS / ENI / CLB / NAT / HAVIP / IP
- **Resource ID**: Exact instance ID, ENI ID, NAT ID, etc.
- **Additional parameters (instance-type specific):**
  - If `NetworkInterface`: Must have `PrivateIpAddress` (private IP to bind)
  - If `IpAddress`: Must have `VpcId` (VPC ID where IP address resides)
**If ANY required parameter is missing, STOP and ask user:**
```
❌ Missing: Region[REQUIRED] | ResourceType[ECS/ENI/CLB/NAT/HAVIP/IP] | ResourceID | [PrivateIP for ENI] | [VpcId for IP]
```
**CRITICAL:**
- **Region MUST be explicitly provided by user. Do NOT use default region (like cn-hangzhou).**
- Do NOT proceed without explicit user-provided values.

### Step 1.1.1: Input Validation (Security)
**Validate inputs to prevent command injection:**
- **Region:** `^[a-z]{2,3}-[a-z]+-\d*[a-z]*$` (e.g., cn-beijing, ap-southeast-1)
- **Resource IDs:** `^(i|eni|lb|ngw|havip|eip|vpc)-[a-z0-9]+$`
- **IP Address:** `^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$`
**If validation fails, STOP:** `❌ Invalid input format`

### Step 1.2: Set CLI region to target region
**Before any API operation, configure CLI region:**
```bash
aliyun configure set --region {REGION}
```
This ensures the CLI connects to the correct regional API endpoint.

### Step 1.3: Check if resource already has EIP bound
**Use DescribeEipAddresses to check if the target resource already has an EIP:**
**Map user input to InstanceType parameter:**
| User Input | AssociatedInstanceType Value |
|------------|------------------------------|
| ECS        | EcsInstance                  |
| ENI        | NetworkInterface             |
| CLB        | SlbInstance                  |
| NAT        | Nat                          |
| HAVIP      | HaVip                        |
| IP         | IpAddress                    |
**Query command:**
```bash
aliyun vpc describe-eip-addresses \
  --biz-region-id {REGION} \
  --associated-instance-type {INSTANCE_TYPE} \
  --associated-instance-id {RESOURCE_ID} \
  --user-agent AlibabaCloud-Agent-Skills
```
**Check response:**
**If `TotalCount > 0` (resource already has EIP bound):**
```
❌ ERROR: Resource {RESOURCE_ID} already has EIP bound.
Existing EIP: {EipAddress} | ID: {AllocationId} | Bandwidth: {Bandwidth}Mbps | Status: {Status}
To bind a different EIP, first unbind existing: aliyun vpc unassociate-eip-address --biz-region-id {REGION} --allocation-id {AllocationId} --instance-id {RESOURCE_ID} --instance-type {INSTANCE_TYPE}
```
**STOP. Do not proceed.**
**If `TotalCount = 0` (resource has no EIP bound):**
```
✅ Resource {RESOURCE_ID} has no EIP bound. Proceeding to next validation...
```
**Continue to Step 1.3.5.**

### Step 1.3.5: Check if ECS instance has PIP (Public IP) - ECS Only
> **This step is ONLY executed when `INSTANCE_TYPE = EcsInstance`.**
> **For other resource types (ENI, CLB, NAT, HAVIP, IP), skip directly to Step 1.4.**
**Purpose:** Check if the ECS instance already has a Public IP (PIP) assigned at creation time. PIP is different from EIP:
- **EIP (Elastic IP)**: Can be dynamically bound/unbound to resources
- **PIP (Public IP)**: Fixed public IP assigned when ECS is created, released when ECS is deleted, cannot be unbound
**Query command:**
```bash
aliyun ecs describe-instance-attribute \
  --instance-id {RESOURCE_ID} \
  --user-agent AlibabaCloud-Agent-Skills
```
**Parse response and check `PublicIpAddress` field:**
**Case 1: `PublicIpAddress.IpAddress` is not empty (ECS has PIP):**
```
❌ ERROR: ECS instance {RESOURCE_ID} already has a Public IP (PIP) assigned.
Public IP: {PublicIpAddress.IpAddress[0]} | Type: PIP (fixed, created with ECS)

⚠️ You CANNOT bind an EIP to an ECS instance that already has a PIP.
Options:
1. Use the existing Public IP (no action needed)
2. Convert PIP to EIP (requires ECS Stopped): aliyun vpc convert-nat-public-ip-to-eip --biz-region-id {REGION} --instance-id {RESOURCE_ID}
3. Release and recreate ECS without PIP
Operation stopped.
```
**STOP. Do not proceed.**
**Case 2: `PublicIpAddress.IpAddress` is empty (no PIP):**
```
✅ ECS instance {RESOURCE_ID} has no Public IP (PIP). Ready to bind EIP.
```
**Continue to Step 1.4.**
**Case 3: API call fails (e.g., InvalidInstanceId.NotFound):**
```
❌ ERROR: ECS instance {RESOURCE_ID} not found in region {REGION}.
Error: {ERROR_CODE} - {ERROR_MESSAGE}
Please verify: instance ID, region, and permissions.
```
**STOP. Do not proceed.**

### Step 1.4: Choose between existing EIP or new EIP
```
Options for {RESOURCE_TYPE} {RESOURCE_ID}:
A) Use existing EIP (query available or provide ID)
B) Create new EIP (configure bandwidth, ISP, billing)
Choice (A/B):
```
**If user selects Option A (use existing EIP), proceed to Step 1.5.**
**If user selects Option B (create new EIP), proceed to Step 1.6.**

### Step 1.5: Use Existing EIP (Option A)
#### Step 1.5.1: Ask if user has specific EIP ID
```
Have specific EIP ID? (yes: provide ID / no: query available)
```
**If user provides EIP ID:**
- Save as `ALLOCATION_ID`
- Validate EIP exists and is Available (query with DescribeEipAddresses)
- If EIP not found or not Available, show error and ask again
- **Skip to Phase 3 (bind existing EIP)**
**If user wants to see available EIPs, proceed to Step 1.5.2.**

#### Step 1.5.2: Query available EIPs

Query all Available EIPs in the region:
```bash
aliyun vpc describe-eip-addresses \
  --biz-region-id {REGION} \
  --status Available \
  --page-size 100 \
  --user-agent AlibabaCloud-Agent-Skills
```
**Handle pagination if needed:**
- If `TotalCount > 100`, make multiple requests with `--page-number 2, 3, ...` until all Available EIPs are retrieved
- Collect all Available EIPs across all pages
**If no available EIPs found (`TotalCount = 0`):**
```
❌ No available EIPs in {REGION}. Create new EIP? (yes/no)
```
**If user says yes, go to Step 1.6. If no, STOP.**
**If available EIPs found:**

#### Step 1.5.3: Present available EIPs to user
**If 5 or fewer:** Show all. **If >5:** Show 5 random.
```
Found {TOTAL_COUNT} available EIP(s) in {REGION}:
1. eip-bp1xxx | 47.1.2.3 | 5Mbps | BGP | PayByTraffic
2. eip-bp1yyy | 47.4.5.6 | 10Mbps | BGP | PayByBandwidth
...
Select: Enter number (1-5), EIP ID, or "new" for new EIP:
```
**Wait for user selection.**
**Validate user selection:**
- If user enters number: Map to corresponding EIP from the list
- If user enters EIP ID: Validate it's in the Available state
- If user types "new": Go to Step 1.6
- If invalid input: Ask again
**Save selected EIP's `AllocationId`.**
**Set `USE_EXISTING_EIP = true` (to skip EIP allocation in Phase 2).**
**Skip to Phase 3 (bind existing EIP).**

### Step 1.6: Create New EIP (Option B)
Ask user for EIP configuration:
```
Create new EIP in {REGION} for {RESOURCE_TYPE} {RESOURCE_ID}.
Config (Enter for defaults): Bandwidth[5Mbps] | ISP[BGP/BGP_PRO] | Billing[PayByTraffic/PayByBandwidth] | Purpose[optional for naming]
```
**Defaults:** BANDWIDTH=5, ISP=BGP, INTERNET_CHARGE_TYPE=PayByTraffic
**EIP Naming:** If purpose provided, generate name: `eip-{purpose}-{resource_type}` (e.g., `eip-web-ecs`)
**Set `USE_EXISTING_EIP = false` (will allocate new EIP in Phase 2).**
**IMPORTANT: Always create PayByTraffic (pay-by-traffic) EIP by default unless user explicitly requests PayByBandwidth.**
**IMPORTANT: PrePaid (subscription/包年包月) EIP is NOT supported by this skill. If user requests PrePaid EIP, respond:**
```
❌ This skill does not support creating PrePaid (subscription) EIPs.
Please create PrePaid EIPs through the Alibaba Cloud Console: https://vpc.console.aliyun.com/eip
```
**STOP. Do NOT proceed.**
**Continue to Phase 1.7 (pre-allocation validation) if creating new EIP.**

### Step 1.7: Pre-Allocation Validation (Only for New EIP)
> **This step is ONLY executed when `USE_EXISTING_EIP = false` (creating new EIP).**
> **If using existing EIP, skip directly to Phase 3.**

#### Step 1.7.1: Check EIP quota
Query EIP count: `aliyun vpc describe-eip-addresses --biz-region-id {REGION} --page-size 100`
If approaching 20 (standard limit), show quota warning. This is a soft check.

#### Step 1.7.2: Validate target resource (best-effort)
**For EcsInstance:** `aliyun ecs describe-instances --instance-ids '["ID"]'`
- Status != Running/Stopped: warning
- PublicIpAddress non-empty: STOP (PIP conflict)
**For NetworkInterface (ENI):** `aliyun ecs describe-network-interfaces --network-interface-id '["ID"]'`
- Validate PrivateIpAddress exists in PrivateIpSets. STOP if not found.
**For SlbInstance (CLB):** `aliyun slb describe-load-balancer-attribute --load-balancer-id ID`
- AddressType=internet: STOP (PIP conflict). AddressType=intranet: proceed.
**For Nat:** `aliyun vpc describe-nat-gateways --nat-gateway-id ID`
**For HaVip:** `aliyun vpc describe-havips --havip-id ID`
**For IpAddress:** `aliyun vpc describe-vpcs --vpc-id ID`
**Note:** If resource not found, STOP before Phase 2.

#### Step 1.7.3: Summary of validation results

Show user a summary:
```
✅ Pre-allocation validation passed!
Region: {REGION} | Target: {INSTANCE_TYPE} {RESOURCE_ID} | Status: {STATUS}
EIP Config: {BANDWIDTH}Mbps | {ISP} | {INTERNET_CHARGE_TYPE} [Name: {EIP_NAME}]
Proceeding to allocate EIP...
```
## Phase 2: Allocate EIP (Only for New EIP)
> **This phase is ONLY executed when `USE_EXISTING_EIP = false` (creating new EIP).**
> **If using existing EIP (`USE_EXISTING_EIP = true`), skip directly to Phase 3 (bind).**

### Step 2.1: Allocate EIP with user-confirmed parameters
**Generate ClientToken for idempotency (prevents duplicate EIP on retry):**
```bash
CLIENT_TOKEN=$(uuidgen | tr -d '-' | head -c 32)
```
**Build command dynamically:**
```bash
aliyun vpc allocate-eip-address \
  --biz-region-id {REGION} \
  --bandwidth {BANDWIDTH} \
  --isp {ISP} \
  --internet-charge-type {INTERNET_CHARGE_TYPE} \
  --client-token $CLIENT_TOKEN \
  [--name "{EIP_NAME}"] \
  --user-agent AlibabaCloud-Agent-Skills
```
**Notes:**
- `--client-token` ensures idempotency: same token within 10min returns same EIP
- Only include `--name` parameter if `EIP_NAME` is not empty
- Default to `--internet-charge-type PayByTraffic` (pay-by-traffic)
**Extract from response:**
- `AllocationId`: EIP instance ID (e.g., `eip-bp1xxx`)
- `EipAddress`: Public IP address (e.g., `47.1.2.3`)
**Save to tracking variable:**
```
CREATED_EIPS.append(AllocationId)
```
### Step 2.2: Handle allocation errors (Fail Fast)
**If `QuotaExceeded.Eip`:** STOP. List current EIPs if user wants.
**Other errors (InvalidParameter, InsufficientBalance):** STOP immediately.

### Step 2.3: Wait for EIP to become Available
Query EIP status with **maximum 30 retries** (5s interval = 150s total):
```bash
for i in {1..30}; do
  aliyun vpc describe-eip-addresses \
    --biz-region-id {REGION} \
    --allocation-id {ALLOCATION_ID} \
    --user-agent AlibabaCloud-Agent-Skills

  # Check if Status = "Available"
  # If Available: break
  # If not: sleep 5 seconds and retry
done
```
**If status is NOT "Available" after 30 retries:**
```
❌ ERROR: EIP {ALLOCATION_ID} not Available after 150s. Status: {CURRENT_STATUS}. Cleaning up...
```
**Trigger cleanup (go to Phase 4: Cleanup on Failure).**

### Step 2.4: Show allocated EIP information
```
✅ EIP allocated successfully!
EIP: {EipAddress} | ID: {AllocationId} | {BANDWIDTH}Mbps | {ISP} | {INTERNET_CHARGE_TYPE}
Proceeding to bind to {RESOURCE_TYPE} {RESOURCE_ID}...
```
## Phase 3: Bind EIP to Target Resource
### Step 3.1: Build AssociateEipAddress command
**Base command structure:**
```bash
aliyun vpc associate-eip-address \
  --biz-region-id {REGION} \
  --allocation-id {ALLOCATION_ID} \
  --instance-id {RESOURCE_ID} \
  --instance-type {INSTANCE_TYPE} \
  [--private-ip-address {PRIVATE_IP}] \
  [--vpc-id {VPC_ID}] \
  --user-agent AlibabaCloud-Agent-Skills
```
**Instance Type Mapping:**
| User Input | CLI --instance-type Value | Additional Required Params |
|------------|---------------------------|----------------------------|
| ECS        | EcsInstance               | None |
| ENI        | NetworkInterface          | --private-ip-address (REQUIRED) |
| CLB        | SlbInstance               | None |
| NAT        | Nat                       | None |
| HAVIP      | HaVip                     | None |
| IP         | IpAddress                 | --vpc-id (REQUIRED) |
**Validation before execution:**
- If `INSTANCE_TYPE = NetworkInterface` and `PRIVATE_IP` is empty: **ERROR** - PrivateIpAddress REQUIRED. STOP.
- If `INSTANCE_TYPE = IpAddress` and `VPC_ID` is empty: **ERROR** - VpcId REQUIRED. STOP.

### Step 3.2: Execute binding
Execute the constructed command.
**Success response:** Extract `RequestId` and proceed to verification.

### Step 3.3: Handle binding errors (Fail Fast)
**Common binding errors:**
| Error Code | Meaning | Action |
|------------|---------|--------|
| `EIP_CAN_NOT_ASSOCIATE_WITH_PUBLIC_IP` | ECS already has system-assigned public IP (PIP) | **STOP. Show error. Trigger cleanup.** PIP and EIP are mutually exclusive. |
| `InvalidInstance.NotExist` | Resource ID does not exist (ECS) | **STOP. Show error. Trigger cleanup.** |
| `InvalidInstanId.NotFound` | Resource ID does not exist (CLB/SLB) | **STOP. Show error. Trigger cleanup.** |
| `ResourceNotFound.NetworkInterface` | ENI does not exist | **STOP. Show error. Trigger cleanup.** |
| `InvalidParams.NotFound` | NAT/HAVIP does not exist | **STOP. Show error. Trigger cleanup.** |
| `InvalidAssociation.Duplicated` | Resource already has EIP bound | **STOP. Show error. Trigger cleanup.** |
| `IncorrectEipStatus` | EIP status not ready | Retry up to 3 times (wait 5s between retries). If still fails, **STOP and trigger cleanup.** |
| `InvalidParameter.*` | Invalid parameter value | **STOP. Show error. Trigger cleanup.** |
**Error message template:**
```
❌ ERROR: Failed to bind EIP to {RESOURCE_TYPE} {RESOURCE_ID}
Error: {ERROR_CODE} - {ERROR_MESSAGE}
Possible causes: Resource not exist, already has EIP bound, wrong state, invalid parameters.
Cleaning up...
```
**Trigger cleanup (Phase 4).**
**CRITICAL: Do NOT retry indefinitely. Do NOT query resources to "fix" the issue. Fail fast and cleanup.**

## Phase 4: Verify Binding
### Step 4.1: Query EIP status to confirm binding
Wait briefly (5 seconds), then query:
```bash
aliyun vpc describe-eip-addresses \
  --biz-region-id {REGION} \
  --allocation-id {ALLOCATION_ID} \
  --user-agent AlibabaCloud-Agent-Skills
```
**Expected response:**
- `Status`: `InUse`
- `InstanceType`: Matches `{INSTANCE_TYPE}`
- `InstanceId`: Matches `{RESOURCE_ID}`
**If verification passes:**
```
✅ SUCCESS: EIP binding completed!
EIP: {EipAddress} | ID: {AllocationId} | Bound to: {INSTANCE_TYPE} {RESOURCE_ID} | Region: {REGION} | Status: InUse
```
**Remove from cleanup tracking:**
```
CREATED_EIPS.remove(AllocationId)  # Binding successful, no cleanup needed
```
**If verification fails (Status != InUse or wrong InstanceId):**
```
⚠️ WARNING: Binding command succeeded but verification failed.
Expected: Status=InUse, InstanceId={RESOURCE_ID}
Actual: Status={ACTUAL_STATUS}, InstanceId={ACTUAL_INSTANCE_ID}
Please check EIP status manually in Console.
```
**Do NOT trigger cleanup in this case** (binding may be in progress).

## Phase 5: Cleanup on Failure
> **This phase is ONLY executed when an unrecoverable error occurs during Phase 2 or Phase 3.**
> **IMPORTANT: Only applies to newly created EIPs (`USE_EXISTING_EIP = false`). Do NOT release user's existing EIPs.**

### Step 5.1: Ask user about cleanup
**If binding failed and `CREATED_EIPS` is not empty (newly created EIP in this session):**

List the newly created EIPs:
```bash
aliyun vpc describe-eip-addresses \
  --biz-region-id {REGION} \
  --allocation-id {ALLOCATION_ID} \
  --user-agent AlibabaCloud-Agent-Skills
```
Show user the information and ask:
```
❌ ERROR: EIP binding failed. Error: {ERROR_CODE} - {ERROR_MESSAGE}
Newly Created EIP: {EipAddress} | ID: {AllocationId} | {BANDWIDTH}Mbps | {ISP}
⚠️ This EIP was created but binding failed.
Options: A) Keep EIP (bind later) | B) Release EIP (avoid charges)
Your choice (A/B):
```
**Wait for user decision.**

### Step 5.2: Execute cleanup if user chooses to release
**If Option B:** Check EIP status, unbind if InUse, then release:
```bash
# If InUse: aliyun vpc unassociate-eip-address --allocation-id {ALLOCATION_ID} --instance-id {INSTANCE_ID} --instance-type {INSTANCE_TYPE}
# Release: aliyun vpc release-eip-address --allocation-id {ALLOCATION_ID}
```
**Success:** `✅ Released EIP {AllocationId}`
**Fail:** `❌ CLEANUP FAILED - Manually release via Console`

### Step 5.3: If user chooses to keep EIP
**If user chooses Option A (keep EIP):**
```
✅ EIP {AllocationId} ({EipAddress}) kept. Bind later with: aliyun vpc associate-eip-address --allocation-id {AllocationId} --instance-id <ID> --instance-type <TYPE>
```
### Step 5.4: Final summary
```
Operation aborted. Binding: Failed | Error: {ERROR_CODE} | EIP: {AllocationId} | Cleanup: [Kept/Released]
```
## Error Recovery Reference
| Error Code | Action |
|------------|--------|
| `QuotaExceeded.Eip` | STOP. User resolves quota manually. |
| `EIP_CAN_NOT_ASSOCIATE_WITH_PUBLIC_IP` | STOP. ECS has PIP (caught in Step 1.7.2). |
| `InvalidInstance.NotExist`, `InvalidInstanId.NotFound`, `ResourceNotFound.*`, `InvalidParams.NotFound` | STOP. Resource not found. |
| `InvalidAssociation.Duplicated` | STOP. Already has EIP. |
| `IncorrectEipStatus` | Retry 3x (5s wait), then STOP. |
| `InvalidParameter.*` | STOP. Invalid parameters. |
| `InsufficientBalance` | STOP. No cleanup (allocation failed). |
**Fail Fast**: STOP on unrecoverable errors, ask user for cleanup decision.

## Best Practices
1. **Region Must Be Explicit**: No default region
2. **Pre-check EIP Binding**: DescribeEipAddresses before proceeding
3. **Pre-check ECS PIP**: DescribeInstanceAttribute for ECS
4. **PIP vs EIP**: Mutually exclusive (PIP fixed, EIP dynamic)
5. **User Choice**: Existing EIP or new EIP
6. **User-Controlled Cleanup**: ASK user, never auto-release
7. **Only Cleanup New EIPs**: Never release pre-existing EIPs
8. **Default PayByTraffic**: Unless user requests PayByBandwidth. **PrePaid (subscription) is NOT supported.**
9. **30 Retry Limit**: 150s total for status checks
10. **Security**: Never read/echo AK/SK values


## Reference Documentation
| Document | Description |
|----------|-------------|
| [references/cli-commands.md](references/cli-commands.md) | CLI command examples for all EIP operations |
| [AssociateEipAddress API](https://api.aliyun.com/document/Vpc/2016-04-28/AssociateEipAddress) | Official API documentation for EIP binding |
| [references/related-apis.md](references/related-apis.md) | Related APIs & CLI commands |
| [references/ram-policies.md](references/ram-policies.md) | RAM permission policies |
| [references/acceptance-criteria.md](references/acceptance-criteria.md) | Acceptance test criteria |
