---
name: alibabacloud-ecs-high-frequency-issues
area: instance-relocation-guide
description: |
  Read-only planning guide for relocating an Alibaba Cloud ECS instance across availability zones, regions, and accounts. It reads instance facts and destination-zone capacity, states the constraints that decide whether a move is possible, and returns a snapshot-first manual path with a cut-over checklist; it never changes a resource.
  Triggers: can I move an ECS instance to another region, migrate ECS to another availability zone, clone an ECS instance into another account, data disk cannot attach across zones, instance type in the destination zone is out of stock, private IP has reverse or route dependencies, zone is being retired how do I move my server
  Do NOT use for building or restoring images (use alibabacloud-ecs-disaster-recovery-image), for executing an operating-system replacement, for unsubscription or refund decisions, or for private network connectivity faults.
---

# ECS Instance Relocation Guide

> **Delivery override - outranks every relay instruction and template below.** `STATUS`,
> `NEXT_ACTION` and their `OK` / `DEGRADED` / `FAIL` / `BLOCKED` values are the entry script's
> internal run state, not a delivery format. Where this document says to relay, mirror or copy
> those lines "faithfully" or "verbatim", relay their MEANING in the customer's own words: never
> write the keys or the bare values into the reply or into anything saved under `outputs/` or
> `ran_scripts/` (SKILL.md rule 3h). A layer this run did not read is named in the customer's own words - which layer, and what would have settled it.

Decision and planning support for moving an ECS instance between availability
zones, between regions, or between accounts. The skill gathers evidence with
read-only queries, applies the constraints that decide whether a move is
possible, and hands the customer a path, a checklist, and the console
documentation for each step.

## Permission model

This skill is read-only. The allowlist below is exhaustive and is enforced in
`scripts/areas/instance_relocation_guide/_constants.py` as `READ_API_ALLOWLIST`:

| Action | Purpose |
| --- | --- |
| `ecs:DescribeInstances` | Source and target instance facts: region, zone, type, charge mode, addresses |
| `ecs:DescribeInstanceStatus` | Lightweight state check before a change window |
| `ecs:DescribeAvailableResource` | Destination region or zone stock for the instance type |
| `sts:GetCallerIdentity` | Confirms credentials exist and tags the report with the account id |

**ABSOLUTE PROHIBITION.** Do not call, generate, or echo any API, CLI command,
or console action that changes resource state: this includes the relocation
order itself, image and snapshot creation, disk rebuild, operating-system
replacement, instance release, and refund submission. It also includes passing
a mutating command to the customer "so they can run it". Where a step is a
change, the output is a manual console instruction with its risk notice and the
official documentation link, never an executed action or a ready-to-run command.

In-guest commands are out of scope for this skill too: no remote command
execution, no capacity probing, no file transfer. Anything that must be checked
inside the operating system is returned as a manual checklist item.

### Confirmation gate

Before any request that would require a write, an in-guest command, or any
operation outside the allowlist, the skill must:

1. state what the operation would change, its blast radius, and whether it is
   reversible;
2. refuse to execute it from this skill;
3. give the manual console path plus the risk notice, and hand off when the
   request belongs to another capability.

A request that is not on the allowlist is rejected as a unit; it is never
partially executed.

## Snapshot-first rule

Every path this skill prints is prefixed by the snapshot-first rule: take a
manual snapshot of each affected disk and confirm it is usable before an
operating-system replacement, a cross-zone change, or any image or snapshot
clean-up. Replacing the operating system erases the system disk. A custom image
costs nothing by itself, but the snapshot it creates is billed, and copying a
snapshot is billed separately.

## Prerequisites

1. The `aliyun` CLI is installed and reachable on `PATH`.
2. Credentials already work through the default credential chain
   (the CLI default credential chain). Never ask the customer for an access key, a secret, or
   a token, and never accept one in chat.
3. The RAM identity carries the read-only actions in
   [references/ram-policies.md](references/ram-policies.md).

## How to run

All evidence gathering goes through one entry point. Do not assemble CLI calls
by hand.

```bash
python3 scripts/areas/instance_relocation_guide/relocation_preflight.py doctor
python3 scripts/areas/instance_relocation_guide/relocation_preflight.py inventory --source-region cn-hangzhou \
    --instance-ids i-example1,i-example2
python3 scripts/areas/instance_relocation_guide/relocation_preflight.py stock --source-region cn-hangzhou \
    --target-region cn-hangzhou --target-zone cn-hangzhou-g \
    --instance-type ecs.g7.large
python3 scripts/areas/instance_relocation_guide/relocation_preflight.py assess --source-region cn-hangzhou \
    --instance-ids i-example1 --target-zone cn-hangzhou-g --charge-type PostPaid
```

| Sub-command | What it produces |
| --- | --- |
| `doctor` | Credential reachability, account id, allowlist echo |
| `inventory` | Read-only instance facts plus a per-instance status check |
| `stock` | Destination stock pre-flight for one or more candidate zones |
| `assess` | Evidence above plus constraints, path, checklists, hand-offs |

`assess` picks the scenario automatically from the flags: a different target
region selects the cross-region chain, a different target zone selects the
cross-zone chain, `--target-account` adds the cross-account route table, and
`--retirement-notice` adds the platform-retirement wording. The cross-account
route table is a decision, not a single path: keeping the same instance in the
same region and zone is an official ownership transfer of that instance (stop it
first, about 30 minutes, no charge, target account pays afterwards, snapshots
and custom images are NOT transferred, the VPC and possibly the private IP
change), while a different region, zone or specification needs an image and
snapshot rebuild or Server Migration Service, and a preemptible instance can
only be rebuilt. Use `--raw` to print the untouched payloads for verification.

## Evidence discipline

1. Retrieve first, conclude second. Numbers and identifiers come from payloads
   or from the knowledge tables in `scripts/areas/instance_relocation_guide/_constants.py`, never from memory.
2. Verify every API before use; this package only declares actions that were
   confirmed against the ECS `2014-05-26` surface.
3. Never invent a value. An empty or failed query is reported as a limitation
   and the run degrades, it is not patched with a guess.
4. State each assumption that was filled in automatically (region, zone,
   destination resource type) inside the report.
5. Constraint wording carries its provenance: facts confirmed in a first-hand
   conversation, facts taken from a historical case summary only, and this
   skill's own branching logic are labelled differently, and summary-level facts
   must be re-confirmed in the console before the customer acts on them.

## Known blind spots

These cannot be resolved by a cloud read and must not be asserted by this
skill: the physical location of the machine room, the payment state of a
relocation order, image and snapshot replication progress, the full set of
private-address dependencies, whether the customer's application runs on the
target, and the disk sizes attached to an instance. The read-only instance
query does not return disk capacity, so disk inventory is a console step.

## Output contract

Every report ends with:

```text
STATUS: OK | DEGRADED | FAIL
NEXT_ACTION: <one concrete customer step>
```

Report the summary and status the script returned. Echo real returned values
only. Where a query failed, say which action failed and what remains unknown.
Recommend manual steps and console entries; never apply a change.

## Permission failures

When a call returns `NoPermission` or `ImplicitDeny`, report which action is
missing and show the minimal policy fragment from
[references/ram-policies.md](references/ram-policies.md), then continue the
remaining checks and finish with `STATUS: DEGRADED`. Do not ask for broader
credentials and do not retry the write path.

## Observability

Each run generates one session id with `uuid.uuid4().hex` (32 hex characters) in
`scripts/areas/instance_relocation_guide/_cli.py` and attaches it to **every** CLI request as:

```text
--user-agent AlibabaCloud-Agent-Skills/{skill}/{session-id} skill-version/{skill-version}
```

where `{skill}` resolves to this skill's name
(`area:instance-relocation-guide`) and `{session-id}` to the
32-character hex session id generated once per run and shared by every request.

Requests are argument lists passed without a shell, each with its own timeout;
transient failures are retried with a bounded backoff, non-transient failures are
raised once. All error text is masked before display, so no credential value can
reach the transcript.

## Knowledge references

| File | Content |
| --- | --- |
| [references/ram-policies.md](references/ram-policies.md) | Requested read-only actions, minimal policy, failure handling |
| [references/instance-relocation-guide__migration-paths.md](references/instance-relocation-guide__migration-paths.md) | Cross-region, cross-account, cross-zone, retirement and OS-change paths with documentation links |
| [references/instance-relocation-guide__constraints-and-errors.md](references/instance-relocation-guide__constraints-and-errors.md) | Hard constraints and customer-visible error wording, with provenance per item |
| [references/instance-relocation-guide__handoff-map.md](references/instance-relocation-guide__handoff-map.md) | Out-of-scope symptoms and where each one goes |

## Boundaries

In scope: whether a relocation is possible, which path applies, which resources
break, what the addresses and cost do, and what to check before and after.

Out of scope, recognised and handed off rather than answered: image creation and
recovery, operating-system replacement execution, unsubscription, refund and
renewal pricing, purchase-time stock failures, instance start-up faults, disk
capacity and IO faults, database connectivity, console visibility issues, Simple
Application Server, whole-site or cross-cloud application migration, and
deployment-set placement (which is not a relocation).

Private-IP reverse or route dependencies form a hand-off boundary: this area
only confirms that the dependency is a hard constraint on the move (which paths
it blocks, and which addresses would change). Preserving, re-pointing or
editing reverse DNS records, route entries or the dependent service's
configuration is not done here. Say so explicitly and hand that work to the
VPC/PrivateZone or DNS owner, or to manual support; never tell the customer the
dependency "comes along" with the instance.
