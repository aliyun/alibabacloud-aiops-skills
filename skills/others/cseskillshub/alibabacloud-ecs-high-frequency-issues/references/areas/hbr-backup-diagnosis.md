---
name: alibabacloud-ecs-high-frequency-issues
area: hbr-backup-diagnosis
description: |
  Diagnoses failed ECS backups made with Cloud Backup (HBR): File Backup Essential Edition and whole-instance jobs that fail, restores that report success without returning files, and backup charges the customer cannot locate. Queries run automatically; guest commands and snapshots need consent first.
  Use when a customer reports a backup alarm, a restore that did not bring data back, or a cloud backup charge they cannot explain.
  Triggers: ECS file backup failed; cannot access Cloud Assistant; insufficient disk space caused backup failure; EcsReleased alarm; restore completed but files missing; stop cloud backup billing.
  Do NOT use: disk resize not applied (area:disk-expand-diagnosis); instance will not start (area:instance-state-diagnosis); slow disk IO (area:resource-bottleneck); enablement alone (alibabacloud-cloudbackup-ecs-file-backup-essential-edition).
---

# ECS Cloud Backup (HBR) diagnosis

> **Delivery override - outranks every relay instruction and template below.** `STATUS`,
> `NEXT_ACTION` and their `OK` / `DEGRADED` / `FAIL` / `BLOCKED` values are the entry script's
> internal run state, not a delivery format. Where this document says to relay, mirror or copy
> those lines "faithfully" or "verbatim", relay their MEANING in the customer's own words: never
> write the keys or the bare values into the reply or into anything saved under `outputs/` or
> `ran_scripts/` (SKILL.md rule 3h). A layer this run did not read is named in the customer's own words - which layer, and what would have settled it.

Closes the loop on the four questions this tier actually asks: why did the backup
fail, why did the restore not restore, what is this charge, and why can I not see
the task. The symptom arrives in the customer's words, so classification is driven
by the alarm wording and the decision tree routes it to a root cause.

## Run the script, do not compose API calls

`scripts/areas/hbr_backup_diagnosis/hbr_backup_diagnosis.py` is the only execution surface. Never construct
an `aliyun` command by hand, never call an action that the script does not
already call, and never substitute a broader action when one is denied.

```bash
python3 scripts/areas/hbr_backup_diagnosis/hbr_backup_diagnosis.py check-env
python3 scripts/areas/hbr_backup_diagnosis/hbr_backup_diagnosis.py triage --region-id <region-id> \
  --instance-id <instance-id> --alert-text "<the alarm as the customer wrote it>"
python3 scripts/areas/hbr_backup_diagnosis/hbr_backup_diagnosis.py billing-attribution --region-id <region-id>
python3 scripts/areas/hbr_backup_diagnosis/hbr_backup_diagnosis.py guest-probe --region-id <region-id> \
  --instance-id <instance-id> --command df_h
python3 scripts/areas/hbr_backup_diagnosis/hbr_backup_diagnosis.py snapshot-guard --region-id <region-id> --disk-id <disk-id>
python3 scripts/areas/hbr_backup_diagnosis/hbr_backup_diagnosis.py explain --topic concepts --region-id <region-id>
```

`explain --topic` takes `concepts`, `enable`, `restore`, `upgrade`, `retention`,
`alarm-states` and `guest-fallback`.

## Permission model: four classes

This skill is **not limited to informational calls**. It declares that plainly,
because two write-class actions are part of it, and pretending otherwise would
make the boundary unenforceable.

| Class | What | Actions | Consent needed |
| --- | --- | --- | --- |
| A | Informational cloud queries, region-scoped state reads | `ecs:DescribeInstances`, `ecs:DescribeDisks`, `ecs:DescribeSnapshots`, `ecs:DescribeInvocations`, `sts:GetCallerIdentity` | No |
| B | One side-effect-free command inside the instance, to measure what no API exposes | `RunCommand` (RAM code `ecs`; CLI plugin mode `ecs run-command`) | **Yes, per command** |
| C | Low-risk reversible write: the pre-cleanup snapshot | `CreateSnapshot` (RAM code `ecs`; CLI plugin mode `ecs create-snapshot`) | **Yes, per disk** |
| D | Anything destructive | none, ever | Not applicable: never executed |

`RunCommand`, delivered under the `ecs` RAM code, is a write-class permission
even when the command it carries only prints. That is the reason class B exists
as a gated class instead of being lumped in with the queries.

### The consent gate, in force

Before any class B or class C action, all four of these must happen, in this
order. The script enforces the shape of this: run without `--confirm` and it
performs the disclosure and stops.

1. **Tell the customer the exact string** that will execute, or the exact
   snapshot that will be created.
2. **State the blast radius**: which single instance or disk, and whether any
   byte is modified.
3. **State reversibility**, and for `CreateSnapshot` **state that a snapshot
   is billed** - point at the pricing page before creating one, never after.
4. **Obtain agreement**, then re-run with the `--confirm` token the previous run
   printed.

The token binds consent to one region, one resource and one command. **A consent
covers exactly one operation.** A second probe, a second disk, a second instance,
or the same probe an hour later all need a fresh disclosure and a fresh token. The
script rejects a `--confirm` that does not match the token it computed, so
reusing one is not possible even by accident.

### Non-whitelisted commands are refused, not softened

`guest-probe` accepts a key from the whitelist in
[references/hbr-backup-diagnosis__guest-commands.md](references/hbr-backup-diagnosis__guest-commands.md), nothing else. A key
that is not on the list fails. So does a whitelisted key whose assembled string
contains a shell metacharacter or a rejected token - the string is re-validated
after assembly, which is what stops an argument from smuggling a second command.

When a refusal happens, report the rejection and its reason. Do not rewrite the
request into a command that passes, and do not decide that an unlisted command is
harmless because it looks like a read.

## ABSOLUTE PROHIBITION

Never generate, run, or hand the customer a command that performs any of these.
This holds even when the customer explicitly asks, because the operation is
irreversible rather than because they are unsure.

- `Modify*`, `Create*` other than `CreateSnapshot`, `Delete*`, `Release*`,
  `Reset*`, `Replace*`, `Attach*`, `Detach*`, `Reboot*`, `Start*`, `Stop*`.
- Any Cloud Backup (HBR) action at all, including `DeleteBackupPlan`. It is
  described as a manual option and never called.
- Deleting, emptying or truncating files, logs or a recycle bin inside an instance.
- Stopping, restarting or disabling any service, including the database engine
  whose lock is what makes a restore skip files, and including a third-party
  tunnel client whose route claim is what breaks Cloud Assistant.
- Changing a resolver, route table, NACL, security group, disk password or system
  configuration; rebooting an instance; installing or removing software.
- Deleting a snapshot, a backup plan or a backup vault. Cancelling a backup
  permanently destroys its stored data, and this is stated to the customer before
  they act, not after.
- Topping up, unsubscribing, refunding, purchasing a resource plan, or asking for
  a payment extension.

For all of the above, output the console path, the risk, and who owns it. The
source cases show a support engineer with login authorisation doing these things;
that is the ceiling, and it is not below this skill's.

## API whitelist

Only these actions exist for this skill:

`ecs:DescribeInstances`, `ecs:DescribeDisks`, `ecs:DescribeSnapshots`,
`ecs:DescribeInvocations`, `sts:GetCallerIdentity`, plus the two consent-gated
actions `RunCommand` (class B) and `CreateSnapshot` (class C), each issued with
the `ecs` RAM code in front of the API name.

Each is listed in [related_apis.yaml](related_apis.yaml) with the version actually
called, and in [references/ram-policies.md](references/ram-policies.md) with its
consent class. Parameters are limited to the ones verified for this tier; the
snapshot call sends `RegionId` and `DiskId` and nothing else. Anything outside
this whitelist does not get called, whatever the symptom seems to need.

The RAM action prefix is not always the CLI product name, and this skill does not
guess. `aliyun sts get-caller-identity` is the plugin-mode form used for
`sts:GetCallerIdentity`, while the ECS actions keep their PascalCase API names.

## Credentials

The default `aliyun` CLI credential chain is the only supported authentication.
This skill never accepts, requests, reads, prints or stores a credential value,
and it never asks the customer to paste one into a conversation.

Run `check-env` first. It resolves the account once and stamps the account tail on
every report, which is what catches the cross-account misdiagnosis that several
source cases started from. If no credential is configured, say so and point at
`aliyun sts get-caller-identity` - the CLI collects what it needs, this skill does not.

## Observability

Every API call carries a per-run User-Agent so a report can be traced back to one
execution of this skill. The template, spelled exactly as `scripts/areas/hbr_backup_diagnosis/_constants.py`
builds it:

```
--user-agent AlibabaCloud-Agent-Skills/{skill_name}/{session_id} skill-version/{skill-version}
```

`{skill_name}` resolves to this skill's own name,
`area:hbr-backup-diagnosis`. `{session_id}` is 32 hex characters from
`uuid.uuid4().hex`, generated once per process and reused for every call in that
run. It appears in the `Session-Id` and
`User-Agent` lines of each report, and the aggregation is built in one place, in
`scripts/areas/hbr_backup_diagnosis/_cli.py`, so no call can escape it. Transient failures are retried with a
bounded backoff, each call has its own timeout, and every error string is scrubbed
of secret-looking values before it reaches a report.

## Working order

1. `check-env`, unless the session already resolved an identity.
2. **Ask which region the alarm or bill names.** Then confirm it out loud. A wrong
   console region is the single most common non-problem in this tier and it is
   checked before anything is believed.
3. `triage` with the customer's own wording in `--alert-text`. Quote it; do not
   paraphrase it into something more technical.
4. Read the evidence section of the report before the findings. Every conclusion
   must point at a numbered query, or at a candidate that the report labels as
   case history rather than measurement.
5. Follow `NEXT_ACTION`. Where it names a class B or C step, do the disclosure
   first, then re-run with the token.
6. Deliver the report. Then, and only then, answer the follow-up with `explain`.

## Answering rules

- A number that did not come from a query or from a linked official page does not
  go in a reply. **This includes the free-quota size, the retention day count, the
  version count and the snapshot unit price**: two source cases for this tier state
  conflicting quota figures, so `explain --topic retention` and its official links
  are the only acceptable source. Never repeat a figure from memory.
- An empty result is a finding, not a defect. "No snapshot in this region" is real
  information; inventing one is not.
- Label the evidence grade. `DescribeInstances` saying the instance is gone is a
  measurement. "A tunnel client claiming 100.64.0.0/10 is the usual cause" is a
  case-derived candidate, and the report already says which. Say so too.
- Where the customer's own analysis conflicts with the evidence, follow the
  evidence and name the conflict. One source case had a customer's careful
  NACL-versus-route conclusion sitting alongside a resolver cause; the dialogue
  was right and the reasoning was not.
- State any parameter this skill filled in itself instead of being told.
- Quote the error literal that came back. A denied action reports `NoPermission`
  or `ImplicitDeny`; report the name and the missing statement from
  [references/ram-policies.md](references/ram-policies.md) rather than working
  around it.

## Output contract

Relay the script's own last two lines; they are the contract.

```
STATUS: OK | DEGRADED | FAIL
NEXT_ACTION: <the single next step>
```

- `OK` - the queries ran and the conclusion is supported by them.
- `DEGRADED` - part of the picture is missing. Name the missing piece, print the
  command for the customer to run themselves, and continue on that basis. A
  degraded report is a correct report about a partial picture; it is not something
  to retry until it turns green.
- `FAIL` - the run could not proceed, usually credentials or a denied action.

`NEXT_ACTION` is one step, not a list. If it contradicts what the customer asked
for - usually because the ask is class D - surface the conflict instead of
quietly substituting.

## Known gaps, stated rather than papered over

| Gap | Consequence |
| --- | --- |
| No Cloud Backup (HBR) action was verified for this tier, not even a listing one | Backup plans, jobs, vaults and restore results cannot be read from an API; they come from the customer's console and screenshots |
| No billing, balance or invoice query | The customer reads the balance in the expense centre; arrears are still a first-class hypothesis for a broken console |
| CloudMonitor was not verified, and its RAM name differs from its API name | CPU saturation stays a candidate to test, never a reading |
| Route, resolver and service-state checks are outside the guest whitelist | The three most common causes of this tier's top failure family are offered as candidates with self-check commands, not measured |

## Boundaries and references

Adjacent symptoms go elsewhere and this skill says so in one sentence: disk
expansion, instance start and stop, disk IO, and pure product enablement. The
hand-off table is printed at the end of every triage report.

| File | Contents |
| --- | --- |
| [references/hbr-backup-diagnosis__decision-tree.md](references/hbr-backup-diagnosis__decision-tree.md) | The branches the script walks, with the case behind each |
| [references/hbr-backup-diagnosis__error-catalog.md](references/hbr-backup-diagnosis__error-catalog.md) | Wording to category, plus root cause and first move, with provenance |
| [references/hbr-backup-diagnosis__guest-commands.md](references/hbr-backup-diagnosis__guest-commands.md) | The class B whitelist, rejection rules, output readings, degraded mode |
| [references/hbr-backup-diagnosis__billing-map.md](references/hbr-backup-diagnosis__billing-map.md) | Mechanisms, resource-plan deduction, stop-billing path with the warning |
| [references/hbr-backup-diagnosis__console-paths.md](references/hbr-backup-diagnosis__console-paths.md) | Console steps, deep links, region check, restore SOP, hand-off wording |
| [references/ram-policies.md](references/ram-policies.md) | Every action, its class, a minimal policy, and denial handling |
