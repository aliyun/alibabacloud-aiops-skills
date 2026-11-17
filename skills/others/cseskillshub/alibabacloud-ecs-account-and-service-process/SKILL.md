---
name: alibabacloud-ecs-account-and-service-process
description: |
  Handle ECS account-level and process questions: account transfer, instance cloning, simple-application-server (SWAS) boundaries, business contact routing, ticket progress triage.
  Use when (customer wording): - can i convert my simple application server to ecs; - is my lightweight server physical; - promo price gone after refund; - simple application server / swas / lightweight server; can i move region; file-transfer function unavailable; overseas site slow from mainland china; what does 2 core 2g mean; bought the server in the wrong account.
  Do NOT use for symptoms covered by alibabacloud-ecs-high-frequency-issues (it routes first); remote-desktop connection first response stays with the core pack; non-ECS products.
  Triggers: "can i convert my simple application server to ecs", "is my lightweight server physical", "bought the server in the wrong account", "promo price gone after refund", "what does 2 core 2g mean".
---

# alibabacloud-ecs-account-and-service-process

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
  `CREDENTIAL-FAIL-CLOSED:` and the customer's own checks instead (exit 3). ABSOLUTE PROHIBITION on reading
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
| `swas-boundary-guide` | `python3 scripts/account-and-service-process.py --axis swas-boundary-guide -- <args>` | query-only | [swas-boundary-guide](references/axes/swas-boundary-guide.md) |
| `account-transfer-guide` | `python3 scripts/account-and-service-process.py --axis account-transfer-guide -- <args>` | gated | [account-transfer-guide](references/axes/account-transfer-guide.md) |
| `business-contact-routing` | `python3 scripts/account-and-service-process.py --axis business-contact-routing -- <args>` | query-only | [business-contact-routing](references/axes/business-contact-routing.md) |
| `invalid-ticket-triage` | `python3 scripts/account-and-service-process.py --axis invalid-ticket-triage -- <args>` | query-only | [invalid-ticket-triage](references/axes/invalid-ticket-triage.md) |
| `instance-tag-metadata-guide` | `python3 scripts/account-and-service-process.py --axis instance-tag-metadata-guide -- <args>` | query-only | [instance-tag-metadata-guide](references/axes/instance-tag-metadata-guide.md) |

Gated axes in this package: account-transfer-guide. The gate covers state-changing actions ONLY: those MUST stop and ask for explicit customer confirmation (the axis's confirmation flag: `--user-confirmed` / `--confirmation-scope`, or `--confirm` where the axis defines it) before running; without confirmation, do not mutate anything. Read-style in-guest probes also travel through Cloud Assistant RunCommand. They are NOT query-only from the customer's side: the command still executes inside their machine and leaves a task record there. ABSOLUTE PROHIBITION: never dispatch one without the customer's consent for that exact command in this turn. Ask first, then pass `--allow-guest-read` to the entry command. Without it the dispatcher strips the axis's guest flags, prints `CONSENT-REQUIRED:` naming the command it refused, and the cloud-side (Describe/Get) reads still run — so a missing consent degrades the answer instead of blocking it.

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
- Do NOT use for disk IO slowness, resize not applied, instance state or
- Do NOT use for disk usage or inode checks, expand-not-effective, transitional instance state,
- Do NOT use for real ECS faults, disk or order changes, refund or price questions, or ticket write-back; route those to the ECS fault, disk, billing or sales skills.

## Important Notes
- Relative paths only; all assets live in this package.
- All network/API/subprocess calls carry timeouts.
