---
name: alibabacloud-ecs-keypair-login-config
description: |
  Diagnose an ECS logon credential failure: key pair binding, passwordless Workbench logon, authorized_keys, multi-user RDP, private key errors, Windows lockout. Guest inspection and snapshots need per-call confirmation.
  Use when key pair or password logon fails.
  Triggers:
  - Permission denied (publickey)
  - UNPROTECTED PRIVATE KEY FILE, bad .pem permissions
  - cannot connect using a temporary SSH key
  - Windows logon 0xd07, account locked out
  - bound a key pair but it does not take effect
  - authorized_keys lost or changed on its own
  - reset the instance password, create key pair failed
  Do NOT use: damaged OS files (alibabacloud-ecs-linux-os-troubleshooting), disk IO faults, an instance that will not boot, passkey logon to a third-party site.
---

# ECS Key Pair and Logon Credential Diagnosis

Explains and evidences one class of problem: a customer cannot log on to an ECS
instance because of a credential or a credential channel. The skill queries the
cloud for what is true now, matches the customer's own error wording against a
fixed signature table, routes to one branch, and returns an evidence-backed
report plus the console steps a human performs next.

This package is not confined to queries. Two capabilities change state, and each
one is the operator's decision, never the skill's: an inspection command run
inside the guest through Cloud Assistant, and a snapshot taken before a restart
window. Both need a confirmation that repeats, verbatim, the single command or
disk involved, and both are refused without it. Everything else in this tier —
binding a key pair, resetting a password, releasing a lockout, restarting an
instance — stays guidance, with its console path and its risk stated.

## Scope

Use this skill for the credential and logon-channel axis only:

* key pair creation, import, binding, replacement, unbinding, and the condition
  that makes a binding effective;
* instance password recovery, online and offline, and why a reset can succeed
  while logon still fails;
* console passwordless logon, which is a temporary SSH key pair delivered inside
  the guest by the Cloud Assistant agent;
* the local SSH client side: key file permissions, which key is offered, which
  user name is used;
* the in-guest SSH configuration, as a reading taken by a confirmed command or by
  a human: daemon options, the `authorized_keys` permission chain, host firewall,
  logon audit;
* Windows logon: the concurrent session ceiling, account lockout, multi-user
  expectations;
* mechanism questions: whether a lost private key can be recovered, whether the
  platform pre-installs keys, how many key pairs one instance carries.

Do not use it for the neighbouring tiers. `references/keypair-login-config__handoff-boundaries.md`
carries the full trigger-to-target table; the short version is capacity and
inode problems, disk IO saturation and a wedged guest, an instance that will not
boot, damaged operating system base files, account and billing scope, security
group rule edits, third-party terminal-services activation, and passkey or
biometric logon to a third-party website. Recognise those, name the boundary in
one sentence, and hand off instead of continuing to test credentials.

## Permission model and execution gates

Four classes, and the class decides who acts. The transport layer enforces the
boundary in code: `scripts/axes/keypair_login_config/_cli.py` refuses any action outside `API_WHITELIST`
before a process is spawned, and separately refuses the two gated actions when no
confirmation was supplied for that call.

**A — evidence queries, run on their own.** They mutate nothing, so no prompt is
needed. `GetCallerIdentity`, `DescribeInstances`, `DescribeInstancesFullStatus`,
`DescribeCloudAssistantStatus`, `DescribeInvocations`.

**B — guest inspection through Cloud Assistant, one confirmed call at a time.**
`RunCommand` is a mutating action: it runs something inside the customer's
instance. It is therefore used for the inspection list in
`references/keypair-login-config__guest-evidence-commands.md` and for nothing else, and only when the
operator passes the exact command back as its own confirmation:

```bash
python3 scripts/axes/keypair_login_config/keypair_login_diagnosis.py --instance-id i-2ze8example --region-id cn-beijing \
  --entry local-ssh --symptom keypair-not-effective \
  --run-inspection "sshd -T" --confirm-inspection "sshd -T"
```

Before that call the agent MUST tell the operator which single command is about
to run, what it reads, its scope, that it changes nothing, and that a retry needs
a fresh confirmation. One confirmation covers one command; it is never reused for
the next one, never inferred from an earlier yes, and never held between runs. A
command outside the published list is refused and falls back to a manual
suggestion, which is also the correct answer while the inspection list is still
awaiting approval for this tier.

**C — a snapshot before a restart window, confirmed per call.** `CreateSnapshot`
is the low-risk reversible write of this tier, offered whenever the guidance
reaches a restart, an offline reset, or a repair-disk step. It needs the disk id
repeated as its confirmation, and it states snapshot billing in the same breath:

```bash
python3 scripts/axes/keypair_login_config/keypair_login_diagnosis.py --instance-id i-2ze8example --region-id cn-beijing \
  --symptom password-reset-failed --snapshot-disk-id d-2ze8exampledisk \
  --confirm-snapshot d-2ze8exampledisk
```

**D — never executed here, only explained.** Instance power changes, key pair
creation, import, binding, replacement and release, password resets, security
group rule edits, snapshot and key pair deletion, sshd configuration edits and
service restarts, account unlock writes, and repair-disk attachment. For each one
the report gives the console path, what it changes, the interruption or cost
involved, and who approves it. Recommending that the operator call one of these
through a hand-written request is equally out of bounds.

**ABSOLUTE PROHIBITION.** No action outside `API_WHITELIST` is ever assembled,
issued, or proposed as a CLI command by this skill, and no D-class change is ever
performed or scripted on the customer's behalf. A mutating call without its own
confirmation does not reach the cloud.

## Granted actions

| Action | Product and version | Class | What it answers or does |
|---|---|---|---|
| `GetCallerIdentity` | sts / 2015-04-01 | A | Which account and principal is asking. A wrong account or region presents as a broken credential |
| `DescribeInstances` | ecs / 2014-05-26 | A | Exists, `Running`, OS and image, bound security groups, operation locks, expiry, recorded key pair name |
| `DescribeInstancesFullStatus` | ecs / 2014-05-26 | A | Instance health and scheduled events, which are not credential faults |
| `DescribeCloudAssistantStatus` | ecs / 2014-05-26 | A | Whether the agent behind passwordless logon and online password reset reports at all |
| `DescribeInvocations` | ecs / 2014-05-26 | A | Whether remote commands ran recently and how they ended; also how a confirmed inspection call is read back |
| `RunCommand` | ecs / 2014-05-26 | B | Runs ONE inspection command from the published list inside the guest, only with that command as its confirmation |
| `CreateSnapshot` | ecs / 2014-05-26 | C | Takes the pre-change snapshot of ONE disk, only with that disk id as its confirmation, after the billing note |

Deliberately absent: key pair lifecycle actions, password recovery actions, power
actions, security group rule actions, and the snapshot and key pair deletion
actions. Their parameter and policy contracts are not verified for this tier, and
each one is a D-class change; the in-guest execution path is limited to the
inspection list above and never carries an edit.

## Execution principle

Run the entry script and read its report. Do not hand-write `aliyun` commands, do
not paste a customer's instance data into an ad-hoc query, and do not fall back to
composing API calls yourself when the script reports a problem. If the script
fails, report its failure and its `NEXT_ACTION`; that is the deliverable.

The one exception is the identity check, which is a documented diagnostic step in
its own right:

```bash
aliyun sts get-caller-identity
```

Plugin-style products take the lowercase hyphenated command form, as above.
RPC-style products keep the PascalCase action name, which is why the entry script
calls `DescribeInstances` and not a hyphenated variant.

## Intake: collect four elements first

A symptom is what the customer says; a root cause is what a query returns. These
four elements decide which branch is correct, and each one has burned a whole
round trip when it was skipped:

1. Instance id **and** region.
2. Operating system, Linux or Windows.
3. Which logon path was attempted: console passwordless, console with a chosen
   key pair, local SSH, Remote Desktop, or VNC.
4. The exact error text, verbatim, in the customer's own casing and language.

Worth asking in the same breath, because each one changes the conclusion: which
user name was used, whether a console restart followed a key pair binding,
whether the image was changed and where it came from, and whether VNC works.
Pass the answers to the script as flags rather than reasoning around them; an
unanswered question keeps the report `DEGRADED`, which is the correct outcome.

## Workflow

1. Collect the four intake elements above.
2. Confirm the credential chain and the account with `scripts/axes/keypair_login_config/sts_token.py`.
3. Run `scripts/axes/keypair_login_config/keypair_login_diagnosis.py` with the instance, the region, and
   everything the customer said.
4. Read the report top to bottom: evidence first, then branch, then findings.
5. When the deciding fact is inside the guest, announce the one command that will
   read it, get the operator's confirmation, and re-run with `--run-inspection`
   and `--confirm-inspection`. Never batch two commands into one confirmation.
6. When the guidance reaches a restart, an offline reset, or a repair-disk step,
   state the snapshot and its billing first; create it only on confirmation with
   `--snapshot-disk-id` and `--confirm-snapshot`.
7. Relay the findings the evidence supports, the numbered manual guidance, the
   risk notes, and the handoff if there is one. Quote only values that actually
   came back.
8. Close with `STATUS` and `NEXT_ACTION` from the report, unchanged.

Never state a number, a status or a timestamp the script did not return. Never
present a candidate cause as the cause. Where the deciding fact lives inside the
guest and no reading has been taken, say that plainly and mark the conclusion
unproven.

## Running the entry script

`scripts/axes/keypair_login_config/keypair_login_diagnosis.py` is the single entry point. Every cloud call
a diagnosis needs happens here, the identity check included, through the shared
transport in `scripts/axes/keypair_login_config/_cli.py`, and the script prints either a text report or
JSON.

```bash
python3 scripts/axes/keypair_login_config/keypair_login_diagnosis.py \
  --instance-id i-2ze8exampleinstance --region-id cn-beijing \
  --entry workbench-passwordless --symptom passwordless-workbench \
  --error-text "Instance logon failed: cannot connect using a temporary SSH key"
```

```bash
python3 scripts/axes/keypair_login_config/keypair_login_diagnosis.py \
  --instance-id i-bp1exampleinstance --region-id cn-hangzhou \
  --entry local-ssh --symptom client-key-error --username root \
  --error-text "WARNING: UNPROTECTED PRIVATE KEY FILE! Permissions 0664, bad permissions" \
  --restart-done no --output json
```

### Arguments

| Flag | Required | Meaning |
|---|---|---|
| `--instance-id` | yes | The target instance |
| `--region-id` (alias `--region`) | yes | Its region; a mismatch looks like a deleted instance |
| `--symptom` | no | Symptom class from `SYMPTOM_TAXONOMY`; default classifies from the evidence |
| `--entry` | no | Logon path attempted: `workbench-passwordless`, `workbench-key`, `local-ssh`, `rdp`, `vnc`, `unknown` |
| `--error-text` | no | The customer's error wording, verbatim; drives signature matching |
| `--username` | no | Log-on user name used, for example `root` or `ecs-user` |
| `--os-type` | no | Overrides the OS reported by the API when the customer knows better |
| `--key-pair-name` | no | Filters the instance list by key pair name |
| `--restart-done` | no | `yes`, `no` or `unknown`: did a console restart follow the binding |
| `--image-origin` | no | `public`, `marketplace`, `community-other-linux`, `custom`, `unknown` |
| `--vnc-works` | no | `no` splits the layers immediately and routes below the credential branch |
| `--run-inspection` | no | One command from the published inspection list; refused unless it is on that list |
| `--confirm-inspection` | no | That same command, repeated, which is what makes the B-class call run |
| `--inspection-shell` | no | `auto` (default), `shell`, `bat` or `powershell`; `auto` follows the reported OS |
| `--guest-wait` | no | Seconds to wait for the inspection result before degrading, capped at 240 |
| `--snapshot-disk-id` | no | Disk for the C-class pre-change snapshot |
| `--confirm-snapshot` | no | That same disk id, which is what makes the snapshot happen |
| `--note` | no | One line of customer wording, used for routing only |
| `--timeout` | no | Per-call timeout override in seconds |
| `--output` | no | `text` (default) or `json` |

Exit status follows the contract: `0` for `OK`, `1` for `DEGRADED`, `2` for
`FAIL`. A refused or failed B-class or C-class call degrades the report; it never
retries itself into a different command.

`scripts/axes/keypair_login_config/sts_token.py` answers the account question on its own and prints the
remediation when the credential chain is broken. `scripts/axes/keypair_login_config/_constants.py` holds
every table this skill knows (symptom taxonomy, error signatures, guest
readings, console paths, handoff table, documentation anchors) as code constants,
because `scripts/` carries no data files.

## Reading the report

| Block | What it is for |
|---|---|
| `DECLARED INPUTS` | Every input, and whether the caller supplied it or a default filled it |
| `INSTANCE FACTS` | The instance truth the conclusions stand on |
| `CLOUD ASSISTANT CHANNEL` | Status, version, last heartbeat: the passwordless dependency |
| `EVIDENCE COLLECTED` | One line per query attempted, failures included |
| `GUEST INSPECTION` | The confirmed reading and what came back, or why nothing ran |
| `PRE-CHANGE SNAPSHOT` | The confirmed pre-change snapshot id, or the console path if none was confirmed |
| `PERMISSION GAPS` | The exact refused action and the single grant that fixes it |
| `BRANCH` / `FINDINGS` | The routed symptom and what the evidence proves about it |
| `MANUAL GUIDANCE` | Numbered steps for the customer or engineer, with console paths |
| `RISK NOTES` | The snapshot gate, the actions never issued here, and the interruption, data and billing warnings |
| `HANDOFF` | Trigger, boundary sentence, target |
| `CHANNEL STATE ON THIS RUN` | One line saying what ran and what did not, so no reader infers it |
| `PUBLISHED IN-GUEST READINGS` | The commands, and what each reading proves |
| `LIMITATIONS` | What no cloud query can see, stated as a gap rather than a guess |
| `STATUS` / `NEXT_ACTION` | The contract tail |

Relay the report faithfully. Where a signature matched, quote the customer's own
wording back to them so they can see the match was real; the mapping from each
wording to a fix side is in `references/keypair-login-config__error-signatures.md`.

## In-guest evidence

Facts that exist only inside the guest — the public key actually present, its
file permissions, the live daemon options, a lockout counter — are invisible to
every evidence query. Two ways to get them, and the skill uses whichever the
operator chose:

* a confirmed B-class call, one command at a time, which prints the reading under
  `GUEST INSPECTION`;
* a command list a human runs, which is the default answer whenever no
  confirmation was given, and the only answer while this tier's inspection list
  is still awaiting whitelist approval.

Accept output a customer pastes; it is their machine and their choice. Never ask
for a private key, and never ask them to paste output that contains one. The
lists, the per-command gate and the interpretation notes are in
`references/keypair-login-config__guest-evidence-commands.md`.

## Snapshot gate

Before any step that needs a restart, an offline password reset, or a detached
repair disk, a snapshot of the system disk exists and has completed. A pure
evidence review needs none. C-class can take it on confirmation; otherwise the
report prints the console path and leaves the decision to the owner.

Say the cost too: snapshots are billable storage, so note the identifier and
delete it when the change window closes, and a snapshot is not a substitute for a
verified backup on a data-critical volume. The restart itself is a D-class change
and always the customer's, with its service-interruption window stated.

## Observability

Every cloud call in this package carries a User-Agent header built from one
session identifier, so a single diagnosis is traceable end to end and can be
distinguished from console traffic.

* Template: `AlibabaCloud-Agent-Skills/{skill}/{session-id} skill-version/{skill-version}`, rendered per run with
  `{skill}` set to `alibabacloud-ecs-keypair-login-config`.
* `<session-id>` is a 32-character hex string from `uuid.uuid4().hex`, generated
  once per run by `new_session_id()` in `scripts/axes/keypair_login_config/_cli.py`.
* It is attached to **every** invocation through the CLI `--user-agent` flag by
  `build_command()`, including the identity check and both gated calls, with no
  call exempt.
* The same identifier is printed on the first lines of the report as
  `session id`, so a report can be matched to the calls that produced it.

Calls are issued as argument lists, never through a shell, and every one has a
per-call timeout (30 seconds by default, overridable with `--timeout`).
Transient failures (throttling, service unavailable, timeouts) are retried with
exponential backoff and jitter, up to three attempts; a parameter or
authorization failure is reported immediately and never retried. A gated call is
never retried into a different command or a different disk. A failed evidence
step is recorded in the report as a gap and degrades the status instead of
stopping the run.

## Credentials and secrets

The aliyun CLI resolves credentials from its own default credential chain. This
package never asks for, reads, stores, prints, or passes an AccessKey pair, a
security token, or a private key, and it never works around a missing credential
by building a request by hand.

When the chain is broken the scripts print the remediation: ask the operator to
run `aliyun configure` in a terminal. Nothing else. If a customer has already
pasted a private key, a password or a phone number into the conversation, treat
that material as compromised, do not repeat it, and never write it into a report
or a skill artifact. `mask_secrets()` scrubs credential-shaped values out of
every message that leaves the transport layer, including PEM blocks, and out of
every guest reading before it reaches the report.

## When a call is refused

Four literals cover refusals, and they mean different things:

* `NoPermission`: no statement allows that action. Grant the single named action
  from `references/ram-policies.md`.
* `ImplicitDeny`: a control or group policy denies it. Ask the account
  administrator to lift the deny for that action; do not work around it with a
  broader grant.
* `ConfirmationRequired`: a B-class or C-class call arrived without its
  confirmation. Tell the operator what the call does and its scope, then re-run
  with the confirmation for that one call.
* `RefusedBySkillPolicy`: the action is outside this skill's whitelist. It is
  never issued from here; the report prints the console path for a human instead.

The report names the refused action under `PERMISSION GAPS` together with the
pointer to the exact statement. Never widen a policy to a product-level wildcard
to make a refusal go away, and never report an authorization failure with any
other wording.

## Output contract

The final answer to the customer or engineer must:

* restate `STATUS` and `NEXT_ACTION` from the report, unchanged;
* quote only values the queries returned, and declare which parameters were
  auto-filled or defaulted;
* give the numbered manual guidance with its console paths, and the risk notes
  when a restart or a repair disk is involved;
* state plainly what ran: which inspection command was confirmed and what it
  returned, or that nothing ran inside the guest;
* name the single unanswered question when the report is `DEGRADED`, instead of
  filling the gap with a plausible cause;
* state the boundary and the target when the case belongs to another tier.

| Tail | Meaning |
|---|---|
| `STATUS: OK` | Every evidence step returned and the branch conclusion is supported |
| `STATUS: DEGRADED` | A step did not return, or the deciding fact is missing, so the conclusion is partial |
| `STATUS: FAIL` | Nothing meaningful could be established: wrong account or region, an unusable credential chain, or no matching instance |

## References

* [references/ram-policies.md](references/ram-policies.md): granted actions by
  class, the minimal policy, the two authorization literals, and what is never
  granted.
* [references/keypair-login-config__login-decision-tree.md](references/keypair-login-config__login-decision-tree.md): intake,
  the standing evidence group, and the branch per logon path.
* [references/keypair-login-config__error-signatures.md](references/keypair-login-config__error-signatures.md): each
  customer-visible wording, its verdict, and which side the fix lives on.
* [references/keypair-login-config__keypair-and-credential-guidance.md](references/keypair-login-config__keypair-and-credential-guidance.md):
  key pair lifecycle, the effect condition of a binding, the no-restart
  alternative, password resets, multi-user key logon, image changes, the
  snapshot gate.
* [references/keypair-login-config__guest-evidence-commands.md](references/keypair-login-config__guest-evidence-commands.md):
  the Linux and Windows readings, what each proves, and the per-command gate.
* [references/keypair-login-config__faq.md](references/keypair-login-config__faq.md): short answers to the questions this
  tier actually receives.
* [references/keypair-login-config__handoff-boundaries.md](references/keypair-login-config__handoff-boundaries.md): the
  trigger-to-target table and the wording for each handoff.
