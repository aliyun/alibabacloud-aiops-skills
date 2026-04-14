---
name: alibabacloud-sas-install-agent
description: >
  Alibaba Cloud Security Center (SAS) agent onboarding and management assistant.
  Use this skill when the user wants to onboard servers to Security Center,
  install the security agent, deploy cloud security protection, connect via proxy,
  troubleshoot agent offline or installation failures, create image templates
  with pre-installed agent, view Security Center version and expiration,
  check authorization quota, upgrade or switch server protection versions,
  toggle pay-as-you-go feature modules, uninstall the Security Center agent
  from a server, find servers with specific software installed (e.g. Nginx,
  MySQL, Redis), or detect security risks (vulnerability scanning, baseline
  checks, security alert queries).
---

# Security Center Agent Onboarding and Management

Manage Alibaba Cloud Security Center agent installation, version authorization, asset queries, and security risk detection via the `aliyun` CLI.

**Architecture**: `Security Center (SAS) + ECS + Cloud Assistant + Proxy Cluster (optional)`

Execution model: read operations execute directly (ReAct), write operations display details and require user confirmation before execution (Command). Keep analysis concise -- output a brief reasoning for each action.

> **Pre-check: Aliyun CLI >= 3.3.1 required**
> Run `aliyun version` to verify >= 3.3.1. If not installed or version too low,
> see `references/cli-installation-guide.md` for installation instructions.
> Then [MUST] run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.

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
> **If no valid profile exists, STOP here.**
> 1. Obtain credentials from [Alibaba Cloud Console](https://ram.console.aliyun.com/manage/ak)
> 2. Configure credentials **outside of this session** (via `aliyun configure` in terminal or environment variables in shell profile)
> 3. Return and re-run after `aliyun configure list` shows a valid profile

## Security Guidelines

- Never expose sensitive information (AccessKey, passwords) in output, because leaking credentials could compromise the account
- Never call any Delete-class API, because delete operations are irreversible and may disrupt protection
- Write operations (create install codes, create clusters, install proxies, run commands via cloud assistant, bind authorization, modify switches) must display operation details and wait for user confirmation before execution, because these operations modify live resources
- Display the full command content before dispatching commands via cloud assistant, because executing arbitrary commands on production servers is high-risk

## RAM Policy

Detailed permissions required by this skill: `references/ram-policies.md`

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `references/ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

> **IMPORTANT: Parameter Confirmation** — Before executing any command or API call,
> ALL user-customizable parameters (e.g., RegionId, instance names, CIDR blocks,
> passwords, domain names, resource specifications, etc.) MUST be confirmed with the
> user. Do NOT assume or use default values without explicit user approval.

---

## Tool Inventory

All APIs are invoked via the `aliyun` CLI. Every `aliyun` command MUST include `--user-agent AlibabaCloud-Agent-Skills`.

| CLI Command | Purpose |
|-------------|---------|
| `aliyun sas describe-cloud-center-instances` | Query server client status by instance ID/IP |
| `aliyun ecs describe-instances` | Query ECS instance info and running status |
| `aliyun ecs describe-cloud-assistant-status` | Check if cloud assistant is online |
| `aliyun ecs run-command` | Remote install command execution (write) |
| `aliyun ecs invoke-command` | Trigger existing command on instances (write) |
| `aliyun ecs describe-invocation-results` | Query command execution results |
| `aliyun sas refresh-assets` | Sync latest asset data |
| `aliyun sas describe-install-codes` | Get existing install code list |
| `aliyun sas add-install-code` | Generate new install code (write) |
| `aliyun sas create-or-update-asset-group` | Create or update asset group (write) |
| `aliyun sas get-auth-summary` | Get authorization quota and usage per version |
| `aliyun sas describe-version-config` | Get version, feature modules, expiration |
| `aliyun sas get-serverless-auth-summary` | Get pay-as-you-go serverless status |
| `aliyun sas modify-post-pay-module-switch` | Toggle pay-as-you-go module switches (write) |
| `aliyun sas bind-auth-to-machine` | Bind/unbind authorization version (write) |
| `aliyun sas update-post-paid-bind-rel` | Change pay-as-you-go version binding or downgrade to free version (write) |
| `aliyun sas describe-property-sca-detail` | Query software info on servers |
| `aliyun sas add-uninstall-clients-by-uuids` | Uninstall agent from specified servers (write) |
| `aliyun sas modify-push-all-task` | Dispatch security check tasks to servers (write) — use this for targeted single-server scans |
| `aliyun sas modify-start-vul-scan` | Trigger global full-scan across ALL servers (write) — NEVER use for targeted single-server scans |
| `aliyun sas describe-grouped-vul` | Query grouped vulnerability statistics |
| `aliyun sas exec-strategy` | Execute baseline check strategy (write) |
| `aliyun sas describe-strategy` | Query baseline check strategy list |
| `aliyun sas list-check-item-warning-summary` | Get baseline check risk statistics |
| `aliyun sas describe-susp-events` | Query security alert events |
| `aliyun sas generate-once-task` | Trigger full asset fingerprint collection (write) |
| `aliyun sas create-asset-selection-config` | Create virus scan asset selection (write) |
| `aliyun sas add-asset-selection-criteria` | Add assets to selection config (write) |
| `aliyun sas update-selection-key-by-type` | Associate selection to virus scan (write) |
| `aliyun sas create-virus-scan-once-task` | Create one-time virus scan task (write) |
| `aliyun sas get-virus-scan-latest-task-statistic` | Query latest virus scan task stats |
| `aliyun sas list-virus-scan-machine` | Query machines involved in virus scan |
| `aliyun sas list-virus-scan-machine-event` | Query virus events on a specific machine |
| `aliyun sas describe-once-task` | Poll vulnerability scan task progress |

> Detailed API parameters: `references/api-reference.md`. RAM permissions: `references/ram-policies.md`. Full command list: `references/related-commands.md`.

---

## Common Flow: Get or Create Install Code

When any installation scenario requires an install code, follow this unified flow.

**Step 1: Query existing install codes**

```bash
aliyun sas describe-install-codes --user-agent AlibabaCloud-Agent-Skills
```

Display as table: install code, OS, vendor, group, image flag, expiration.

**Step 2: Ask user to choose**

User can select an existing matching unexpired code, or request a new one.

**Step 3: Confirm new install code config (creation only)**

| Config | Parameter | Notes |
|--------|-----------|-------|
| OS | `--os` | linux or windows |
| Vendor | `--vendor-name` | Determined by network access method (see below) |
| Asset Group | `--group-id` | Target group; create via create-or-update-asset-group if needed |
| Expiration | `--expired-date` | 13-digit timestamp; defaults if omitted |
| Image Install | `--only-image` | Whether for image template creation |

**VendorName and network access method mapping:**

The vendor parameter determines the connection domain used by the install command. Using the wrong value causes the agent to fail connecting to the server:

| Network Access | VendorName | Reason |
|---------------|-----------|--------|
| Direct line (leased line) | **ALIYUN** | Uses internal domain jsrv2.aegis.aliyun.com |
| Public network (Alibaba Cloud ECS) | **ALIYUN** | ECS uses internal network |
| Public network (third-party cloud/IDC) | **OTHER** | Uses public domain jsrv.aegis.aliyun.com |

> When the scenario already identifies the network access method, auto-fill VendorName without asking the user.

After confirmation, execute creation (pass only user-specified parameters). This is a write operation requiring confirmation.

**Step 4: Get install command**

After creation, re-query the install code list to get the new CaptchaCode for building the install command.

---

## Scenario Routing

### Scenario 0: Initial Consultation

**Trigger**: User vaguely says "onboard to Security Center", "install security agent", "deploy cloud security".

**Strategy**: Do not call any tools. Collect information through questions, then route:

1. **Server type**:
   - Alibaba Cloud ECS -> Scenario 1
   - Third-party cloud / On-premises IDC -> Continue to question 2

2. **Network access method**:
   - Public or leased-line direct -> Scenario 2

3. **Image deployment** -> Scenario 3

---

### Scenario 1: Alibaba Cloud ECS Onboarding

**Trigger**: User confirms the server is an Alibaba Cloud ECS instance.

**Summary**:
1. Get ECS info, query instance and client status
2. Based on ClientStatus + ClientSubStatus: online = no action needed, uninstalled = install, offline = troubleshoot
3. Get or create install code (common flow)
4. If cloud assistant is online, dispatch remotely; otherwise provide manual install command
5. Verify onboarding

> Detailed steps and CLI commands: `references/install-scenarios.md#scenario-1-alibaba-cloud-ecs-onboarding`

---

### Scenario 2: On-Premises IDC Direct Connection (Public/Leased Line)

**Trigger**: On-premises IDC or third-party cloud server with public or leased-line connectivity.

**Summary**:
1. Get or create install code (common flow, VendorName auto-determined by network type)
2. Select install command based on network situation (public/leased-line/overseas), refer to `references/agent-install-guide.md`
3. Verify onboarding

> Detailed steps: `references/install-scenarios.md#scenario-2-on-premises-idc-direct-connection`

---

### Scenario 3: Image-Based Batch Installation

**Trigger**: User mentions image deployment, batch server creation with pre-installed agent, template creation.

**Summary**:
1. Confirm template server info, remind about clean environment requirement
2. Get or create image-specific install code (OnlyImage=true)
3. Provide install command; emphasize: after execution, only shutdown is allowed -- restarting activates the agent and occupies the UUID
4. Warn about UUID conflict risk: every image creation requires repeating this process
5. Verify new instance onboarding

> Detailed steps and caveats: `references/install-scenarios.md#scenario-3-image-based-batch-installation`

---

### Scenario 4: Network Troubleshooting

**Trigger**: User reports installation failure, agent offline, or connection issues.

**Strategy**: Do not call tools; provide troubleshooting guidance directly:
- Confirm required domains and ports (public: jsrv.aegis.aliyun.com:80, leased-line: jsrv2.aegis.aliyun.com:80)
- Provide network connectivity test commands
- Common cause analysis (firewall, DNS, no public network)

> Detailed troubleshooting steps: `references/install-scenarios.md#scenario-4-network-troubleshooting`

---

### Scenario 5: Query Version and Feature Info

**Trigger**: User wants to know about **account-level** version, authorization quota, enabled features, or pay-as-you-go status.

> **[MUST] Routing distinction**: Scenario 5 is for **account-level** queries ("我们的版本是什么", "配额还剩多少", "过期时间"). When the user asks about **specific servers** ("哪些服务器未授权", "哪些机器是免费版", "未绑定付费版本的服务器"), route to `describe-cloud-center-instances` with AuthVersion filter instead — this is an asset query, NOT a version query.

**Summary**:
1. Query version details (describe-version-config)
2. Query authorization usage (get-auth-summary)
3. Optionally query Serverless status (get-serverless-auth-summary)
4. Optionally modify pay-as-you-go module switches (modify-post-pay-module-switch, write operation)

**[MUST]** The `MergedVersion` field in `describe-version-config` response is a sensitive internal field — NEVER display, output, save to file, or include it in any response exposed to the user. Strip it before any output. Use `Version` and `HighestVersion` instead.

> Detailed steps and field mappings: `references/manage-scenarios.md#scenario-5-query-version-and-feature-info`

---

### Scenario 6: Query or Modify Asset Authorization Version

**Trigger**: User wants to view or change a **specific server's** authorization version, or **list servers** filtered by authorization status (e.g. "哪些服务器未授权", "免费版的机器有哪些").

> When listing/filtering servers by authorization status, use `describe-cloud-center-instances` with criteria filters. When viewing/modifying a specific named server's version, follow the full Scenario 6 flow below.

**Summary**:
1. Query asset current status and authorization version
2. Confirm operation type (view/bind/unbind/change pay-as-you-go version/downgrade to free)
3. Subscription bind/unbind (bind-auth-to-machine, write operation)
4. Pay-as-you-go version change or downgrade to free (update-post-paid-bind-rel, write operation). Downgrade to free version uses `Version=1` in `--bind-action`
5. Verify change

**Key constraints**:
- Subscription binding cannot be unbound within 30 days, because authorization resources have a lock period
- K8s/ACK cluster assets only support Ultimate edition, because other editions do not cover container runtime protection

> Detailed steps: `references/manage-scenarios.md#scenario-6-query-or-modify-asset-authorization`

---

### Scenario 7: Query Assets with Specific Software

**Trigger**: User wants to find servers with a specific software installed.

**Summary**:
1. Confirm query conditions (software name, type)
2. Query asset fingerprint (describe-property-sca-detail)
3. Optionally supplement with detailed asset info

> Detailed steps: `references/manage-scenarios.md#scenario-7-query-assets-with-specific-software`

---

### Scenario 8: Uninstall Security Center Agent

**Trigger**: User wants to uninstall the Security Center agent from a specific server.

**Summary**:
1. Get target server identifier, query asset info to obtain UUID
2. Display uninstall details (server name, UUID, current status), warn that uninstalling removes all protection
3. After confirmation, execute uninstall (add-uninstall-clients-by-uuids, write operation)
4. Verify uninstall result

**Key constraints**:
- This API applies to non-Alibaba Cloud servers (IDC/third-party cloud); Alibaba Cloud ECS requires console or cloud assistant for uninstall
- Uninstalling removes all Security Center protection capabilities; the user must explicitly confirm

> Detailed steps: `references/manage-scenarios.md#scenario-8-uninstall-security-center-agent`

---

### Scenario 9: Security Risk Detection and Query

**Trigger**: User wants to detect security risks, trigger vulnerability scans, execute baseline checks, view security alerts, or get risk results.

**Summary**:
1. Confirm detection type (query existing risk results / trigger new scan)
2. Query risk results: vulnerabilities (describe-grouped-vul), baseline (list-check-item-warning-summary), security alerts (describe-susp-events)
3. Trigger new scans — two distinct modes:
   - **Targeted scan** (specific server): Use `modify-push-all-task` with the target UUID for ALL scan types (vulnerability + baseline + fingerprint). **NEVER use `modify-start-vul-scan` for targeted scans.**
   - **Full scan** (all servers): Use `modify-start-vul-scan` (vulnerability), `exec-strategy` (baseline), `generate-once-task` (fingerprint), `create-virus-scan-once-task` (virus)
4. For targeted asset scans, automatically execute prerequisite chain: authorization check -> client check -> auto-install -> dispatch scan + virus scan
5. After dispatching, poll progress: vulnerability scan (describe-once-task), baseline check (describe-strategy.ExecStatus), virus scan (get-virus-scan-latest-task-statistic); query risk results after all complete

**Key constraints**:
- **[HARD GATE] NEVER use `modify-start-vul-scan` for targeted scans**: `modify-start-vul-scan` triggers a **global full-scan across ALL servers in the entire account**, not just the target. When scanning a specific server (targeted scan), you MUST use `modify-push-all-task` with the server's UUID — this is the ONLY correct command for targeted vulnerability scans. `modify-start-vul-scan` is reserved exclusively for full-scan scenarios where no specific target is specified.
- **[HARD GATE] Client online required for ALL scans**: ALL scan dispatch operations (modify-push-all-task, modify-start-vul-scan, exec-strategy, create-virus-scan-once-task) are host-based and require the target server's Security Center agent `ClientStatus=online`. If the agent is not installed or offline, scans CANNOT be dispatched and WILL produce NO results. There is NO agentless scanning mode in this skill. Do NOT proceed with any scan dispatch if the client is not online — instead, guide the user to install or bring the agent online first
- **[HARD GATE] Paid authorization required for scans**: The target server must be bound to a paid authorization version (`AuthVersion > 1`); free version (`AuthVersion <= 1`) servers cannot be scanned
- Querying existing risk results (describe-grouped-vul, list-check-item-warning-summary, describe-susp-events) is a READ operation that queries historical data in Security Center's database — this does NOT trigger new scans and does NOT require the agent to be online
- Before full scan, query all asset statuses first, show the user ready/not-ready asset breakdown, and confirm before dispatching
- Targeted asset scans are fully automated with the prerequisite chain (authorization + client), only authorization binding requires user confirmation
- Baseline detection (HEALTH_CHECK / exec-strategy) requires a pre-paid host protection version (Version > 1) or enabled Cloud Security Posture Management (CSPM); skip baseline detection if neither is met
- Scan operations are write operations; full scans require confirmation before execution

> Detailed steps: `references/manage-scenarios.md#scenario-9-security-risk-detection-and-query`

---

### Fallback Scenario

**Trigger**: No scenario matched, or the request exceeds this skill's capability.

**Strategy**: Honestly inform the user this is not currently supported; recommend referring to official documentation or submitting a support ticket.

---

## Execution Rules

### Read Operations (Execute Directly)

describe-cloud-center-instances, describe-instances, describe-cloud-assistant-status, describe-invocation-results, describe-install-codes, refresh-assets, get-auth-summary, describe-version-config, get-serverless-auth-summary, describe-property-sca-detail, describe-grouped-vul, list-check-item-warning-summary, describe-susp-events, describe-strategy, get-virus-scan-latest-task-statistic, list-virus-scan-machine, list-virus-scan-machine-event, describe-once-task

Briefly state intent (1-2 sentences) before calling.

### Write Operations (Confirm Before Execution)

add-install-code, run-command, invoke-command, create-or-update-asset-group, modify-post-pay-module-switch, bind-auth-to-machine, update-post-paid-bind-rel, add-uninstall-clients-by-uuids, modify-push-all-task, modify-start-vul-scan, exec-strategy, generate-once-task, create-asset-selection-config, add-asset-selection-criteria, update-selection-key-by-type, create-virus-scan-once-task

Flow: Display operation details -> Wait for user confirmation -> Execute -> Report result.

### Observation Phase

- Briefly describe the returned result
- Determine if it matches expectations
- Decide next action

### Iteration Principles

1. If the agent is already online, immediately inform the user no action is needed
2. Limit to 8 CLI tool calls per scenario (proxy scenarios may extend moderately)
3. Do not call APIs without confirmed server information, because wrong parameters return meaningless results
4. Do not skip steps, because each step's output is the next step's input
5. Do not fabricate API return results, because this misleads the user into wrong decisions

### Cost Estimation Rules

- When displaying pay-as-you-go module status, include billing method and unit price references for each module
- Before the user enables pay-as-you-go modules, include cost estimates in the confirmation details
- Fetch pricing from the official billing documentation page: https://help.aliyun.com/zh/security-center/product-overview/billing-overview
  - Fetch once on the first pricing need per session, then reuse
  - If unable to fetch, provide the billing page link for the user to check
- Base service fee: when any pay-as-you-go module is enabled, a base service fee applies (~0.05 CNY/hour, approx. 36 CNY/month)
  - If no modules are currently enabled, remind the user about this fee when first enabling

> Module classification, estimation formulas, and display formats: `references/manage-scenarios.md` cost estimation section.

---

## Termination and Summary

Enter summary when any of the following conditions is met:
- Agent has successfully come online
- Install command has been provided to the user
- Version/authorization/software info has been queried and displayed
- Authorization bind/unbind/change operation has completed
- Agent uninstall operation has completed
- Security risk detection has completed or risk results have been displayed
- Issue has been identified and solution provided
- Scenario is unsupported and support ticket has been recommended

Summary format adapts to the scenario. Core elements: operation result, key information (server/version/status), follow-up recommendations.

---

## Best Practices

1. Always verify CLI version and credentials before any operation
2. Use the correct VendorName based on network access method to avoid connection failures
3. For batch installations, prefer image-based approach to reduce manual effort
4. Check authorization quota before binding new servers to avoid exceeding limits
5. When troubleshooting offline agents, verify network connectivity to Security Center endpoints first
6. For proxy scenarios, ensure proxy server meets requirements (Linux, ports 80/443/8080) before proceeding
7. Always verify agent online status after installation before considering the task complete

---

## References

This skill references the following documents, loaded on demand:

| Reference | Description |
|-----------|-------------|
| `references/install-scenarios.md` | Detailed execution steps for installation scenarios (1, 2, 3, 4) |
| `references/manage-scenarios.md` | Detailed execution steps for management/query scenarios (5, 6, 7, 8, 9) |
| `references/agent-install-guide.md` | Agent install commands and verification methods |
| `references/api-reference.md` | All API parameter details and CLI examples |
| `references/ram-policies.md` | RAM permission manifest |
| `references/cli-installation-guide.md` | Alibaba Cloud CLI installation guide |
| `references/related-commands.md` | Complete CLI command reference table |
| `references/verification-method.md` | Success verification methods for each scenario |
| `references/acceptance-criteria.md` | Skill acceptance criteria and test patterns |
