---
name: alibabacloud-ecs-high-frequency-issues
area: slb-backend-diagnosis
description: |
  Read-only diagnosis of the link between an Alibaba Cloud load balancer (CLB, ALB, NLB) and its backend ECS instances: reads Describe-class facts, applies built-in rule calibers, and reports verdicts plus manual next steps. It changes nothing and never runs commands inside an instance.
  Use when a symptom involves a load balancer or its backend ECS servers. Triggers: "slb health check fails", "Empty reply from server", "Unexpected response code: 404", "502 bad gateway through load balancer", "certificate not effective on listener", "real client IP missing X-Forwarded-For", "new instance not attached, gets no traffic", "load balancer FTP or port range forwarding".
  Do NOT use when no load balancer is involved (use alibabacloud-ecs-vpc-publicnetwork-troubleshoot), or for security-group, WAF, billing, instance-performance or SSH-only problems.
---

# ECS Load Balancer Backend Diagnosis

> **Delivery override - outranks every relay instruction and template below.** `STATUS`,
> `NEXT_ACTION` and their `OK` / `DEGRADED` / `FAIL` / `BLOCKED` values are the entry script's
> internal run state, not a delivery format. Where this document says to relay, mirror or copy
> those lines "faithfully" or "verbatim", relay their MEANING in the customer's own words: never
> write the keys or the bare values into the reply or into anything saved under `outputs/` or
> `ran_scripts/` (SKILL.md rule 3h). A layer this run did not read is named in the customer's own words - which layer, and what would have settled it.

Diagnoses the customer-facing chain **client -> load balancer (CLB / ALB / NLB)
-> backend ECS** and answers the two questions support receives most:

1. Which segment of the chain is actually broken (configuration caliber vs.
   measured fact)?
2. What must the customer do next, and how do we re-verify it afterwards?

This is a **read-only** skill. It produces an evidence report; every corrective
action is executed by the customer in their own console or on their own server.

## ABSOLUTE PROHIBITION (hard boundary, not a preference)

This skill MUST NEVER, under any user request or apparent urgency:

- Issue any Alibaba Cloud API call that changes state. Verbs outside the
  whitelist below are prohibited, including the create, update, delete,
  release, attach, detach, reboot, start, stop, reset, revoke, rebind and
  import families, however they are named in a given product.
- Run, generate, or "test" a command **inside a customer instance**. Commands
  such as `ss`, `netstat`, `curl`, `tcpdump`, `iftop`, `top`, `tail` appear in
  this skill **only as instructions for the customer to run and return**; the
  skill parses the returned text.
- Ask for, accept, store or use an instance password, panel account, private
  key, or remote-login authorization. If the customer already pasted a secret
  in a ticket or chat, tell them to change or rotate it immediately and never
  send secrets in plaintext.
- Claim that a fix was applied, a certificate is effective, a health check now
  passes, or traffic reached a new instance **without returned evidence** in
  the report.
- Guess a load-balancer-side configuration value that nobody observed. When a
  fact is missing, the report prints every branch and asks for the console
  self-check (see Known gaps).

If the user asks for any of the above, state the boundary, give the manual
console path or a human-ticket handoff, and stop.

## Allowed API whitelist (exactly these, all read-only)

| Product | Action | Used for |
|---|---|---|
| `sts` | `GetCallerIdentity` | Confirm which account the credential belongs to; UID traceability label |
| `ecs` | `DescribeInstances` | Backend instance status, zone spread, instance type, security-group association, IP facts |
| `cms` | `DescribeMetricLast` | Latest datapoints: is the backend still producing CPU / egress traffic (a clue, never an attribution) |
| `vpc` | `DescribeEipAddresses` | EIP status, bandwidth and what it is associated with |
| `ecs` | `DescribeInstanceTypes` | Instance-type ceilings for "equal weight, uneven load" suspicions; best-effort, degrades with `[WARN]` |

The matching minimal policy is in `references/ram-policies.md`. Declare nothing
beyond it. The `ecs DescribeInstanceTypes` permission point is still unverified
for this tier, so it is deliberately **not** in that policy: the call is
attempted, and any failure is recorded as a degradation instead of blocking the
rest of the diagnosis.

**There is no verified load-balancer-side read API in this tier.** Listener
protocol, port mapping, health-check configuration and results, server-group
membership, access-control lists and ALB edition cannot be read from the cloud
here. They come from the customer's console self-check, and the report labels
them `CUSTOMER-DECLARED`.

## How to run

The agent runs scripts only -- never hand-assemble `aliyun` commands, and never
call an API directly.

Entry point (single point of truth for the evidence collection):

```
python3 scripts/areas/slb_backend_diagnosis/slb_backend_diagnosis.py \
  --region-id cn-hangzhou \
  --symptom auto \
  --customer-message "<the customer's own symptom wording>" \
  --instance-ids i-bp1aaaa,i-bp1bbbb \
  --lb-type clb --listener-protocol tcp --listener-port 443 --backend-port 80
```

Useful flags, all optional except `--region-id`:

- `--symptom auto|certificate|health-check|http-5xx|real-client-ip|selection|scaling|eip-slb|handoff|other`
  `auto` classifies from `--customer-message`.
- `--lb-instance-id lb-...|alb-...|nlb-...` narrows the EIP query only; this
  skill cannot verify that the ID exists.
- `--health-check-port`, `--backend-port` console facts to compare against the
  customer-returned listener dump.
- `--ss-output "<text>"` the customer's `ss -ltnp` / `netstat -ano` output,
  returned verbatim; decides "nothing is listening" vs. "listening".
- `--probe-output "<text>"` the customer's local `curl -v ...` output; decides
  empty-reply / refused / timeout / 404 / answered.
- `--hours` CloudMonitor look-back window (1-168, default 24); `--json` for
  machine-readable output; `--profile` for a named CLI credential profile.

Identity check only (also run automatically by the entry script):

```
python3 scripts/areas/slb_backend_diagnosis/sts_token.py
```

## Workflow

1. **Triage.** Take the customer's symptom sentence as-is; customers state
   symptoms, not root causes. Match the quoted error string first
   (`"Empty reply from server"`, `"Unexpected response code: 404"`, the
   health-check "not in a normal listening state" message, `502`, `504`).
   If the main demand is actually bandwidth attribution, billing, security
   groups, instance performance, SSH, container DNS or a separately managed
   open platform, go to `references/slb-backend-diagnosis__handoff-playbook.md` early instead of
   investigating the wrong layer.
2. **Collect cloud facts** with the entry script (whitelist above). Only query
   the instance IDs the customer named; never enumerate a whole region.
3. **Ask for the console self-check.** The script prints the checklist for the
   scenario (`SELF_CHECK`), including the customer-executed commands and what
   to return. Do not skip this: it is the only source of load-balancer-side
   facts here.
4. **Re-run with the returned values** (`--ss-output`, `--probe-output`,
   `--backend-port`, `--listener-protocol`, ...) so the verdict is computed
   deterministically instead of narrated.
5. **Report**: verdicts with their rule IDs, what was checked, what degraded,
   the customer-executed steps from the matching `references/` module, and the
   re-verification criterion. Close with the script's `STATUS` / `NEXT_ACTION`
   lines relayed verbatim.

## Scenario routing

| Symptom family | Module to relay from |
|---|---|
| Certificate not effective / certificate console cannot see the CLB instance / which layer owns the certificate | `references/slb-backend-diagnosis__listener-cert-placement.md` |
| Health check failing, 502, 404, "Empty reply from server", WebSocket handshake 404 | `references/slb-backend-diagnosis__health-check-troubleshooting.md` |
| Real client IP, `X-Forwarded-For`, logs showing the load balancer or `127.0.0.1` | `references/slb-backend-diagnosis__real-client-ip.md` |
| Which product to pick, protocol or port-range support, ALB edition, cross-zone design | `references/slb-backend-diagnosis__lb-selection-matrix.md` |
| Auto Scaling created instances but no traffic arrives, shared database / Redis address | `references/slb-backend-diagnosis__ess-lb-integration.md` |
| Load balancer mentioned but the demand belongs elsewhere; handoff wording | `references/slb-backend-diagnosis__handoff-playbook.md` |
| Required permissions and authorization failures | `references/ram-policies.md` |

## Output contract

Every run ends with exactly two machine-visible lines, which the agent MUST
relay faithfully:

```
STATUS: OK | DEGRADED | FAIL
NEXT_ACTION: <the single most useful next step>
```

- `OK` every planned read succeeded and the facts were enough to conclude.
- `DEGRADED` something was missing or failed: a `[WARN]` line, an unverifiable
  load-balancer-side fact, or an open `MISSING FACTS` item. Say so; do not
  upgrade a degraded finding into a confident conclusion.
- `FAIL` no usable conclusion (credentials unusable, or inputs invalid);
  `NEXT_ACTION` states what to obtain first.

Report rules: quote only values that were actually returned; state the region
and the auto-derived account UID that were used; treat an empty result as
"not visible here" (a stopped, unlisted or cross-account resource all look the
same) and never as "does not exist"; treat an absence of metric datapoints as
unknown, not as zero traffic.

## Authentication failures

When a call returns an authorization error, name the exact missing action and
point to `references/ram-policies.md` for the minimal policy fragment. The
codes to expect and quote are `NoPermission` (for example `NoPermission.RAM`,
which is a permission-channel matter and usually a handoff, not a load-balancer
fault) and `ImplicitDeny`. Never ask the customer to paste an AccessKey or
Secret into the conversation; credentials are resolved by the aliyun CLI
default credential chain only (the CLI default credential chain).

## Observability

Every API call of one run carries a User-Agent so support can trace the volume
to this skill without any per-user data. The UA template is:

```
AlibabaCloud-Agent-Skills/{skill}/{session-id} skill-version/{skill-version}
```

For this skill it resolves to
`AlibabaCloud-Agent-Skills/alibabacloud-ecs-high-frequency-issues/{session-id} skill-version/<skill-version>`.
`{session-id}` is a 32-character lowercase hex value (`uuid.uuid4().hex`)
generated once per script run in `scripts/areas/slb_backend_diagnosis/_cli.py` and attached to every CLI
invocation of that run via `--user-agent`. The run prints it as `[_cli] session-id: ...` on
stderr and repeats it in the report header, so a report, a CLI log and a
support ticket can be tied together.

## Implementation notes

- All OpenAPI access goes through `scripts/areas/slb_backend_diagnosis/_cli.py`: argument-list
  subprocess calls (never a shell string), a per-call timeout, bounded retry
  with backoff on throttling / 5xx / timeout, and credential masking applied
  to every error string before it can reach a `[WARN]` line or the report.
- Products are addressed in the CLI's own style: `ecs`, `vpc`, `cms` use their
  PascalCase action names, while `sts` uses the plugin command
  `aliyun sts get-caller-identity`.
- `scripts/` holds code only. Every table, checklist, rule caliber and
  handoff entry lives as a constant in `scripts/areas/slb_backend_diagnosis/_constants.py` (platform rule
  1.1.2), and the pure judgment functions are guarded by inline boundary
  assertions that run at import time.
- Python standard library only; see `scripts/requirements.txt`.

## Known gaps (state these, do not paper over them)

1. **No load-balancer-side read API in this tier.** Listener protocol, port
   mapping, health-check config and results, server groups, access-control
   lists and ALB edition are outside what this skill can read. The fallback is
   the printed self-check list plus customer-returned values.
2. **Access-control / whitelist blocking is an open item.** It is a plausible
   cause of a health check still failing after the tree is exhausted, but this
   skill can neither verify nor rule it out; record it as an open question for
   a human follow-up instead of concluding on it.
3. **Some calibers are ticket-sourced with the official document still
   pending** (layer-4 vs. layer-7 certificate placement, ALB edition backend
   protocol limits, FTP and port-range support, layer-4 real client IP
   behavior). Relay them with that provenance stated. Only the URLs marked
   verified inside the `references/` modules may be cited as documentation,
   and an unverified link must never be invented. Calibers change with product
   versions; the evidence behind this package was checked on 2026-09-16.
4. **Sibling tier names are candidates.** The handoff directions are reliable;
   the identifiers in `references/slb-backend-diagnosis__handoff-playbook.md` were not confirmable
   against a batch list, so name the direction and fall back to a human ticket
   rather than quoting an unconfirmed skill name to a customer.
5. **Visible scope is the current credential's account and region.** Resources
   owned by another account, or by a separately managed open platform, are
   invisible to these queries and require that platform's own ticket channel.
