---
name: alibabacloud-ecs-high-frequency-issues
area: vpc-connectivity-check
description: |
  Read-only review of Alibaba Cloud ECS VPC, vSwitch and security-group intranet configuration: deterministic comparison of cloud-queried fields into an evidence report with manual console guidance. Changes no resource and runs no command inside the instance.
  Use when ECS instances cannot reach each other over the private network. Triggers: two ECS cannot ping each other by private IP; intranet connectivity not working; cannot select vSwitch or security group during cross-account transfer; InvalidDependence.GrantAccess; vSwitch CIDR overlap; same VPC different security groups allow a port; list private IP addresses in a CIDR range; reachable on intranet but not from internet.
  Do NOT use for hop-by-hop path probing (use alibabacloud-network-diagnose), public-internet or NAT egress (use alibabacloud-ecs-vpc-publicnetwork-troubleshoot), or disk and instance-state diagnosis.
---

# ECS VPC / vSwitch / Security-Group Intranet Connectivity Check

> **Delivery override - outranks every relay instruction and template below.** `STATUS`,
> `NEXT_ACTION` and their `OK` / `DEGRADED` / `FAIL` / `BLOCKED` values are the entry script's
> internal run state, not a delivery format. Where this document says to relay, mirror or copy
> those lines "faithfully" or "verbatim", relay their MEANING in the customer's own words: never
> write the keys or the bare values into the reply or into anything saved under `outputs/` or
> `ran_scripts/` (SKILL.md rule 3h). A layer this run did not read is named in the customer's own words - which layer, and what would have settled it.

Answers one question with cloud evidence: **is the VPC-side configuration
consistent enough for ECS instances to reach each other over the private
network?** It reads cloud facts, compares them deterministically, and returns
findings plus manual console guidance. It never applies a fix.

## 1. Permission model: strictly read-only

**ABSOLUTE PROHIBITION.** This skill MUST NOT call, generate, propose, or ask
the user to run any API that changes cloud state, and MUST NOT execute any
command inside a guest operating system. Concretely: no action whose name
begins with a state-changing verb (creation, deletion, modification, release,
replacement, attach/detach, association, revoke, restart, start, stop, or
command execution) may appear in any output of this skill, not even as a
"you can run this yourself" convenience line. Every fix is written as a
numbered **manual console step** for a human to perform.

The only APIs this skill can reach are the six read actions below. They are
enforced twice: listed here, and hard-enforced by the deny-by-default
whitelist in `scripts/areas/vpc_connectivity_check/_constants.py`, which is checked inside
`scripts/areas/vpc_connectivity_check/_cli.py` before any process is spawned.

| Product | Action | Version | Read-only purpose |
|---|---|---|---|
| ecs | `DescribeInstances` | 2014-05-26 | VpcId, VSwitchId, ZoneId, private IPs, bound security groups, instance type |
| ecs | `DescribeInstanceStatus` | 2014-05-26 | Live instance state context for the compared instances |
| ecs | `DescribeAvailableResource` | 2014-05-26 | Availability-zone context for the instance family |
| ecs | `DescribeSecurityGroupAttribute` | 2014-05-26 | Inbound RULE CONTENT: direction, IP protocol, port range, authorization object (CIDR or source group), policy and priority |
| vpc | `DescribeEipAddresses` | 2016-04-28 | EIP presence and in-use status for the public-side branch |
| sts | `GetCallerIdentity` | 2015-04-01 | Confirms which account the active credential belongs to |

If a request needs anything else, state the boundary, give the console entry
point, and hand off (section 8). Do not improvise a call.

## 2. Prerequisites

1. Alibaba Cloud CLI installed and configured through its **default credential
   chain** (the CLI default credential chain).
2. This skill performs no explicit credential handling. Never collect, echo,
   store, or pass an AccessKey ID, AccessKey secret, or STS token in a command,
   argument, file, or reply. If credentials are missing, tell the customer to
   configure the CLI profile themselves.
3. Identity preflight (also validates the credential):

   ```bash
   python3 scripts/areas/vpc_connectivity_check/sts_token.py
   ```

   Every finding is scoped to the account returned here. For a cross-account
   case, run the check once with **each** account's own credential.
4. Required RAM permissions: `references/ram-policies.md`.

## 3. Execution principle

Run the checks **only** through the single entry point:

```bash
python3 scripts/areas/vpc_connectivity_check/vpc_connectivity_check.py --check <mode> [options]
```

MUST NOT assemble `aliyun` API commands by hand, MUST NOT call a cloud SDK
directly, and MUST NOT bypass `scripts/areas/vpc_connectivity_check/_cli.py`. The entry point owns parameter
validation, pagination, timeouts, retry, credential masking, and the
whitelist. Base the report on the script's returned values; never state a
configuration fact from memory or from an assumption about the customer's
resources.

## 4. Symptom routing

Map what the customer says to one mode, then run it. The full decision tree,
root-cause frequencies, and the wording of each hand-off live in
`references/vpc-connectivity-check__vpc-intranet-connectivity.md`.

| Customer symptom | Mode | What it decides |
|---|---|---|
| Two ECS cannot reach each other by private IP / a port on the peer is refused | `pair` (add `--port`, `--protocol`) | Same VPC? Same vSwitch? Which security groups are bound, what their inbound rules actually say, and whether one of them allows this exact source/port flow |
| Two vSwitch CIDRs may overlap, or "connection shows success but internal ping fails" | `pair` with `--cidr-a`/`--cidr-b`, or `cidr-only` | Deterministic overlap relation between the two ranges |
| Cannot select a vSwitch or security group while transferring an instance to another account, or `InvalidDependence.GrantAccess` | `transfer` | Region and zone rules of the picked target resources, the one-target-VPC rule, the grant / reverse-authorization dependency, and zone availability of the family |
| Need every private IP in a range, or ask how private IPs behave | `ip-inventory` | Paged primary plus secondary private IP list, optional CIDR or VPC filter |
| Reachable inside the VPC but not from the internet | `public-path` | Whether a public path exists at all; if it does, the fault is not this skill's area |
| Look-alikes: HTTPS not deployed, reverse-proxy 5xx, DNS resolution, an "attack from an internal IP" alert, a `NoPermission` / `ImplicitDeny` policy denial | no mode | Identify as out of scope and hand off (section 8) |

`--region-id` is mandatory for every cloud-backed mode. The skill never
guesses a region: if the customer did not say it, ask.

## 5. Commands

```bash
# Same-VPC pair: CIDR overlap verdict, the target inbound rules read back from
# the API, and the rule-level verdict for one source/port flow
python3 scripts/areas/vpc_connectivity_check/vpc_connectivity_check.py --check pair \
  --region-id cn-hangzhou \
  --instance-id-a i-bp1example0b79486034 \
  --instance-id-b i-bp1example80057dc0bd \
  --cidr-a 172.26.0.0/18 --cidr-b 172.26.32.0/20 \
  --port 51711 --protocol tcp

# Cross-account transfer pre-check against the target zone
python3 scripts/areas/vpc_connectivity_check/vpc_connectivity_check.py --check transfer \
  --region-id cn-hangzhou --instance-id i-bp1example0b79486034 \
  --target-zone-id cn-hangzhou-h --target-vpc-id vpc-example

# Same-account vSwitch move: --same-account makes the VPC comparable
python3 scripts/areas/vpc_connectivity_check/vpc_connectivity_check.py --check transfer \
  --region-id cn-hangzhou --instance-id i-bp1example0b79486034 \
  --target-zone-id cn-hangzhou-h --target-vpc-id vpc-bp1a1b2c3d4e5f6g7h \
  --same-account

# Private IP inventory filtered by range
python3 scripts/areas/vpc_connectivity_check/vpc_connectivity_check.py --check ip-inventory \
  --region-id cn-hangzhou --cidr-filter 10.19.0.0/16

# Public-side context for the "intranet yes, internet no" branch
python3 scripts/areas/vpc_connectivity_check/vpc_connectivity_check.py --check public-path \
  --region-id cn-hangzhou --instance-id i-bp1example0b79486034

# Pure local CIDR comparison (no API call, no credential needed)
python3 scripts/areas/vpc_connectivity_check/vpc_connectivity_check.py --check cidr-only \
  --cidr-a 172.26.0.0/18 --cidr-b 172.26.32.0/20
```

Add `--json` for the machine-readable form. Instance, vSwitch, security group,
VPC and zone IDs must come from the customer or from a prior query; never
invent an ID or a value.

## 6. Interpreting the findings

- `PASS` / `FAIL` / `INFO` / `SKIPPED` are per-check results. Relay them as
  returned, quoting the concrete field values the script printed (VPC IDs,
  zone IDs, CIDRs, statuses). `SKIPPED` means a required input was not
  supplied, so ask for it and re-run rather than assuming a verdict.
- Three misconceptions are corrected on every `pair` run, because they are the
  dominant ticket root causes: intranet access is opened on the **target**
  side only; authorizing the whole large private range is **not** required (a
  `/32` of the source IP plus the port is precise); and **ping tests ICMP
  only**, so a blocked ping does not prove the TCP port is blocked. Retest a
  service port with telnet or curl.
- Security-group **rule contents ARE read** here: `pair` mode calls
  `DescribeSecurityGroupAttribute` for the target instance's groups (read-only,
  no gate) and compares each returned rule on direction, IP protocol, port
  range, authorization object, policy and priority against the flow. The
  verdict is one of `PASS` (an allow matches and no better-priority deny
  shadows it), `FAIL` (`shadowed-by-deny` or `no-matching-rule`, which is a
  cloud-side root cause) and `INFO` when no `--port` was given. Pass `--port`
  (and `--protocol` when it is not tcp) to get the rule-level verdict. A
  group-to-group authorization is reported separately: whether the source
  instance belongs to that group is not an address match, so it is never
  silently counted as allowed. If the read fails, the run degrades with a
  `[WARN]` and the printed dimensions become the console fallback.
- A **different VPC ID across the two accounts is not a mismatch**: VPC IDs
  are account-local. Only `--same-account` (a vSwitch move inside one
  account) makes the destination VPC comparable with the instance's current
  VPC. For a transfer, the rule the target account must satisfy is that its
  chosen vSwitch and security group sit in one and the same target VPC, which
  this skill cannot read - so it is reported as a manual console
  verification, never as a PASS or a FAIL.
- `InvalidDependence.GrantAccess` maps to an uncleared grant or
  reverse-authorization dependency: the source account cancels its reverse
  authorization, then the target account retries the selection. If the picker
  still fails, capture the RequestId and route to human support.
- A refusal that surfaces as `NoPermission` or `ImplicitDeny` is reported with
  the exact missing action name plus the minimal policy fragment from
  `references/ram-policies.md`. This skill does not interpret RAM policy
  conditions; a policy-condition problem is handed off.
- An empty result set is a valid finding, not an error. Missing fields print
  `N/A`; never fill a gap with a plausible value.

## Observability

Every run generates one 32-character lowercase hexadecimal session id
(`uuid.uuid4().hex`, generated once and cached per process) that is attached
to **every** API call of that run as the request User-Agent, so the whole call
chain of one check is correlatable. UA template (as assembled by
`scripts/areas/vpc_connectivity_check/_cli.py`):

```text
--user-agent AlibabaCloud-Agent-Skills/{skill-name}/{session-id} skill-version/{skill-version}
   e.g. --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-high-frequency-issues/<32-char-hex>
```

The session id is printed once to `stderr` at startup and recorded per call by
`scripts/areas/vpc_connectivity_check/_cli.py`. Each invocation additionally enforces a 60-second
subprocess timeout, argument-list execution (no shell interpolation),
standard-input detachment, linear-backoff retry on throttling or transient
server errors, and credential masking of all returned error text.

## 8. Boundaries and hand-offs

| Situation | Route to |
|---|---|
| Configuration confirmed correct, hop-by-hop path probing needed | `alibabacloud-network-diagnose` |
| Public-internet reachability, NAT or SNAT egress chain | `alibabacloud-ecs-vpc-publicnetwork-troubleshoot` |
| Disk expansion not taking effect | `area:disk-expand-diagnosis` |
| Instance stuck between start and stop states | `area:instance-state-diagnosis` |
| Disk IO performance, capacity or inode pressure | `area:resource-bottleneck` |
| Policy conditions, AccessKey VPC access-control policy | RAM / access-control guidance (human) |
| Guest firewall, Docker bridge CIDR collision, NIC configuration, application-layer faults | Customer in-guest self-check or manual support |

The last row is the structural limit of a read-only skill: cloud APIs cannot
see anything inside the operating system. After the cloud-side checks come
back clean, say so explicitly and hand off; do not assert a guest-side cause
that no returned field supports.

## 9. Output contract

The final answer MUST reproduce the report the entry script printed (its
findings with their evidence values, manual console steps and degradation log)
plus the two trailing contract lines, and MUST declare any parameter the script
auto-filled (the account UID from the identity preflight, the region supplied
by the customer):

```text
STATUS: OK | DEGRADED | FAIL
NEXT_ACTION: <single most important next step>
```

- `OK`: usable conclusion from complete evidence.
- `DEGRADED`: conclusion delivered, but a sub-query failed; show the
  "Graceful Degradation Log" and name the gap.
- `FAIL`: no usable conclusion (missing input, unknown instance, or no
  credential). State the reason and the exact correction; do not publish a
  speculative analysis.

Report structure: verdict first, then findings with their evidence, then the
manual console steps the customer performs, then the guest-side items this
skill could not see, then the hand-off if one applies. Remediation is always
guidance for a human; this skill applies nothing.

## 10. References

- `references/vpc-connectivity-check__vpc-intranet-connectivity.md` - symptom routing, per-sub-area
  root causes, remediation wording, boundary matrix.
- `references/ram-policies.md` - the exact read-only RAM actions, the
  least-privilege fragment, and missing-permission handling.
- `scripts/areas/vpc_connectivity_check/vpc_connectivity_check.py` - the only entry point.
- `scripts/areas/vpc_connectivity_check/sts_token.py` - identity preflight and account UID label.
- `related_apis.yaml` - the declared API surface, one entry per called action.
