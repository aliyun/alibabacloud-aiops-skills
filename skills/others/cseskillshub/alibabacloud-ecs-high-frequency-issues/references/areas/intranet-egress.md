---
name: alibabacloud-ecs-high-frequency-issues
area: intranet-egress
description: |
  Diagnoses ECS connectivity failures in two directions: instance-to-instance private access, and instance-to-internet egress. Attributes each fault to a cloud-side, guest-side, external-link or client-side owner.
  Use when instances cannot reach each other over the private network, or an instance cannot reach the internet.
  Triggers: instances cannot access each other over the intranet; ping works but the port is unreachable; server cannot access the public internet; apt-get update or git pull fails from the instance; timed out; err_connection_reset; err_timed_out; err_proxy_connection_failed.
  Do NOT use: load balancer, VPC interconnect or DNS product diagnosis (alibabacloud-network-diagnose); disk or instance-state faults (the matching ECS diagnosis skill).
---

# ECS Intranet and Egress Connectivity Diagnosis

> **Delivery override - outranks every relay instruction and template below.** `STATUS`,
> `NEXT_ACTION` and their `OK` / `DEGRADED` / `FAIL` / `BLOCKED` values are the entry script's
> internal run state, not a delivery format. Where this document says to relay, mirror or copy
> those lines "faithfully" or "verbatim", relay their MEANING in the customer's own words: never
> write the keys or the bare values into the reply or into anything saved under `outputs/` or
> `ran_scripts/` (SKILL.md rule 3h). A layer this run did not read is named in the customer's own words - which layer, and what would have settled it.

Direction-aware diagnosis for two customer symptoms: two ECS instances that
cannot reach each other over the private network, and an instance that cannot
reach the internet. The skill decides **which direction** the traffic flows,
**where the packet is lost**, and **who owns the next step**, then reports the
evidence behind that attribution.

## Scope

In scope:

- Asset ownership: is the address an ECS instance of the account currently
  configured in the CLI?
- Direction: ingress (outside to instance), egress (instance to outside) or
  internal (instance to instance). The category a case was filed under is
  **never trusted**; direction is re-derived from the initiator and the target.
- Cloud-side path: security group rules in both directions, VSwitch CIDRs,
  route tables, NAT gateway availability and SNAT coverage.
- Target geography: whether the target endpoint sits inside or outside the
  Chinese mainland, which decides the cross-border branch.
- In-guest state: host firewall, listener bind address, guest routes, DNS,
  proxy settings and live probe results, collected through the manual path in
  [Step 4](#step-4--in-guest state inspection manual).

Out of scope: see [When not to use](#when-not-to-use).

## When to use

Trigger this skill when the customer says any of:

- Two instances cannot access each other over the intranet, or one instance
  cannot reach another private address.
- Ping succeeds but a specific port is unreachable, or a port probe reports the
  port as filtered.
- The instance cannot access the public internet, an external website, a
  package repository, a code-hosting service or a certificate endpoint.
- Outbound traffic is refused or silently dropped, including after an egress
  security group rule was added or removed.
- The customer quotes `timed out`, `err_connection_reset`, `err_timed_out` or
  `err_proxy_connection_failed`.

## When not to use

Recognize these, state the boundary, and hand off. Do not attempt them here.

| Symptom | Hand off to |
| --- | --- |
| Load balancer, VPC interconnect, transit router or DNS product architecture | `alibabacloud-network-diagnose` |
| Disk capacity or inode exhaustion, expansion not taking effect | `area:disk-expand-diagnosis` |
| Disk throughput or latency problems | `area:resource-bottleneck` |
| Instance will not start, stuck stopping, unexpected state | `area:instance-state-diagnosis` |
| HTTP 403, HTTP 502, missing index file, directory permissions, application errors | The application or web service owner. The network path already reached the instance. |
| Search-console site verification, third-party platform validation flows | The third-party platform. Confirm packet arrival in the service log first. |
| Anti-DDoS blackhole or cleaning status, underlying host incidents | A support ticket. These platform-side states have no query entry point. |
| Customer premises equipment, local hosts file, local DNS cache, browser cache | The customer's own environment. Provide the self-check list and stop. |
| Changing a public IP, converting to an EIP, enabling an acceleration product, buying bandwidth | The resource owner in the console. Explain applicability and billing risk only. |

Full matrix: [references/intranet-egress__handoff-matrix.md](references/intranet-egress__handoff-matrix.md).

## Required inputs

Ask for exactly what is missing. Never guess an input.

| Input | Required | Why |
| --- | --- | --- |
| `--region-id` | Yes | Every query is region-scoped. |
| Instance locator: `--instance-id`, `--private-ip` or `--public-ip` | Yes (one of) | Locates the instance and proves account ownership. |
| `--direction` (`egress`, `ingress`, `internal`) | Yes | Selects the decision branch. |
| `--target` or `--target-ip` | Yes for egress | The endpoint the instance cannot reach. |
| `--port` | Yes for ingress and internal | Port-level rule evaluation needs a port. |
| `--peer-instance-id` or `--peer-ip` | Yes for internal | The other side of the mutual-access check. |
| `--client-ip`, `--client-location` | Recommended | Lets a rule match pin a CIDR; required for the regional reset analysis. |
| `--error-text` | Recommended | Mapped to an evidence class. |

Never accept, request or record an account password, control-panel login,
private key or phone number. See
[Credential handling red line](#credential-handling-red-line).

## Workflow

The agent runs the scripts below and nothing else. Do not assemble `aliyun`
commands by hand and do not bypass the entry scripts.

### Step 1 - Verify caller identity

```bash
python3 scripts/areas/intranet_egress/sts_token.py
```

Establishes the account UID that every subsequent query is scoped to. A large
share of connectivity cases are mis-routed: the target server belongs to a
different Alibaba Cloud account, or is not an Alibaba Cloud asset at all.
Confirming ownership first turns that into one query instead of a support round
trip.

### Step 2 - Run the direction-aware diagnosis

```bash
python3 scripts/areas/intranet_egress/ecs_connectivity_diagnose.py \
  --region-id cn-shenzhen \
  --instance-id i-example001 \
  --direction egress \
  --target https://acme-v02.api.letsencrypt.org/directory \
  --error-text "curl: (28) Operation timed out after 10000 milliseconds"
```

Add `--json` for machine-readable output. The script runs the decision tree in
[references/intranet-egress__diagnosis-decision-tree.md](references/intranet-egress__diagnosis-decision-tree.md):
identity and ownership, direction split, security group rule evaluation in both
directions, VSwitch and route table reads, NAT and SNAT coverage, target
geography, then attribution.

A failing query never aborts the run. It is logged as `[WARN|DEGRADE]`, recorded
in the degradation log, and the report ends with `STATUS: DEGRADED` naming the
missing evidence.

### Step 3 - Interpret the verdict

| `ATTRIBUTION` | Meaning | Who acts next |
| --- | --- | --- |
| `cloud-config` | A specific cloud-side item blocks the path: a blanket egress drop rule, no ingress accept for the port, no public IP and no NAT gateway, an SNAT entry that does not cover the instance, zero outbound bandwidth. | The resource owner, in the console. This skill never edits it. |
| `external-link` | The instance and the target sit on opposite sides of the Chinese mainland border. | Explain the boundary; the customer evaluates options. |
| `external-carrier` | A reset seen from one region across several carriers. | The customer contacts the carrier. The cloud can neither confirm nor lift it. |
| `guest-config` | The deciding evidence is inside the instance. | The customer runs the inspection checklist and pastes back plain text. |
| `application-layer` | The connection was refused or answered with an HTTP status, so it arrived. | The application owner. Out of scope. |
| `ownership` | The locator matched no instance in this account. | The owning account, or the customer's own network team. |
| `undetermined` | Evidence so far is clean and incomplete. | Collect the in-guest evidence, or escalate with the evidence bundle. |

Security group interpretation details, including blanket `-1` drop rules,
priority shadowing and the ICMP false-negative trap:
[references/intranet-egress__security-group-readback.md](references/intranet-egress__security-group-readback.md).

Cross-border and regional-blocking wording, including the hard limit that an
acceleration product cannot front a closed third-party SaaS:
[references/intranet-egress__cross-border-and-blockage.md](references/intranet-egress__cross-border-and-blockage.md).

### Step 4 - In-guest state inspection (manual)

No cloud query exposes the host firewall state, the address a service actually
binds to, guest routes and DNS, proxy settings, or what a live probe returns.
The collection path is always manual: this skill is strictly read-only and
never executes anything inside a customer instance.

**Manual path (the only path).** The diagnosis script prints a checklist of
state-inspection commands for the customer to run inside the instance and paste
back as plain text. Ask for text, not screenshots.

```bash
python3 scripts/areas/intranet_egress/guest_command_gate.py --list-accepted --os-type linux
```

`scripts/areas/intranet_egress/guest_command_gate.py` makes no cloud API call. It prints the vetted
checklist, and it validates a proposed inspection command against the
inspection-only text guards before that command is handed to the customer:
the leading binary must be an accepted inspection command, its arguments must
satisfy the positional or flag policy for that binary, and the text must
contain no side-effect or command-chaining fragment.

A command that fails a guard prints the refusal reasons plus the manual
checklist and exits `3`. Do not retry with looser text.

Accepted commands and the two argument policies:
[references/intranet-egress__guest-inspection-commands.md](references/intranet-egress__guest-inspection-commands.md).

## Permission model and confirmation gates

This skill is **strictly read-only**: every cloud API it invokes is a
non-mutating query, and it never executes anything inside a customer instance.
Four tiers apply.

| Tier | Actions | Gate |
| --- | --- | --- |
| 1. Non-mutating cloud queries | `sts:GetCallerIdentity`, `ecs:DescribeInstances`, `ecs:DescribeSecurityGroupAttribute`, `vpc:DescribeVSwitches`, `vpc:DescribeRouteTableList`, `vpc:DescribeNatGateways`, `vpc:DescribeSnatTableEntries` | None. Run automatically. |
| 2. In-guest inspection | None. The skill never dispatches or executes a command inside a customer instance; inspection commands are printed for the customer to run manually and paste back as plain text | Not applicable. Guidance only. |
| 3. Low-risk reversible writes | None are invoked by this skill. Taking a snapshot before an interactive console or login session is a manual step the resource owner performs in the console. | Announce before any such manual step is recommended. |
| 4. Destructive or billing-bearing operations | See below | **Never.** Guidance only. |

In-guest evidence collection stays with the customer end to end: the skill
prints the commands, the customer runs them and pastes back plain text, and
the report continues from that text.

### Never executed by this skill (ABSOLUTE PROHIBITION)

This skill MUST NOT generate, write, execute, or instruct the automation to
execute any operation that changes cloud or guest state. That prohibition
covers, without limitation:

- Adding, modifying or removing a security group rule, or changing a network
  ACL.
- Editing a route table, a default route, a NAT gateway or an SNAT entry.
- Purchasing, associating, disassociating, converting or releasing an EIP or a
  public IP address; changing bandwidth; enabling an acceleration product.
- Writing to `iptables`, `ip6tables`, `nft`, `firewalld` or `ufw`; starting,
  stopping, restarting or reloading a network service or an instance.
- Dispatching or executing any command inside a customer instance through
  Cloud Assistant or any other remote-execution mechanism. In-guest evidence
  is collected only by the customer, running the printed checklist manually.
- Killing a process, deleting or truncating a file, formatting, repartitioning,
  deleting a snapshot, unsubscribing or downgrading a resource.
- Any of the above phrased as a command for the customer to run. Describe the
  console path and the risk instead, and let the resource owner decide.

Where such a change is the actual fix, output the console entry point, the
documentation link, and an explicit statement that the operation may be
irreversible and may carry billing or discount consequences.

## Credential handling red line

Authentication is resolved exclusively by the Alibaba Cloud CLI default
credential chain. The scripts never read, print, cache, accept as an argument,
or write out any access key, secret or session token. When the credential chain
is unusable, the guidance is to repair it with `aliyun sts get-caller-identity`; the scripts
never ask the customer for key material.

This skill MUST NOT request, accept or record:

- An instance account password, a control-panel or dashboard login, or a
  private key.
- A customer phone number or other contact detail.

If a customer volunteers a credential anyway, do not use it, do not echo it back,
and advise the customer to rotate it immediately. All CLI error text passes
through a credential mask before it can reach a report, a log line or the
conversation, and customer-pasted guest output is treated the same way: quote
only the diagnostic part, never a credential.

## RAM permissions

The minimum policy grants exactly the actions this skill invokes, with no
wildcard:

- `sts:GetCallerIdentity`
- `ecs:DescribeInstances`
- `ecs:DescribeSecurityGroupAttribute`
- `vpc:DescribeVSwitches`
- `vpc:DescribeRouteTableList`
- `vpc:DescribeNatGateways`
- `vpc:DescribeSnatTableEntries`

Every grant above is a non-mutating read. The skill declares no execute-class
and no write-class permission: it never runs anything inside a customer
instance and never changes any cloud resource.

Full policy fragments, per-action justification and the RAM-name-versus-API-name
traps: [references/ram-policies.md](references/ram-policies.md).

When a query is denied, report **which action is missing** and print the minimal
policy fragment that adds it. Use the literals `NoPermission` for an explicit
denial and `ImplicitDeny` for a missing grant. Classify the denial, then
continue with the remaining queries and end with `STATUS: DEGRADED`.

## Observability

Every Alibaba Cloud API call made by this skill carries a User-Agent header so
that all calls belonging to one diagnosis can be correlated. The UA template:

```
AlibabaCloud-Agent-Skills/{skill}/{session-id} skill-version/{skill-version}
```

- `{skill}` is `area:intranet-egress`, the skill name from the
  frontmatter.
- `{session-id}` is a 32-character lowercase hex string produced once per script
  run by `uuid.uuid4().hex`, cached for that run, and printed to stderr as
  `[_cli] session-id: <value>`.
- The value is attached to **every** invocation through the shared CLI layer in
  `scripts/areas/intranet_egress/_cli.py`; no call path bypasses it.
- Transient failures (throttling, 5xx, subprocess timeout) are retried up to
  three times with linear backoff, and each retry is logged as `[WARN]` with the
  error code. Non-transient failures are raised immediately.
- Command style is product-specific and handled in one place. Plugin-style
  products use the lowercase hyphenated command form, for example
  `aliyun sts get-caller-identity`; RPC-style products keep the PascalCase
  action name, for example `aliyun ecs describe-instances`.
- Every subprocess invocation carries an explicit timeout and runs with an
  argument list, never through a shell, and never inherits an interactive
  stdin.

## Error-string evidence classes

A customer error string is evidence about **where** a packet died, never a root
cause on its own. The classes below route the decision tree.

| Class | Recognized from | What it proves | Branch |
| --- | --- | --- | --- |
| `timeout` | `timed out`, `i/o timeout`, `could not connect to server`, `100% packet loss`, `no response` | A SYN or ICMP echo went unanswered. Consistent with a silent drop, a missing route, or a dead far end. | Check direction rules, ICMP allowance, egress path, then target geography. |
| `reset` | `err_connection_reset`, `err_timed_out`, `connection reset`, `reset by peer` | Something answered with a RST, so the packet reached an endpoint or a middlebox. | Ingress plus a single-region multi-carrier pattern points to regional blocking; collect client egress IP and carrier. |
| `refused` | `connection refused`, `actively refused` | The host was reached but no service accepted the port. | Application layer. Out of scope. |
| `proxy-path` | `err_proxy_connection_failed`, `proxy` | Only that a proxy path failed. | Verify guest and browser proxy settings. Make no root-cause claim without that output. |
| `filtered` | `filtered` | A probe was answered by neither SYN-ACK nor RST. | Treat like a silent drop; check both security group directions and the host firewall. |

Two traps worth naming explicitly:

- **Ping failure proves nothing about TCP.** ICMP is frequently not permitted by
  a security group, so a failed ping alongside a working port is normal. The
  script reports ICMP allowance in both directions for exactly this reason.
- **"Everything is unreachable" is usually partial.** Probe a domestic endpoint
  and an overseas endpoint separately before accepting a blanket claim.

## Output contract

Report the script output faithfully. Quote only values that were actually
returned; never fill a gap with an assumption.

Both scripts end with contract lines:

```
STATUS: OK | DEGRADED | FAIL
VERDICT: RESOLVED-POINTED | NEED-INPUT | NEED-HUMAN | OUT-OF-SCOPE | UNDETERMINED
ATTRIBUTION: <owner of the next step>
NEXT_ACTION: <the single next step>
```

The customer-facing report must contain:

1. A one-sentence attribution conclusion.
2. The evidence list, each item naming its source query and the value read.
3. Every parameter that was auto-filled or defaulted, and every open item or
   uncertainty, including cases where platform-side observation and the
   customer's own observation disagree.
4. The next step: who does it, where, and which documentation applies.
5. On handoff, the target skill or team plus the evidence bundle to carry over.

`STATUS: DEGRADED` means at least one query failed; name the missing evidence
and say what conclusion it prevents. `STATUS: FAIL` means no usable conclusion;
say which input or credential is blocking.

## Known limitations

Stated plainly, because overclaiming here is worse than admitting the gap:

- This skill performs no live link measurement and cannot confirm current
  cross-border link quality. Platform-side probes and customer observations
  frequently disagree; when they do, say so rather than picking a side.
- Anti-DDoS blackhole and cleaning status, and underlying host incidents, have
  no query entry point. Escalate with the evidence bundle.
- Third-party host security agents inside the guest are not fully visible to
  the inspection commands.
- Resources owned by another Alibaba Cloud account are not readable from here.
- Application and service log contents beyond "did the request arrive" are out
  of scope.

## References

- [references/ram-policies.md](references/ram-policies.md) - minimum RAM
  policy, per-action justification, naming traps.
- [references/intranet-egress__diagnosis-decision-tree.md](references/intranet-egress__diagnosis-decision-tree.md) -
  the D0 to D6 decision tree and the direction and boundary tables.
- [references/intranet-egress__security-group-readback.md](references/intranet-egress__security-group-readback.md) -
  reading back ingress and egress rules, blanket drops, priority shadowing,
  ICMP traps.
- [references/intranet-egress__cross-border-and-blockage.md](references/intranet-egress__cross-border-and-blockage.md) -
  cross-border and regional-blocking wording and hard limits.
- [references/intranet-egress__guest-inspection-commands.md](references/intranet-egress__guest-inspection-commands.md) -
  the in-guest inspection checklist and the two argument policies.
- [references/intranet-egress__handoff-matrix.md](references/intranet-egress__handoff-matrix.md) - out-of-scope
  symptom to handoff target.
