---
name: alibabacloud-ecs-image-boot-repair-diagnosis
description: |
  Read-only diagnosis with manual guidance for Alibaba Cloud ECS custom images: interpret image-detection warnings and critical items, parse failed image-repair task logs, map boot failures such as GRUB damage after a kernel upgrade, and re-check after customer-run repairs.
  Use when the customer mentions image detection, checking or repairing an image, or repairing the boot loader. Triggers: image detection shows severe; image repair failed; InvalidAccountStatus.NotEnoughBalance; Disk.MountTargetDirNotFound; Invalid image format in header; custom image import fails; stuck at BIOS after kernel upgrade; fstab mount target not found; CloudAssistant not installed.
  Do NOT use: image or snapshot billing -> alibabacloud-ecs-image-billing-cleanup; Cloud Assistant agent faults -> alibabacloud-ecs-cloud-assistant-diagnosis; start/stop state machine -> alibabacloud-ecs-instance-start-stop-anomaly.
---

# ECS image detection, repair-failure and boot-repair diagnosis

Diagnose Alibaba Cloud ECS custom-image problems stated as symptoms: "image
detection shows severe on every image", "the repair task failed with
InvalidAccountStatus.NotEnoughBalance but the page says Success", "after the
kernel upgrade the instance is stuck at BIOS". Covers three capabilities:
**(1) detection-result interpretation** (what each WARN/critical item means
and which read-only check settles it), **(2) repair-task failure diagnosis**
(the customer-pasted pipeline log is localized to its failing step and
error code), and **(3) boot-failure guidance with read-only re-verification**
(root-cause mapping, the two official self-repair paths relayed as manual
steps, whitelisted guest checks on a booted instance, and the after-repair
recheck). Informational cloud reads run automatically; a guest command or
any repair step runs only as customer action after consent disclosure —
this skill never mutates anything.

## Absolute Rules

1. **ABSOLUTE PROHIBITION (no mutations):** Under NO circumstances may you
   generate, write or execute — through this skill's scripts or as a command
   the skill itself runs — any mutating action: `Create*`, `Modify*`,
   `Delete*`, `Attach*`, `Detach*`, `Start*`, `Stop*`, `Reboot*`, `Reset*`,
   `Release*`, `Import*`, `Replace*` class APIs, snapshot taking, fstab
   editing, bootloader regeneration, component installation, service
   control, or instance power changes. Every such conclusion is emitted as
   MANUAL customer-run steps plus the console entry, and this skill then
   verifies the result read-only. This holds even when the customer
   explicitly asks the skill to "just do it".
2. **API WHITELIST:** The only cloud actions are the class A reads
   `ecs:DescribeInstances`, `ecs:DescribeImages`, `ecs:DescribeInstanceStatus`,
   `ecs:DescribeInvocations` and `sts:GetCallerIdentity`, plus — behind rule 3 —
   ONE whitelisted read-only guest command dispatched through the Cloud
   Assistant channel (CLI metadata-mode action name `RunCommand`) under the
   CUSTOMER's own credentials: no standing grant for it exists or is declared
   (see [references/ram-policies.md](references/ram-policies.md)). Nothing
   else may ever be called; there is NO verified read-only API for repair
   task details, so task state is NEVER fetched — the customer pastes the log.
3. **CONFIRMATION GATE (mechanical, per command):** Before ANY guest
   command: tell the customer the EXACT command string, the scope (one
   region, one Running instance), its read-only nature (lists/stats paths;
   writes nothing, reads no file contents), and that it is reversible
   trivially (nothing changes). The entry script enforces this: the first
   run prints the disclosure + a single-use token and dispatches NOTHING;
   only the re-run carrying that exact token executes. One confirmation
   covers exactly one operation.
4. **GUEST WHITELIST:** Only `findmnt`, `stat <one path>` and `ls <one path>`
   may be proposed. Everything else — `cat`/`grep` of the fstab,
   `systemctl`, `lsblk`/`blkid`/`fdisk`, any `grub` operation, any package
   manager, any redirection or chaining — is REFUSED with its reason and
   converted into a customer-run step. Never soften a refusal into a
   lookalike that passes the gate.
5. **NO FABRICATION:** Conclusions come only from real API responses, the
   customer's pasted evidence, and the embedded knowledge in `references/`.
   Empty results and permission gaps are reported as such. Where the docs in
   this batch do not settle a question (is a WARN mandatory? why does the
   task page differ from the log? the official URL of the PE-disk repair
   page? agent install directories?), say it is not settled — never invent
   an answer or a URL. Describe-read results are visible only for the
   current account and the named region; state that scope on every answer.
6. **EXECUTION RULE FOR ERRORS:** Every failed step logs `[WARN|DEGRADED]`
   to stderr, is recorded in the report's degradation log, and the run
   continues with the evidence that did arrive. On permission errors the
   report names the missing action and points to
   [references/ram-policies.md](references/ram-policies.md) (`NoPermission` /
   `ImplicitDeny` literals are the report vocabulary). Never conclude
   "everything is fine" from "could not see anything".
7. **SCOPE BOUNDARY:** Billing/usage questions about images and snapshots,
   deleting old images, agent installation/runtime, instance
   start/stop state-machine faults, suspected platform-side image-service
   faults and local format-conversion execution all route out per
   [references/image-boot-repair-diagnosis__handoff.md](references/image-boot-repair-diagnosis__handoff.md). Windows guests are out
   of scope for this release (no Windows evidence in this tier).

## Execution Principle

All operations MUST run through the single entry script
`scripts/axes/image_boot_repair_diagnosis/image_boot_repair_diagnosis.py` (subcommands in Quick Start). The
agent MUST NOT assemble raw `aliyun` CLI commands, import SDK code or
re-implement any query — the script embeds the whitelist gate, consent
token, retry, masking, pagination and degradation that ad-hoc calls lack.
**If a script run fails, do NOT fall back to manual CLI**: read its
`[WARN]` lines, `STATUS` and `NEXT_ACTION`, and act on them. Knowledge
answers come from `explain` output or `references/`, never from memory.

## Quick Start

```bash
cd <this skill directory>
python3 scripts/axes/image_boot_repair_diagnosis/image_boot_repair_diagnosis.py check-env
python3 scripts/axes/image_boot_repair_diagnosis/image_boot_repair_diagnosis.py triage --region-id cn-hangzhou \
  [--instance-id i-xxxx] [--image-id m-xxxx] \
  [--symptom "<customer wording verbatim>" | --error-text "<console line>"]
python3 scripts/axes/image_boot_repair_diagnosis/image_boot_repair_diagnosis.py analyze-log --text "<pasted repair log>" \
  [--task-status "<what the page shows>"]
python3 scripts/axes/image_boot_repair_diagnosis/image_boot_repair_diagnosis.py analyze-report --text "<pasted detection report>"
python3 scripts/axes/image_boot_repair_diagnosis/image_boot_repair_diagnosis.py plan-check --scenario fstab|components|bootdir
python3 scripts/axes/image_boot_repair_diagnosis/image_boot_repair_diagnosis.py probe --region-id cn-hangzhou \
  --instance-id i-xxxx --command "findmnt"          # prints disclosure, dispatches NOTHING
python3 scripts/axes/image_boot_repair_diagnosis/image_boot_repair_diagnosis.py probe ... --confirm <printed-token>
python3 scripts/axes/image_boot_repair_diagnosis/image_boot_repair_diagnosis.py verify-repair --region-id cn-hangzhou \
  [--instance-id i-xxxx] [--image-id m-xxxx]
python3 scripts/axes/image_boot_repair_diagnosis/image_boot_repair_diagnosis.py handoff --symptom "<wording>"
python3 scripts/axes/image_boot_repair_diagnosis/image_boot_repair_diagnosis.py explain --topic docs|detection|repair|guest|boot
```

## Trigger Conditions

Match the customer's own wording (same list the `description` advertises);
route on the symptom sentence or the literal error string, not on product
vocabulary:

- "image detection shows severe" / "check this image for me"
- "image repair failed" / `InvalidAccountStatus.NotEnoughBalance` in a
  pasted pipeline log (task page may even say Success)
- `Disk.MountTargetDirNotFound` / "fstab mount target not found"
- "custom image import fails" / `Invalid image format in header`
- "instance stuck at BIOS after kernel upgrade" (GRUB damage candidate)
- "CloudAssistant not installed" / "SecurityCenterAgent not installed"
  warnings from an image check

## Prerequisites

1. **aliyun CLI 3.x** installed; ECS reads run in metadata mode (PascalCase
   actions), the identity check in plugin mode (`aliyun sts
   get-caller-identity`). No direct HTTP signing, no external SDK.
2. **Python 3.9+**, standard library only (see `scripts/requirements.txt`).
3. Credentials resolved by the CLI default chain (see Credentials).

## Credentials

Authentication is resolved exclusively by the aliyun CLI default credential
chain. This skill never accepts, requests, reads, prints or stores any
credential value; the agent MUST NOT pass credential flags anywhere, and
must not echo credential-shaped text found in customer-pasted logs — the
scripts mask such values on every output path. If identity cannot be
resolved, `check-env` fails with guidance to configure the CLI itself.

## User Confirmation

Two distinct gates:

1. **Diagnostic scope** (before any cloud read): restate the region, the
   target image/instance ids and the fact that only the whitelisted reads
   above will run. An explicit request naming its target is sufficient
   authorization; if region or resource is ambiguous, ask once and wait.
   Regions are never guessed — a wrong region produces false "not found".
2. **Guest probe** (before any dispatch): Absolute Rule 3's disclosure and
   the single-use token flow. A refused or expired confirmation means the
   command never runs: switch to the degraded path (customer runs it,
   pastes the output) and continue.

## Input Parameters

| Parameter | Required | Notes |
| --- | --- | --- |
| `--region-id` | yes (triage, probe, verify-repair) | Never guessed or auto-filled; ask the customer. Reads see one account + region only. |
| `--instance-id` / `--image-id` | as the mode needs | Id-shape validated by the script; wrong ids degrade honestly. |
| pasted log / report text | yes for analyze-log / analyze-report | `--text` or `--file`; no task API exists to fetch it. |
| `--task-status` | optional | Page status the customer reports; drives the contradiction note. |
| `--command` + `--confirm` | probe only | One whitelisted command; token from this run's disclosure. |
| `--symptom` / `--error-text` | recommended | Verbatim customer/console wording drives routing. |
| UID | never asked | Auto-derived via the identity check and DECLARED in the report. |

## Module Index

| Module | File | Responsibility |
| --- | --- | --- |
| Detection items | [references/image-boot-repair-diagnosis__detection-codes.md](references/image-boot-repair-diagnosis__detection-codes.md) | What each detection WARN/critical means, which read-only check settles it, manual resolution + re-detect loop |
| Repair failures | [references/image-boot-repair-diagnosis__repair-failure-codes.md](references/image-boot-repair-diagnosis__repair-failure-codes.md) | Pipeline-log anatomy, error-code semantics, task-page contradiction discipline, "is my backup invalid" answer |
| Guest checks | [references/image-boot-repair-diagnosis__guest-readonly-commands.md](references/image-boot-repair-diagnosis__guest-readonly-commands.md) | The whitelist, refused list, disclosure protocol, channels and degraded fallback |
| Handoffs | [references/image-boot-repair-diagnosis__handoff.md](references/image-boot-repair-diagnosis__handoff.md) | Boundary routes, the two guided self-repair paths, risk statements |
| RAM policies | [references/ram-policies.md](references/ram-policies.md) | Minimum read-only policy actually required; consent-gated operations documented ungranted |

## Orchestration

```
customer symptom / pasted text
   |
   +-- boundary wording?  --> handoff route (references/image-boot-repair-diagnosis__handoff.md) --> stop or keep in-scope part
   |
   +-- detection report pasted --> analyze-report --> item semantics
   |                                                    |
   +-- repair log pasted -----> analyze-log --> failing api + code --> conclusion + manual exit
   |                                                    |
   +-- boot symptom ----------> triage --symptom --> root-cause candidates
   |              (cloud evidence: DescribeInstances / DescribeInstanceStatus /
   |               DescribeImages / DescribeInvocations, account+region scoped)
   |                                                    |
   +-- needs an in-guest reading? -- instance Running? -+
                                   | yes                | no
                          plan-check -> probe           STATUS: DEGRADED on guest axis
                          (disclose, consent, token,    + guided paths + ask to paste
                           ONE whitelisted command)
                                   |
                                   v
                        manual steps (customer-run) --> verify-repair (read-only recheck)
                                   --> final report: STATUS + NEXT_ACTION
```

## Execution Flow

1. **Scope confirmation** — restate region + resources + read-only scope per
   User Confirmation; do not call anything before this.
2. **Identity** — run `check-env`; declare the auto-derived UID; credential
   failure aborts with `aliyun configure` guidance (never ask for AK/SK).
3. **Boundary first** — if the wording matches a handoff axis, relay that
   route's script and keep only the in-scope remainder.
4. **Evidence pass** — run the matching mode: `analyze-log` on a pasted
   repair log, `analyze-report` on a pasted detection report, and/or
   `triage` for control-plane evidence (image status/progress, instance
   lifecycle, visible custom images, recent execution records).
5. **Guest pass (only if it changes the verdict)** — bootable instance:
   `plan-check` then `probe` under the consent protocol; non-bootable
   instance: skip, emit the DEGRADED statement, give the guided paths and
   ask for pasted readings instead.
6. **Interpret** — map readings to the detection/repair/boot knowledge;
   contradictions (page vs log) are reported as two sources, never resolved
   by invention.
7. **Manual resolution steps** — concrete, customer-run, ordered, each
   with the risk statement where repair is involved; this skill applies
   nothing.
8. **Re-verify** — after the customer acts, `verify-repair` + fresh pasted
   report; relay the final answer per the Final Answer Contract.

## Output Contract

Every mode ends with the script's own lines, relayed verbatim:

- `STATUS: OK` — usable conclusion from complete evidence.
- `STATUS: DEGRADED` — usable conclusion with gaps listed in the
  degradation log (permission, offline agent, non-booting instance,
  unmatched wording); the report says what could not be seen.
- `STATUS: FAIL` — no usable conclusion (missing input, refused command,
  bad consent token); `NEXT_ACTION` names what to ask for or how to
  re-obtain consent. Exit code 1. Exit 2 is argparse usage only.

## Observability

- **Session-id**: one 32-character hex value per run (`uuid.uuid4().hex`),
  created in `scripts/axes/image_boot_repair_diagnosis/_cli.py` and reused by every call of that run.
- **User-Agent**: attached to **every** API call via the `--user-agent`
  flag using the template `AlibabaCloud-Agent-Skills/{skill-name}/{session-id} skill-version/{skill-version}`,
  with `{skill-name}` = `alibabacloud-ecs-image-boot-repair-diagnosis`;
  the constant lives in `scripts/axes/image_boot_repair_diagnosis/_constants.py` (`USER_AGENT_TEMPLATE`).
- Each report header prints the same `Session-Id` and `User-Agent` so a
  report can be tied to one diagnosis session; the trace carries the skill
  name and random session id only — never any credential value.

## Important Notes

1. The repair pipeline's balance threshold (>= 100 CNY for postpaid
   ordering) is an account condition: say "not an image-content failure",
   and keep the top-up itself on the billing axis.
2. Task-page status contradicting a pasted failing log: report both,
   recommend human verification; do not declare success either way.
3. WARN != blocker; critical != invalid backup — the guide is
   [references/image-boot-repair-diagnosis__detection-codes.md](references/image-boot-repair-diagnosis__detection-codes.md), and the
   settle-it reading is the guest check or the rebuilt-image re-detect.
4. No boot means no guest channel: for startup failures the answer is
   always root cause + guided self-repair paths + pasted evidence, never a
   claimed remote inspection.
5. Auto-filled and declared: the UID (identity check) and poll/consent
   token scope. NEVER auto-filled: region. Any other assumption must be
   voiced as a question.
6. Credential safety and relative paths are absolute; see Credentials and
   the Execution Principle.

## Examples

**Example 1 — repair failed at the transition stage:**

> "Image repair failed twice but the task page says Success. Here is the
> log: ... api:CreateInstance, code:InvalidAccountStatus.NotEnoughBalance ..."

Run `analyze-log --text "<log>" --task-status Success`; relay the
transition-resource localization, the balance-threshold root cause, the
NOT-an-image-problem conclusion, the both-sources contradiction note and
the customer re-trigger guidance.

**Example 2 — mount-target critical:**

> "Every custom image shows critical: Disk.MountTargetDirNotFound. Can I
> ignore it?"

Run `analyze-report --text "<report>"`; explain the stale-fstab-line
mechanics, ask for the fstab paste plus a `findmnt` reading
(`plan-check --scenario fstab`; on a Running instance the consent-gated
`probe` may fetch it), then give the comment-out + rebuild + re-detect
manual loop and close with `verify-repair`.

**Example 3 — stuck at BIOS after an apt upgrade:**

> "I upgraded Debian 12 to 13 from inside the OS; now the instance is
> stuck at BIOS. I do not want to reinstall."

Run `triage --region-id <r> --instance-id <i> --symptom "stuck at BIOS
after kernel upgrade"`: lifecycle read + GRUB-damage candidate + the two
guided paths (console PE-disk repair; system-disk-on-another-instance
chroot) with stop/snapshot/billing risk statements; after the customer
repairs, `verify-repair` re-checks state and the guest checks confirm.

## Error Handling

| Situation | What the script does | What the agent says |
| --- | --- | --- |
| `NoPermission` / `ImplicitDeny` on a read | `[WARN|DEGRADE]`, continue | name the action, point to ram-policies.md |
| Instance/image not visible | honest finding | recheck region/account scope; ids are per-region |
| No custom images in region | valid empty finding | "none visible for THIS account+region" |
| Dispatch refused / agent offline | `STATUS: DEGRADED` | customer runs the whitelisted command, pastes output |
| Consent token mismatch | `STATUS: FAIL` | fresh disclosure + fresh confirmation |
| Unmatched pasted wording | `STATUS: DEGRADED` | ask for the full report/log, never guess |

## Final Answer Contract

The reply to the customer MUST: (1) lead with the script's findings and its
`STATUS` outcome relayed faithfully; (2) quote only real values and literal
codes from the output or the pasted evidence; (3) declare auto-filled
items (UID) and named gaps; (4) present resolution as manual steps with the
risk statements where repair is involved, and — for handed-off axes — the
boundary statement plus the named exit; (5) close with `NEXT_ACTION` and,
where a customer action was taken, the `verify-repair` loop. Never present
raw JSON; never claim an inspection that did not happen.

## Available Scripts

| Script | Purpose |
| --- | --- |
| `scripts/axes/image_boot_repair_diagnosis/image_boot_repair_diagnosis.py` | SINGLE entry: check-env, triage, analyze-log, analyze-report, plan-check, probe (consent-gated), verify-repair, handoff, explain |
| `scripts/axes/image_boot_repair_diagnosis/sts_token.py` | Identity pre-check helper (`aliyun sts get-caller-identity`), UID label + session/UA echo |
| `scripts/axes/image_boot_repair_diagnosis/_cli.py` | Shared CLI layer: per-call timeout, transient retry, credential masking, session-id + `--user-agent` on every call |
| `scripts/axes/image_boot_repair_diagnosis/_constants.py` | All embedded knowledge: detection items, repair codes, boot signatures, whitelist, handoff routes, doc links |
