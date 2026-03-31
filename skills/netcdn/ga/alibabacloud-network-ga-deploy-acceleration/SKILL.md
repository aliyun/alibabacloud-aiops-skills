---
name: alibabacloud-network-ga-deploy-acceleration
description: |
  Deploy acceleration services using Alibaba Cloud Global Accelerator (GA). Applicable to cross-border Web/API acceleration, global gaming acceleration, audio/video transmission acceleration, and more.
  Trigger words: "GA acceleration", "Global Accelerator", "deploy GA", "create GA instance", "GA", "acceleration configuration"
---

# Deploy Acceleration Services with Global Accelerator (GA)

Create a GA instance from scratch and complete end-to-end configuration (Instance -> Acceleration Region -> Listener -> Endpoint Group -> Forwarding Rules) to enable global network acceleration for your services.

## 1. Scenario Overview

### 1.1 Applicable Scenarios

- **Cross-border Web/API acceleration**: Overseas users accessing domestic web services, or domestic users accessing overseas services
- **Global gaming acceleration**: Reduce cross-region latency and improve player experience
- **Audio/video transmission acceleration**: Optimize cross-region real-time audio/video communication
- **Enterprise application acceleration**: Accelerate cross-border enterprise internal system access

### 1.2 Architecture

```
Client -> Accelerated IP/CNAME -> Global Accelerator (GA) -> (Cross-border/Cross-region transit) -> Forwarding Rules -> Endpoint Group -> Origin Server
```

```
                         +---------------------------------------------+
                         |         Client (Acceleration Region)         |
                         +----------------------+----------------------+
                                                |
                                         +------+------+
                                         | Accelerated |
                                         |  IP (by GA) |
                                         +------+------+
                                                |
    +-------------------------------------------+-------------------------------------------+
    |  Global Accelerator (GA)                  |                                           |
    |  +----------------------------------------+----------------------------------------+  |
    |  |  Listener                              |                                        |  |
    |  |  Protocol: HTTPS/HTTP/TCP/UDP          |                                        |  |
    |  |  Port: 443/80/Custom                   |                                        |  |
    |  +----------------------------------------+----------------------------------------+  |
    |                                           |                                           |
    |  +----------------------------------------+----------------------------------------+  |
    |  |  Forwarding Rules                      |                                        |  |
    |  |  HTTP/HTTPS: Route by Host/Path        |  TCP: Route by Host                    |  |
    |  +-------+----------------+---------------+-------------------+--------------------+  |
    |          |                |                                   |                        |
    |  +-------+------+ +------+-------+ +-------------------------+--+                     |
    |  | Endpoint     | | Endpoint     | | Default Endpoint           |                     |
    |  | Group A      | | Group B      | | Group                      |                     |
    |  | api.example  | | web.example  | | (Unmatched rules)          |                     |
    |  | +----------+ | | +----------+ | | +----------+               |                     |
    |  | | ECS/ALB  | | | |  Domain  | | | |  NLB/IP  |              |                     |
    |  | +----------+ | | +----------+ | | +----------+               |                     |
    |  +--------------+ +--------------+ +----------------------------+                     |
    +-----------------------------------------------------------------------------------+
```

**Products involved**: GA + Certificate Management Service (for HTTPS scenarios)

### 1.3 Customer Value

- Leverage the Alibaba Cloud global transmission network to significantly reduce cross-region access latency
- Complete end-to-end configuration in a single session to quickly enable Global Accelerator

---

## 2. Installation

> **Pre-check: Aliyun CLI >= 3.3.1 required**
>
> Run `aliyun version` to verify >= 3.3.1. If not installed or version too low, see `references/cli-installation-guide.md` for installation instructions.
>
> Then **[MUST]** run the following to enable automatic plugin installation:
> ```bash
> aliyun configure set --auto-plugin-install true
> ```

---

## 3. Authentication

> **Pre-check: Alibaba Cloud Credentials Required**
>
> **Security Rules:**
> - **NEVER** read, echo, or print AK/SK values (e.g., `echo $ALIBABA_CLOUD_ACCESS_KEY_ID` is FORBIDDEN)
> - **NEVER** ask the user to input AK/SK directly in the conversation or command line
> - **NEVER** use `aliyun configure set` with literal credential values
> - **ONLY** use `aliyun configure list` to check credential status
>
> ```bash
> aliyun configure list --user-agent AlibabaCloud-Agent-Skills
> ```
> Check the output for a valid profile (AK, STS, or OAuth identity).
>
> **If no valid profile exists, STOP here.**
> 1. Obtain credentials from [Alibaba Cloud Console](https://ram.console.aliyun.com/manage/ak)
> 2. Configure credentials **outside of this session** (via `aliyun configure` in terminal or environment variables in shell profile)
> 3. Return and re-run after `aliyun configure list` shows a valid profile

---

## 4. RAM Policy

This skill requires the following RAM permissions. See `references/ram-policies.md` for the complete list.

---

## 5. GA Service Activation Check

> **Pre-check: GA service must be activated**
>
> Before performing any GA operation, you must confirm that the Global Accelerator service has been activated.
>
> ```bash
> aliyun ga DescribeAcceleratorServiceStatus --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills
> ```
>
> Check the `Status` field in the response:
> - **`Normal`**: The service is activated. Proceed with subsequent steps.
> - **Other statuses**: The service is not activated. Activate it first:
>
> ```bash
> aliyun ga OpenAcceleratorService --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills
> ```
>
> After activation, re-run `DescribeAcceleratorServiceStatus` to confirm the status is `Normal`, then proceed.
> **If the service is not activated and activation fails, STOP here.**

---

## 6. Parameter Confirmation

> **Important: Parameter Confirmation** -- Before executing any command or API call,
> all user-configurable parameters must be confirmed with the user.
> Do not assume or use default values without the user's explicit consent.

| Parameter           | Required    | Description                                        | Default                                          |
| ------------------- | ----------- | -------------------------------------------------- | ------------------------------------------------ |
| AcceleratorName     | Optional    | GA instance name                                   | -                                                |
| AccelerateRegionId  | Required    | Acceleration region ID (region where users access)  | -                                                |
| IspType             | Optional    | ISP line type for the acceleration region           | China (Hong Kong): `BGP_PRO`, Others: `BGP`      |
| Bandwidth           | Required    | Acceleration region bandwidth (Mbps)                | -                                                |
| ListenerProtocol    | Optional    | Listener protocol: `TCP`/`UDP`/`HTTP`/`HTTPS`      | `HTTPS`                                          |
| ListenerPort        | Optional    | Listener port                                       | `443`                                            |
| CertificateId       | Conditional | SSL certificate ID (HTTPS listeners only)           | -                                                |
| EndpointGroupRegion | Required    | Endpoint group region (region of the origin server) | -                                                |
| EndpointType        | Required    | Endpoint type                                       | -                                                |
| Endpoint            | Required    | Endpoint address (IP/domain/instance ID)            | -                                                |
| EndpointPort        | Optional    | Endpoint port                                       | Same as listener port                            |
| CrossBorder         | Required    | Whether cross-border acceleration is involved       | -                                                |
| CrossBorderMode     | Required    | Cross-border mode: `private` or `bgpPro`            | `private` (recommended for production)           |

**Supported endpoint types**: `Domain` (Custom Domain) / `Ip` (Custom IP) / `ECS` / `SLB` (CLB) / `ALB` / `NLB` / `OSS`

---

## 7. Core Workflow

### 7.1 Prerequisites and General Rules

> **Blocking requirement**: Before entering the workflow, you MUST use the Read tool to fully read the following files. No steps may be executed until reading is complete.
> - [references/important-notes.md](references/important-notes.md) -- GA defaults, constraints, and common pitfalls
> - [references/related-apis.md](references/related-apis.md) -- API list and CLI parameter formats

**Scope constraints** (strictly enforced):

- **Instance type and billing restriction**: This skill can ONLY create **pay-as-you-go (postpay) + CDT Standard GA instances**. Creating prepaid (subscription) Standard instances or Basic GA instances of any billing mode is FORBIDDEN. Calling `CreateBasicAccelerator` is FORBIDDEN. If the user requests a prepaid instance or a Basic instance, inform them that this skill does not support it and suggest creating it manually via the [Alibaba Cloud Console](https://ga.console.aliyun.com/).
- **New instances by default**: This skill defaults to creating and configuring **new** GA instances. Modifying, updating, or deleting existing GA instances or their sub-resources (acceleration regions, listeners, endpoint groups, forwarding rules, etc.) is only permitted when the user **explicitly specifies** the target GA instance ID to operate on. Without an explicit user instruction identifying a specific existing instance, all operations MUST target newly created instances only.
- **GA product boundary**: Write operations (create/update/delete) are limited to the GA product only. For all other Alibaba Cloud products and services (e.g., CAS, CMS, ECS, SLB, ALB, NLB, OSS), only **read-only** (Describe/List/Get/Query) operations are permitted. Any non-read-only operation on other products is FORBIDDEN.

**General rules** (apply throughout the entire workflow):

- **User-Agent requirement [MANDATORY]**: ALL `aliyun` CLI commands (including `ga`, `sts`, `cas`, `cms`, and any other Alibaba Cloud service calls) MUST include `--user-agent AlibabaCloud-Agent-Skills`. This flag must be appended to every CLI invocation without exception. Commands missing this flag are non-compliant.
- **Parameter confirmation**: All user-configurable parameters must be confirmed with the user before execution. Do not assume or use default values.
- **Status check**: After each creation step, query the instance status and wait until it becomes `active` before proceeding to the next step.
- **API metadata validation**: Before generating CLI commands, use WebFetch to retrieve API metadata and verify parameter accuracy.
  URL: `https://api.aliyun.com/meta/v1/products/GA/versions/2019-11-20/apis/{api_name}/api.json`

### 7.2 Interaction Flow

```
Step 1: Gather user requirements
  |-- Service type (Web/API/Gaming/Audio-Video, etc.)
  |-- Origin server information (type, region, IP/domain)
  |-- Acceleration region (where users access from)
  |-- Protocol and port (HTTP/HTTPS/TCP/UDP, port number)
  |-- Whether cross-border acceleration is needed
  +-- Certificate information (for HTTPS scenarios)
      |
Step 2: Analyze and recommend configuration
  |-- Call `aliyun ga ListAccelerateAreas --user-agent AlibabaCloud-Agent-Skills` to get supported acceleration regions and available ISP line types
  |-- Analyze requirements based on important-notes.md and GA features
  |-- Match the optimal configuration (billing mode, ISP line type, protocol, endpoint type, etc.)
  |-- [MANDATORY] Billing mode: ALWAYS use pay-as-you-go (postpay) + CDT. Do NOT guide or recommend the user to create prepaid (subscription) instances
  |-- Identify potential issues (cross-border compliance, Proxy Protocol compatibility, HTTP/2 back-to-origin limitations, etc.)
  +-- Output recommended configuration with rationale
      |
Step 3: Format configuration parameters for user confirmation
  |-- Present all configuration objects and parameters in a table
  |   (Instance, cross-border mode, acceleration region, listener, endpoint group, forwarding rules, etc.)
  +-- Wait for user confirmation
      |
Step 4: Iterative adjustments
  |-- Incorporate user feedback and update configuration parameters
  +-- Repeat Step 3 until the user gives final confirmation
      |
Step 5: Generate execution plan
  |-- List each operation in execution order (target object, parameters, CLI command)
  |-- Annotate dependencies between steps (e.g., wait for instance status to become active)
  +-- Use WebFetch to retrieve API metadata and verify all parameter accuracy
      |
Step 6: Present final configuration summary and execution steps
  |-- [MANDATORY] Run `aliyun sts GetCallerIdentity --user-agent AlibabaCloud-Agent-Skills` and display account identity in a table:
  |   - This step is REQUIRED and MUST NOT be skipped under any circumstances
  |   - Parse the response and present it in the following table format:
  |   | Field            | Value                          |
  |   |------------------|--------------------------------|
  |   | AccountId        | (from response)                |
  |   | IdentityType     | (from response)                |
  |   | PrincipalId      | (from response)                |
  |   | Arn              | (from response)                |
  |-- Display a "Final Configuration Summary" table with the following format:
  |   - Table columns MUST be properly aligned using consistent-width separators
  |   - Use fixed-width padding so that all columns line up cleanly in monospace rendering
  |   - Example format (values are illustrative only, actual content is dynamic):
  |
  |   | #  | Resource Object      | Parameter      | Value                |
  |   |----|----------------------|----------------|----------------------|
  |   | 1  | GA Instance          | Name           | my-ga-instance       |
  |   |    |                      | BillingMode    | CDT (pay-as-you-go)  |
  |   | 2  | Acceleration Region  | RegionId       | us-west-1            |
  |   |    |                      | ...            | ...                  |
  |
  |   Rules:
  |   - List each resource object with ALL its confirmed parameters, one parameter per row
  |   - Group rows by resource object (GA Instance, Cross-border Mode, Acceleration Region, Listener, Endpoint Group, Forwarding Rules, etc.)
  |   - Do not omit any confirmed parameter
  |   - The # column only shows the number on the first row of each resource group; subsequent rows leave it blank
  |-- Display an "Execution Steps" table with the following format:
  |   | Step | Operation | API | Depends On | Notes |
  |   |------|-----------|-----|------------|-------|
  |   | (List each operation in execution order based on the actual plan generated in Step 5.)
  |   | (Include dependency references and key notes such as "wait for active", "cross-border only", etc.)
  +-- Wait for user to review and confirm both tables
      |
Step 7: [MANDATORY] Pre-execution validation and user confirmation
  |-- [BLOCKING CHECK] Prepaid (subscription) instance interception:
  |   - Before requesting user confirmation, verify the billing mode in the confirmed configuration
  |   - If the configuration contains prepaid/subscription billing (PREPAY/Subscription),
  |     IMMEDIATELY BLOCK execution and display the following message:
  |     "⚠️ Automatic creation of prepaid (subscription) GA instances is NOT supported by this skill.
  |      Prepaid instances must be created manually via the Alibaba Cloud Console: https://ga.console.aliyun.com/
  |      It is recommended to use the pay-as-you-go (postpay) + CDT billing mode, which charges based on
  |      actual usage and provides better cost-effectiveness and elastic scaling.
  |      To continue, please switch the billing mode to pay-as-you-go + CDT and re-confirm the configuration."
  |   - DO NOT proceed to ask for execution confirmation; return to Step 4 for user to adjust parameters
  |-- DO NOT proceed to execute any commands until the user explicitly confirms
  |-- Present all information from Step 6 and ask the user: "Please confirm to proceed with execution"
  +-- Only after receiving explicit user confirmation (e.g., "确认", "执行", "proceed", "yes"), move to Step 8
      |
Step 8: Execute the plan
  |-- Execute CLI commands in order (see 7.3 API Execution Order)
  |-- [MANDATORY] After EACH step, immediately display the execution result to the user before proceeding:
  |   - Print the current step number, operation name, and execution status (success/failure/waiting)
  |   - On success: show key output fields (e.g., resource ID, status) so the user can track progress
  |   - On waiting: show the current polling status (e.g., "Waiting for instance ga-xxx to become active... current status: configuring")
  |   - On failure: show the full error message, pause, and wait for user decision
  |   - Do NOT batch multiple steps silently — each step must be reported individually and sequentially
  |-- Check the instance status after each creation step (wait for active) before moving to the next
  +-- Pause and report on errors, wait for user decision
      |
Step 9: Configuration verification
  |-- Query instance status and confirm it is active
  |-- Check each created resource (acceleration region, listener, endpoint group, forwarding rules)
  |-- Compare actual configuration against the target parameters confirmed in Step 3
  |-- Check endpoint health status
  |-- [Cross-border scenarios] Perform post-deployment cross-border checks (see 7.4)
  |-- End-to-end connectivity test
  +-- Output verification report (pass/anomalies with recommendations)
```

### 7.3 API Execution Order

Call the following APIs in order to create resources. After each step, wait for the instance status to become `active`:

```
DescribeAcceleratorServiceStatus -> [Status Not Normal] OpenAcceleratorService
    -> CreateAccelerator [pay-as-you-go (postpay) + CDT; do NOT use subscription-based instance specs]
    -> [Cross-border scenarios] UpdateAcceleratorCrossBorderStatus -> UpdateAcceleratorCrossBorderMode -> QueryCrossBorderApprovalStatus
    -> CreateIpSets
    -> CreateListener
    -> CreateEndpointGroup
    -> [Multi-domain scenarios] CreateForwardingRules
    -> [Cross-border scenarios] Post-deployment cross-border checks (see 7.4)
```

### 7.4 Cross-border Configuration Key Points

> **Cross-border mode MUST be set before creating IpSets/Listeners. Do not skip or defer this step.**

**Mode selection:**

| Mode | Description | Applicable Scenario |
| --- | --- | --- |
| `private` (Private cross-border) | Higher quality, lower cost | Recommended for production |
| `bgpPro` (BGP Premium cross-border) | Temporary alternative | Use only when `private` fails due to compliance review |

**Execution steps:**

1. Enable cross-border acceleration: `UpdateAcceleratorCrossBorderStatus`
2. **Immediately** set the cross-border mode: `UpdateAcceleratorCrossBorderMode --CrossBorderMode private`
3. Confirm approval status: `QueryCrossBorderApprovalStatus`

**Fallback handling:**

If switching to `private` fails (e.g., cross-border compliance review has not been approved), inform the user:
*"Switching cross-border mode to `private` is pending compliance approval. Currently using `bgpPro` (BGP Premium).
Please complete the cross-border compliance review, then re-run `UpdateAcceleratorCrossBorderMode --CrossBorderMode private`."*

**Post-deployment check:**

After all resources are created, call `DescribeAccelerator` to check the current cross-border mode. If the mode is not `private`, attempt to switch:

```bash
aliyun ga UpdateAcceleratorCrossBorderMode --region cn-hangzhou --AcceleratorId <ga-id> --CrossBorderMode private --user-agent AlibabaCloud-Agent-Skills
```

If it still fails, inform the user:
*"The current cross-border mode is `bgpPro` (BGP Premium). It is recommended to switch to `private` (Private cross-border) mode after the cross-border compliance review is approved for better performance and stability."*

---

## 8. Verification

### Quick Verification

```bash
# 1. Confirm instance status and cross-border mode
aliyun ga DescribeAccelerator --AcceleratorId <ga-id> --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills

# 2. Confirm acceleration regions and assigned accelerated IP addresses
aliyun ga ListIpSets --AcceleratorId <ga-id> --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills

# 3. Confirm listener status
aliyun ga ListListeners --AcceleratorId <ga-id> --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills

# 4. Confirm endpoint groups and health status
aliyun ga ListEndpointGroups --AcceleratorId <ga-id> --ListenerId <listener-id> --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills
```

### Acceleration Performance Testing

> **Must read**: When performing acceleration performance testing or latency comparison, use the Read tool to read [references/acceleration-test-guide.md](references/acceleration-test-guide.md) and select the appropriate test method based on the listener protocol:
>
> - **HTTP**: curl output `time_connect` / `time_starttransfer` / `time_total`
> - **HTTPS**: curl output `time_connect` / `time_appconnect` / `time_starttransfer` / `time_total`
> - **TCP** (non-HTTP): curl with `telnet://` protocol
> - **UDP**: `scripts/udping.py -c 10 <ip> <port>` -- requires a UDP Echo Server running on the origin server
>
> You must compare **non-accelerated** (direct to origin server) and **accelerated** (through GA) results.

---

## 9. Cleanup

```bash
# Delete the GA instance (associated sub-resources are automatically cleaned up in the background)
aliyun ga DeleteAccelerator --AcceleratorId <ga-id> --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills
```

---

## 10. API and Command Reference

See [references/related-apis.md](references/related-apis.md) for the complete API list and CLI parameter formats.

> **Note**: GA APIs use RPC-style PascalCase naming. Nested array parameters require dot notation + `--method POST --force`.

---

## 11. Important Notes

> **All important operational notes, constraints, defaults, and common pitfalls are maintained in [references/important-notes.md](references/important-notes.md).**
> You must fully read important-notes.md before starting the deployment workflow. It contains critical information on billing, cross-border configuration, status management, and parameter formats that directly affect deployment success.

---

## 12. Best Practices

1. **Gather before configuring** -- Fully understand the business requirements before planning configuration
2. **Confirm all parameters** -- All user-configurable parameters must be confirmed before execution
3. **Check status after each step** -- After each creation operation, wait for the instance status to become `active`
4. **Prefer private cross-border mode** -- Use `private` mode whenever possible for cross-border scenarios
5. **Isolate endpoint groups** -- Use separate endpoint groups + forwarding rules for different domains/services
6. **Verify after deployment** -- Perform end-to-end configuration verification and connectivity testing after deployment

---

## 13. Reference Documents

| Document                                                                       | Description                                     |
| ------------------------------------------------------------------------------ | ----------------------------------------------- |
| [references/important-notes.md](references/important-notes.md)                 | **Must read** -- GA defaults and common pitfalls |
| [references/related-apis.md](references/related-apis.md)                       | API and CLI command reference                    |
| [references/ram-policies.md](references/ram-policies.md)                       | RAM permission policies                          |
| [references/acceleration-test-guide.md](references/acceleration-test-guide.md) | Acceleration performance testing guide           |
| [GA Official Documentation](https://help.aliyun.com/zh/ga/)                    | Global Accelerator official documentation        |
| [GA OpenAPI Explorer](https://api.aliyun.com/product/Ga)                       | Online API debugging                             |
