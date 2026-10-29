---
name: alibabacloud-ga-easyconfig
description: Alibaba Cloud Global Accelerator (GA / 阿里云全球加速 / 全球加速实例 / GA实例) configuration and lifecycle management skill. Use when users ask to create, configure, set up, manage, monitor, diagnose, or optimize GA accelerators, listeners, endpoint groups, bandwidth packages, IP sets, ACLs, forwarding rules, certificates, application monitors, cross-border acceleration, health checks, or configuration drift. Trigger on Global Accelerator, GA, 全球加速, 全球加速实例, GA实例, 跨境加速, 跨境合规, 跨境业务, 海外用户访问, 海外访问, 访问延迟, 延迟高, 游戏加速, 电商加速, 创建GA, 配置GA, 设置GA, GA监听, GA终端节点, GA带宽包, GA健康检查, GA诊断, GA漂移检测, GA导入, GA计费, 健康检查失败, 诊断GA, create Global Accelerator, configure GA, set up GA, GA listener, GA endpoint, GA bandwidth package, GA health check, GA diagnosis, GA cross border.
license: MIT
---

# Alibaba Cloud GA EasyConfig

This skill automates end-to-end lifecycle management for Alibaba Cloud Global Accelerator (GA) Standard and Basic accelerators. All write operations against Alibaba Cloud APIs require explicit user confirmation before execution. The PreToolUse hook is configured in `assets/manifest.json` to intercept Bash tool use automatically; if the hook does not run, errors out, or returns `allow` for a command that creates, updates, or deletes resources, ask the user for confirmation before executing it — the hook is a safety net, not a substitute for your own judgement. Purchase-like operations with significant cost (PREPAY instances, bandwidth packages, resource packages, spec upgrades) additionally require a dedicated second confirmation from the user — see `High-Cost Operations — Mandatory Second Confirmation` below.

## When to Use

- Create or configure Standard/Basic GA accelerators.
- Import existing accelerators into local configuration files.
- Deploy from JSON templates across multiple environments.
- Detect configuration drift, manage ACLs/forwarding rules/certificates.
- Monitor health, estimate cost, or optimize resources.

## Trigger Keywords

Use this skill when the user mentions any of the following in Chinese or English:

- **Product names**: Global Accelerator, GA, `阿里云全球加速`, `全球加速`, `全球加速实例`, `GA实例`.
- **Lifecycle actions**: `创建GA`, `配置GA`, `设置GA`, `GA监听`, `GA终端节点`, `GA带宽包`, `GA健康检查`, `GA诊断`, `GA漂移检测`, `GA导入`, `GA计费`, `健康检查失败`, `诊断GA`, create GA, configure GA, set up GA.
- **Scenarios**: `跨境加速`, `跨境合规`, `跨境业务`, `海外用户访问`, `海外访问`, `访问延迟`, `延迟高`, `游戏加速`, `电商加速`, `中国大陆到海外加速`, GA cross border, cross-border acceleration.

## Prerequisites

- **CLI**: Alibaba Cloud CLI (`aliyun`) **version 3.3.3 or higher** installed and configured with valid credentials. Verify with `aliyun version`. If the CLI is missing or older than 3.3.3, stop and ask the user to install or upgrade it following the official documentation at `https://help.aliyun.com/document_detail/121541.html`. Never download, unpack, or install the CLI during a session, and never write to system paths with `sudo`.
- **Region**: GA control plane uses `cn-hangzhou` for all API calls; acceleration regions are specified via dedicated parameters.
- **Tools**: `jq` (Linux/macOS) or PowerShell `ConvertFrom-Json` (Windows). Format output with `jq` directly; do not depend on `column`, `less`, or other optional utilities that may be absent in the execution environment.
- **Session tracking**: Each invocation must generate a unique `GA_SESSION_ID` (UUID4) and set `User-Agent: AlibabaCloud-Agent-Skills/alibabacloud-ga-easyconfig/<GA_SESSION_ID> skill-version/<version>` when calling aliyun CLI.

## Reference Loading

`SKILL.md` contains the complete command set for the standard workflows. Do **not** read `references/` files up front. Open a specific reference file only when:

- the step needs a capability listed in `Advanced Features`, or
- a command fails and you need that API's parameter or error tables.

This keeps the session context small — reading every reference file before planning can consume thousands of lines without adding information for a standard deployment.

## CLI Parameter Syntax (Mandatory)

The installed `aliyun` CLI enforces **kebab-case** syntax for GA commands. The legacy PascalCase flag style (capitalized parameter names such as a legacy region flag) is rejected with an explicit error. Apply these rules to every command:

1. **Command region parameter**: GA's API-level `RegionId` is passed as `--biz-region-id` (e.g. `--biz-region-id cn-hangzhou`). Never use the legacy PascalCase region flag. The CLI global flag `--region` only controls the signing endpoint and is optional.
2. **Scalar parameters**: kebab-case, e.g. `--accelerator-id`, `--listener-id`, `--endpoint-group-region`, `--instance-charge-type`, `--bandwidth-package-id`.
3. **List/nested parameters**: pass the group once with inline `Field=Value` pairs, e.g. `--accelerate-region AccelerateRegionId=cn-hangzhou Bandwidth=5 IpVersion=IPv4 IspType=BGP`. Field names inside a group keep **PascalCase** (`AccelerateRegionId`, `FromPort`, `Id`, `Type`, `Endpoint`); lowercasing them fails with an `unknown field` error.
4. **Enum values**: billing/charge types are UPPERCASE (`POSTPAY`, `PREPAY`, `CDT`, `BandwidthPackage`); listener protocols are UPPERCASE (`TCP`, `UDP`, `HTTP`, `HTTPS`); health-check protocols are lowercase (`tcp`, `udp`, `http`, `https`); IP version is `IPv4`/`IPv6`; ISP type is `BGP`.
5. **POSTPAY instances**: `--bandwidth-billing-type CDT` is mandatory, and `--spec` is NOT supported (API errors `InvalidateBandwidthBillingType.PostPayAccelerator` / `NotSupportSpecification.PostPayAccelerator` otherwise).
6. **Acceleration region bandwidth**: must be greater than 2 Mbps (`IllegalBandwidth.IpSet` otherwise).
7. **Dry-run validation**: for parameter combinations that are easy to get wrong (PREPAY with `--spec`, Anycast `--bandwidth`, enum values), run the command once with `--dry-run true` before the real call. A valid dry run returns the error code `DryRunOperation` with no resource created; a real validation problem returns its normal error code, also with no resource created.

If a command fails with an unknown-parameter or unknown-field error, run `aliyun ga <command> --help` and adapt to the printed kebab-case syntax instead of retrying the legacy PascalCase form.

## Session Initialization

Before the first Alibaba Cloud API call in every session, initialize the session exactly once. `scripts/init-session.sh` reads `assets/manifest.json`, generates a UUID4 session ID, exports the User-Agent variables, and optionally writes them to an env file:

```bash
source "${SKILL_ROOT}/scripts/init-session.sh" --env-file ./ran_scripts/00-session-env.sh
```

This exports (and persists to the env file):

- `GA_SKILL_NAME`
- `GA_SKILL_VERSION`
- `GA_SESSION_ID`
- `GA_USER_AGENT`

Never pipe the sourcing into `tee` — a pipe runs in a subshell and loses the exported variables, and re-running the script generates a second session ID that no longer matches the logs. If a later shell invocation lost the variables, reload them with `source ./ran_scripts/00-session-env.sh` instead of re-running `init-session.sh`.

Every subsequent `aliyun ga ...` command in this session must include `--user-agent "$GA_USER_AGENT"`.

## Bounded Execution (Mandatory)

An agent session is killed by a hard wall-clock limit, so no command may block indefinitely:

1. Every polling loop needs both a maximum attempt count and a wall-clock budget (for example 20 attempts x 10 s). Stop when either is reached, then report the last observed state and what is still pending.
2. Never run a `while true` loop, `tail -f`, or a continuous-monitor script in the foreground of a tool call. For continuous monitoring, start it in the background with `nohup ... &`, report the PID and how to stop it, then continue with the task.
3. `scripts/ga-health-monitor.sh` is bounded by default through `--count` and `--max-duration`; use `--unbounded` only in a background process.
4. A one-off status check does not need monitoring: call `get-health-status` once instead of starting the monitor script.
5. If a single API call appears to hang, re-run that call once with the CLI global timeouts `--cli-read-timeout 60 --cli-connect-timeout 10`. If it hangs again, stop and report the blocker instead of retrying in a loop.

## Required RAM Permissions

Use the least-privilege policy in `references/ram-policies.md`. At minimum the skill needs read access to GA and dependent services, plus write access when the user explicitly confirms a mutating operation.

## Configuration Files

- `assets/ga-config.json`: Sample accelerator, bandwidth packages, and IP sets configuration.
- `ga-listeners.json`: Listeners, endpoint groups, endpoints, and forwarding rules (kept in the working directory).

Copy `assets/ga-config.json` to the working directory and update it after every mutating operation.

## Idempotency (Mandatory for create calls)

Agent retries are common, and a repeated create call produces duplicate resources — for PREPAY instances and bandwidth packages that means a duplicate charge.

1. Never blind-retry a create call after a timeout or a network error. Re-run the Step 0 inventory first and check whether the resource from the previous attempt already exists.
2. When the API parameter table in `references/` lists `ClientToken`, pass a deterministic token derived from the stable inputs so a retry of the same request is deduplicated by the service:

```bash
GA_CLIENT_TOKEN=$(printf '%s' "${NAME}|${REGION}|${SPEC}" | sha256sum | cut -c1-32)
aliyun ga create-accelerator ... --client-token "$GA_CLIENT_TOKEN" --user-agent "$GA_USER_AGENT"
```

3. For actions whose parameter table has no `ClientToken`, use check-then-act: list the existing resources first, match by name and configuration, and reuse the match instead of creating a second copy.

## High-Cost Operations — Mandatory Second Confirmation

Purchase-like operations generate prepaid orders or significantly increase cost. Before executing any of them, you MUST stop and obtain an explicit second confirmation from the user in the conversation — never batch them silently with other steps:

| Operation | Command | Cost driver |
|---|---|---|
| PREPAY instance purchase | `create-accelerator --instance-charge-type PREPAY` (with `--spec`, `--pricing-cycle`, `--duration`) | spec x duration |
| PREPAY instance spec change | `update-accelerator --spec <spec> --auto-pay true` | spec delta, prorated |
| Basic PREPAY accelerator purchase | `create-basic-accelerator --charge-type PREPAY` | spec x duration |
| Bandwidth package purchase (Basic only — CrossDomain is manual-only, see cross-border note below) | `create-bandwidth-package --charge-type PREPAY` | bandwidth x duration |
| Bandwidth package spec upgrade (PREPAY) | `update-bandwidth-package --bandwidth-package-id <id> --bandwidth <mbps>` | bandwidth delta, prorated |
| Any other order-generating or resource-package purchase | varies | order amount |

Before asking, present the user with: resource type, spec/bandwidth, billing type, duration, auto-renew setting, and the exact command to run (pricing references: `references/ga_pricing.md`). Proceed only after the user explicitly confirms; if the user does not confirm, stop and offer the POSTPAY/CDT alternative where applicable (POSTPAY + CDT needs no bandwidth package at all).

## Blocked-State Protocol

When an account-level constraint blocks the requested operation — `QuotaExceeded.Accelerator`, cross-border compliance held, missing RAM permission, or a resource conflict — do **not** improvise destructive fixes. Deliver a consistent blocked outcome:

1. **Stop before any irreversible action** (delete/release objects, modify another workload's resources).
2. **Write a blocker log** containing: the exact failed command, timestamp, error code and RequestId, account ID, and the inventory you inspected.
3. **Produce a corrected, ready-to-run script** for the remaining steps and syntax-check it (`bash -n`).
4. **Write a short report** with numbered options — e.g. release an idle resource, raise the quota, or reuse an existing resource — and the trade-off of each.
5. **Ask the user to choose and stop.** Re-run the corrected script once they decide.

Never delete or modify GA resources that belong to another workload or subscription without explicit confirmation for that specific resource ID.

## Standard Accelerator Workflow

Follow the steps in order. Pause and ask the user at every red decision point; execute green steps automatically after confirmation.

### Step 0: Pre-flight (read-only)

Run these checks before creating anything — they are cheap and prevent late failures caused by exhausted quota or name collisions:

```bash
# 1. GA service status
aliyun ga describe-accelerator-service-status --biz-region-id cn-hangzhou \
  --user-agent "$GA_USER_AGENT"
# 2. Instance inventory: quota usage + same-name collisions
aliyun ga list-accelerators --biz-region-id cn-hangzhou --page-size 50 \
  --user-agent "$GA_USER_AGENT" \
| jq --arg name "<name>" '{TotalCount,
    SameName: [.Accelerators[]? | select(.Name == $name)
               | {AcceleratorId, State, InstanceChargeType}]}'
```

**Quota awareness**: GA instance count is capped by an account-level quota (commonly 10; confirm the current value in Quota Center). If `TotalCount` is at or near the limit, stop **before** doing further work and tell the user that creating the instance will fail with `QuotaExceeded.Accelerator` — then follow the Blocked-State Protocol. Instance names are **not unique**: if `SameName` is non-empty, report those instances and ask whether to reuse one or create another.

**Backend verification**: confirm any ECS/SLB/NLB backend exists, is `Running`, and sits in the endpoint-group region before building the listener stack.

### Step 1: Create or Select Accelerator

**Decision (ask user)**: billing type (`POSTPAY`/`PREPAY`), name, spec (PREPAY only), IP access mode (`UserDefine`/`Anycast`).

Create POSTPAY (do not pass `--spec`):
```bash
aliyun ga create-accelerator \
  --biz-region-id cn-hangzhou \
  --name <name> \
  --instance-charge-type POSTPAY \
  --bandwidth-billing-type CDT \
  --ip-set-config AccessMode=UserDefine \
  --user-agent "$GA_USER_AGENT"
```

Create PREPAY (**cost gate**: this generates a prepaid order — confirm spec, pricing cycle, duration, and estimated cost with the user before executing; run it only after the user explicitly confirms, and use `--auto-pay true` so the subscription is actually paid and the instance is created):
```bash
aliyun ga create-accelerator \
  --biz-region-id cn-hangzhou \
  --name <name> \
  --instance-charge-type PREPAY \
  --spec <spec> \
  --bandwidth-billing-type BandwidthPackage \
  --pricing-cycle Month --duration 1 --auto-pay true \
  --user-agent "$GA_USER_AGENT"
```

Or list existing:
```bash
aliyun ga list-accelerators --biz-region-id cn-hangzhou --state active \
--user-agent "$GA_USER_AGENT"
```

Poll with `aliyun ga describe-accelerator --biz-region-id cn-hangzhou --accelerator-id <ga-id>` until `State` is `active`, then save to `ga-config.json`.

### Step 2: Bind Bandwidth Package (PREPAY only)

Skip for `POSTPAY`. For `PREPAY`, create a basic bandwidth package and bind it (**cost gate**: `create-bandwidth-package --charge-type PREPAY` is a prepaid purchase — present bandwidth x duration x billing type and obtain the user's second confirmation before running it):
```bash
aliyun ga create-bandwidth-package \
  --biz-region-id cn-hangzhou --type Basic --bandwidth <mbps> --bandwidth-type Basic --charge-type PREPAY \
  --user-agent "$GA_USER_AGENT"
aliyun ga bandwidth-package-add-accelerator \
  --biz-region-id cn-hangzhou --bandwidth-package-id <id> --accelerator-id <ga-id> \
  --user-agent "$GA_USER_AGENT"
```

**Cross-border acceleration (mainland-china-to-overseas)**: A `CrossDomain` bandwidth package involves cross-border compliance and is **never purchased or bound by this skill** — regardless of the approval status. You may run the read-only status checks below to inform the guidance, but the compliance application, purchase, and binding of a `CrossDomain` package must be completed by the user in the console:
```bash
# Check account-level cross-border compliance approval
aliyun ga query-cross-border-approval-status \
  --biz-region-id cn-hangzhou \
  --user-agent "$GA_USER_AGENT"
# Check the accelerator's cross-border status (fields in the accelerator details)
aliyun ga describe-accelerator \
  --biz-region-id cn-hangzhou --accelerator-id <ga-id> \
  --user-agent "$GA_USER_AGENT"
```
After the status checks, output a manual operation guide tailored to the current `ApprovalStatus` and stop — never run `create-bandwidth-package --type CrossDomain` or `bandwidth-package-add-accelerator` for a CrossDomain package, even when the user asks to proceed. The guide must tell the user how to (1) submit the cross-border compliance application in the GA console (approval takes 1-5 business days), (2) purchase the `CrossDomain` bandwidth package in the console once approved, and (3) bind it to the GA instance — all done by the user manually. See `references/ga_cross_border.md` § 8 for the guide template. The non-cross-border parts (instance, Basic bandwidth package, acceleration regions, listeners, endpoint groups) continue as normal automated steps.

### Step 3: Create Acceleration Regions

List available areas (`list-accelerate-areas`, `list-available-accelerate-areas`, `list-isp-types`), ask the user for region(s), bandwidth, and IP version, then create:
```bash
aliyun ga create-ip-sets \
  --biz-region-id cn-hangzhou \
  --accelerator-id <ga-id> \
  --accelerate-region AccelerateRegionId=<region> Bandwidth=<mbps> IpVersion=IPv4 IspType=BGP \
  --user-agent "$GA_USER_AGENT"
```

Bandwidth must be greater than 2 Mbps. Query assigned IPs with `list-ip-sets` and update `ga-config.json`.

### Step 4: Create Listener

**Decision (ask user)**: routing type (`Standard`/`CustomRouting`), protocol (`TCP`/`UDP`/`HTTP`/`HTTPS`), port range.

```bash
aliyun ga create-listener \
  --biz-region-id cn-hangzhou \
  --accelerator-id <ga-id> \
  --name <name> \
  --protocol TCP \
  --port-ranges FromPort=80 ToPort=80 \
  --type Standard \
  --user-agent "$GA_USER_AGENT"
```

For HTTPS, additionally ask for the certificate (auto-discover from CAS with `scripts/ga-discover-certificate.sh`, which prints certificates with remaining validity and the GA certificate ID form `<CertificateId>-cn-hangzhou`) and TLS policy, then append:
```bash
  --certificates Id=<CertificateId>-cn-hangzhou \
  --security-policy-id <tls-policy-id>
```

Poll with `describe-listener --listener-id <listener-id>` until `State` is `active`.

### Step 5: Create Endpoint Group

**Decision (ask user)**: endpoint group region, traffic percentage, health check settings.

**IMPORTANT — two-step flow**: create the endpoint group **without** endpoints first. Never pass `--endpoint-configurations` to `create-endpoint-group`; endpoints are always added in Step 6 via `update-endpoint-group`.

**Idempotent finalization (mandatory)**: a retried `create-endpoint-group` can land on an endpoint group that an earlier attempt already created, and that group may already contain the endpoint you want. Whatever `create-endpoint-group` returns — a new ID, a name conflict, or an existing group found via `list-endpoint-groups` — Step 6 still issues `update-endpoint-group` explicitly with the target endpoint list. A read-only check (`describe-endpoint-group` / `list-endpoint-groups` showing the expected endpoint) never replaces the update call. The deployment is complete only when the session log contains a successful `UpdateEndpointGroup` request for the target endpoint group.

**Region note (Standard)**: for Standard accelerators the endpoint group region may equal the acceleration region — it is allowed, but traffic stays in-region so the acceleration benefit is limited. The "must differ" rule applies to Basic accelerators only (see below). Mention this to the user and keep it if they confirm.

```bash
aliyun ga create-endpoint-group \
  --biz-region-id cn-hangzhou \
  --accelerator-id <ga-id> \
  --listener-id <listener-id> \
  --endpoint-group-region <region> \
  --name <name> \
  --traffic-percentage 100 \
  --health-check-enabled true \
  --health-check-protocol tcp \
  --health-check-port 80 \
  --user-agent "$GA_USER_AGENT"
```

### Step 6: Add Endpoints

**Decision (ask user)**: endpoint type (`Ip`/`ECS`/`SLB`/`ALB`/`NLB`/`OSS`), address (IP or resource ID), weight.

Even if the user already provided endpoints during Step 5, you MUST still call `update-endpoint-group` in this step to register them. Auto-discover backend resources when type is ECS/SLB/NLB/ALB (see `references/ga_auto_discovery.md`).
```bash
aliyun ga update-endpoint-group \
  --biz-region-id cn-hangzhou \
  --endpoint-group-id <epg-id> \
  --endpoint-configurations Type=Ip Endpoint=<ip-or-resource-id> Weight=255 \
  --user-agent "$GA_USER_AGENT"
```

`Type` accepts `Ip`, `ECS`, `SLB`, `ALB`, `NLB`, `OSS`; `Endpoint` is the IP address (for `Ip`) or the resource ID (for the others, e.g. `i-...`, `lb-...`, `alb-...`, `nlb-...`).

### Step 7: Validate

Check instance, listener, and endpoint health:
```bash
aliyun ga describe-accelerator --biz-region-id cn-hangzhou --accelerator-id <ga-id> \
--user-agent "$GA_USER_AGENT"
aliyun ga list-listeners --biz-region-id cn-hangzhou --accelerator-id <ga-id> \
--user-agent "$GA_USER_AGENT"
aliyun ga get-health-status --biz-region-id cn-hangzhou --listener-id <listener-id> \
--user-agent "$GA_USER_AGENT"
```

Show a deployment summary table and update `ga-listeners.json`.

This is a single status check: run `get-health-status` once and report the result. Do not start `scripts/ga-health-monitor.sh` (continuous monitor) during validation.

## Basic Accelerator Workflow

Basic accelerators are layer-3 point-to-point and support only one acceleration region and one endpoint group.

**HARD CONSTRAINT — endpoint group region**: For a Basic accelerator the endpoint group region MUST differ from the acceleration region. If the user asks for both in the same region (e.g. both `cn-hangzhou`), you MUST stop, explain the constraint, and ask for a different endpoint group region. NEVER execute `create-basic-endpoint-group` in this case — creating it will fail and pollute the account.

**KNOWN CONSTRAINT — ECS endpoint binding**: Basic GA binds the accelerate IP onto the ECS primary ENI. If that ENI already carries a public IP (an EIP, or an accelerate IP bound by another Basic accelerator), `create-basic-accelerate-ip-endpoint-relation` fails with `EcsCannotBind.BasicEndpoint`. Check the primary ENI with `describe-network-interfaces` before selecting an ECS backend. Do NOT silently switch to ENI/SLB type or release another accelerator's binding — report the conflict and let the user choose (release the existing binding, use another ECS, or use another endpoint type).

### Step B1: Create Basic Accelerator
```bash
aliyun ga create-basic-accelerator --biz-region-id cn-hangzhou --charge-type POSTPAY \
--user-agent "$GA_USER_AGENT"
```
Poll with `get-basic-accelerator` until `State` is `active`.

### Step B2: Create Basic IP Set
```bash
aliyun ga create-basic-ip-set \
  --biz-region-id cn-hangzhou \
  --accelerator-id <ga-id> \
  --accelerate-region-id <region> \
  --bandwidth 2 \
  --isp-type BGP \
  --user-agent "$GA_USER_AGENT"
```

### Step B3: Create Basic Accelerate IP
```bash
aliyun ga create-basic-accelerate-ip --biz-region-id cn-hangzhou --accelerator-id <ga-id> --ip-set-id <ipset-id> \
--user-agent "$GA_USER_AGENT"
```

### Step B4: Create Basic Endpoint Group

Verify first that the chosen region differs from the acceleration region (see the hard constraint above).
```bash
aliyun ga create-basic-endpoint-group \
  --biz-region-id cn-hangzhou \
  --accelerator-id <ga-id> \
  --endpoint-group-region <region> \
  --name <name> \
  --user-agent "$GA_USER_AGENT"
```

### Step B5: Create Basic Endpoint
```bash
aliyun ga create-basic-endpoint \
  --biz-region-id cn-hangzhou \
  --accelerator-id <ga-id> \
  --endpoint-group-id <epg-id> \
  --name <name> \
  --endpoint-type ECS \
  --endpoint-address <resource-id> \
  --user-agent "$GA_USER_AGENT"
```

### Step B6: Bind IP to Endpoint
```bash
aliyun ga create-basic-accelerate-ip-endpoint-relation \
  --biz-region-id cn-hangzhou \
  --accelerator-id <ga-id> \
  --accelerate-ip-id <ip-id> \
  --endpoint-id <endpoint-id> \
  --user-agent "$GA_USER_AGENT"
```

### Step B7: Validate
```bash
aliyun ga get-basic-accelerator --biz-region-id cn-hangzhou --accelerator-id <ga-id> \
--user-agent "$GA_USER_AGENT"
aliyun ga get-basic-ip-set --biz-region-id cn-hangzhou --ip-set-id <ipset-id> \
--user-agent "$GA_USER_AGENT"
aliyun ga list-basic-accelerate-ip-endpoint-relations --biz-region-id cn-hangzhou --accelerator-id <ga-id> \
--user-agent "$GA_USER_AGENT"
```

## Import Existing Accelerators

Resolve the accelerator type first: run `list-basic-accelerators` and match the requested ID against `.Accelerators[]`. If it matches, the instance is Basic; otherwise it is Standard. When the user does not know the ID (for example they want the earliest active Basic instance), select it from the same `list-basic-accelerators` output by `State` and `CreateTime` instead of guessing. See `references/ga_import_existing.md`.

**Basic accelerator query chain (mandatory, in this order)** — never substitute the Standard APIs for a Basic instance:

1. `list-basic-accelerators` → resolve the ID, `State`, `InstanceChargeType`.
2. `get-basic-accelerator --accelerator-id <ga-id>` → instance info, `BasicIpSetId`, `BasicEndpointGroupId`.
3. `list-basic-accelerate-ip-endpoint-relations --accelerator-id <ga-id>` → instance-level bindings. ALWAYS run this even when no IP set or endpoint group is configured — the call succeeds on a bare instance and returns an empty `AccelerateIpEndpointRelations` list with a real `RequestId`.

Then, only when the corresponding ID is non-empty: `get-basic-ip-set` / `list-basic-accelerate-ips`, `get-basic-endpoint-group` / `list-basic-endpoints`.

`list-accelerators` and `describe-accelerator` return Standard accelerators only. Using them to answer a Basic accelerator question silently picks an unrelated Standard instance from the same account or reports the Basic instance as missing — this is a wrong answer, not a fallback. If `get-basic-accelerator` fails, report that error and stop the Basic import; do not retry it through the Standard APIs.

Every result file you save must be the raw output of a real API call; never substitute synthesized placeholder JSON for a query that was skipped or failed.

## Advanced Features

| Feature | Reference |
|---|---|
| Template batch deployment | `references/ga_template_deployment.md` |
| Configuration drift detection | `references/ga_config_drift_detection.md` |
| ACLs | `references/ga_acl.md` |
| Layer-7 forwarding rules | `references/ga_forwarding_rules.md` |
| HTTPS additional certificates | `references/ga_additional_certificates.md` |
| Application monitor (origin probing) | `references/ga_application_monitor.md` |
| Cross-border compliance | `references/ga_cross_border.md` |
| Auto-discovery of backends/certs | `references/ga_auto_discovery.md` |
| CloudMonitor metrics/alarms | `references/ga_monitoring.md` |
| Log delivery | `references/ga_logs.md` |
| Tagging | `references/ga_tagging.md` |
| Pricing/billing | `references/ga_pricing.md` |
| Postpay bandwidth/spec changes | `references/ga_postpay_bandwidth.md` |

## Diagnostics

Standard diagnostic flow (run every step in order; do not skip the health-status check):
1. `describe-accelerator` / `get-basic-accelerator` → confirm `State` is `active`.
2. `list-listeners` → confirm listeners are `active` and identify the affected listener.
3. `get-health-status` → you MUST call `aliyun ga get-health-status --biz-region-id cn-hangzhou --listener-id <listener-id>` for the affected listener to obtain per-endpoint health (`Healthy`/`Unhealthy`/`Unknown`) and pinpoint the unhealthy endpoints. Never conclude a health-check diagnosis without running `get-health-status`.

For health-check alarms, follow the ordered steps in `references/ga_diagnostics.md` (`Issue 1: endpoint health check fails`), which starts with `describe-accelerator`, lists listeners, and then calls `get-health-status` to pinpoint unhealthy endpoints.

For Basic accelerators (which have no listeners), diagnose with `get-basic-accelerator`, then `get-basic-ip-set` / `list-basic-accelerate-ips` / `list-basic-endpoints` only when those resources are configured, and always `list-basic-accelerate-ip-endpoint-relations --accelerator-id <ga-id>` (instance-level). State explicitly which parts are not configured.

**Mandatory diagnostic report structure**: every diagnostic or import answer ends with these three sections, in this order, and none may be omitted:

1. `已配置` — each discovered resource and its state.
2. `未配置 / 异常` — every missing or abnormal layer (for example no acceleration region, no endpoint group, no endpoint, no health data). Never leave a missing layer implicit.
3. `后续建议` — for every item in section 2, at least one concrete next step with the exact command that implements it, plus the constraints that apply. Examples: a missing acceleration region → `create-basic-ip-set` (Basic: bandwidth >= 2 Mbps, IPv4 only, exactly one acceleration region); a missing endpoint group → `create-basic-endpoint-group` (region must differ from the acceleration region); missing endpoints → `create-basic-endpoint` followed by `create-basic-accelerate-ip-endpoint-relation`; missing listener or endpoint group on a Standard accelerator → the corresponding `create-*` step from the Standard workflow. A diagnosis that only lists what is missing, without section 3, is incomplete — do not deliver it.

Report the health conclusion separately from the configuration conclusion: when no endpoint is configured, health is "not applicable", not "abnormal".

For common issues (health check failures, poor acceleration, cross-border), see `references/ga_diagnostics.md`.

## Best Practices

1. Always run `scripts/init-session.sh` and use `--user-agent "$GA_USER_AGENT"` on every cloud API call.
2. Always wait for `State=active` before the next step.
3. Keep `ga-config.json` and `ga-listeners.json` under version control.
4. Run drift detection before modifying resources.
5. Enable health checks and application monitors in production.
6. Estimate costs before creating PREPAY or large-bandwidth resources, and obtain the user's explicit second confirmation before any prepaid purchase (see `High-Cost Operations — Mandatory Second Confirmation`).
7. Plan cross-border compliance ahead of time.
8. Use consistent tags for cost allocation and access control.
9. Never expose AccessKey secrets in commands or configuration files.
10. Use the two-step endpoint flow: create the endpoint group first, then register endpoints with `update-endpoint-group`.
11. For Basic accelerators, never create an endpoint group in the same region as the acceleration region.
12. Run the Step 0 pre-flight checks before creating resources — quota usage and same-name collisions first.
13. Validate risky parameter combinations with `--dry-run true` before the real call.
14. On account-level blockers, follow the Blocked-State Protocol — no unsupervised deletions.
15. Keep every wait loop bounded — maximum attempts plus a wall-clock budget (see `Bounded Execution (Mandatory)`).
16. For Basic accelerators, use only the Basic query chain `list-basic-accelerators` → `get-basic-accelerator` → `list-basic-accelerate-ip-endpoint-relations`; never substitute the Standard `list-accelerators` / `describe-accelerator`.
17. End every diagnostic or import answer with the three mandatory sections — `已配置`, `未配置 / 异常`, `后续建议` — and give a concrete command for each missing layer.
18. Finish every endpoint group with an explicit `update-endpoint-group`, even when a retried create or a read-only check already shows the endpoint present.
