---
name: alibabacloud-ecs-high-frequency-issues
area: data-recovery-assessment
description: |
  Read-only assessment of whether lost ECS data can still be recovered: verifies instance existence, drives a backup-evidence self-check, returns a tiered verdict, then guides manual console recovery or delivers an unrecoverable outcome.
  Use when files, databases or code on an ECS server went missing after mistaken operations, ransomware, system reinstallation or instance expiry.
  Triggers: "accidentally deleted files on my server, can I recover them", "database dropped and I have no backup", "formatted the disk by mistake", "instance expired and is gone, is my data gone", "rm -rf run by mistake", "data cannot be recovered after reinstalling".
  Do NOT use for the file-backup or Cloud Backup product itself (use alibabacloud-cloudbackup-ecs-file-backup-essential-edition) or for instance expiry and retention-lifecycle questions (use area:expiry-release-retention).
metadata:
  openclaw:
    requires:
      # No environment variable is required: the skill runs on the aliyun CLI
      # credential configuration alone, resolved by its default chain.
      env: []
      # Both binaries evidenced in the shipped code must be installed.
      bins: [aliyun, python3]
---

# ECS Data-Loss Recoverability Assessment

> **Delivery override - outranks every relay instruction and template below.** `STATUS`,
> `NEXT_ACTION` and their `OK` / `DEGRADED` / `FAIL` / `BLOCKED` values are the entry script's
> internal run state, not a delivery format. Where this document says to relay, mirror or copy
> those lines "faithfully" or "verbatim", relay their MEANING in the customer's own words: never
> write the keys or the bare values into the reply or into anything saved under `outputs/` or
> `ran_scripts/` (SKILL.md rule 3h). A layer this run did not read is named in the customer's own words - which layer, and what would have settled it.

Assess whether lost ECS instance data can still be recovered and guide the
customer through the answer. Typical customer wording: "I accidentally
deleted files / a folder / my code on the server, can they come back",
"someone dropped my production database and I have no backup", "I formatted
the disk by mistake", "my instance expired, was released, is my data gone
forever", "after reinstalling the system the old disk data is unrecoverable
-- is there really no way?". The skill states WHAT it does: a read-only
existence check, a structured backup-evidence inventory the customer performs
in the console, a tiered recoverability verdict, step-by-step manual recovery
guidance with risk notices, and firm expectation management when recovery is
impossible. It performs NO cloud change and NO command inside the instance.

## Absolute Rules

1. **ABSOLUTE PROHIBITION (read-only enforcement):** The action whitelist in
   rule 2 is exhaustive and **deny-by-default**: anything not named there is
   forbidden. Under **NO** circumstances may this skill generate, write or
   execute any operation that changes cloud state -- resource creation,
   configuration or attribute changes, destruction or reclaim of resources,
   snapshot rollback, disk or system re-initialization, operating-system
   replacement, image operations, network attachments, power-state changes,
   or in-instance command execution. This also covers handing the user a
   mutating command to run "through this skill". Recovery operations
   (rollback, disk rebuild, image rebuild, re-initialization) are output as
   **manual guidance for the customer to perform in the console**, never as
   executed calls.
2. **API WHITELIST:** the only permitted OpenAPI actions are the read-only
   `DescribeInstances` (product `ecs`, version `2014-05-26`, via
   `aliyun ecs describe-instances ...`) and `sts:GetCallerIdentity` for the
   identity label. Any other action name -- including instance command
   execution and every backup/snapshot/image inventory API -- is out of
   whitelist and must never be called by this skill.
3. **NO IN-GUEST EXECUTION:** this skill never runs commands inside the
   customer instance and never claims guest-side facts. When guest truth is
   needed (mounts, paths, binlog, encryption extent), the customer is asked
   to run read-only checks themselves and paste the output, or the request
   is handed to the remote-connection / Cloud Assistant tier.
4. **ABSOLUTE PROHIBITION (credentials):** never read, print or pass an
   AccessKey pair or security token explicitly; the aliyun CLI default
   credential chain resolves everything. Never ask the user for keys.
5. **NO FABRICATION, NO PROMISES:** every conclusion traces to script output
   or the embedded knowledge files. While evidence is missing the only
   permitted verdict is `INSUFFICIENT-EVIDENCE`; never soften it into "it
   should be recoverable". `NOT-RECOVERABLE` is delivered only after the
   customer confirms no covering backup asset exists (or the read-only query
   plus their release notice proves the carrier is gone).
6. **EXECUTION RULE FOR ERRORS:** any API failure logs `[WARN] <Code>:
   <Message>` to stderr and the run continues to the report; permission
   failures additionally print the missing RAM action and point to
   [references/ram-policies.md](references/ram-policies.md) using the error
   literals `NoPermission` / `ImplicitDeny`.
7. **SCOPE BOUNDARY:** compensation, goodwill refunds, stamped
   "unrecoverable" attestations and platform-notification lookups are
   outside this skill (human channel only, per
   [references/data-recovery-assessment__handoff-rules.md](references/data-recovery-assessment__handoff-rules.md)); neighbouring
   symptoms are recognized and routed, not diagnosed here.

## Data Flows and External Calls

- **Alibaba Cloud ECS OpenAPI** via the `aliyun` CLI subprocess
  (`aliyun ecs describe-instances --biz-region-id <region> ...`): one read-only
  instance query per run, carrying only the region, the instance id or
  public IP the customer supplied, page settings, and the observability
  `--user-agent` label below. Responses (instance id, status, zone, OS
  name, charge type, expiry stamp) are rendered to the customer.
- **Alibaba Cloud STS** via the same CLI: one read-only identity check
  returning the account UID, used only as a local traceability label.
- **No other network egress.** Scripts use the standard library and the CLI
  only; no SDK, no direct HTTP, no third-party endpoints. Nothing beyond
  non-credential query context leaves the machine; no credentials are ever
  transmitted by this skill's own code (the CLI attaches its own
  authentication to its own calls).
- **Account/region visibility:** queries see only the current credential's
  account and the requested region; cross-account or other-region resources
  are invisible and that limit is declared in every conclusion.

## Trigger Conditions

Mirror of the `description` triggers; match the customer's own symptom
wording (and these phrases), not technical root-cause vocabulary:

- "accidentally deleted files on my server, can I recover them"
- "database dropped and I have no backup"
- "formatted the disk by mistake"
- "instance expired and is gone, is my data gone"
- "rm -rf run by mistake"
- "data cannot be recovered after reinstalling"

An instance-lifecycle or backup-product question is still routed per the
Do-NOT-use boundary first; when the request mixes both, take only the
recoverability sub-question here.

## Execution Principle

All cloud evidence MUST come from the bundled scripts under `scripts/`; the
agent is prohibited from assembling its own `aliyun` CLI commands, from
calling any API outside the whitelist, and from running anything inside the
instance. Offline modes of the entry script (`--assess`, `--self-check`,
`--handoff`, `--docs`, `--list-options`) are pure knowledge lookups over the
embedded constants and reference files. Never answer matrix questions from
model memory when a script mode covers them.

## Observability

Every `aliyun` invocation carries
`--user-agent AlibabaCloud-Agent-Skills/{skill-name}/{session-id} skill-version/{skill-version}`, where
`{skill-name}` is `area:data-recovery-assessment` and
`{session-id}` is a **32-character lowercase hex string** (`uuid.uuid4().hex`)
generated once per script run (lazily, cached in the process) and reused by
every call of that run, so all calls of one assessment correlate. The shared
CLI layer (`scripts/areas/data_recovery_assessment/_cli.py`) implements this automatically.

## Prerequisites

1. **aliyun CLI** installed and configured (`ecs` built-in metadata mode;
   the `sts get-caller-identity` plugin command).
2. **Python 3.9+**, standard library only (see
   `scripts/requirements.txt`; no third-party packages).
3. A credential resolved by the CLI default chain (environment or the CLI
   config file). Never pass keys to this skill.

## Authentication

`python3 scripts/areas/data_recovery_assessment/sts_token.py` verifies the caller and prints the account
UID label. If it fails, guide the user to `aliyun sts get-caller-identity` -- never accept
a key pair from the chat. UID and region handling: the UID is auto-derived
and must be declared in the report; the **region is never guessed** -- a
missing region exits `STATUS: FAIL` with a `NEXT_ACTION` asking for it.

## User Confirmation

This skill executes only the two whitelisted read-only calls, so no
confirmation is needed for them beyond restating scope (target instance / IP
and region). Confirmation discipline instead governs the **guided actions the
customer performs**: before recommending any rollback, disk rebuild, image
rebuild or re-initialization step, the guidance must state (a) what the
action does, (b) what it destroys (current system-disk content after the
snapshot moment; running services do not autostart), (c) the safety-net
snapshot of the current state first (small pay-as-you-go snapshot fee), and
(d) an explicit ask for the customer to acknowledge before proceeding.

## Input Parameters

| Parameter | Flag | Required | Notes |
|---|---|---|---|
| Instance id | `--instance-id` | one of id/IP | `i-...` exactly as shown in the console |
| Public IP | `--public-ip` | one of id/IP | alternative locator |
| Region id | `--region-id` | yes for evidence mode | never guessed; ask if absent |
| Loss event | `--loss-type` | assess mode | keys via `--list-options` |
| Carrier | `--carrier` | assess mode | system/data/local disk, memory cache |
| Surviving assets | `--backup` | assess mode | comma list; `none` only when customer-confirmed |
| Asset time fit | `--backup-time` | assess mode | matched / older / unknown |
| Overwrite risk | `--overwrite` | assess mode | none / possible / confirmed |
| Instance state | `--instance-state` | assess mode | from the evidence step |
| Guest OS family | `--os` | optional | selects Windows/Linux document branch |

## Module Index

| Module | File | Responsibility |
|---|---|---|
| M1: RAM policies | [references/ram-policies.md](references/ram-policies.md) | The two whitelisted read-only actions and minimal policy |
| M2: Recoverability matrix | [references/data-recovery-assessment__recoverability-matrix.md](references/data-recovery-assessment__recoverability-matrix.md) | Gate order, verdict tiers, asset-to-carrier matching, data boundaries |
| M3: Customer self-check | [references/data-recovery-assessment__customer-self-check-list.md](references/data-recovery-assessment__customer-self-check-list.md) | Backup inventory via console, four-element guidance, paste-back rules |
| M4: Recovery guides | [references/data-recovery-assessment__recovery-guides.md](references/data-recovery-assessment__recovery-guides.md) | Manual paths A-F with risk notices and re-verification |
| M5: Expectation management | [references/data-recovery-assessment__expectation-management.md](references/data-recovery-assessment__expectation-management.md) | Fixed wording for irreversible outcomes, delivery structure, phrases to avoid |
| M6: Handoff rules | [references/data-recovery-assessment__handoff-rules.md](references/data-recovery-assessment__handoff-rules.md) | Neighbour recognition, routing targets, pre-handoff preservation actions |
| M7: Documentation index | [references/data-recovery-assessment__doc-index.md](references/data-recovery-assessment__doc-index.md) | The only citable URLs and known retrieval gaps |

## Orchestration

1. **Existence evidence** -- read-only `DescribeInstances` via the entry
   script: present/running vs stopped vs not visible.
2. **Event and carrier classification** -- map the customer story onto
   `--loss-type` and `--carrier` (catch "not actually lost" and
   "cache-only" patterns first).
3. **Backup inventory via customer self-check** -- `--self-check` list,
   answers pasted back; no API inventory exists for this step.
4. **Verdict** -- `--assess` runs the gate matrix; five tiers plus the
   conservative floor; every tier carries its evidence list.
5. **Guidance or expectation delivery** -- recovery paths with the
   pre-action gate, or the NOT-RECOVERABLE template; then prevention and
   re-verification with the same read-only evidence mode.

```
customer wording --> Trigger check --> [route neighbours (M6)]
                     |
                     v
   scripts: --instance-id/--public-ip + --region-id   (step 1, read-only)
                     v
   scripts: --self-check  --------------------------\ (step 3, customer console)
                     v                              v
   scripts: --assess <facts from steps 1-3>  <---- pasted answers (step 4)
                     v
   guidance (M4) or expectation wording (M5) --> re-verify via step 1
```

### Exit codes (contract)

- `0` -- conclusion produced: `STATUS: OK` or `STATUS: DEGRADED`
  (conservative `INSUFFICIENT-EVIDENCE` verdict with its evidence list).
- `1` -- no usable conclusion: invalid values, missing region, or the
  evidence call failed outright; `NEXT_ACTION` names what to ask or fix.
- `2` -- argparse usage error only.

## Execution Flow

1. Confirm scope with the customer (instance/IP + region; read-only only)
   and state the account/region visibility limit.
2. Run the evidence mode; relay its `Summary` verbatim and declare the
   auto-derived UID. If the instance is not visible, first exclude
   region/account mistypes before any "released" assumption.
3. Classify the loss event and carrier with the customer; deliver the
   self-check list and collect pasted-back answers.
4. Run `--assess` with all confirmed facts; deliver exactly the tier the
   matrix returns (never stronger), with its rationale lines.
5. Guide the chosen path (M4) with the pre-action confirmation gate, or
   deliver the NOT-RECOVERABLE template (M5). Close with prevention and the
   re-verification step; route out-of-scope asks (M6) with the data-safety
   note first.

## Available Scripts

| Script | Purpose |
|---|---|
| `scripts/areas/data_recovery_assessment/sts_token.py` | Identity check via `aliyun sts get-caller-identity`; UID label; `--json` |
| `scripts/areas/data_recovery_assessment/ecs_data_recovery_assessment.py` | Single entry: evidence mode (`--instance-id`/`--public-ip` + `--region-id`), verdict mode (`--assess`), `--self-check`, `--handoff <key|all>`, `--docs [key]`, `--list-options`, `--json` |
| `scripts/areas/data_recovery_assessment/_cli.py` | Shared read-only CLI layer: argument-list subprocess, per-call timeout, retry with backoff, UA/session-id, credential masking |
| `scripts/areas/data_recovery_assessment/_constants.py` | Embedded knowledge constants (matrix inputs, checklist, guides, handoffs, doc index) |

## Error Handling

| Error literal | Meaning | Handling |
|---|---|---|
| `NoPermission` / `ImplicitDeny` | RAM policy missing a whitelisted read action | Print missing action + minimal policy pointer (M1); re-run after grant |
| `InvalidParameter` | Wrong region/instance format | Script validates before calling; relay the fix, ask the customer for the exact value |
| `Throttling.User` | Flow control | Retried automatically (up to 3 attempts, linear backoff), then `[WARN]` and continue |
| `InternalError` / `ServiceUnavailable` | Transient service failure | Retried; degrade with `[WARN]`; never conclude from a failed call |
| Empty result set | Instance invisible to this account+region query | Not an error: the "not visible" branch with its exclusion list |
| Credential chain failure | CLI not configured | Guide `aliyun sts get-caller-identity`; never accept keys in chat |

All errors keep the `[WARN] <Code>: <Message>` shape; stderr text passes
through credential masking; every run ends `STATUS: OK|DEGRADED|FAIL` plus
`NEXT_ACTION:`.

## Final Answer Contract

1. Lead with the script `Summary` / verdict tier and `STATUS`, relayed
   faithfully; quote only values the scripts returned or the customer
   pasted back.
2. Declare auto-filled context (UID auto-derived, region as provided) and
   the account/region visibility limit with every conclusion.
3. State the verdict tier verbatim (`RECOVERABLE`, `DATA-EXTRACTION-ONLY`,
   `OLDER-BACKUP-POINT-ONLY`, `NOT-A-DATA-LOSS`, `NOT-RECOVERABLE`,
   `INSUFFICIENT-EVIDENCE`) and its decision basis from the script output.
4. Guidance is manual-practice only, prefixed by the pre-action gate
   (safety-net snapshot, irreversibility, low-traffic window) and closed
   with re-verification; cite only M7 URLs.
5. Out-of-scope asks get the boundary sentence plus the handoff route (M6),
   and the data-preservation warning first.

## Examples

**Example 1 -- deleted files, instance alive**
> "I ran rm -rf on my web project directory on server i-bp1demo0001 in
> cn-hangzhou yesterday, can the files come back?"

Run `python3 scripts/areas/data_recovery_assessment/ecs_data_recovery_assessment.py --instance-id
i-bp1demo0001 --region-id cn-hangzhou`, deliver the self-check, then with
answers: `--assess --loss-type mistaken-delete --carrier data-disk
--backup data-disk-snapshot,auto-snapshot-policy --backup-time matched
--overwrite possible --instance-state present-running`. Verdict plus
extraction path with the safety-net snapshot notice; the customer performs
every step.

**Example 2 -- released after expiry, no backup**
> "My instance expired, was released, and paying now did not bring the data
> back."

Evidence mode shows "not visible"; customer confirms the release notice and
answers `--backup none --loss-type expiry-release --carrier system-disk
--instance-state not-visible`: the NOT-RECOVERABLE delivery follows the M5
template (mechanism, rebuild options, prevention), never a promise, and
lifecycle questions route to the expiry-lifecycle skill.

**Example 3 -- rolled back but still "lost"**
> "I rolled back a snapshot but my website is still down, did the rollback
> eat my data?"

Once the inventory is confirmed (`--assess --loss-type suspected-loss
--backup none`), the not-a-loss gate returns `NOT-A-DATA-LOSS` with the
read-only guest checks the customer runs and pastes back (mounts, paths,
service state) -- the files are usually intact and simply not being served.
An unconfirmed inventory stops earlier at `INSUFFICIENT-EVIDENCE`. The
"rollback restores file-data state, not the running state; start the services
manually" wording is delivered with the rollback path guidance (M4 Path A)
and the fixed statements in M5. The only cloud call is the read-only status
check.

## Important Notes

- The decisive facts (which backup exists, its class, its point in time,
  whether guest data is really gone) come from the **customer's own console
  checks and pasted output**; the API leg only proves instance existence and
  status for the current account and region.
- Quotable error strings: this tier ships no verified OpenAPI error literals
  yet, so triggers stay on customer symptom wording; candidate codes are
  deliberately not cited until verified against the official error tables.
- Some handoff target tier names in M6 are marked "pending batch
  alignment"; when a name is unconfirmed, state the topic boundary and
  route to human support instead of inventing a skill name.
- Windows support follows the official best-practice document branch only;
  volume-level Windows specifics carry medium confidence pending human
  re-review.
- This skill never states or implies that it ran, executed, restored,
  rebuilt or guaranteed anything: it assesses, guides and re-checks.
