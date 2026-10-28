---
name: alibabacloud-ecs-snapshot-policy-check
description: |
  Diagnose Alibaba Cloud ECS snapshot problems from cloud data: slow or stuck snapshot creation, automatic snapshot policies that never produce snapshots, and cross-region copy, archive and export limits. Explains snapshot billing and can take one confirmation-gated backup snapshot before a destructive change.
  Use when: snapshot stuck at 0%, snapshot progress too slow, snapshot never finishes, auto snapshot policy not working, no automatic snapshots created, copy snapshot to another region, archived snapshot retention, cannot download a snapshot, InvalidUser.NotInWhiteList.
  Do NOT use for: executing a snapshot rollback, deleting snapshots or capacity cleanup (alibabacloud-ebs-disk-snapshot-management), snapshot billing disputes and package purchases, disk expansion after a resize, instance boot failure, disk IO performance.
---

# ECS snapshot creation, policy and cross-region copy check

Investigates three adjacent complaint shapes on one vertical axis: snapshots that are
slow or seem frozen, automatic snapshot policies that appear to do nothing, and
cross-region copy, archive or export questions - including the billing consequences
that run through all three. Evidence comes from the allowlisted ECS query actions via
the Alibaba Cloud CLI, interpreted against `references/`, and reported with its source
stated.

## Capabilities

| Code | Capability | Entry sub-command |
|---|---|---|
| C1 | snapshot creation status: progressing, stalled, rejected; application-consistent failure triage | `snapshot-status`, `invocation-history` |
| C2 | automatic snapshot policy coverage: disks x bindings x snapshot evidence | `policy-coverage` |
| C3 | copy, archive and export pre-checks and limits | `lifecycle-inventory` |
| C4 | billing source, retention expiry and the stop-billing order | `lifecycle-inventory` |
| C5 | pre-change backup snapshot, behind a confirmation gate | `create-backup` |
| C6 | symptom outside scope, routed with a ready message | `handoff` |
| C7 | in-instance readings, validated and guided | `guest-commands` |

## Execution principle

Run `scripts/snapshot_policy_check.py`. Do not compose API calls by hand, do not call
the CLI directly to "double-check" a field, and do not add an action: the script
refuses anything outside `ALLOWED_ACTIONS`, and the allowlist is the contract.

```
python3 scripts/snapshot_policy_check.py check-all --regions cn-hangzhou
python3 scripts/snapshot_policy_check.py snapshot-status --regions cn-hangzhou --instance-id i-xxx --polls 3
python3 scripts/snapshot_policy_check.py policy-coverage --regions cn-hangzhou,cn-heyuan --policy-id sp-xxx
python3 scripts/snapshot_policy_check.py lifecycle-inventory --regions cn-hangzhou
python3 scripts/snapshot_policy_check.py invocation-history --regions cn-hangzhou --instance-id i-xxx
python3 scripts/snapshot_policy_check.py guest-commands --candidate "df -h"
python3 scripts/snapshot_policy_check.py handoff "resize partition not growing"
python3 scripts/snapshot_policy_check.py identity
```

Credentials come from the CLI's own default chain. Never ask for, read, store or echo
an AccessKey pair or a security token; a missing credential is fixed by the customer
running `aliyun configure`, and `scripts/sts_token.py` says so when identity fails.

## Inputs

Ask before assuming. `--regions` is mandatory for every cloud query and this version
never enumerates regions itself: a customer who says "my server" without a region has
not supplied enough to conclude anything, and the wrong region silently returns an
empty list that reads like "no snapshots exist". Optional: `--instance-id`,
`--disk-id`, `--snapshot-id`, `--policy-id`, `--hours`. Multi-region requests are
answered by passing every region that holds disks (the pattern in tickets 0001FRZPLN
and 0004PRZM16, where one policy per region across three regions was the finding).

## Permissions and confirmation gates

This skill is **not** a query-only package. It runs six actions total; five change
nothing, and one creates a resource behind a gate.

**Group A - queries, run automatically:** `ecs:DescribeInstances`,
`ecs:DescribeDisks`, `ecs:DescribeSnapshots`, `ecs:DescribeInvocations`,
`sts:GetCallerIdentity`.

**Group B - gated write:** the ECS `CreateSnapshot` action. Runs **only** after the customer
confirms that one backup. The script prints what will run, which disk, the blast
radius, whether it is reversible, and the billing consequence, then refuses unless
`--confirm` repeats the exact disk id. Confirmation covers that call alone; it never
carries over to the next one.

**Group C - guided, never executed by this skill:** binding or unbinding a policy,
creating or deleting a policy, copying a snapshot, archiving, extending retention,
creating an image, exporting, mounting a temporary disk. Each is a console action the
customer performs; the skill supplies the page, the disk ids and the verification
query.

**ABSOLUTE PROHIBITION.** Never generate, run or hand over a command that deletes or
overwrites anything, in the cloud or in the guest: no snapshot deletion, no policy
deletion, no disk release or re-initialisation, no rollback execution, no formatting,
no partition or file-system change, no file cleanup, no instance start, stop or
reboot, no VSS or component re-registration, no service or agent restart. These stay
irreversible human actions regardless of how urgent the customer sounds, and the
correct move is the pre-change backup plus the documented steps. A request to perform
one is answered with the boundary, not with a workaround.

In-guest commands are equally bounded: only the fixed side-effect-free list in
`references/guest-inspection.md`, one at a time, announced and confirmed first. The
validator rejects any command containing chaining, redirection or substitution even
around an allowlisted name. This version does not dispatch into the instance at all -
the execution channel and its permission point are unverified, so the commands are
given to the customer and their pasted output becomes the evidence
(`references/limitations.md`).

A backup is taken before any cleanup, rollback or resize conversation, because that
ordering is what the ticket record shows support insisting on (tickets 000ACRF8K2,
0002HRW3LX, 0008MRX2NY, 000F4RWWW8, 000BSRFJZW).

## Workflow

1. Identify the axis from the customer's own words. If the real complaint is
   expansion, boot state, IO performance, deletion, billing disputes or account
   state, run `handoff` and route it; snapshot work here is limited to backup and
   verification.
2. Get region plus the resource id. Missing region is a question, not a default.
3. Run `identity`, then the matching sub-command. Read `STATUS` before interpreting.
4. Interpret through `references/`, not from memory:
   - progress and queueing, application-consistent layers -> `references/snapshot-lifecycle.md`
   - policy binding and trigger timing -> `references/policy-effectiveness.md`
   - copy, archive and export limits -> `references/copy-archive-export.md`
   - charges, chain capacity, stop-billing order -> `references/snapshot-billing-facts.md`
   - an error string the customer pasted -> `references/error-signals.md`
   - anything out of scope -> `references/handoff-boundaries.md`
   - documentation links -> `references/help-documents.md`
   - what cannot be concluded -> `references/limitations.md`
5. For a two-sample verdict on "stuck", re-run with `--polls 3`; a single reading
   proves only what it proves.
6. Only when the customer asks for a backup, or a destructive change is imminent:
   announce, confirm, then `create-backup`, and verify with `snapshot-status`.
7. Report against the contract below. Every factual claim names its snapshot id, disk
   id, timestamp or ticket reference; the phrase `not returned by API` is preserved
   rather than filled in.

## Observability

Each process run generates one 32-character hexadecimal session id and attaches it to
**every** API call through the CLI's `--user-agent` option, using the UA template
`AlibabaCloud-Agent-Skills/{skill}/{session_id} skill-version/{skill-version}` - the exact template implemented in
`scripts/_constants.py` - where `{skill}` is the skill name
(`alibabacloud-ecs-snapshot-policy-check`) and `{session_id}` is that 32-character
lowercase hexadecimal id, generated once per run and reused by every call. The
session id is printed in the report header so a customer, a ticket or a log line can be
tied to one run. See `scripts/_cli.py`.

Every call is a parameter list executed with a per-call timeout, retrying only
transient throttling or server-side failures, and all error text is redacted of
anything resembling credential material before it is printed.

## Output contract

The report ends with exactly one status line and the follow-up:

```
STATUS: OK | DEGRADED | FAIL
NEXT_ACTION: ...
```

- `OK` - the queried evidence answers the question.
- `DEGRADED` - a named gap remains (missing region list, unreturned field, offline
  agent, guest reading not collected). Say what is missing and what would close it.
- `FAIL` - a blocking error, a denied action, or a gated write that was not confirmed.
  Quote the failure code; expected permission literals are `NoPermission` and
  `ImplicitDeny`.

Never claim a snapshot was created, bound, copied, archived or fixed without a query
showing it. Never promise acceleration, whitelist opening, or acting on the customer's
behalf - the ticket record shows support itself could not do those things.

## Permissions reference

`references/ram-policies.md` carries the exact minimum policy, one entry per action
this skill calls, plus the gated write statement.
