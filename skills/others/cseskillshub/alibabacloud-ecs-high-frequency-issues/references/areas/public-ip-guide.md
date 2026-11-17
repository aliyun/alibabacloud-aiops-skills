---
name: alibabacloud-ecs-high-frequency-issues
area: public-ip-guide
description: |
  Guides Alibaba Cloud ECS public IP and EIP asset questions: fixed public IP vs EIP,
  converting a public IP to an EIP, bind, unbind, release, extra public IPs per instance,
  and whether the address survives an account transfer or renewal.
  Queries are non-mutating; change steps are console guidance the customer
  performs, with the irreversible and cost impact stated.
  Use when:
  - change my public IP or replace my public address
  - my public IP changed on its own
  - convert public IP to EIP
  - unbind or release my EIP
  - recover a released public IP
  - bind multiple public IPs on one instance
  - keep the same public IP after account transfer
  Do NOT use when:
  - packet loss, RST or path checks: alibabacloud-ecs-vpc-publicnetwork-troubleshoot
  - ICP filing interception: area:icp-filing-guide
  - port or security group rules: area:access-block-layered
---

# Alibaba Cloud ECS public IP and EIP change guide

> **Delivery override - outranks every relay instruction and template below.** `STATUS`,
> `NEXT_ACTION` and their `OK` / `DEGRADED` / `FAIL` / `BLOCKED` values are the entry script's
> internal run state, not a delivery format. Where this document says to relay, mirror or copy
> those lines "faithfully" or "verbatim", relay their MEANING in the customer's own words: never
> write the keys or the bare values into the reply or into anything saved under `outputs/` or
> `ran_scripts/` (SKILL.md rule 3h). A layer this run did not read is named in the customer's own words - which layer, and what would have settled it.

## Scope

This skill answers one vertical: the **ownership, type, binding relationship, conversion
rules and billing caliber** of an ECS public IP / EIP asset.

- Can this public IP be changed, and through which steps, at what kind of cost.
- Is the address a fixed public IP or an EIP right now, and is it still attached.
- How many public IPs one instance can carry, and which ENI they live on.
- Whether the address survives account transfer, re-imaging, or OS/architecture change.
- Whether an address that was released can be reclaimed (the 7-day self-service window),
  and where to look for history.
- Whether an IP change is the right remedy at all (counter-example gate, see below).

Out of scope, recognized and handed off only: reachability of a service, filing
interception, security group rules, DDoS mitigation, arrears and expiry lifecycle,
refund negotiation, instance spec change. See `references/public-ip-guide__handoff-map.md`.

## Permission model

- **Queries the skill runs itself**: `sts GetCallerIdentity`, `ecs DescribeInstances`,
  `ecs DescribeInstanceStatus`, `vpc DescribeEipAddresses`. Nothing else. They change no
  resource and no bill, so they need no per-call approval.
- **Guidance the skill emits**: the customer clicks the change themselves in the console.
- **Guidance, not execution**: the answer this skill produces is a step-by-step manual
  path, so it necessarily names the operations inside it (convert, bind, unbind, release).
  Naming one in guidance is not the same as performing it: no such verb is ever turned into
  an API call, a CLI command, or a command handed to anyone to paste and run.
- **ABSOLUTE PROHIBITION**: never call, generate, or paste-for-execution any API or CLI
  command that changes cloud resources or billing, including for the customer to run.
  Banned from any executable form: `ConvertNatPublicIpToEip`, `AllocateEipAddress`,
  `AssociateEipAddress`, `UnassociateEipAddress`, `ReleaseEipAddress`,
  `ModifyInstanceNetworkSpec`, `ChangeResourceGroup`, and any `Modify*` / `Create*` /
  `Delete*` / `Release*` / `Bind*` / `Unbind*` / `Reset*` action.
- **Never automated, human steps only**: the final confirmation of an EIP release, refund
  or down-scale commerce actions, instance release, and reclaiming an already released
  address. Reclaiming is self-service, not a ticket: inside 7 days the customer uses the
  EIP page's apply-for-a-specific-address entry (or `AllocateEipAddressPro` with the
  address in `IpAddress`), and it fails once the window has passed or another account
  holds the address. Give the console path plus the risk notice.
- **Confirmation gate on any in-instance command**: this build runs nothing inside the
  customer's instance; instance-side network settings are collected by asking the customer
  to paste the interface output. If an in-instance inspection channel is enabled later,
  then before any command runs the skill MUST state the exact command, its scope of impact,
  and that it changes nothing, and MUST obtain the customer's explicit confirmation — one
  command at a time, each confirmation valid for that single command only. Until such a
  channel exists and is approved, no in-instance command may be run.
- If a request needs a change this skill will not perform, say so, give the console entry
  point, and hand off. Do not negotiate an exception.

## Prerequisites

- Alibaba Cloud CLI installed and configured through the default credential chain. The
  scripts never read, print, or ask for an access key pair; on missing credentials they
  stop and point at `aliyun sts get-caller-identity`.
- The region is required for every query. Public IPs in the source cases sit in different
  regions (`cn-zhangjiakou`, `us-west-1`, `cn-wulanchabu`), so a wrong region is a common
  false "not found"; `--scan-regions` is provided for that.
- Minimum RAM actions are listed in `references/ram-policies.md`.

## How to run

Run the single entry point; do not hand-assemble CLI calls.

```
python3 scripts/areas/public_ip_guide/public_ip_guide.py --intent change-ip --instance-id i-2ze... --region cn-hangzhou
```

| Flag | Meaning |
| --- | --- |
| `--intent` | `consult` `change-ip` `add-ip` `retain-ip` `billing` `ip-missing` `verify` `triage` |
| `--instance-id` / `--public-ip` / `--allocation-id` | one resource handle, any of the three |
| `--region` | `RegionId`; required unless `--scan-regions` |
| `--scan-regions` | locate the resource across common regions when the region is unknown |
| `--symptom` | free-text symptom, feeds the counter-example and handoff gate |
| `--old-address` | the address that should now be gone; only used by `verify` to compare |
| `--max-regions` | cap the number of regions tried by `--scan-regions` |
| `--timeout` | per-call timeout override in seconds (default 30) |
| `--json` | machine-readable evidence block |

## How-to questions (consult intent, zero reads)

A "how do I view the public IP / EIP?" question has no resource to read and no anomaly to
find. Answer it with ONE call:

```
python3 scripts/ticket-support.py --area public-ip-guide -- --intent consult
```

- It prints the four viewing paths (console list, console details, `DescribeInstances` /
  `DescribeEipAddresses`, EIP console) and the three facts that are usually misread
  (fixed IP vs EIP mutual exclusion, settled by the one-way `ConvertNatPublicIpToEip`
  conversion rather than by releasing the fixed IP; the guest NIC only shows private
  addresses; an empty `PublicIpAddress` means no address, not a failed query).
- It performs **no** cloud read and returns in milliseconds. Do not follow it with
  `--intent verify`, `--intent ip-missing`, or `--scan-regions`: measured 2026-10-26, that
  chain cost 159 s / 444 s / 118 s across three runs of the same question with an
  identical conclusion.
- The tool emits `RULE-LEAD: [platform_rule] ...`, so the verdict line carries the
  determination instead of `unverified`.
- If the customer then names a specific instance, that is a new question: run
  `--intent verify --instance-id ... --region ...` (or `ip-missing`) once.

## Triage order

1. **Counter-example gate first.** If the customer's real complaint is that a service or a
   client is unreachable, or that traffic from other people's domains lands on the IP, run
   the keyword gate (`--intent triage --symptom "..."`). Filing interception, link or
   packet loss, single-client failure, and inherited DNS records are **not** fixed by an
   IP change, and the EIP conversion path is irreversible. Hand off before any change
   guidance.
2. **Classify the asset** with `--intent change-ip` / `add-ip` / `retain-ip` / `billing` /
   `ip-missing`, which reads instance state, address type, and EIP state first.
3. **Branch by type.** Fixed public IP: the direct console entry exists (instance details
   > All Actions > Network and Security Group > Change Public IP) but is limited to a
   stopped instance in standard stop mode, inside a short window after creation, a few
   changes at most, and a randomly assigned address — so for anything else the five-step
   EIP path applies. Already an EIP: the conversion step is skipped, the path is unbind,
   allocate, bind.
4. **Close the loop.** After the customer acts, run `--intent verify` to confirm the old
   EIP is gone and the new address is bound. An unreleased old EIP is a live billing tail.
5. **Every branch ends with the human fallback**: money amounts and console clicks go to
   the console estimate page; a released address is reclaimed by the customer on the EIP
   page inside 7 days, and only a case outside that path becomes a ticket.

## Capability flows

- **C1 current state** (`scripts/areas/public_ip_guide/public_ip_guide.py`): instance exists and its status,
  whether it has a public address, whether that address is fixed or an EIP, region,
  bandwidth billing attributes as returned.
- **C2 change path** (`--intent change-ip`): the five steps in order, each with its doc
  link, plus the three notices that must never be omitted — see
  `references/public-ip-guide__ip-vs-eip-rules.md`. Also corrects the observed wrong
  shortcuts: lowering bandwidth to 0 and re-buying can hand back the same address, the
  conversion cannot be undone, and the console's own Change Public IP entry is narrow
  (standard stop mode only, short window after creation, few attempts, random address)
  rather than a general replacement for the EIP path.
- **C3 billing caliber** (`--intent billing`): two separate models, fixed public IP billed
  with the instance versus EIP billed and renewed on its own; the conversion is one way
  only, there is no reverse operation, and reaching a fixed public IP again means
  releasing the address and allocating another one. No figure is ever computed here.
- **C4 multiple addresses** (`--intent add-ip`): default one EIP per instance, extra
  addresses need secondary ENIs, the operating system sees private addresses while an EIP
  is a NAT mapping, security group reminders. Guest-side network configuration is beyond
  the cloud queries; ask the customer for the interface output rather than assuming.
- **C5 transfer and history** (`--intent retain-ip`): ECS transfer requires the same
  enterprise verification subject; a VPC-type instance does not carry its EIP across a
  transfer, while a pay-as-you-go EIP can be transferred on its own and a system-assigned
  fixed public IP moves with the instance keeping its address; cross-subject migration
  changes the public address; a released address has a 7-day self-service reclaim path.
- **C6 counter-example and handoff** (`--intent triage`): keyword table to skill, plus the
  fixed sentence warning that an IP change will not work and is irreversible.
- **Verify** (`--intent verify`): read-back of the previous state.

## Numbers and links discipline

Any amount or duration taken from a historical case (EIP configuration fee per day, a
trial account release cycle, an available-balance threshold) must be carried with the
qualifier "case-specific figure, confirm the current value on the console or the latest
documentation", or omitted. Platform rules are stated as rules, without that qualifier:
the 7-day reclaim window for a released address and the one-way
fixed-public-IP-to-EIP conversion both belong to that group. Prices come from the console
conversion or buy page, never from this skill. Internal-only hosts are never surfaced to
customers.

## Error handling

- Resource not found in the given region: report the regions searched, ask for the region,
  or rerun with `--scan-regions`.
- `InvalidAccessKeyId`, `NoPermission`, `ImplicitDeny`: name the missing action and point
  at the minimum policy in `references/ram-policies.md`. Never report it as a generic
  access-denied label.
- No EIP returned: distinguish "this instance uses a fixed public IP" from "the EIP was
  already released", because the two lead to different paths.
- Empty or failed query: record the limitation, keep `STATUS: DEGRADED`, never fill the
  gap from memory.

## Output contract

The report restates the script summary honestly, lists only returned fields, declares
parameters that were auto-filled (region, account), and ends with:

```
STATUS: OK | DEGRADED | FAIL
NEXT_ACTION: <the single next step for the customer or the operator>
```

## Handoff

`references/public-ip-guide__handoff-map.md` maps each neighbouring symptom to an existing sibling skill.
Hand off with the reason and the query evidence that excludes the IP asset area.

## References

- `references/public-ip-guide__ip-vs-eip-rules.md` — address types, the five-step change path, the three
  notices, multi-address and transfer rules, counter-examples.
- `references/public-ip-guide__billing-caliber.md` — the two billing models, renewal behaviour, the
  estimate-page caliber and the number discipline.
- `references/public-ip-guide__handoff-map.md` — recognition keywords and handoff wording.
- `references/ram-policies.md` — the exact actions the scripts call.
- `related_apis.yaml` — declared API list, aligned with the scripts.

## Observability

Every CLI call made by `scripts/areas/public_ip_guide/_cli.py` carries a per-run session id and an explicit user
agent built from the template below, so a skill run can be traced on the API side:

```
--user-agent AlibabaCloud-Agent-Skills/{skill}/{session-id} skill-version/{skill-version}
```

Here `{skill}` is this skill's name (`area:public-ip-guide`) and `{session-id}`
is a 32-character lowercase hex string generated once per run with `uuid.uuid4().hex` in
`scripts/areas/public_ip_guide/_cli.py` and passed to each call, including the caller identity check in
`scripts/areas/public_ip_guide/sts_token.py`.
