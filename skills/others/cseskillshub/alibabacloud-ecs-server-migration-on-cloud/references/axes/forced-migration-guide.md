---
name: alibabacloud-ecs-forced-migration-guide
description: |
  Read-only Alibaba Cloud ECS guide for region or data-center decommission, forced or host migration, platform-initiated reboots, and related impact or compensation disputes. It reads only DescribeInstances (status, region, bound security groups), then returns step-by-step self-service guidance; it never changes resources, runs commands inside an instance, or files billing or compensation requests. Use when a customer reports a region retirement, forced or host migration, an unrequested reboot, or a fee tied to a platform action. Triggers: server taken offline by a region decommission; forced migration of my instance; instance rebooted on its own; SystemFailure.Reboot or SystemMaintenance.Reboot notice; compensation for downtime; refund is zero after a downgrade. Do NOT use for pure unsubscribe pricing, security-incident response, or in-instance root-cause diagnosis.
---

# Alibaba Cloud ECS Forced Migration Guide

A **read-only, guidance-only** skill (RO_GUIDE). It gathers instance facts through one
read-only OpenAPI call and turns a customer's symptom into concrete, self-service steps the
customer performs in their own console. It is built for the "region / data-center decommission
and forced migration, and the impact or compensation disputes that follow" symptom axis.

## What this skill does

- Reads the caller's own ECS instances with a single read-only action to establish ground
  facts: existence, `Status`, region/zone, charge type, and the security groups an instance is
  bound to.
- Classifies the customer's symptom into one of four guided playbooks: migration, incident/SLA,
  billing dispute, or exposure/attribution self-check.
- Prints human-followable steps, the correct console entry points, published formulas applied
  to the customer's own numbers, deadline math, and a completion-evidence checklist.
- Ends every run with an explicit `STATUS` and `NEXT_ACTION`, and an honest boundary statement.

## ABSOLUTE PROHIBITION (read-only skill)

The agent MUST NOT call, generate, or execute any resource-changing operation through this
skill. Concretely:

- The ONLY cloud API this skill may invoke is `DescribeInstances` (see
  [references/ram-policies.md](references/ram-policies.md)). Any mutating ECS action is out of
  the allow-list and must never be emitted.
- The skill MUST NOT run any command inside a customer instance (no Cloud Assistant, no
  Workbench, no remote login). Where an in-guest reading is needed, it instructs the customer to
  run a **read-only** command themselves and paste the output back.
- The skill MUST NOT submit, approve, or promise any refund, adjustment, voucher, or
  compensation. It only assembles evidence and names the human channel.
- The skill guides the customer through **console self-service** steps (the customer clicks and
  confirms). It must never hand the customer a mutating CLI command to run.

Because it is read-only, this skill declares no write permission anywhere in its policy files.

## When to use

- A region or availability zone is being decommissioned and the customer must move instances to
  another region.
- An instance was migrated or rebooted by the platform and the customer wants the reason, the
  correct self-service action, and the availability compensation route.
- A fee or refund dispute that the customer ties to a decommission, a platform action, or a
  billing rule (downgrade / unsubscribe / burstable-credit charges).
- A breach, traffic, or blame dispute where the cloud-side facts show no platform fault and the
  job is exposure self-check, attribution wording, and hand-off.

## When NOT to use (hand off)

- A pure unsubscribe or downgrade pricing question with no decommission and no platform fault.
- Active security-incident response (the main ask is blocking, tracing, or the attacker's identity).
- Diagnosing the customer's own application inside the instance.
- Anything requiring a written fault letter, judicial cooperation, or a regulator complaint.

See [references/forced-migration-guide__handoff-boundaries.md](references/forced-migration-guide__handoff-boundaries.md) for the full
recognize-and-hand-off table and the standard wordings.

## Prerequisites

- The `aliyun` CLI must be installed and configured with the **default credential chain** (for
  example `aliyun configure` profiles or standard environment variables).
- This skill only ever uses the caller's own credentials. Never place an access key, secret, or
  token in the conversation, in a file, or on the command line; never ask the customer for one.
- The read query only sees resources in the caller's own account and the single `RegionId` you
  pass. Cross-account data is never visible.

## Permissions

Only one read-only action is required: `ecs:DescribeInstances`. There is no wildcard and no
write permission. See [references/ram-policies.md](references/ram-policies.md) for the minimal
policy document and the handling of a permission failure (which reports `NoPermission` or
`ImplicitDeny` and names the single missing read action).

## Usage

Run the single entry script; do not assemble `aliyun` calls by hand or call any other action.

```bash
python3 scripts/axes/forced_migration_guide/forced_migration_guide.py --region-id cn-hangzhou --intent triage
python3 scripts/axes/forced_migration_guide/forced_migration_guide.py --region-id cn-hangzhou --instance-ids i-bp1xxxx --intent migration
python3 scripts/axes/forced_migration_guide/forced_migration_guide.py --region-id cn-shanghai --intent exposure
python3 scripts/axes/forced_migration_guide/forced_migration_guide.py --region-id cn-hangzhou --json
```

Arguments:

- `--region-id` (required): the region to read. Only instances in this region are visible.
- `--instance-ids` (optional): comma-separated ids to scope the read-only query.
- `--intent` (optional): `triage` (default), `migration`, `incident`, `billing`, or `exposure`.
- `--skip-credential-check` (optional): skip the best-effort caller-identity probe.
- `--json` (optional): emit the raw read-only facts as JSON only.

## Workflow and decision tree

1. Collect inputs: instance id, region, the notice or billing period involved, and the intent
   (migration action / reboot + compensation / fee dispute / blame dispute).
2. Read facts: one `DescribeInstances` call. Extract status, region, and bound security groups.
3. Triage into a branch:
   - Decommission / forced migration -> [references/forced-migration-guide__migration-checklist.md](references/forced-migration-guide__migration-checklist.md):
     the five-step image move plus a completion-evidence checklist, with "verify the new
     instance before retiring the old one" as a hard warning.
   - Reboot / maintenance / availability impact -> [references/forced-migration-guide__incident-sla-guide.md](references/forced-migration-guide__incident-sla-guide.md):
     classify `SystemMaintenance.Reboot` vs `SystemFailure.Reboot` **from the customer's own
     notice or screenshot** (the skill cannot read the platform event), give the matching
     self-service step, and always state the SLA application route and its deadline.
   - Fee / refund dispute -> [references/forced-migration-guide__billing-dispute-guide.md](references/forced-migration-guide__billing-dispute-guide.md):
     apply the published formula to the customer's numbers, point at the self-service evidence,
     and package an escalation.
   - Blame / breach dispute -> [references/forced-migration-guide__exposure-selfcheck.md](references/forced-migration-guide__exposure-selfcheck.md):
     exposure self-check from the bound security groups, read-only in-guest commands for the
     customer to run, and the attribution three-way.
4. Output: evidence-based conclusion, the customer's to-do steps, the re-verification method, and
   an explicit statement of what depends on customer evidence and what must go to a human.

## Key limitation (attribution depends on customer evidence)

The single most important premise on the incident and exposure branches is that the platform
event type, its timing, and any underlying-host fault cannot be read by this skill. Attribution
therefore rests on evidence the customer provides (SMS / message-center text, console event or
monitor screenshots, in-guest read-only command output). When that evidence is missing, the skill
does not guess a cause: it emits the two-branch fallback and routes to a human, and it labels the
conclusion "attribution not self-proved, relies on customer evidence".

## Output contract

Every run reports the script's own result faithfully and closes with:

- `STATUS: OK` (facts resolved and guidance emitted), `DEGRADED` (no matching instance, or a
  credential / evidence gap), or `FAIL` (the read-only query could not complete).
- `NEXT_ACTION`: the concrete follow-up for that status.

Quote only real returned values. If the query is empty or fails, record the limitation instead of
inventing values. State the region and account the facts were read from.

## Observability

Every cloud call from the scripts carries a per-run User-Agent so requests are attributable to
this skill and run:

- Template: `AlibabaCloud-Agent-Skills/{skill-name}/{session-id} skill-version/{skill-version}`; for this skill the
  placeholders resolve to `AlibabaCloud-Agent-Skills/alibabacloud-ecs-forced-migration-guide/<32-hex>`.
- `<session-id>` is a fresh 32-character lowercase hex id generated once per process with
  `uuid.uuid4().hex` and reused for all calls in that run.
- It is attached on every invocation through the `--user-agent` flag (the `User-Agent` on the
  underlying request), including the best-effort `aliyun sts get-caller-identity` probe.

## References

- [references/ram-policies.md](references/ram-policies.md) - the single read action and the
  permission-failure wording.
- [references/forced-migration-guide__migration-checklist.md](references/forced-migration-guide__migration-checklist.md) - decommission / forced
  migration self-service steps and evidence checklist.
- [references/forced-migration-guide__incident-sla-guide.md](references/forced-migration-guide__incident-sla-guide.md) - reboot classification
  from customer evidence and the SLA route.
- [references/forced-migration-guide__billing-dispute-guide.md](references/forced-migration-guide__billing-dispute-guide.md) - published refund
  formulas and the escalation evidence pack.
- [references/forced-migration-guide__exposure-selfcheck.md](references/forced-migration-guide__exposure-selfcheck.md) - security-group exposure,
  read-only in-guest commands, and attribution wordings.
- [references/forced-migration-guide__handoff-boundaries.md](references/forced-migration-guide__handoff-boundaries.md) - recognize-and-hand-off
  table and standard boundary wordings.
