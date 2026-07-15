---
name: alibabacloud-ecs-vpc-publicnetwork-troubleshoot
description: Diagnose Alibaba Cloud ECS public network access problems and VPC cloud service public network access problems. Covers ECS public network access, ECS public IP reachability, and ECS security group blocking (automatically handling the NAT-gateway egress path for instances without a public IP); and VPC cloud service public network access with NAT gateway, SNAT, route and EIP checks for DataWorks, SAE, ACK and other services. Use this when troubleshooting public network connectivity failures for ECS instances or VPC cloud services.
---

# ECS/VPC Public Network Connectivity Troubleshooting

Automated diagnosis of public network connectivity for Alibaba Cloud ECS instances and VPC cloud services. **Two core capabilities only:**

1. **ECS public network diagnosis** — full-chain check for an ECS instance covering public IP reachability and security-group blocking; the NAT-gateway egress path for instances without a public IP is handled automatically as a sub-path (the script picks Branch A / Branch B by itself).
2. **VPC cloud service public network diagnosis** — public egress check for a cloud service (DataWorks / SAE / ACK, etc.) behind a VSwitch (NAT gateway / SNAT / route / EIP).

## Execution Principle (script-only, no fallback)

All diagnostic operations MUST be performed by invoking the bundled Python scripts under `scripts/`. There are exactly three:

| Allowed invocation | Purpose |
|--------------------|---------|
| `python3 scripts/sts_create.py` | Obtain/validate credentials (runs first) |
| `python3 scripts/ecs_public_troubleshoot.py` | ECS public network diagnosis |
| `python3 scripts/vpc_service_public_troubleshoot.py` | VPC cloud service diagnosis |

**Forbidden — do NOT** reproduce the diagnostic logic by any other means (each is a structural violation, even if the output looks correct):
- running `aliyun ecs ...` / `aliyun vpc ...` / `aliyun natgateway ...` / `aliyun antiddos-public ...` / `aliyun cloudfw ...` / `aliyun bssopenapi ...` or any other `aliyun` CLI command for diagnosis;
- running `aliyun configure get` or any command to fetch credentials manually;
- writing numbered/ad-hoc helper scripts (`01_describe_ecs.sh`, ...) or inline SDK/`curl`/HTTP code.

If a script fails (non-zero exit, no JSON, credential/authorization error), **stop and report the error** — never fall back to any of the above.

## Credentials (do not handle manually)

`sts_create.py` runs first and writes credentials to the local cache `scripts/.sts_cache.json`. The two main scripts (`ecs_public_troubleshoot.py`, `vpc_service_public_troubleshoot.py`) **read that cache automatically**. The agent MUST NOT:
- export `ALIBABA_CLOUD_*` variables manually, pass `--access-key-id` / `--access-key-secret` / `--sts-token` (the scripts do not accept them), or run `aliyun configure get`;
- echo plaintext AK/SK/token on the command line.

If `sts_create.py` fails, abort immediately and report the credential/authorization error.

## User Confirmation (required before any API call)

This skill makes **read-only** Alibaba Cloud API calls only (`Describe*` / `GetCallerIdentity` queries); it never creates, modifies, deletes, restarts, or otherwise changes any resource. Before invoking any script:

1. **Restate the diagnostic scope** to the user — the target resource (`instance_id` / `vswitch_id`), the `region_id`, and that only read-only diagnostic APIs will be called against that single resource.
2. **Obtain confirmation to proceed.** An explicit diagnostic request that already names the target resource is sufficient authorization: restate the scope and proceed. If the target or scope is ambiguous, or the user has not clearly authorized the check, **ask the user and wait for confirmation before making any API call**.
3. Never call any API before this confirmation, and never expand scope beyond the confirmed resource.

## Trigger Conditions

- ECS cannot access / be accessed from the public network; public IP reachability issues
- ECS ping / connectivity timeout to the public network; NAT gateway / SNAT outbound issues
- Security group blocking public access to an ECS instance
- VPC cloud service (DataWorks / SAE / ACK) cannot access the public network

## Input Parameters

| Parameter | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| region_id | string | Yes | Alibaba Cloud region ID | cn-hangzhou |
| test_scenario | string | Yes | `ecs_public` / `vpc_service_public` (inferred from identifiers) | ecs_public |
| instance_id | string | ECS scenario | ECS instance ID | i-bp116m5pkhsle6xm5pl8 |
| vswitch_id | string | VPC scenario | VSwitch ID | vsw-bp1xat3xsvck79y8zo8yo |
| uid | string | No | Account UID (auto-obtained from credentials if omitted) | 1552974654746705 |
| service_type | string | No | Cloud service type (VPC scenario): dataworks / sae / ack / others | dataworks |
| output_format | string | No | table / json / markdown | table |

**Mandatory-parameter gate**: `region_id` plus the scenario identifier (`instance_id` for ECS, `vswitch_id` for VPC) are required. Extract everything already present in the user's prompt first. If a mandatory field is still missing, ask the user once; if it is still not provided, abort with:

```
Missing required parameters: [<comma-separated list>]. Aborting diagnostic workflow.
```

Do NOT fabricate/guess mandatory values or read external metadata to infer them.

## Module Index

| Module | Purpose | File |
|--------|---------|------|
| Preparation | Credential acquisition and CLI call templates | [references/module1_preparation.md](references/module1_preparation.md) |
| RAM Policies | Minimum read-only privilege list | [references/ram-policies.md](references/ram-policies.md) |
| Scenario 1: ECS Public Network | ECS script invocation, JSON output, status logic | [references/module2_ecs_public.md](references/module2_ecs_public.md) |
| Scenario 2: VPC Service Public | VPC script invocation, JSON output, status logic | [references/module3_vpc_service.md](references/module3_vpc_service.md) |
| Output & Judgment | Info-table format and status column logic | [references/module4_output.md](references/module4_output.md) |
| Solutions | Remediation advice for abnormal items | [references/module5_solution.md](references/module5_solution.md) |

> Load on demand: read only the reference relevant to the current task.

## Orchestration

```
Input Parsing (extract region_id + identifiers)
  └─▶ Credentials: python3 scripts/sts_create.py  (abort on credential/authorization error)
        └─▶ Scenario Detection: instance_id → ECS scenario; vswitch_id → VPC scenario
              └─▶ Main Script: ecs_public_troubleshoot.py / vpc_service_public_troubleshoot.py
                    │      (parallel sub-checks: ECS/SG, VPC/Route/NAT/SNAT/EIP, DDoS, CFW, account status)
                    └─▶ Result Rendering (module4_output.md): Branch A (direct public) or Branch B (NAT)
                          └─▶ Solution Output for abnormal items (module5_solution.md)
```

Principles: strict order (abort on any step failure, never skip or fall back); the main script decides Branch A vs Branch B by whether the ECS has a public IP/EIP.

## Execution Flow

1. **Scope confirmation** (before any API call): restate the target resource, `region_id`, and read-only scope to the user and confirm to proceed, per "User Confirmation" above. Do NOT invoke any script or API before this step.
2. **Credential pre-check**: run `python3 scripts/sts_create.py`; on `SDK.InvalidCredential` / `InvalidAccessKeyId` / `SignatureDoesNotMatch` / `Forbidden` / any auth error / non-zero exit, abort and report.
3. **Scenario detection**: `instance_id` → ECS scenario; `vswitch_id` → VPC scenario.
4. **Main script invocation** (queries all sub-items in parallel).
5. **Script failure circuit breaker**: on non-zero exit / no JSON / unhandled exception, print stderr and abort — do NOT retry with ad-hoc CLI or inline code.
6. **Result rendering**: parse JSON, render info table per module4_output.md (Branch A or Branch B). For ECS, the security-group check is part of the full chain; when the security group is abnormal, state which direction/port is blocked in the report.
7. **Solution output**: for any abnormal item, output remediation per module5_solution.md; skip if all normal.

### Scenario 1 (ECS) Invocation

```bash
python3 scripts/ecs_public_troubleshoot.py \
  --region-id <region_id> \
  --instance-id <instance_id> \
  [--uid <UID>]
```

### Scenario 2 (VPC cloud service) Invocation

```bash
python3 scripts/vpc_service_public_troubleshoot.py \
  --region-id <region_id> \
  --vswitch-id <vswitch_id> \
  [--uid <UID>]
```

> Credentials are read from `sts_create.py`'s local cache (`scripts/.sts_cache.json`); scripts do not accept credential parameters. Never export plaintext credentials on the command line.

## Observability

All OpenAPI calls carry a unified User-Agent `AlibabaCloud-Agent-Skills/alibabacloud-ecs-vpc-publicnetwork-troubleshoot/{session-id}` for call-chain traceability; the session ID is generated once at skill start and shared across scripts via the `SKILL_SESSION_ID` environment variable.

## Important Notes

1. **Credential security**: never hardcode AK/SK; rely on the cache written by `sts_create.py` / SDK default chain.
2. **No fallback**: if any scripted step fails, abort and report; do NOT fall back to raw `aliyun` CLI, ad-hoc/numbered shell scripts, inline SDK code, or evaluation-metadata guessing.
3. **Permissions**: requires read-only access for ECS, VPC, Cloud Firewall, DDoS, BSS. See [references/ram-policies.md](references/ram-policies.md).
4. **Network constraints**: VPC has no public egress by default (needs NAT Gateway / IPv4 Gateway / EIP); inbound public access to ECS needs security-group ingress rules.
5. **ICMP default**: if the security group does not explicitly allow ICMP, it is judged "ICMP blocked"; state this in the report.
6. **Branch decision**: accurately determine whether the ECS has a public IP/EIP to select the correct info table.
7. **No scope creep**: diagnose only the requested instance/vswitch; do not proactively probe other resources.
8. **Dependencies**: aliyun-cli (DDoS/CFW/EIP supplementary queries invoked *inside* the scripts) and Python SDK (`pip install -r scripts/requirements.txt`).

## Example Scenarios

### Example 1: ECS with public IP (Branch A)

**Input**: "Check the public connectivity of instance i-bp116m5pkhsle6xm5pl8 in cn-hangzhou."

1. Parse: region_id=cn-hangzhou, instance_id=i-bp116m5pkhsle6xm5pl8, scenario=ecs_public
2. Run `sts_create.py` for credentials
3. Run `python3 scripts/ecs_public_troubleshoot.py --region-id cn-hangzhou --instance-id i-bp116m5pkhsle6xm5pl8`
4. Script outputs JSON with `branch="A"` → render Direct Public info table (instance / security group / DDoS / CFW)
5. Output remediation for any abnormal item

### Example 2: ECS security group blocking public access

**Input**: "Public access to TCP 80 of i-bp116m5pkhsle6xm5pl8 in cn-hangzhou is blocked — is the security group blocking it?"

1. Parse: region_id=cn-hangzhou, instance_id=i-bp116m5pkhsle6xm5pl8, scenario=ecs_public
2. Run `sts_create.py`
3. Run the ECS script (same command); the full-chain check includes the security group
4. Render the info table; if the security group is abnormal, state which ingress rule blocks the port
5. Output remediation for the abnormal security-group item

### Example 3: DataWorks in VPC cannot access public network

**Input**: "DataWorks cannot access the public network, VSwitch vsw-bp1xat3xsvck79y8zo8yo in cn-hangzhou."

1. Parse: region_id=cn-hangzhou, vswitch_id=vsw-bp1xat3xsvck79y8zo8yo, service_type=dataworks, scenario=vpc_service_public
2. Run `sts_create.py`
3. Run `python3 scripts/vpc_service_public_troubleshoot.py --region-id cn-hangzhou --vswitch-id vsw-bp1xat3xsvck79y8zo8yo`
4. Script outputs JSON (VSwitch / NAT / route / SNAT / EIP / DDoS / CFW checked) → render VPC cloud service info table
5. Output remediation for any abnormal item
