---
name: alibabacloud-ecs-high-frequency-issues
area: cross-border-link-diagnosis
description: |
  Read-only diagnosis of slow, lossy, or timed-out access between mainland China and overseas regions, using read-only cloud queries plus guided MTR and dial-test evidence.
  Use when: cross-border link slow; mainland users cannot access my overseas ECS; high latency and packet loss to Hong Kong Singapore Tokyo Virginia server; err_timed_out; Operation timed out; i/o timeout; only some cities or ISPs cannot reach my server.
  Do NOT use: per-hop MTR analysis with no cross-border question (use alibabacloud-mtr-network-diagnosis-customer); disk, instance-state, disk-io, SSH, web-access, intranet, bandwidth, filing, attack, or file-transfer tiers; any change request.
---

# Cross-Border and Overseas Link Quality Diagnosis (Read-Only)

> **Delivery override - outranks every relay instruction and template below.** `STATUS`,
> `NEXT_ACTION` and their `OK` / `DEGRADED` / `FAIL` / `BLOCKED` values are the entry script's
> internal run state, not a delivery format. Where this document says to relay, mirror or copy
> those lines "faithfully" or "verbatim", relay their MEANING in the customer's own words: never
> write the keys or the bare values into the reply or into anything saved under `outputs/` or
> `ran_scripts/` (SKILL.md rule 3h). A layer this run did not read is named in the customer's own words - which layer, and what would have settled it.

Diagnoses access quality between Chinese mainland networks and overseas (or China
Hong Kong) ECS endpoints: slow response, packet loss, connect timeouts, ports that
only fail from some cities or some carriers, and the recurring misunderstandings
around them ("is this an Alibaba Cloud outage", "will a new IP fix it").

This skill gathers evidence, classifies the failure into one attribution branch, and
produces an evidence-based report with fixed customer-facing wording. It changes
nothing and never logs into the guest operating system.

## Permission model (hard boundary)

This skill is **read-only**. It executes only the actions in the whitelist below, via
the entry script.

| Product | Action | Access | Purpose |
|---|---|---|---|
| ecs | `DescribeInstances` | read | region, ownership, status, bandwidth and address data of the instance |
| ecs | `DescribeInstanceStatus` | read | confirm the instance itself is running normally |
| ecs | `DescribeAvailableResource` | read | confirm a suggested migration region actually has stock |
| vpc | `DescribeEipAddresses` | read | EIP status, bound instance, provisioned bandwidth |
| sts | `get-caller-identity` | read | confirm which account the queries ran against |

**ABSOLUTE PROHIBITION**: never generate, print, or run any mutating action
(`Modify*`, `Create*`, `Delete*`, `Release*`, `Reset*`, `Replace*`, `Attach*`,
`Detach*`, `Reboot*`, `Start*`, `Stop*`), including "commands for the customer to run
on the cloud side". Any action not present in the whitelist above is out of scope,
even if the customer asks for it explicitly.

**No guest execution.** This skill does not open a Workbench or Cloud Assistant
session and does not run any command inside the instance. Where guest-side readings
are required (ping/ICMP switch, firewall rules, `sshd` config, `mtr` from the server),
the report lists the exact command, its nature (read-only or writing, reversible or
not), and asks the customer or a human engineer to run it and paste the raw output.

Every suggested command in the output carries a nature label. Read this label before
advising anyone to run it.

## Scope: only this symptom area

Handle "cross-border / overseas link quality and reachability" and nothing else.
When the symptom belongs to another tier, stop and emit the handoff wording.
See [references/cross-border-link-diagnosis__handoff-map.md](references/cross-border-link-diagnosis__handoff-map.md) for the full table of
recognition features, target skill, and the one-sentence wording to use.

**First-question anchoring (MANDATORY).** The root-cause chain is anchored to
the customer's FIRST question; secondary context MUST NOT rewrite the primary
root cause. When the first question is "the instance cannot use an overseas
service (for example Let's Encrypt) - it shows a timeout", the causal chain is
mainland -> overseas API reachability (the regulated outbound direction, D4),
and that chain leads the verdict. Side context such as "the website also broke
after I changed the public IP" or bandwidth worries is at most a parallel
observation to rule out: changing the public address does not change the
cross-border path, so it never replaces the anchored chain. ABSOLUTE
PROHIBITION on attributing the first question's timeout to the IP change or to
bandwidth while the cross-border chain is unaddressed; treat side facts only
after the anchored chain, each with its own evidence.

## Inputs to collect

| Field | Required | Notes |
|---|---|---|
| `--region-id` | yes | never guessed; ask if unknown |
| `--instance-id` / `--public-ip` / `--eip` | at least one | identifies the resource |
| `--direction` | yes | `inbound` (users -> server) or `outbound` (server -> external target) |
| `--source-side` / `--target-side` | yes | `mainland` / `overseas` / `unknown` |
| `--symptom` | yes | `slow`, `timeout`, `packet-loss`, `port-blocked`, `partial-isp` |
| `--source-location` | recommended | city + carrier of the affected client |
| `--error-string` | if any | e.g. `err_timed_out`, `Operation timed out`, `i/o timeout` |
| `--target-desc` | outbound only | external domain / IP range / port that fails |
| `--time-window` | recommended | when it started, is it continuous |
| `--evidence` | repeatable | observed facts, drives the attribution branch |
| `--check-target-region` | optional | validates stock before recommending a migration |

Collect inputs in one turn. Missing fields produce `STATUS: DEGRADED` with an
explicit list of what is still needed, instead of a guessed conclusion.

## How to run

Use the single entry script. Do not assemble cloud CLI calls yourself.

```bash
python3 scripts/areas/cross_border_link_diagnosis/cross_border_link_diagnosis.py \
  --region-id ap-northeast-1 \
  --instance-id i-exampleid0000000000 \
  --direction inbound --source-side mainland --target-side overseas \
  --symptom timeout --source-location "Beijing, China Unicom" \
  --error-string err_timed_out \
  --evidence mainland-nodes-fail-overseas-ok --evidence server-side-clean
```

Machine-readable output for further processing: add `--format json`.

## Decision tree

Full text, wording templates, and MTR reading rules:
[references/cross-border-link-diagnosis__cross-border-link-diagnosis.md](references/cross-border-link-diagnosis__cross-border-link-diagnosis.md).

1. **D1 Ownership and geography.** `DescribeInstances` (+ `DescribeEipAddresses`).
   Not found in this account and region -> cross-account wording, stop. Both ends on
   the same side (both mainland, or both nearby overseas) -> not cross-border, handoff.
   Mainland <-> overseas or <-> China Hong Kong -> cross-border candidate, continue.
2. **D2 Rule-outs.** Instance status, EIP status and provisioned bandwidth, and the
   customer-supplied guest self-check list. If the customer already proved that the
   request arrives and the response is sent but never received, do not ask for the
   same checks again; jump to D4 escalation.
3. **D3 Probe evidence.** Multi-node dial test (mainland nodes fail while overseas
   nodes succeed = congestion signature), bidirectional raw `mtr` output, and the
   bandwidth-usage vs link-quality split. Raw screenshots or text only; never an
   AI-summarised report.
4. **D4 Attribution branch.** Cross-border congestion; suspected platform egress,
   NAT, or return-path fault (escalate); carrier-side policy or blocking; regulatory
   boundary; non-network root cause (handoff).
5. **D5 Output.** Verdict with direction, evidence list with the source of each item,
   options matched to where the users are, the no-guarantee statement, and how to
   re-test.

## Output contract

Every run ends with:

```
STATUS: OK | DEGRADED | FAIL
NEXT_ACTION: <one concrete action for the customer or the engineer>
```

`STATUS: OK` requires at least one confirmed evidence item. With none, the report is
`STATUS: DEGRADED` plus the missing-item list, each item stating how to obtain it.
Report the script's `STATUS` and summary verbatim; do not upgrade a degraded result
into a confident conclusion.

Recommendations are guidance only. Migration, carrier contact, and console-side
monitoring are performed by the customer or a human engineer, never by this skill.

## What this skill cannot promise

State it plainly whenever congestion or a carrier path is involved: cross-border
capacity belongs to public carrier networks, it is not controlled by Alibaba Cloud,
and no recovery time can be forecast. Never promise a fix, a time window, or a new IP
as a cure.

## Authentication and credentials

Credentials come from the machine's existing default credential chain. This skill
never asks for, reads, stores, or prints an AccessKey ID, AccessKey secret, password,
or token, and it never substitutes credentials supplied in conversation.

If identity cannot be resolved, tell the customer to configure their own profile
locally (the CLI default credential chain) and continue read-only from the console. If an action is
denied, name the exact missing action (for example `ecs:DescribeInstances`) and print
the smallest policy snippet from
[references/ram-policies.md](references/ram-policies.md). The denial literals used in
output are `NoPermission` and `ImplicitDeny`.

If a customer pastes secrets into the conversation, tell them to rotate those
secrets immediately and do not echo the values back.

## Observability

Every CLI invocation is tagged with a per-run session id so calls from one diagnosis
run can be traced together. The session id is a random 32-character hex value
(`uuid.uuid4().hex`) generated once per run and attached as
`--user-agent AlibabaCloud-Agent-Skills/{skill}/{session-id} skill-version/{skill-version}` — for this skill, rendered
as `AlibabaCloud-Agent-Skills/alibabacloud-ecs-high-frequency-issues/<32-hex-session-id>`.
The template lives in `scripts/areas/cross_border_link_diagnosis/_constants.py` and the attachment happens in
`scripts/areas/cross_border_link_diagnosis/_cli.py`. No credential value is ever part of the user agent or of any log.

## References

- [references/cross-border-link-diagnosis__cross-border-link-diagnosis.md](references/cross-border-link-diagnosis__cross-border-link-diagnosis.md) -
  decision tree, attribution wording library, MTR reading, probe guide, escalation pack.
- [references/cross-border-link-diagnosis__handoff-map.md](references/cross-border-link-diagnosis__handoff-map.md) - non-cross-border symptoms and
  the tier each one belongs to.
- [references/ram-policies.md](references/ram-policies.md) - least-privilege read-only policy.
