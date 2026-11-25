---
name: alibabacloud-ecs-server-migration-on-cloud
description: |
  Assess and troubleshoot moving workloads to and between Alibaba Cloud ECS: website and inter-server relocation, on-migration assessment, forced-migration notices, instance cloning for environment replication.
  Use when (customer wording): copy a server to another region; error establishing a database connection; error establishing a database connection" after a move; instance expired, rescue my data; migrate the whole site to a new server; move my website to another ecs server; move off a virtual host; other cloud; site still loads the old server after dns change; transfer an instance to another account.
  Do NOT use for symptoms covered by alibabacloud-ecs-high-frequency-issues (it routes first); non-ECS products.
  Triggers: "copy a server to another region", "migrate the whole site to a new server", "move my website to another ecs server", "site still loads the old server after dns change", "instance expired, rescue my data".
---

# alibabacloud-ecs-server-migration-on-cloud

Merged ECS support skill (5 axes, customer-symptom family). Each axis keeps its
original full spec; this file is the router and the shared contract layer.

## Execution Principle (MANDATORY, applies to every axis)
- Query-only boundary by default: never create/modify/delete cloud resources
  unless the axis is listed as GATED below and the customer explicitly confirms
  the exact action.
- ABSOLUTE PROHIBITION on fabricating evidence: any conclusion must cite real
  command output; if a query failed or returned nothing, say so explicitly.
  Claiming "verified/executed" without trace = violation.
- ABSOLUTE PROHIBITION on fabricating customer facts: the customer's situation
  may come ONLY from their first question and the given context. Never infer
  or assert unstated facts such as "newly purchased instance", "no workloads
  running", "no data on the disks" or an empty business state. Anything not
  supplied by the customer and not read by a query in this run is UNVERIFIED:
  mark it so, or ask once - never present a guess as "your situation". A plan
  may branch on such facts only as an explicit conditional ("if the instance
  carries no workloads, ..."), never as an asserted customer fact.
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
| `site-migration-guide` | `python3 scripts/server-migration-on-cloud.py --axis site-migration-guide -- <args>` | query-only | [site-migration-guide](references/axes/site-migration-guide.md) |
| `onmigration-assessment` | `python3 scripts/server-migration-on-cloud.py --axis onmigration-assessment -- <args>` | gated | [onmigration-assessment](references/axes/onmigration-assessment.md) |
| `forced-migration-guide` | `python3 scripts/server-migration-on-cloud.py --axis forced-migration-guide -- <args>` | query-only | [forced-migration-guide](references/axes/forced-migration-guide.md) |
| `instance-clone-guide` | `python3 scripts/server-migration-on-cloud.py --axis instance-clone-guide -- <args>` | query-only | [instance-clone-guide](references/axes/instance-clone-guide.md) |
| `instance-relocation-guide` | `python3 scripts/server-migration-on-cloud.py --axis instance-relocation-guide -- <args>` | query-only | [instance-relocation-guide](references/axes/instance-relocation-guide.md) |

Gated axes in this package: onmigration-assessment. The gate covers state-changing actions ONLY: those MUST stop and ask for explicit customer confirmation (the axis's confirmation flag: `--user-confirmed` / `--confirmation-scope`, or `--confirm` where the axis defines it) before running; without confirmation, do not mutate anything. Read-style in-guest probes also travel through Cloud Assistant RunCommand. They are NOT query-only from the customer's side: the command still executes inside their machine and leaves a task record there. ABSOLUTE PROHIBITION: never dispatch one without the customer's consent for that exact command in this turn. Ask first, then pass `--allow-guest-read` to the entry command. Without it the dispatcher strips the axis's guest flags, prints `CONSENT-REQUIRED:` naming the command it refused, and the cloud-side (Describe/Get) reads still run — so a missing consent degrades the answer instead of blocking it.

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
`AlibabaCloud-Agent-Skills/{skill}/{session-id} skill-version/{skill-version}` (skill = the axis's own skill name, kept for traceability),
where session-id is a 32-character hex string generated once per run and reused
across all calls in that run (implemented by each axis's `_cli.py` under scripts/axes/).

## Boundary (Do NOT use for)
- Do NOT use for: disk size unchanged after expansion (the disk-expand-diagnosis axis of alibabacloud-ecs-high-frequency-issues), instance will not start (the instance-state-diagnosis axis of alibabacloud-ecs-high-frequency-issues), slow disk IO (the disk-io-diagnosis axis of alibabacloud-ecs-disk-io-and-data-protection), image backup design (alibabacloud-ecs-disaster-recovery-image).
- Do NOT use for disk space or inode cleanup; a resize that did not apply (the disk-expand-diagnosis axis of alibabacloud-ecs-high-frequency-issues); instance state (the instance-state-diagnosis axis of alibabacloud-ecs-high-frequency-issues); slow disk IO (the disk-io-diagnosis axis of alibabacloud-ecs-disk-io-and-data-protection); an image copy inside one account (alibabacloud-ecs-disaster-recovery-image); website move steps (the site-migration-guide axis of this package); kernel SMC-R "can not stat /proc/sys/net/smc/tcp2smc"; refunds; ICP filing.
- Do NOT use for pure unsubscribe pricing, security-incident response, or in-instance root-cause diagnosis.
- Do NOT use for security-group rule diagnosis, IP/EIP retention, CloudMonitor agent data, on-premises image export, instance resize, batch scaling or refunds.

## Important Notes
- Relative paths only; all assets live in this package.
- All network/API/subprocess calls carry timeouts.
