---
name: alibabacloud-ecs-snapshot-and-backup
description: |
  Diagnose ECS snapshot and backup state: snapshot policies, IO impact, consistency groups, rollback flow, backup strategy design and HBR integration.
  Use when (customer wording): automatic snapshot policy keeps consistency; consistency group entry missing; create a group automatically; implicitdeny on describesnapshots; multi-disk snapshot same time point; nopermission; nopermission or implicitdeny on describesnapshots; snapshot consistency group; snapshot stuck creating, uploading to oss; stop the instance to roll back.
  Do NOT use for symptoms covered by alibabacloud-ecs-ticket-support (it routes first); non-ECS products.
  Triggers: "snapshot stuck creating, uploading to oss", "consistency group entry missing", "multi-disk snapshot same time point", "nopermission on describesnapshots", "stop the instance to roll back".
---

# alibabacloud-ecs-snapshot-and-backup

Merged ECS support skill (5 axes, customer-symptom family). Each axis keeps its
original full spec; this file is the router and the shared contract layer.

## Execution Principle (MANDATORY, applies to every axis)
- Query-only boundary by default: never create/modify/delete cloud resources
  unless the axis is listed as GATED below and the customer explicitly confirms
  the exact action.
- ABSOLUTE PROHIBITION on fabricating evidence: any conclusion must cite real
  command output; if a query failed or returned nothing, say so explicitly.
  Claiming "verified/executed" without trace = violation.
- ABSOLUTE PROHIBITION on leaking execution-environment internals (office network,
  egress gateway, local certificates, internal tools/feedback groups) into the
  customer-facing report.
- Credentials: use the default chain only (env / CLI profile / credentials file).
  Never print or hardcode AK/SK. ABSOLUTE PROHIBITION on reading
  `~/.aliyun/config.json`, `~/.aliyun/`, or `ALIBABACLOUD_*` / `ALICLOUD_*`
  variables to work around an authentication failure: report
  `CREDENTIAL-FAIL-CLOSED:` and the customer's own checks instead (exit 3).

## Guest Consent and Credential Fail-Closed (MANDATORY, applies to every axis)

**In-guest reads are OFF by default.** Cloud Assistant `RunCommand` executes inside the
customer's instance. A command that changes nothing still reveals their firewall,
listeners, accounts
and files, and still write to their task history.

- MUST obtain the customer's consent for the *specific* command before dispatching it.
  Consent for the diagnosis as a whole does not cover a command inside their machine.
- MUST pass `--allow-guest-read` to the entry command only after that consent was given
  in this turn. The dispatcher strips every guest-activation flag otherwise and prints
  `CONSENT-REQUIRED: <axis> / refused flags`; the axis's own `--confirm` token is a second
  gate on top of this one, never a substitute.
- MUST NOT re-run with `--allow-guest-read` on your own initiative. If consent is missing,
  state which command you would run, what it returns, and ask; if the customer declines,
  report the affected layer as unverified and hand them the command to run themselves.
- MUST NOT describe a layer as clean because its guest read did not run.

**Credential failure is fail-closed.** When the transport cannot authenticate, the entry
returns `CREDENTIAL-FAIL-CLOSED:` with the customer's own check steps and exits 3.

- ABSOLUTE PROHIBITION: never read `~/.aliyun/config.json`, `~/.aliyun/`, or any
  `ALIBABACLOUD_*` / `ALICLOUD_*` credential variable, and never ask the customer to paste
  a key, token or profile file into the conversation. `_guardrails.py` refuses to spawn a
  command that carries those paths or names.
- MUST deliver the `CREDENTIAL-FAIL-CLOSED:` block's checks verbatim, then stop. Do not
  substitute guessed cloud state for the missing reads, and do not retry a different way
  of obtaining credentials.
- MUST NOT claim "no issue found" when the evidence was unreadable. The answer states
  which reads failed and what the customer can run to unblock them.

## Axis Index (Module Index)
| Axis | Entry command (keep the scripts/ prefix verbatim) | Mode | Full spec |
|---|---|---|---|
| `snapshot-policy-check` | `python3 scripts/snapshot-and-backup.py --axis snapshot-policy-check -- <args>` | gated | [snapshot-policy-check](references/axes/snapshot-policy-check.md) |
| `snapshot-io-impact` | `python3 scripts/snapshot-and-backup.py --axis snapshot-io-impact -- <args>` | gated | [snapshot-io-impact](references/axes/snapshot-io-impact.md) |
| `snapshot-consistency-group` | `python3 scripts/snapshot-and-backup.py --axis snapshot-consistency-group -- <args>` | query-only | [snapshot-consistency-group](references/axes/snapshot-consistency-group.md) |
| `snapshot-rollback-guide` | `python3 scripts/snapshot-and-backup.py --axis snapshot-rollback-guide -- <args>` | gated | [snapshot-rollback-guide](references/axes/snapshot-rollback-guide.md) |
| `backup-strategy-design` | `python3 scripts/snapshot-and-backup.py --axis backup-strategy-design -- <args>` | query-only | [backup-strategy-design](references/axes/backup-strategy-design.md) |

Gated axes in this package: snapshot-policy-check, snapshot-io-impact, snapshot-rollback-guide. The gate covers state-changing actions ONLY: those MUST stop and ask for explicit customer confirmation (`--confirm` flow) before running; without confirmation, do not mutate anything. Read-style in-guest probes also travel through Cloud Assistant RunCommand. They are NOT query-only from the customer's side: the command still executes inside their machine and leaves a task record there. ABSOLUTE PROHIBITION: never dispatch one without the customer's consent for that exact command in this turn. Ask first, then pass `--allow-guest-read` to the entry command. Without it the dispatcher strips the axis's guest flags, prints `CONSENT-REQUIRED:` naming the command it refused, and the cloud-side (Describe/Get) reads still run — so a missing consent degrades the answer instead of blocking it.

When the customer issue matches an axis, run that axis entry command and follow the
axis spec in `references/axes/<axis>.md`. Do not mix axes in one report.

## Trigger Conditions
See description (customer wording kept verbatim from the merged intake analysis).

## Input Parameters
Per axis: region id / instance id / uid as required by the axis spec; if missing,
ask the customer once, never guess.

## Execution Flow
1. Classify the symptom into one axis via the table above.
2. Run the axis entry command in query-only mode.
3. Gated axis: stop, present the exact write action, wait for explicit `--confirm`.
4. Deliver the report in the axis spec's format.

## Observability
Every CLI/API call in this skill attaches the User-Agent template
`AlibabaCloud-Agent-Skills/{skill}/{session-id} skill-version/{skill-version}` (skill = this package name),
where session-id is a 32-character hex string generated once per run and reused
across all calls in that run (implemented by each axis's `_cli.py` under scripts/axes/).

## Boundary (Do NOT use for)
- Do NOT use for: executing a snapshot rollback, deleting snapshots or capacity cleanup (alibabacloud-ebs-disk-snapshot-management), snapshot billing disputes and package purchases, disk expansion after a resize, instance boot failure, disk IO performance.
- Do NOT use for snapshot creation failure (alibabacloud-ecs-snapshot-policy-check),
- Do NOT use for snapshot fees, storage packages, single-disk snapshot management, running a rollback, or in-guest mount errors.
- Do NOT use for snapshot object operations or rollback (use alibabacloud-ebs-disk-snapshot-management), security incidents, connectivity faults, disk resizing, or account billing matters.

## Important Notes
- Relative paths only; all assets live in this package.
- All network/API/subprocess calls carry timeouts.
