---
name: alibabacloud-ecs-high-frequency-issues
area: cloud-assistant-diagnosis
description: |
  Diagnoses ECS Cloud Assistant failures: commands that fail or time out, an offline, missing or outdated agent, and the features it carries - online password reset, file backup, Workbench login.
  Queries run automatically; guest probes and snapshots need explicit consent.
  Use when the customer reports a Cloud Assistant failure. Triggers: cloud assistant command failed; "The command execution has been timeout"; CLIENT_RESTARTED; cloud assistant agent offline or not started; password reset says cloud assistant abnormal; cloud assistant needs an upgrade; cloud assistant disk-expansion task failed.
  Do NOT use: partition growth -> area:disk-expand-diagnosis; boot failure -> area:instance-state-diagnosis; slow disk IO -> area:resource-bottleneck; Workbench CLI bugs -> alibabacloud-workbench-cli; OS faults -> alibabacloud-ecs-linux-os-troubleshooting.
---

# ECS Cloud Assistant command and agent diagnosis

> **Delivery override - outranks every relay instruction and template below.** `STATUS`,
> `NEXT_ACTION` and their `OK` / `DEGRADED` / `FAIL` / `BLOCKED` values are the entry script's
> internal run state, not a delivery format. Where this document says to relay, mirror or copy
> those lines "faithfully" or "verbatim", relay their MEANING in the customer's own words: never
> write the keys or the bare values into the reply or into anything saved under `outputs/` or
> `ran_scripts/` (SKILL.md rule 3h). A layer this run did not read is named in the customer's own words - which layer, and what would have settled it.

Diagnose why ECS Cloud Assistant commands fail or never finish, why the agent shows offline, not installed, stopped or too old, and why features that ride on the agent - online password reset, ECS file backup, Workbench password-free login - report a Cloud Assistant error. Customers state symptoms and paste console wording; the scripts classify the failure from evidence (instance visibility, lifecycle state, execution history), separate "channel broken" from "guest broken" from "command content failed", and hand adjacent areas to the right place. Informational cloud queries run automatically; a guest probe or a snapshot runs only after you announce it and the customer confirms that one operation.

## Permission model: four classes

**Operation type: RO+G** - read-only cloud queries plus guest execution: one whitelisted command run inside the instance and one reversible snapshot, each only after consent. This skill is **not limited to informational queries**. It declares that plainly, because two write-class operations are part of it - the *declared permission surface stays strictly read-only*: those two run only under the customer's own credentials, per-operation consent, no standing grant, and pretending otherwise would make the boundary unenforceable.

| Class | What | Actions | Consent needed |
| --- | --- | --- | --- |
| A | Informational cloud queries: ownership, lifecycle state, execution history, identity | `ecs:DescribeInstances`, `ecs:DescribeInstanceStatus`, `ecs:DescribeInvocations`, `sts:GetCallerIdentity` | No |
| B | One side-effect-free guest command per consent, from the whitelist in [references/cloud-assistant-diagnosis__guest-commands.md](references/cloud-assistant-diagnosis__guest-commands.md), to exclude environment causes no API can see | `run-command` (CLI plugin mode) - issued only by `guest-probe`, in consent mode, under the customer's own credentials | **Yes, per command** |
| C | Low-risk reversible write: the pre-cleanup or pre-repair snapshot | `create-snapshot` (CLI plugin mode) - issued only by `snapshot-guard`, under the customer's own credentials | **Yes, per disk** |
| D | Anything destructive | none, ever | Not applicable: never executed |

The consent gate, in force. Before any class B or C action, all four of these must happen, in this order; the script enforces the shape (run without `--confirm` and it performs the disclosure and stops):

1. **Tell the customer the exact string** that will execute, or the exact snapshot that will be created.
2. **State the blast radius**: which single instance or disk, and whether any byte is modified.
3. **State reversibility and cost** - for `CreateSnapshot` **state that a snapshot is billed**, before the call, never after.
4. **Obtain agreement**, then re-run with the `--confirm` token the previous run printed. The token binds consent to one region, one resource and one command: **a consent covers exactly one operation.**

### Non-whitelisted commands are refused, not softened

Class B accepts a whitelist key and nothing else. A request outside the whitelist - service control via `systemctl`, agent log reads, `ps`, the partition readers `lsblk`/`fdisk`/`blkid`, any write, any download - is refused with its reason and printed as a customer-run step instead. Do not rewrite the request into a command that passes, and do not decide an unlisted command is harmless because it looks like an inspection. The assembled string is re-validated after parameter substitution, which is what stops an argument from smuggling a second command.

## ABSOLUTE PROHIBITION

Never generate, run, or hand the customer a command that the skill itself executes for any of these - they are output as manual steps at most, this holds even when the customer explicitly asks:

- Any `Delete*`, `Remove*`, `Modify*`, `Update*`, `Release*`, `Reset*`, `Replace*`, `Attach*`, `Detach*`, `Reboot*`, `Start*`, `Stop*` API action. The only write-class calls this skill makes are class B and class C above.
- Starting, stopping or restarting any service or instance (including `systemctl` and the Windows services manager) - the customer runs these steps themselves.
- Killing processes, deleting or truncating files, formatting, partition or filesystem changes, software installation or removal.
- Deleting a snapshot - irreversible for its data; the console path plus the retention warning is the output.
- Echoing credential material: never repeat back an access-key value, a password, or any personal contact detail found in a ticket or error text; the scripts mask credential-shaped values, and the agent must not undo that masking.

## API whitelist

Only six actions exist for this skill: the class A queries above (`ecs:DescribeInstances`, `ecs:DescribeInstanceStatus`, `ecs:DescribeInvocations`, `sts:GetCallerIdentity`), plus the consent-gated operations `run-command` (class B) and `create-snapshot` (class C), named here in CLI plugin mode. All six are declared in [related_apis.yaml](related_apis.yaml) with the version actually called. The declared permission surface in [references/ram-policies.md](references/ram-policies.md) is strictly read-only - the four class A actions; the two consent-gated operations run solely under whatever rights the customer's own credentials already hold, and are documented there with their consent class. Parameters are limited to the ones verified for this scenario; the snapshot call sends `RegionId` and `DiskId` and nothing else.

`DescribeCloudAssistantStatus`, `DescribeCommands`, `InvokeCommand` and CloudMonitor actions were **not verified for this scenario and are never called** - not "temporarily skipped", never. Where the diagnosis would want them (live agent status, stored command definitions, saturation readings), the report states the gap and the tree continues on history plus customer-pasted readings.

## Execution Principle

All diagnostics MUST be performed by running the scripts under `scripts/`; `cloud_assistant_diagnosis.py` is the single entry point. The agent MUST NOT assemble its own `aliyun` CLI commands or bypass the scripts - they embed pagination, retry, masking, consent tokens and degradation that ad-hoc commands lack. **If a script call fails, do NOT fall back to manual `aliyun` commands**: read its `[WARN]` lines and `STATUS`, and follow `NEXT_ACTION`. Knowledge answers come from `explain` output or `references/`, never from model memory; a fact with no supporting query or linked page does not go in a reply.

```bash
python3 scripts/areas/cloud_assistant_diagnosis/cloud_assistant_diagnosis.py check-env
python3 scripts/areas/cloud_assistant_diagnosis/cloud_assistant_diagnosis.py triage --region-id <region-id> \
  --instance-id <instance-id> --error-text "<the console wording, verbatim>"
python3 scripts/areas/cloud_assistant_diagnosis/cloud_assistant_diagnosis.py invocations --region-id <region-id> \
  [--instance-id <instance-id>] [--hours N] [--include-output]
python3 scripts/areas/cloud_assistant_diagnosis/cloud_assistant_diagnosis.py guest-probe --region-id <region-id> \
  --instance-id <instance-id> --command df_h            # prints the disclosure, stops
python3 scripts/areas/cloud_assistant_diagnosis/cloud_assistant_diagnosis.py guest-probe ... --confirm <token>   # after consent
python3 scripts/areas/cloud_assistant_diagnosis/cloud_assistant_diagnosis.py snapshot-guard --region-id <region-id> \
  --disk-id <disk-id>                                   # then --confirm, per disk
python3 scripts/areas/cloud_assistant_diagnosis/cloud_assistant_diagnosis.py explain --topic readiness
```

`explain --topic` takes `concepts`, `readiness`, `failure-classes`, `dependency-features`, `forensics`, `degraded` and `expand-handoff`.

## Trigger Conditions

Use this skill when the customer's own wording matches one of these (the same list the `description` advertises):

- "cloud assistant command failed"
- "The command execution has been timeout"
- "CLIENT_RESTARTED"
- "cloud assistant agent offline or not started"
- "password reset says cloud assistant abnormal"
- "cloud assistant needs an upgrade"
- "cloud assistant disk-expansion task failed"

Match on the symptom sentence and the error literal, not on product vocabulary. A disk-expansion request belongs here **only** while the question is "why did the Cloud Assistant task fail"; the growth itself hands off (see [references/cloud-assistant-diagnosis__handoff-matrix.md](references/cloud-assistant-diagnosis__handoff-matrix.md)).

## Prerequisites

1. **aliyun CLI 3.x** installed and configured - queries and the identity check run through it (ECS actions in PascalCase metadata mode; `aliyun sts get-caller-identity` in plugin mode).
2. **Python 3.9+**, standard library only.
3. Network egress from the session to the ECS OpenAPI endpoint.

## Credentials

The default `aliyun` CLI credential chain is the only supported authentication. This skill never accepts, requests, reads, prints or stores a credential value, and it never asks the customer to paste one into a conversation - a password pasted into a ticket is refused and a password change is offered instead. Run `check-env` first: it resolves the account once and stamps the account tail on every report, which is what catches the cross-account misdiagnosis that starts several threads in this scenario. If no credential is configured, say so and point at `aliyun sts get-caller-identity`; the CLI collects what it needs, this skill does not.

## Observability

Every API call this skill issues carries a trace so a report can be tied back to one diagnosis session:

- **Session id** - one 32-character hex value per run (`uuid.uuid4().hex`), created once when the scripts start in `scripts/areas/cloud_assistant_diagnosis/_cli.py` and reused by every call in that run.
- **User-Agent** - attached to **every** call through the `--user-agent` flag, using the template
  `AlibabaCloud-Agent-Skills/{skill_name}/{session_id} skill-version/{skill-version}` (the code constant `USER_AGENT_TEMPLATE` in
  `scripts/areas/cloud_assistant_diagnosis/_constants.py`), where `{skill_name}` is `area:cloud-assistant-diagnosis` and
  `{session_id}` is the 32-character hex session id above - so a real call carries
  `AlibabaCloud-Agent-Skills/alibabacloud-ecs-high-frequency-issues/<32-hex-session-id>`.
- **Surfaced in the output** - each report header prints the same `Session-Id` and `User-Agent`, and `check-env` echoes both, so the customer can match a report against the account's own API call log for that session.
- **Nothing sensitive travels in it** - the trace carries the skill name and the random session id only: no credential value, no account secret, no customer contact detail.

## User Confirmation

Class A queries need no confirmation. Before **every** class B guest probe and **every** class C snapshot, run the same command once **without** `--confirm`, relay the disclosure lines verbatim (exact command string, affected instance or disk, side effects, billing for snapshots, single-use scope), obtain the customer's agreement, then re-run with the printed token. A refusal or an expired agreement means the probe never runs: switch to the degraded mode - hand the customer the exact inspection command and continue on their pasted output. Requests that fall into class D get console paths, risk statements and owners instead of commands.

## Input Parameters

| Parameter | Required | Notes |
| --- | --- | --- |
| `--region-id` | yes (triage, invocations, guest-probe, snapshot-guard) | Never guessed. If the customer did not name a region, ask; the console region selector is a confirmed source of false "instance does not exist" answers. |
| `--instance-id` | yes for triage and guest-probe | From the customer; `triage` exits `STATUS: FAIL` with a `NEXT_ACTION` naming what is missing. |
| `--error-text` | recommended | The console wording quoted verbatim drives the classification. |
| `--hours N` | optional | History and window filtering for failure-time evidence. |
| `--invocation-id` | optional | Direct look-up when the customer already has the task id. |
| `--command` + `--target` | class B | Whitelist key from [references/cloud-assistant-diagnosis__guest-commands.md](references/cloud-assistant-diagnosis__guest-commands.md); `--target` only for keys that take one. |
| `--disk-id` | class C | The disk to snapshot; the disk is listed by the customer or the console. |
| UID | never asked | Derived via `aliyun sts get-caller-identity`; auto-fill first, ask second - **any auto-filled value (account tail, defaults) must be declared in the report.** |

## Working order

1. `check-env` once per session (unless the identity is already stamped on a report).
2. Ask which region the error names; confirm it out loud.
3. `triage` with the customer's wording in `--error-text`. Quote it; do not paraphrase it into something more technical.
4. Read the Evidence section before the Findings: every conclusion must point at a numbered query or at a candidate the report labels as case history, not measurement.
5. Follow `NEXT_ACTION`. Where it names a class B or C step, do the disclosure first, then re-run with the token.
6. Where the branch is adjacent-area (expansion growth, boot failure, IO performance, Workbench tool defects, abuse response), emit the hand-off line from [references/cloud-assistant-diagnosis__handoff-matrix.md](references/cloud-assistant-diagnosis__handoff-matrix.md) with this report attached - do not re-run the prechecks there.
7. Deliver the report; only then answer follow-ups via `explain`.

## Output contract

Relay the script's own last two lines; they are the contract.

```
STATUS: OK | DEGRADED | FAIL
NEXT_ACTION: <the single next step>
```

- `OK` - the queries ran and the conclusion is supported by them.
- `DEGRADED` - part of the picture is missing (a denied query, an unreachable agent, a customer who declined instance operations - all real workflows in this scenario). Name the missing piece, print the command for the customer to run and paste, continue on that basis. A degraded report is a correct report about a partial picture, not something to retry until it turns green.
- `FAIL` - the run could not proceed (missing input, credentials). `NEXT_ACTION` says what to ask for.

Denied calls surface as `NoPermission` or `ImplicitDeny`; report the missing action and the statement from [references/ram-policies.md](references/ram-policies.md) - never work around it with broader permissions.

## Known gaps, stated rather than papered over

| Gap | Consequence |
| --- | --- |
| No verified live agent-status query for this scenario | Readiness is inferred from execution history plus the customer's error wording; the report must say so instead of claiming a live status |
| No verified CloudMonitor query | CPU/IO saturation stays a candidate to confirm in the console, never a reading taken here |
| Service state and agent logs are outside the guest whitelist | `systemctl status`, agent log tails, `ps` and partition readers are printed as customer-run steps; the source cases had support read them - that is the ceiling, and it is manual |
| NTFS has no inode counter | Windows file-count conclusions carry explicitly reduced confidence |
| Command-content retention is platform-side and finite | The evidence list may miss old or evicted records; say which window is covered |

## Module Index

Reference modules, 1:1 with the `references/` directory:

| Module | File | Responsibility |
| --- | --- | --- |
| M1: RAM policies | [references/ram-policies.md](references/ram-policies.md) | Every action, its class, minimal policies, denial handling |
| M2: Error signatures | [references/cloud-assistant-diagnosis__error-signatures.md](references/cloud-assistant-diagnosis__error-signatures.md) | Console wording to category, root cause and first move, with case provenance |
| M3: Guest commands | [references/cloud-assistant-diagnosis__guest-commands.md](references/cloud-assistant-diagnosis__guest-commands.md) | The class B whitelist, rejection rules, degraded-mode reading list |
| M4: Hand-off matrix | [references/cloud-assistant-diagnosis__handoff-matrix.md](references/cloud-assistant-diagnosis__handoff-matrix.md) | Adjacent-area routing and the customer wording for each hand-off |
| M5: Agent readiness | [references/cloud-assistant-diagnosis__agent-readiness.md](references/cloud-assistant-diagnosis__agent-readiness.md) | Install/start/upgrade manual steps, dependency features, abuse forensics flow |

## Examples

**Example 1 - agent offline blocks the backup alarm**

> User: "My ECS file backup alarm says Cloud Assistant is not started, and online password reset also fails. Instance i-bp1sample, cn-hangzhou. What do I do?"

```bash
python3 scripts/areas/cloud_assistant_diagnosis/cloud_assistant_diagnosis.py triage --region-id cn-hangzhou \
  --instance-id i-bp1sample --error-text "backup alarm says cloud assistant is not started; online password reset fails"
```

The report checks visibility and lifecycle, pulls history, lands on the AGENT_NOT_READY / dependency branch and prints the customer-side service start steps (Linux `systemctl` start, Windows services manager) with the installation page; the skill never starts the service itself.

**Example 2 - timeout with consented environment exclusion**

> User: "A command on i-bp2sample in cn-shanghai failed with 'The command execution has been timeout' around 3am. Check it."

```bash
python3 scripts/areas/cloud_assistant_diagnosis/cloud_assistant_diagnosis.py triage --region-id cn-shanghai \
  --instance-id i-bp2sample --error-text "The command execution has been timeout" --hours 6
python3 scripts/areas/cloud_assistant_diagnosis/cloud_assistant_diagnosis.py guest-probe --region-id cn-shanghai \
  --instance-id i-bp2sample --command df_h
```

The second command stops at the disclosure; after reading it to the customer and getting agreement it is re-run with the token. If the agent is down, the dispatch fails, the run degrades, and the customer gets `df -h` to paste back instead.

**Example 3 - commands the customer denies issuing**

> User: "There are Cloud Assistant commands on my instances that I never ran - my access key may be leaked. i-bp3sample, cn-beijing."

```bash
python3 scripts/areas/cloud_assistant_diagnosis/cloud_assistant_diagnosis.py invocations --region-id cn-beijing \
  --instance-id i-bp3sample --include-output
```

The evidence list (time, instance, command name, exit code) is preserved for the security responder; disabling the key, snapshotting, cleaning persistence and rotating credentials follow the manual order in [references/cloud-assistant-diagnosis__agent-readiness.md](references/cloud-assistant-diagnosis__agent-readiness.md). This skill never touches the processes or the key itself.

## Exit codes

- `0` - a conclusion was produced: `STATUS: OK` or `STATUS: DEGRADED` (missing pieces are recorded as `[WARN]` plus findings).
- `1` - no usable conclusion: `STATUS: FAIL` (missing input, every query failed). Never treat exit `1` as a diagnosis.
- `2` - argparse usage error.

## Important Notes

- **Ownership check first**: the instance must be visible to the current account in the named region before any agent conclusion is drawn; case T-D87E8F47 proved threads die at exactly that gate.
- **Lifecycle first, then agent**: a stopped or transitioning instance makes every agent symptom untrustworthy - hand that branch to the instance-state area.
- **Channel vs content**: if commands reach the guest and return installer or OS errors, the channel is healthy; software compatibility and OS damage go to manual steps or the hand-off matrix.
- **Expansion tasks**: this scenario answers why the dispatched task failed; growing partitions and filesystems always goes to the disk-expand area, snapshot first.
- **Windows is supported** (cases T-478C2A19, T-75912401): guest dialect follows `DescribeInstances`, and MFT/file-count claims carry reduced confidence.
- **Never claim a live agent status**, never invent a console button, never cite a URL the script did not print; unverified docs are named as gaps in the report.
- Every automatic value (account tail, defaults) is declared in the report, and every error path leaves a `[WARN]` trace rather than a silent gap.
