---
name: alibabacloud-ecs-high-frequency-issues
area: ddh-capacity-guide
description: |
  Read-only Alibaba Cloud ECS Dedicated Host (DDH) / capacity-reservation and
  host-reboot-event guidance: confirms instance facts with Describe* APIs and
  answers from official rules. Use when the customer asks about: DDH / dedicated
  host / capacity reservation / elasticity assurance; a host-driven reboot event
  such as SystemMaintenance.Reboot or SystemFailure.Reboot; CPU contention from a
  noisy neighbor on a shared instance family; an instance that shows Running but
  is unresponsive at the storage performance ceiling; or an instance not visible
  under the current account or region. Do NOT use for network / public
  connectivity or VPC routing faults (use the ECS VPC public-network
  troubleshooting skill), for purchasing or reconfiguring resources, or for
  running commands inside the guest OS; it changes nothing.
---

# ECS DDH / Capacity Guide (read-only)

> **Delivery override - outranks every relay instruction and template below.** `STATUS`,
> `NEXT_ACTION` and their `OK` / `DEGRADED` / `FAIL` / `BLOCKED` values are the entry script's
> internal run state, not a delivery format. Where this document says to relay, mirror or copy
> those lines "faithfully" or "verbatim", relay their MEANING in the customer's own words: never
> write the keys or the bare values into the reply or into anything saved under `outputs/` or
> `ran_scripts/` (SKILL.md rule 3h). A layer this run did not read is named in the customer's own words - which layer, and what would have settled it.

This skill turns a customer's **symptom** about Dedicated Host (DDH) / capacity
reservation, host-driven system events, or instance-family isolation into an
**evidence-based, read-only** answer plus the correct next step. It fetches facts
with read-only `Describe*` APIs, applies official rules that are baked into the
reference modules, and clearly separates what is "explained / ruled out / not
visible". What the read-only APIs genuinely cannot see (per-process guest I/O,
readings outside the disk-monitor window, whether a host is about to fail) is
stated honestly with the customer-side source of truth. Nothing is ever changed.

## Operation type and boundaries

- **Operation type: RO / RO+G** (read-only query plus manual, human-guided
  next steps). The default permission model is strictly read-only.
- **ABSOLUTE PROHIBITION - read-only skill**: never call, generate, or tell the
  user to run any mutating ECS/STS API. This skill only calls `Describe*` / `Get*`
  read operations, and every one of them is enforced by the `READ_ONLY_ACTIONS`
  whitelist in `scripts/areas/ddh_capacity_guide/_cli.py` (anything else is refused
  before a subprocess starts). It does not create, modify, delete, reboot, migrate,
  start, stop, reconfigure, or attach/detach any resource, and it never executes
  commands inside a guest OS.
- Read-only evidence this area actually collects: `DescribeInstances`,
  `DescribeInstanceStatus`, `DescribeInstanceHistoryEvents` (event type,
  lifecycle status, publish / scheduled / finish time), `DescribeDedicatedHosts`
  (host usage status), `DescribeDisks`, `DescribeDiskMonitorData` (cloud-disk IOPS
  / BPS / latency), `sts GetCallerIdentity` (account label).
- Moving an instance to another host is **customer self-service**, not a ticket-only
  operation: `RedeployInstance` after a `*.Redeploy` event, or
  `ModifyInstanceDeployment` to place an instance on / move it between Dedicated
  Hosts. Both are described as paths with prerequisites and risks; the skill never
  executes them and never adds them to its whitelist. A ticket is reserved for a
  host hardware investigation or a locked instance (see
  [references/ddh-capacity-guide__handoff-playbook.md](references/ddh-capacity-guide__handoff-playbook.md)).
- Actions the customer must do themselves (rebooting inside a maintenance window,
  redeploying, reconfiguring to a dedicated family, purchasing DDH / a capacity
  reservation, creating a snapshot) are given as **console steps and risk notices
  only**; the skill never claims such an action was completed on the customer's
  behalf.
- Compensation / SLA disputes are **handed off** to a human support ticket (see
  [references/ddh-capacity-guide__handoff-playbook.md](references/ddh-capacity-guide__handoff-playbook.md)).

## Prerequisites

- Alibaba Cloud CLI (`aliyun`) installed and configured through its **default
  credential chain**. The scripts never read, print, or accept an AccessKey
  ID/Secret and never handle credentials directly; a RAM profile may be selected
  with `--profile`.
- Read-only RAM actions this area issues: `sts:GetCallerIdentity`,
  `ecs:DescribeInstances`, `ecs:DescribeInstanceStatus`,
  `ecs:DescribeInstanceHistoryEvents`, `ecs:DescribeDedicatedHosts`,
  `ecs:DescribeDisks`, `ecs:DescribeDiskMonitorData`. No write action is required
  or granted. (The package-level minimum list also lives in
  [references/ram-policies.md](references/ram-policies.md); it must carry the same
  set for the event / host-status / disk-I/O branches to return data.)

## Entry point and scripts

All cloud access goes through the shared CLI layer; run the entry script and do
not hand-assemble `aliyun` commands.

| Path | Role |
|---|---|
| `scripts/areas/ddh_capacity_guide/ddh_capacity_guide.py` | Single entry point: visibility pre-check, family classification, event record / host status / disk I/O evidence, symptom routing, evidence report |
| `scripts/areas/ddh_capacity_guide/sts_token.py` | Verifies the caller identity and derives the account UID label |
| `scripts/areas/ddh_capacity_guide/_cli.py` | Shared `aliyun`-CLI layer: per-run session-id User-Agent, `READ_ONLY_ACTIONS` whitelist, transient-error retry, per-call timeout, credential masking |
| `scripts/areas/ddh_capacity_guide/_constants.py` | Embedded rule data (family classification, host-event semantics incl. `*.Redeploy` / `*ErrorDisk`, DDH status table, guidance) as code constants |
| `scripts/requirements.txt` | Standard library only; no third-party packages |

### Usage

```
python3 scripts/areas/ddh_capacity_guide/sts_token.py
python3 scripts/areas/ddh_capacity_guide/ddh_capacity_guide.py --region-id cn-hangzhou \
    --instance-id i-bp1xxxx --instance-id i-bp2xxxx \
    --symptom "instance was rebooted by the underlying host, want to know why"
python3 scripts/areas/ddh_capacity_guide/ddh_capacity_guide.py --region-id cn-hangzhou \
    --instance-id i-bp1xxxx --dedicated-host-id dh-bp1xxxx \
    --symptom "Running but unresponsive, SSH returns no banner, storage ceiling"
python3 scripts/areas/ddh_capacity_guide/ddh_capacity_guide.py --region-id cn-hangzhou \
    --instance-type ecs.e-c1m2.xlarge --symptom "shared CPU contention, noisy neighbor"
```

`--region-id` is required (the ECS Describe APIs are regional). Pass `--json` for
machine-readable output. Add `--profile <name>` to use a named CLI credential.
`--dedicated-host-id` is optional: without it the host id reported by the instance
(`DedicatedHostAttribute.DedicatedHostId`) is used.

Which evidence is fetched depends on the matched route: a host-event symptom reads
the event record and the Dedicated Host status, a storage-ceiling symptom reads the
disk inventory and the disk monitor series, and a type-only question makes no cloud
call beyond the identity pre-check.

## How it works (decision tree)

1. **Visibility pre-check.** Query `DescribeInstances` (and
   `DescribeInstanceStatus`) for the region + instance id(s). An empty result is
   reported as a **not-visible-under-this-account/region** boundary, never as
   "the instance does not exist" ([references/ddh-capacity-guide__account-visibility.md](references/ddh-capacity-guide__account-visibility.md)).
2. **Family classification.** Classify each instance type as shared / burstable /
   dedicated using the embedded rule table (bare-metal first, then `t` burstable,
   then shared `e`/`s6`/`xn4`/`n4`/`mn4`/`e4`, then dedicated `g`/`c`/`r`/`u`)
   ([references/ddh-capacity-guide__instance-family-isolation.md](references/ddh-capacity-guide__instance-family-isolation.md)).
3. **Event record.** Read `DescribeInstanceHistoryEvents` per instance with every
   documented lifecycle status, so an event the customer received is named with its
   real type, status and timing
   ([references/ddh-capacity-guide__host-events-and-maintenance.md](references/ddh-capacity-guide__host-events-and-maintenance.md)).
4. **Dedicated Host status.** Read `DescribeDedicatedHosts` for the host the
   instance reports (or `--dedicated-host-id`). `Status` is a single-value filter
   whose default is `Available`, so the queryable values `Available` /
   `UnderAssessment` / `PermanentFailure` are read explicitly; `TempUnavailable` and
   `Redeploying` are documented in the CLI help but rejected by the live service and
   are therefore never reported as checked.
5. **Cloud-disk I/O.** For a storage-ceiling symptom, read `DescribeDisks` then
   `DescribeDiskMonitorData` for the recent window and quote the returned IOPS /
   BPS / latency peaks with the window
   ([references/ddh-capacity-guide__performance-limits.md](references/ddh-capacity-guide__performance-limits.md)).
6. **Symptom routing.** Route the customer's own wording to the matching official
   rules:
   - Reboot / redeploy / local-disk maintenance event / downtime / notification /
     compensation -> event explanation, maintenance-window steps, SLA process.
   - Performance difference / contention / migration request -> isolation selection
     (dedicated family vs DDH vs capacity reservation) and the two host-migration
     self-service paths.
   - Running but unresponsive / SSH no banner / IOPS-BPS -> specification
     performance ceiling.
7. **Evidence report.** Emit facts + rule-based guidance + explicit limitations,
   ending with a `STATUS` and `NEXT_ACTION`. When any API is unavailable, lacks
   permission, or returns nothing, degrade to the rule-based answer, record the
   `[WARN]` trace and state which evidence is missing; never fabricate a reading.

## Observability

Every `aliyun` CLI invocation carries a per-run User-Agent so all calls of one
diagnosis can be correlated. The UA follows the template

```
AlibabaCloud-Agent-Skills/{skill}/{session-id} skill-version/{skill-version}
```

where `{skill}` resolves to this skill's name
(`area:ddh-capacity-guide`) and `{session-id}` is a 32-character
lowercase hex `session_id`, generated once per run (`uuid.uuid4().hex`) and
attached to every call via `--user-agent`.

## Output contract

The report relays the script's `Summary` truthfully, names the account UID and
region that were queried, quotes only real returned fields, and gives **manual
guidance only** (never a change). It ends with:

- `STATUS: OK` - facts retrieved and guidance produced.
- `STATUS: DEGRADED` - a read-only query failed or returned empty; findings plus
  the recorded `[WARN]` degradations are relayed.
- `STATUS: FAIL` - insufficient input (missing region / no id, type, or symptom).
- `NEXT_ACTION: ...` - the concrete next step, including any handoff to a ticket.

On a permission failure the skill prints, for every denied call, one identifiable
line

```
NoPermission: <ram action>
```

using the literal `NoPermission` (or `ImplicitDeny` / `Forbidden` when that is the
denial the service reported), plus a minimal read-only policy snippet containing
only the denied actions, `"Effect": "Allow"` and `"Resource": "*"`. The same data
is exposed in `--json` as `permission_gaps` and `minimal_readonly_policy`. This
branch is part of the normal degradation structure: the failure is still recorded
as a `[WARN]` and the `STATUS` semantics are unchanged (`DEGRADED`, never a stack
trace).

## References

- [references/ram-policies.md](references/ram-policies.md) - minimal read-only actions.
- [references/ddh-capacity-guide__host-events-and-maintenance.md](references/ddh-capacity-guide__host-events-and-maintenance.md)
- [references/ddh-capacity-guide__instance-family-isolation.md](references/ddh-capacity-guide__instance-family-isolation.md)
- [references/ddh-capacity-guide__performance-limits.md](references/ddh-capacity-guide__performance-limits.md)
- [references/ddh-capacity-guide__account-visibility.md](references/ddh-capacity-guide__account-visibility.md)
- [references/ddh-capacity-guide__handoff-playbook.md](references/ddh-capacity-guide__handoff-playbook.md)
