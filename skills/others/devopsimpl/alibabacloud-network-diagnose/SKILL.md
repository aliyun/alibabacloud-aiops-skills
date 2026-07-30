---
name: alibabacloud-network-diagnose
description: "[project] [user] Alibaba Cloud private network connectivity diagnosis tool. Use when ECS ping/telnet fails, same-VPC access fails, cross-VPC access fails, VPN or Express Connect is unreachable, NAT Gateway DNAT/SNAT behaves asymmetrically, or the user suspects security group, network ACL, route table, CEN/TR, VPC Peering, VPN Gateway, VBR, or NAT Gateway blocking. Not for classic network, public internet access, DNS resolution, CDN, SLB, or WAF issues."
---

# Alibaba Cloud Private Network Connectivity Diagnosis

## Mandatory First Action

Before reasoning about the cause or running any diagnostic command, execute Step 0 with the skill scripts:

```bash
PYTHON=$(bash scripts/detect_python.sh) || exit 1
$PYTHON scripts/net_common.py check-env
$PYTHON scripts/net_common.py parse-input --input "<all user-provided information>"
```

If `parse-input` returns `workflow_blocked: true` or exits with code `2`, stop and output its `required_action` to the user. Wait for source/destination instance IDs, IP addresses, or VPC IDs and their region. Do not continue diagnosis, infer a local target, or inspect the execution environment. In particular, do not run `ss`, `netstat`, `lsof`, `curl`, `ping`, `nc`, `telnet`, `ip`, `iptables`, `firewall-cmd`, `nslookup`, or inspect `/proc`, nginx, Kubernetes, container, proxy, certificate, host, listener, interface, or local route state. Those describe the AgentHub runner, not the user's Alibaba Cloud network.

Once blocked, do not rerun `parse-input` with fabricated, guessed, example, or default endpoints. A normal second call cannot clear the guard. Only after a new user response supplies endpoint information, parse that response with `--resume-after-user-response`. Using this flag before a real user follow-up is a critical violation.

This gate applies even when the prompt only says that a protocol or port, such as TCP 443, is unreachable. The only permitted next action without a cloud endpoint is to ask for the missing endpoint information.

**Blocked-workflow completion rule**: The first turn is complete as soon as `required_action` is returned. Do not keep a command running while waiting for the user and do not poll, sleep, or retry. Resume only in a later user turn.

## Applicable Scenarios

| Scenario | Typical Issues |
|----------|---------------|
| **Same-VPC instance interconnection** | ECS ping/telnet failure, security group blocks, missing route entries |
| **Cross-VPC access** (VPC Peering / CEN) | Missing cross-VPC routes, CEN route not learned, VPC Peering status abnormal |
| **Cloud-to-IDC** (VPN Gateway) | VPN tunnel status abnormal, routes not propagated, IKE/IPsec configuration issues |
| **Cloud-to-IDC** (Express Connect / VBR) | VBR status abnormal, BGP neighbor down, routes not learned |
| **NAT Gateway DNAT/SNAT** | DNAT asymmetric return path, missing DNAT/SNAT rules, NAT Gateway status abnormal |

**Not applicable**: Classic network, public internet access, DNS resolution (use `dns-resolve-diagnose`), CDN/SLB/WAF configuration.

## Prerequisites

- **Python 3.7+** (required) — scripts use standard library only, no third-party dependencies
- **aliyun CLI** (required): macOS `brew install aliyun-cli`; Linux download from [aliyuncli.alicdn.com](https://aliyuncli.alicdn.com). See [cli-installation-guide.md](references/cli-installation-guide.md).
- **Alibaba Cloud credentials**: Use the aliyun CLI default credential chain. Prefer a configured CLI profile; if no profile is configured, an environment-backed default provider can be used. Diagnosis cannot run without credentials.
- **User input**: Supports any combination — instance IDs, VPC IDs, IP addresses, security group IDs, protocol/port, problem description. The skill intelligently determines the diagnosis path.

> See [ram-policies.md](references/ram-policies.md) for permission details. All operations are read-only.

## Core Principles

> **Must use scripts for diagnosis**: Do not use ping/telnet/nc/traceroute, curl, ss, netstat, lsof, or direct `aliyun` commands. Never inspect or report the AgentHub runner/container's IP addresses, listening ports, processes, certificates, hosts file, proxy, firewall, or Kubernetes configuration as if they were the user's environment. All steps are executed through `net_common.py`, `net_ecs.py`, `net_vpc.py`, `net_cross_vpc.py`, `net_hybrid.py`, and `net_analyze.py`. The wrappers already retry and fall back between official CLI invocation modes. Run each script command once. If it returns a JSON `error`, preserve that file, mark the step failed, and continue only independent script-based checks. Do not retry it with a longer shell timeout, inspect script source to bypass it, invoke `aliyun` directly, or fabricate/modify step JSON.
>
> **Empty endpoint guardrail**: After `parse-input`, if `workflow_blocked` is `true`, output `required_action` and wait for the user. Do not make any cloud API call or execute Step 1 and later. There are no exceptions.
>
> **Multi-fault investigation**: After finding an issue, including a P0 root cause, continue all applicable remaining steps through Step 7. Do not run the final analysis early. The final report must list all problems found.
>
> **Bidirectional route check**: Route checks must cover both forward and return paths. Both VPC route tables and TR route tables require bidirectional verification. When the forward path passes through an intermediary device (e.g., NAT), the return path must also traverse the same device.

## Diagnosis Workflow

Execute steps strictly in order. Output results and conclusions immediately after each step. Save data to `./output/net_diag_<timestamp>/`, analyze each step with `net_analyze.py` and output concise conclusions.

Before the final response, verify the execution log contains Step 0 and exactly one final `scripts/net_analyze.py all --dir "$DIAG_DIR"` call. If either is absent, the workflow is incomplete. Direct `aliyun` commands and manually authored step/report JSON never satisfy a workflow step.

## Observability

All Alibaba Cloud CLI calls must use the same user-agent template during one diagnosis session:

```text
--user-agent AlibabaCloud-Agent-Skills/{SKILL_NAME}/{session-id}
```

Generate one `session-id` per diagnosis session. It must be a 32-character hex string and must be reused by all CLI, SDK, or Terraform calls in that session. Do not use deprecated mechanisms such as `aliyun configure ai-mode` or `export ALIBABA_CLOUD_USER_AGENT`.

The Python wrappers inject this user-agent automatically. Never append `--user-agent`, timeout flags, or OpenAPI flags to a `scripts/*.py` command; only pass arguments shown in that script's command example or `--help` output.

### Step 0: Environment Check & Input Parsing

```bash
PYTHON=$(bash scripts/detect_python.sh) || exit 1
DIAG_DIR="./output/net_diag_$(date +%s)" && mkdir -p "$DIAG_DIR"
$PYTHON scripts/net_common.py check-env
$PYTHON scripts/net_common.py parse-input --input "<all user-provided information>" > "$DIAG_DIR/input.json"
```

Inspect `input.json` before any cloud query. Exit code `2` from `parse-input` is an intentional blocked-workflow signal, not a script failure to work around. If `workflow_blocked` is `true`, stop immediately, output its `required_action` verbatim, and wait for the user response. Do not query a default/common region, attempt discovery, inspect the local environment, or run Step 1. The parser also installs a local guard that makes every cloud API wrapper reject queries until a later `parse-input` receives an endpoint. Otherwise, query extracted instance IDs directly or reverse-lookup extracted IPs via ENI.

On a later turn after the user provides the requested endpoints, resume with `$PYTHON scripts/net_common.py parse-input --resume-after-user-response --input "<new user response>"`. Never use the resume flag in the same turn that created the guard.

### Step 1: Instance & Network Fundamentals

```bash
$PYTHON scripts/net_ecs.py instances --instance-ids <ids> --region <region> > "$DIAG_DIR/instances.json"
$PYTHON scripts/net_ecs.py find-by-ip --ip <ip> --region <region>
$PYTHON scripts/net_ecs.py enis --instance-ids <ids> --region <region> > "$DIAG_DIR/enis.json"
$PYTHON scripts/net_vpc.py vpcs --vpc-ids <vpc_ids> --region <region> > "$DIAG_DIR/vpcs.json"
$PYTHON scripts/net_vpc.py vswitches --vpc-id <vpc_id> --region <region> > "$DIAG_DIR/vswitches.json"
$PYTHON scripts/net_analyze.py step1 --dir "$DIAG_DIR" > "$DIAG_DIR/step1.json"
```

Check instance status (Running), network type (VPC, not classic), whether source and destination are in the same VPC. Output instance information table and scenario determination (same-VPC / cross-VPC / hybrid).

### Step 2: Security Group Diagnosis

```bash
$PYTHON scripts/net_ecs.py sg-rules --instance-ids <all related instance IDs> --region <region> > "$DIAG_DIR/sg_rules.json"
$PYTHON scripts/net_ecs.py sg-check --sg-ids <source SGs> --direction egress --ip <dest IP> --protocol <protocol> --port <port> --region <region>
$PYTHON scripts/net_ecs.py sg-check --sg-ids <dest SGs> --direction ingress --ip <source IP> --protocol <protocol> --port <port> --region <region>
```

Save sg-check results to `$DIAG_DIR/sg_check.json`, then run `$PYTHON scripts/net_analyze.py step2 --dir "$DIAG_DIR" --protocol <protocol> --port <port> --src-ip <source IP> --dst-ip <dest IP> > "$DIAG_DIR/step2.json"`

When both endpoint instance IDs are known, prefer the deterministic combined command below. It resolves security groups from ECS/ENI data and always emits all four directions; use it even when the API reports a normal security group because the user's stated enterprise-SG scenario still requires four-direction evidence:

```bash
$PYTHON scripts/net_ecs.py sg-four-direction-check --source-instance-ids <source IDs> --dest-instance-ids <destination IDs> --source-ip <source IP> --dest-ip <destination IP> --protocol <protocol> --port <port> --region <region> > "$DIAG_DIR/sg_check.json"
```

**Security group type determination**: Check the `sg_type` field in `sg_rules.json`. `enterprise` (enterprise security group) has no default outbound allow and is stateless — check four directions (source egress, dest ingress, dest egress return, source ingress return). `normal` (normal security group) allows all outbound by default — for unidirectional access, only check source egress and dest ingress. Enterprise security group return path check:
```bash
$PYTHON scripts/net_ecs.py sg-check --sg-ids <source SGs> --direction ingress --ip <dest IP> --protocol <protocol> --port 0 --region <region>
$PYTHON scripts/net_ecs.py sg-check --sg-ids <dest SGs> --direction egress --ip <source IP> --protocol <protocol> --port 0 --region <region>
```

Output security group rule match results (allow/deny/no match), annotate blocking rules and remediation suggestions. If protocol/port is unspecified, display the full rule table.

### Step 3: Route Table Diagnosis

> **Bidirectional check is mandatory**

```bash
$PYTHON scripts/net_vpc.py routes --vpc-id <vpc_id> --region <region> > "$DIAG_DIR/routes.json"
$PYTHON scripts/net_vpc.py route-check --route-table-id <source route table ID> --dst-ip <dest IP> --region <region>
$PYTHON scripts/net_vpc.py route-check --route-table-id <dest route table ID> --dst-ip <source IP> --region <region>
```

Save results to `$DIAG_DIR/route_check.json` (keys: "source" and "destination"), then run `$PYTHON scripts/net_analyze.py step3 --dir "$DIAG_DIR" --src-ip <source IP> --dst-ip <dest IP> > "$DIAG_DIR/step3.json"`

Output route match results, next-hop type and status, annotate missing routes, blackhole routes, and incorrect next-hops.

**Route display convention**: Display in **Instance -> VSwitch -> Route Table** chain dimension. Check forward and return next-hop symmetry (e.g., in DNAT scenarios where forward goes through NAT but return points to CEN TR, this is asymmetric routing). Route entries must show the `Origin` field: `CEN` routes cannot be directly deleted/modified (add more specific static routes to override, or use CEN route maps); `Custom` routes can be modified directly; `System` routes cannot be modified.

### Step 4: Network ACL Diagnosis

```bash
$PYTHON scripts/net_vpc.py acls --vpc-id <vpc_id> --region <region> > "$DIAG_DIR/acls.json"
$PYTHON scripts/net_vpc.py acl-check --vpc-id <vpc_id> --vswitch-id <source VSwitch> --direction egress --ip <dest IP> --protocol <protocol> --port <port> --region <region>
$PYTHON scripts/net_vpc.py acl-check --vpc-id <vpc_id> --vswitch-id <dest VSwitch> --direction ingress --ip <source IP> --protocol <protocol> --port <port> --region <region>
```

Save to `$DIAG_DIR/acl_check.json`, then run `$PYTHON scripts/net_analyze.py step4 --dir "$DIAG_DIR" --protocol <protocol> --port <port> --src-ip <source IP> --dst-ip <dest IP> > "$DIAG_DIR/step4.json"`

**CEN scenario additional check**: For Enterprise TR attachments, check NACLs bound to all TR VPC Attachment zone mapping VSwitches on both source and destination sides. Run `$PYTHON scripts/net_cross_vpc.py tr-vpc-attachments --tr-id <tr_id> --region <region> > "$DIAG_DIR/tr_attachments.json"` to obtain `ZoneMappings` VSwitch IDs, then use `net_vpc.py acl-check` on every zone VSwitch in both directions. A deny rule on any zone VSwitch NACL can cause CEN traffic to be dropped. Basic TR attachments do not expose `ZoneMappings`; in that case explicitly record the TR zone VSwitch NACL check as not applicable and check the source and destination workload VSwitch NACLs instead.

For Basic TR, workload VSwitch ACL inspection is mandatory evidence, not a report-only statement. Run `net_vpc.py acls` for both workload VPCs and save `acls_source.json` and `acls_destination.json`; when ACLs are bound, run `acl-check` for source egress and destination ingress and save `acl_check.json`. Never state that workload VSwitch ACLs were checked unless these script outputs exist.

Output ACL evaluation results. If no ACL is bound, state "no blocking". For CEN scenarios, additionally list NACL check results for all TR zone VSwitches.

### Step 5: Cross-Network Connection Check (Conditional)

Execute only for cross-VPC or hybrid cloud scenarios. Choose based on route table next-hop type:

**VPC Peering** (next-hop is VpcPeer):
```bash
$PYTHON scripts/net_cross_vpc.py peering-check --src-vpc <source VPC> --dst-vpc <dest VPC> --region <region> > "$DIAG_DIR/peering.json"
```

**CEN** (next-hop is Attachment or CEN ID is explicitly provided): Prefer `tr-check` for one-step diagnosis:
```bash
$PYTHON scripts/net_cross_vpc.py cen-check --src-vpc <source VPC> --dst-vpc <dest VPC> --region <region> > "$DIAG_DIR/cen.json"
$PYTHON scripts/net_cross_vpc.py tr-check --src-vpc <source VPC> --dst-vpc <dest VPC> --src-region <source region> --dst-region <dest region> --cen-id <cen_id> --dst-ip <dest IP> --src-ip <source IP>
```
`tr-check` output contains `verdict` (ok/route_missing/propagation_missing/association_missing/route_conflict/route_map_deny) and `details`. On failure or when step-by-step troubleshooting is needed, read [cen-diagnosis.md](references/cen-diagnosis.md) for detailed commands and decision logic.

For every cross-region CEN diagnosis, the final report must include this exact statement: "跨地域 CEN 路由不支持通过中间地域中继，源端与目的端必须存在直接的路由学习或 Attachment 配置。" Confirm whether both regions have direct route learning/attachments even when another control is the root cause. `net_analyze.py all` also adds this statement when `input.json` contains a CEN ID and multiple regions.

**VPN Gateway** (next-hop is VpnGateway):
```bash
$PYTHON scripts/net_hybrid.py vpn --vpc-id <vpc_id> --region <region> > "$DIAG_DIR/vpn.json"
```

Tunnel status determination: Information is in the `TunnelStatusSummary` array. A single tunnel is UP when: `State == "active" AND Status == "ipsec_sa_established"`. Do not use the top-level `Status` field of VpnConnection (may be empty). `active_count`/`down_count` are correctly computed. IKE/IPsec configuration is in the `TunnelDetails` array.

Output VPN gateway info and tunnel status table. If `active_count == 0`, annotate all tunnels down; if `> 0`, annotate active tunnel details.

**VPN Gateway internal routing**: After traffic enters the VPN gateway, an internal route table selects the next-hop VCO. Priority: P0 specific routes > P1 system routes > P2 static routes (policy routes > destination routes) > P3 BGP dynamic routes. When multiple IPsec connections exist under the same VPN gateway, traffic is forwarded based on route matching. Mixing destination routes, policy routes, and BGP (two or three simultaneously) is not recommended. When VPC routes exist but traffic still fails, investigate VPN gateway internal destination routes, policy routes, and BGP configuration. See [VPN Gateway Route Overview](https://help.aliyun.com/zh/vpn/sub-product-ipsec-vpn/user-guide/vpn-gateway-route-overview/).

**Express Connect / VBR** (next-hop is RouterInterface or VBR):
```bash
$PYTHON scripts/net_hybrid.py vbr --vbr-id <vbr_id> --dst-ip <peer or destination IP> --region <region> > "$DIAG_DIR/vbr.json"
```
The VBR result includes its route table ID, VLAN RouterInterface ID, route entries, longest-prefix match for `--dst-ip`, BGP groups, and BGP peers. Do not use `net_vpc.py` or direct CLI calls for a VBR route table.
When a VBR is a CEN child instance and routes are missing, run `$PYTHON scripts/net_cross_vpc.py vbr-route-sync-check --cen-id <cen_id> --vbr-id <vbr_id> --region <region> > "$DIAG_DIR/vbr_route_sync.json"`. If `verdict` is `route_sync_missing`, first check route maps with `$PYTHON scripts/net_cross_vpc.py cen-route-maps --cen-id <cen_id> --cen-region-id <region> --region <region> > "$DIAG_DIR/route_maps.json"` to rule out deny rules, then conclude. If no CEN association is present, explicitly state: "如果 VBR 不是 CEN 子实例，跳过此步骤". Do not silently omit the route synchronization check. See [cen-diagnosis.md](references/cen-diagnosis.md).

Analysis: `$PYTHON scripts/net_analyze.py step5 --dir "$DIAG_DIR" --scenario <scenario type> > "$DIAG_DIR/step5.json"`. Output connection status and health check.

### Step 6: NAT Gateway Diagnosis (Conditional)

Execute when route next-hop is NatGateway, NAT/DNAT/SNAT is involved, or `parse-input` contains `nat_gw_ids`:
```bash
$PYTHON scripts/net_vpc.py nat-check --vpc-id <vpc_id> --region <region> > "$DIAG_DIR/nat_check.json"
$PYTHON scripts/net_analyze.py step-nat --dir "$DIAG_DIR" --src-ip <source IP> --dst-ip <dest IP> --protocol <protocol> --port <port> > "$DIAG_DIR/step_nat.json"
```

Check NAT Gateway status (Available), whether DNAT rules match the destination IP/port, whether SNAT rules cover the source IP range. **DNAT return path check**: The backend ECS return route (destination is client IP) must match the NAT Gateway via longest prefix match. If a CEN-propagated specific route overrides the broader NAT-bound route, return traffic bypasses the NAT Gateway and TCP connections fail. Annotate root cause and remediation when asymmetric routing is detected.

### Step 7: Comprehensive Analysis & Report

```bash
$PYTHON scripts/net_analyze.py all --dir "$DIAG_DIR"
```

This command is mandatory even when earlier checks returned errors. Do not write the final diagnosis manually before it succeeds. If it returns an error, fix missing/malformed step JSON and retry; the final response must be rendered from its `conclusion`, `severity`, `root_causes`, `check_table`, and `recommendations` fields.

For a cross-region CEN scenario, confirm the final output contains the exact mandatory sentence from Step 5 before responding. For a NAT/DNAT scenario, confirm `step_nat.json` exists and the final output discusses the backend return route and path symmetry. If either scenario-specific check is missing, rerun the corresponding Skill script and then rerun `net_analyze.py all`; never fill the gap manually.

Use only these analysis filenames: `step1.json`, `step2.json`, `step3.json`, `step4.json`, `step5.json`, and `step_nat.json`. Each contains a top-level `checks` array. `net_analyze.py all` automatically regenerates a missing or malformed step file when its corresponding raw script output exists. Never create `step*_summary.json`, `step6.json`, `step7.json`, or a manual substitute.

Key fields: `conclusion` (one-sentence summary), `severity` (critical/warning/normal), `root_causes` (sorted P0->P3, see [root-cause-priority.md](references/root-cause-priority.md)), `check_table` (check result summary table), `recommendations` (suggested actions). Render `check_table` as a Markdown table, list `root_causes` and `recommendations`.

## Degradation Strategy

| Unavailable Resource | Fallback |
|---------------------|----------|
| `aliyun` CLI not installed / credentials missing | Cannot degrade — prompt to install/configure |
| ECS permissions missing | Skip instance/security group checks, VPC/route/ACL only |
| VPC permissions missing | Skip route/ACL checks, ECS/security group only |
| CBN permissions missing | Skip CEN checks |
| Only single-endpoint info | Diagnose known endpoint only |
| Protocol/port unspecified | Display full rule tables |
| Region uncertain | Try cn-hangzhou/shanghai/beijing/shenzhen/chengdu in sequence |
| Script timeout/error | The wrapper already retried and tried the supported CLI fallback. Preserve the JSON error, continue independent script checks, and report the failed step. Never use direct `aliyun` or manual JSON. |

**Report template**: When generating reports, read [report-template.md](references/report-template.md), which includes diagnosis conclusion, check result summary table, issue list (by severity), recommended actions, and detailed data (route tables displayed in Instance -> VSwitch -> Route Table dimension).

## Important Notes

- For permission errors, see [ram-policies.md](references/ram-policies.md)
- Must distinguish between normal and enterprise security groups (see Step 2)
- VSwitches with no bound ACL allow all traffic by default
- OS-level firewalls (iptables/firewalld/Windows Firewall) are out of scope — suggest users check when API-level diagnosis is normal
- **CEN route learning scope**: CEN-propagated routes are distributed to **all route tables** in the VPC (including system and custom route tables). Do not assume "placing ECS and TR in different VSwitches avoids CEN route interference"
- **AutoPublishRouteEnabled & RoutePropagationEnable dual-layer control**: Both must be true for CEN routes to appear in VPC route tables. `RoutePropagationEnable` can be disabled on the system route table (not limited to custom route tables). See [cen-diagnosis.md](references/cen-diagnosis.md) section 5f for decision logic
- **Cross-region routes cannot transit**: CEN cross-region routes cannot be relayed through an intermediate region. E.g., if Beijing VPC and Shenzhen VPC are both attached to Shanghai TR, Beijing-Shenzhen connectivity still requires explicit cross-region configuration
- **TR zone VSwitch NACL traffic path**: In CEN scenarios, traffic does not necessarily traverse the "nearest" zone VSwitch. Source-side TR zone VSwitch NACLs affect return traffic (TR -> ECS) entering the source VPC; destination-side TR zone VSwitch NACLs affect forward traffic (TR -> ECS) entering the destination VPC. Missing checks on either side can lead to "fixed one issue but still not working"
- **DNAT asymmetric routing**: When CEN-propagated specific routes override the broader NAT-bound route, return traffic bypasses the NAT Gateway and TCP connections fail (SYN enters via NAT, SYN-ACK exits via CEN, source IP mismatch). See Step 6
- **VPN Gateway internal routing**: A VPC route entry pointing to the VPN gateway is only the first step — after traffic enters the VPN gateway, it uses an internal route table (destination routes/policy routes/BGP) to select the next-hop VCO. When VPC routes and tunnel status are both normal but traffic still fails, investigate VPN gateway internal route configuration. Priority: policy routes > destination routes > BGP dynamic routes. See Step 5

## References

- Detailed API parameter reference: [api-reference.md](references/api-reference.md)
- Diagnosis examples: [examples.md](references/examples.md)
- CLI installation guide: [cli-installation-guide.md](references/cli-installation-guide.md)
