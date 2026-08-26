---
name: alibabacloud-lb-healthcheck
description: |
  Read-only health-check diagnostics for Alibaba Cloud load balancers
  (CLB/ALB/NLB). Collects listener health-check configuration, forwarding
  rules, server groups and backend server probe status, and produces a
  structured diagnosis report; never changes any configuration.
  Use when health checks fail, backend servers are marked unhealthy, or
  the customer asks about load balancer health-check configuration.
  Triggers: "health check failed", "unhealthy backend server",
  "backend probe abnormal", "backend server unhealthy",
  "SLB health check diagnosis", "CLB health check diagnosis",
  "ALB health check diagnosis", "NLB health check diagnosis",
  "listener health check configuration query",
  "server group probe status".
---

# Load Balancer Health-Check Diagnostics

Diagnose health-check issues on Alibaba Cloud load balancers: "health check failed", "backend server unhealthy", "listener health check configuration", "which backends are being probed and why they fail".

Core approach: route to the matching diagnosis script by instance ID prefix, collect listeners, forwarding rules, server groups and per-backend probe status, then deliver a structured report plus per-server self-check commands.

## Observability

All OpenAPI calls (invoked through the aliyun CLI) include:
- **User-Agent**: `--user-agent AlibabaCloud-Agent-Skills/{SKILL_NAME}/{session-id}`
- **SKILL_NAME**: `alibabacloud-lb-healthcheck`
- **session-id**: 32-character hex string generated per diagnostic session

## Prerequisites

1. **aliyun CLI 3.x** with the `slb`, `alb`, `nlb` and `vpc` plugins installed. All API calls go through the CLI plugin mode (e.g. `aliyun slb describe-health-status`); there are no Python SDK dependencies.
2. **Alibaba Cloud credentials** — resolved automatically by the aliyun CLI default credential chain (environment variables or ~/.aliyun/config.json). Do not read, print, or pass AK/SK/STS tokens explicitly.
3. **Target inputs**: the load balancer instance ID (required) and the region (optional, auto-resolvable; see Missing Information Handling).

## Instance Routing

Route by the instance ID prefix and load only the guide of the matched product:

| Prefix | Product | Script | Reference Guide |
|--------|---------|--------|-----------------|
| `lb-` | CLB (Classic Load Balancer) | `scripts/diagnose_clb.py` | [references/clb-guide.md](references/clb-guide.md) |
| `alb-` | ALB (Application Load Balancer) | `scripts/diagnose_alb.py` | [references/alb-guide.md](references/alb-guide.md) |
| `nlb-` | NLB (Network Load Balancer) | `scripts/diagnose_nlb.py` | [references/nlb-guide.md](references/nlb-guide.md) |

## Orchestration

One diagnosis run touches these products, always in this order, always read-only:

```
instance ID prefix
   |
   v
[1] STS  GetCallerIdentity            -- confirm the caller identity behind the CLI credential chain
   |
   v
[2] SLB | ALB | NLB  instance attribute  -- enumerate listeners of the matched product only
   |
   v
[3] same product, per listener        -- health-check configuration of each listener
   |                                     (HTTP/HTTPS listeners additionally: forwarding rules)
   v
[4] same product, per server group    -- server group members (backend servers)
   |
   v
[5] same product, per listener        -- backend probe status, merged onto [4] by server ID + port
   |
   v
[6] VPC  DescribeVSwitches            -- ALB/NLB only: vSwitch CIDRs for probe source context
   |                                     (skipped for CLB, whose probe range is fixed)
   v
report tables + Graceful Degradation Log
```

Decision criteria at each branch point:

| Decision | Input | Rule |
|----------|-------|------|
| Which product API set and script | Instance ID prefix | `lb-` -> SLB/CLB, `alb-` -> ALB, `nlb-` -> NLB (see Instance Routing) |
| Which listener attribute API | Listener protocol | TCP / UDP / HTTP / HTTPS each have their own attribute query on CLB; ALB/NLB expose one listener list per product |
| Whether to read forwarding rules | Listener protocol | Only for HTTP/HTTPS listeners; L4 listeners have none |
| Which server group API | Group reference on the listener | vServer group id, master-slave group id, or neither (instance-level default backends) |
| Whether to resolve vSwitch CIDRs | Product | ALB/NLB only; CLB probes come from a fixed range |
| Which listeners to visit at all | `--listener-protocols` / `--listener-ports` | Filters are applied before any per-listener loop, so a narrowed scope costs fewer calls |
| Continue or abort after a failed query | Error kind | Permission denial and per-entity failures are recorded and the run continues; only a failed first instance query leaves an empty report skeleton (both land in the degradation log) |

## Usage

The three scripts share an identical parameter interface:

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--load-balancer-id` | Yes | Instance ID (`lb-xxx` / `alb-xxx` / `nlb-xxx`) |
| `--region` | No | RegionId, e.g. `cn-hangzhou`. Fallback: env vars (`ALIBABA_CLOUD_REGION_ID` etc.) → current profile of `~/.aliyun/config.json` → exit with guidance |
| `--format` | No | `json` or `markdown`; default `markdown` |
| `--output` | No | Report file path; default stdout |
| `--listener-protocols` | No | Filter listeners by protocol, comma separated (e.g. `HTTP,HTTPS` or `TCP,UDP`) |
| `--listener-ports` | No | Filter listeners by port, comma separated (e.g. `80,443`) |

```bash
# CLB
python3 scripts/diagnose_clb.py --load-balancer-id lb-xxx --region cn-hangzhou \
  --output output/lb-xxx-healthcheck.md

# ALB, scoped to ports 80/443
python3 scripts/diagnose_alb.py --load-balancer-id alb-xxx --listener-ports 80,443 \
  --output output/alb-xxx-healthcheck.md

# NLB, scoped to L4 protocols
python3 scripts/diagnose_nlb.py --load-balancer-id nlb-xxx --listener-protocols TCP,UDP \
  --output output/nlb-xxx-healthcheck.md
```

Every Markdown report ends with a fixed `## Graceful Degradation Log` section listing queries that degraded (for example, a permission-denied probe-status query) instead of aborting the diagnosis.

## Read-Only Absolute Rule

This skill is strictly read-only: only `Describe*` / `List*` / `Get*` queries are allowed. Never execute any Update / Delete / Modify / Create / Set operation — no listener, server group, forwarding rule or instance configuration changes — even when the user asks to "fix" something. Report findings and recommendations instead.

## Missing Information Handling (HITL)

**MANDATORY AUTO-FILL DECLARATION.** Whenever any target input is not given by the user and you fill it in yourself instead of asking, the final reply (or the report metadata) **MUST** carry an explicit auto-fill declaration naming the item and its source — e.g. "Instance ID auto-located via a read-only load balancer list query: lb-xxx" or "Region auto-resolved from ~/.aliyun/config.json: cn-hangzhou". A scope line such as "diagnosis scope: all instances named *-test" is **not** a declaration: it states what was covered, not that the value was auto-filled. Stating a bare conclusion over auto-filled inputs without this declaration is a violation.

1. **Load balancer ID missing** — auto-fill first, ask second. Try to resolve the target yourself with at most three read-only list queries, then **declare it** per the rule above: state plainly that the instance was not specified, that you auto-located it, which query produced it, and on what basis you picked it. Never fabricate an instance ID or present a name-based guess as a confirmed target. If the queries yield no single target, report the candidates you found (or that you found none), say what you could not determine, and stop there — one question at most, and never a second round of questions.
2. **Region missing**: the scripts auto-resolve the region from environment variables, then from the current profile of `~/.aliyun/config.json`. When the region is auto-filled, declare the source explicitly in the response, e.g. "Region auto-resolved from ~/.aliyun/config.json: cn-hangzhou". If no source yields a region, ask the user for the RegionId.

## Report Delivery

1. Always write the full report to a file with `--output output/<instance-id>-healthcheck.md`.
2. In the conversation, reply only with the file link plus one key conclusion (e.g. "3 backends failing health checks" or "all backends healthy"); do not paste full tables or report sections into the chat.
3. Results inside the report must be presented as tables; never paste raw API JSON.
4. Deduplicate fields sourced from multiple APIs — the same parameter must not be repeated across tables.

## Customer-Facing Script Template

The customer-facing script is the wording handed to the customer when backends fail health checks. It is **never written into the Markdown report file** — it is output as a standalone section in the conversation body so the user can copy it directly. If the script stdout or the generated report contains customer-facing wording, remove it from the file and move it to the conversation body.

### General Rules

1. Written in the voice of an Alibaba Cloud after-sales engineer, plain text only — no tables in the customer-facing script.
2. State only abnormal facts and customer action items. No background explanations (e.g. same-VPC probing bypasses security groups, probe source CIDR, internal dedicated-line details) and no internal reasoning.
3. No low-level inference: never guess root causes for error codes without evidence.
4. Anything not determinable goes into a numbered "customer self-check plan" that the customer can follow step by step.

### Banned Words

Never use the following in the opening or closing paragraph: "probe completed" / "diagnosis completed"; any region name or region alias (e.g. `cn-hangzhou` / `China (Hangzhou)`); layer terminology such as "Layer 4 / Layer 7 / L4 / L7"; "health check probing completed / this probe covered N listeners". State conclusions directly and use protocol + port instead of layer terms.

### Opening Paragraph Templates

Abnormal case:

> Hello, instance {Instance ID} currently has {N} backend servers failing health checks; they have been isolated by {CLB|ALB|NLB} and no longer receive traffic. Please log into each backend server below and run the corresponding commands to troubleshoot:

All-normal case:

> Hello, instance {Instance ID} currently passes all backend server health checks; no abnormal backends were found. If the business is still affected, continue investigating from directions such as the network path and application-layer timeouts.

### Per-Server Self-Check Blocks

Each abnormal backend block starts with its owning server group / listener entry plus the health-check protocol / port / path / method, followed by the five-step commands defined in [Backend Server Self-Check Commands](#backend-server-self-check-commands). Background data at the top of a block states probe facts and parameters only, never inferred causes. Command lines contain the command itself only — no trailing "— to verify xxx" explanations. Product-specific structure, security-group step conditions, tcpdump filter expressions and entry-point deduplication rules are defined by the per-product guides ([references/clb-guide.md](references/clb-guide.md), [references/alb-guide.md](references/alb-guide.md), [references/nlb-guide.md](references/nlb-guide.md)). Multi-port servers follow Pitfall 3.

### Template Validation Checklist

1. Never merge servers: different backend servers never share one command list; no `grep -E 'port1|port2'` aggregation.
2. Every self-check block must state its owning server group / listener entry and the health-check protocol / port / path / method.
3. The block's background data states probe facts and parameters only; it never infers causes.
4. Command lines output the command itself only; no explanatory suffixes.
5. The opening paragraph contains no background explanation; the closing never adds boilerplate such as "self-check first, contact us if needed".
6. Exception reason codes never appear in the customer-facing script — they stay in the engineer report tables only.
7. Multi-port wording follows the per-port vs "Common:" format defined in Pitfalls.

## Backend Server Self-Check Commands

When backends fail health checks, hand these commands to the customer (run on each failing backend server; replace `<PORT>`, `<PATH>`, `<METHOD>` and `<PROBE_IP>` with values from the report):

1. Verify the service is listening:
   - TCP/HTTP/HTTPS: `ss -tlnp | grep ':<PORT>'`
   - UDP: `ss -ulnp | grep ':<PORT>'`
2. Verify local connectivity (pick by health-check protocol):
   - HTTP: `curl -v -X <METHOD> http://127.0.0.1:<PORT><PATH>`
   - HTTPS: `curl -v -k -X <METHOD> https://127.0.0.1:<PORT><PATH>`
   - TCP: `telnet 127.0.0.1 <PORT>`
   - UDP: skip this step
3. Verify host firewall rules: `iptables -L INPUT -n -v --line-numbers` and `systemctl status firewalld && firewall-cmd --list-all`
4. Verify routing: `ip route show` and `ip rule show`
5. Capture probe packets to confirm they arrive:
   - CLB: `tcpdump -i eth0 'src net 100.64.0.0/10 and tcp port <PORT>' -nn -c 20`
   - ALB/NLB: `tcpdump -i eth0 'tcp port <PORT> and (host <PROBE_IP_1> or <PROBE_IP_2>)' -nn -c 20`

## Pitfalls

1. **Always pass listener filters when the scope is limited.** When the user specifies a layer (L4/L7), protocols, or specific ports, call the script with `--listener-protocols` and/or `--listener-ports` to avoid querying every listener, wasting credits and producing redundant output. All three scripts support both filters.
2. **tcpdump multi-IP filters need parentheses.** ALB/NLB have multiple health-check probe source IPs, and in tcpdump expressions `and` binds tighter than `or`. Correct: `tcpdump -i eth0 'tcp port 80 and (host 172.22.0.52 or 172.22.0.51 or 172.16.10.170)' -nn -c 20`. Wrong (`and host A or B or C` parses as `(port 80 and host A) or B or C`): `tcpdump -i eth0 tcp port 80 and host 172.22.0.52 or 172.22.0.51 or 172.16.10.170 -nn -c 20`. CLB uses the single expression `src net 100.64.0.0/10` and has no such issue.
3. **Multi-port customer wording format.** When the same backend server has multiple ports under one entry: list per-port steps (ss / curl / telnet) one port at a time, each port with its own step group; place common steps (iptables / route / tcpdump) at the end under a "Common:" label that continues the numbering. Never mix per-port and common steps under a single label.

## Error Handling

| Error | Cause | Resolution |
|-------|-------|------------|
| No credentials found | Default credential chain not configured | Configure the aliyun CLI default credential chain (run `aliyun configure`) |
| Region cannot be resolved | No `--region`, no region env var, no profile region | Pass `--region <RegionId>` explicitly or set `ALIBABA_CLOUD_REGION_ID` |
| Permission denied (403) on a query | RAM policy lacks the specific read action | The script degrades gracefully and logs it in `## Graceful Degradation Log`; grant the action per [references/ram-policies.md](references/ram-policies.md) |
| Instance not found / wrong region | Instance ID and region mismatch | Confirm the instance ID prefix and the correct region with the user |

## References

- Per-product diagnosis guides (load only the matched one): [references/clb-guide.md](references/clb-guide.md), [references/alb-guide.md](references/alb-guide.md), [references/nlb-guide.md](references/nlb-guide.md)
- Per-product API and field reference: [references/clb-reference.md](references/clb-reference.md), [references/alb-reference.md](references/alb-reference.md), [references/nlb-reference.md](references/nlb-reference.md)
- Official API documentation links (read on demand only): [references/api-doc-links.md](references/api-doc-links.md)
- Required RAM permissions: [references/ram-policies.md](references/ram-policies.md)
