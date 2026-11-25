---
name: alibabacloud-ecs-boot-and-login-repair
description: |
  Repair ECS boot and login configuration: key pair setup, Linux file permissions blocking login, boot-failure repair, system-event notifications.
  Use when (customer wording): - authorized_keys lost; - bound a key pair but it does not take effect; - cannot connect using a temporary ssh key; - reset the instance password, create key pair failed; - unprotected private key file, bad .pem permissions; - windows logon 0xd07, account locked out; changed on its own; cannot escalate privileges; cannot su to root; - stuck in grub rescue / emergency mode after reboot.
  Do NOT use for symptoms covered by alibabacloud-ecs-high-frequency-issues (it routes first); SSH publickey-denial first response stays with the core pack, this pack takes the deeper keypair/boot repair after handoff; non-ECS products.
  Triggers: "authorized_keys lost", "bound a key pair but it does not take effect", "unprotected private key file, bad .pem permissions", "windows logon 0xd07, account locked out", "grub rescue".
---

# alibabacloud-ecs-boot-and-login-repair

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
| `keypair-login-config` | `python3 scripts/boot-and-login-repair.py --axis keypair-login-config -- <args>` | gated | [keypair-login-config](references/axes/keypair-login-config.md) |
| `boot-repair-guide` | `python3 scripts/boot-and-login-repair.py --axis boot-repair-guide -- <args>` | query-only | [boot-repair-guide](references/axes/boot-repair-guide.md) |
| `system-event-notice-guide` | `python3 scripts/boot-and-login-repair.py --axis system-event-notice-guide -- <args>` | query-only | [system-event-notice-guide](references/axes/system-event-notice-guide.md) |
| `linux-permission-repair` | `python3 scripts/boot-and-login-repair.py --axis linux-permission-repair -- <args>` | gated | [linux-permission-repair](references/axes/linux-permission-repair.md) |
| `file-transfer-diagnosis` | `python3 scripts/boot-and-login-repair.py --axis file-transfer-diagnosis -- <args>` | gated | [file-transfer-diagnosis](references/axes/file-transfer-diagnosis.md) |

Gated axes in this package: keypair-login-config, linux-permission-repair, file-transfer-diagnosis. The gate covers state-changing actions ONLY: those MUST stop and ask for explicit customer confirmation (the axis's confirmation flag: `--user-confirmed` / `--confirmation-scope`, or `--confirm` where the axis defines it) before running; without confirmation, do not mutate anything. Read-style in-guest probes also travel through Cloud Assistant RunCommand. They are NOT query-only from the customer's side: the command still executes inside their machine and leaves a task record there. ABSOLUTE PROHIBITION: never dispatch one without the customer's consent for that exact command in this turn. Ask first, then pass `--allow-guest-read` to the entry command. Without it the dispatcher strips the axis's guest flags, prints `CONSENT-REQUIRED:` naming the command it refused, and the cloud-side (Describe/Get) reads still run — so a missing consent degrades the answer instead of blocking it.

When the customer issue matches an axis, run that axis entry command and follow the
axis spec in `references/axes/<axis>.md`. Do not mix axes in one report.

## Trigger Conditions
See description (customer wording kept verbatim from the merged intake analysis).

## Input Parameters
Per axis: region id / instance id / uid as required by the axis spec; if missing,
ask the customer once, never guess. Parameter source rule: the instance id and
region are supplied by the customer and are never inferred on the customer's
behalf - a listing, a candidate list or a region sweep is only ever reported as
what this credential can read, and it never selects the target. Until the customer
names a target, the run stops at the question.
Discovery ordering: when the customer cannot name a target at all, the run asks
that question first and does not enumerate instances or regions to find one; the
bounded cross-region confirmation belongs to the step after that, and only for an
instance id the customer already supplied that the reads could not locate.

## Execution Flow
1. Classify the symptom into one axis via the table above.
2. Run the axis entry command in query-only mode. The dispatcher first takes a
   query-only target preflight on the named instance (existence and instance type,
   the lifecycle state the platform records, and any scheduled platform event),
   and it only adopts a record that echoes the requested instance id back; a read
   that fails is reported by its error code, never guessed around.
   When one of those declared query-only calls comes back with an error, the run may
   re-check that same call once, in the foreground and query-only, with the very same
   parameters (the CLI form the skill already documents) before writing the report;
   the error code seen in either pass is what gets recorded. This is a confirmation,
   not a retry loop: never re-issue it a third time, never switch credentials, and
   never let a refused or throttled read be reported as a healthy one.
3. Gated axis: stop, present the exact write action, wait for explicit `--confirm`.
4. Deliver the report in the axis spec's format.
5. Which steps that scenario runs, and what its answer is allowed to claim, follows the
   flow class bound to that `(axis, scenario)` pair in
   [diagnosis-flow-templates](references/diagnosis-flow-templates.md). That file is a
   design contract for report shape; it adds no call, no gate and no parameter of its own.


## Observability
Every CLI/API call in this skill attaches the User-Agent template
`AlibabaCloud-Agent-Skills/{skill}/{session-id} skill-version/{skill-version}` (skill = the axis's own skill name, kept for traceability),
where session-id is a 32-character hex string generated once per run and reused
across all calls in that run (implemented by each axis's `_cli.py` under scripts/axes/).

## Boundary (Do NOT use for)
- Do NOT use for: patch scanning or installation (alibabacloud-ecs-patch-management); disk capacity, expansion or GPT/LVM; instance stuck in Starting; disk IO or CPU performance; SSH or RDP login while the OS is up; ransomware or DDoS cleanup; billing or refunds.

## Important Notes
- Relative paths only; all assets live in this package.
- All network/API/subprocess calls carry timeouts.
