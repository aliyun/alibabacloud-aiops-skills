---
name: alibabacloud-ecs-memory-oom-remediation
description: |
  Diagnose and relieve ECS Linux memory pressure: OOM kills, hangs/freezes on a small spec (2 vCPU 2 GiB) deploying software or AI agents, swap-induced IOPS, SSH login failure, which process used memory.
  Use when (customer wording): out of memory; the OOM killer killed my process; my instance hangs; 2C2G runs out of memory deploying Docker; disk IOPS is maxed out; I cannot SSH into my ECS instance; can I add swap to a small ECS instance.
  Load even for plan-only requests; give the plan without executing.
  Cloud reads are Describe-class only; Swap changes only after the customer confirms that exact change this turn, else guided. No reboot or spec change.
  Do NOT use for: Windows or non-ECS resources, CPU saturation without memory evidence, deep heap-leak analysis.
  Triggers: "out of memory", "the OOM killer killed my process", "disk IOPS is maxed out", "I cannot SSH into my ECS instance", "can I add swap to a small ECS instance".
---

# alibabacloud-ecs-memory-oom-remediation

Memory-pressure triage for one ECS Linux instance. The entry script decides, from
cloud-side reads plus one consented in-guest collection, whether the instance is a
small-spec candidate, what is eating the memory, and which of these five remedies
applies: Swap, runtime memory limits, process-level root cause with atop, staged
restart, or upgrade guidance. Every conclusion cites real output.

## Execution Principle (MANDATORY)

- **The report the script prints is your final answer.** Reply with the script's two code
  blocks (the ```text report block and the ```json block, including every guidance/warning
  line) copied **verbatim**, as your entire final message. Do NOT send a summary, an
  introduction, a closing remark, or a file path in place of the blocks. Full rules: *Final
  Answer Delivery Contract* below.
- One entry command owns the whole flow: `python3 scripts/memory_diagnosis.py`.
  ABSOLUTE PROHIBITION on running the in-guest commands by hand, on re-implementing
  its checks, or on writing a report from the source file: run the script and quote
  its output.
- Query-only by default. The only mutating action this skill can perform is the Cloud
  Assistant Swap enable/disable described in *User Confirmation* below, and only when
  the customer confirmed that exact change in the current turn.
- ABSOLUTE PROHIBITION on fabricating evidence. A check that did not run, failed, or
  returned nothing is reported as `not collected` or `unverified`, never as a clean
  result. Cloud-side reads see the current credential's account only: an empty result
  is a visibility finding, not proof of absence.
- The in-guest collector is dispatched as one frozen, unmodifiable payload. It accepts
  no customer text, uses no `eval`, and changes nothing in the instance.
- Site language: this package emits English output only.
- Missing instance location is a hard stop. If the instance id or region is absent (for
  example the customer gives only an account UID), you MUST first ask the customer for the
  missing instance id / region, or explicitly declare the source you used to resolve it,
  BEFORE running any diagnosis. Never invent an instance id or region, and never jump to a
  process / atop conclusion without first locating the instance.
  Do NOT call DescribeRegions or DescribeInstances yourself to guess the instance from a
  UID: run the entry script, and when it hard-stops for missing location, relay its ask to
  the customer. If you do resolve the location from an account-wide scan, first print a line
  `INSTANCE-LOCATION-SOURCE: resolved <instance-id> in <region> via DescribeInstances
  account scan` before any diagnosis.

## Credentials (MANDATORY)

- Default credential chain only (environment, CLI profile, credentials file). Never
  pass, read back, print or store an AccessKey id, AccessKey secret or STS token.
- ABSOLUTE PROHIBITION on opening `~/.aliyun/config.json`, `~/.aliyun/`, or any
  credential environment variable to work around an authentication failure, and on
  asking the customer to paste a key into the conversation.
- An authentication failure is fail-closed: the script prints `CREDENTIAL-FAIL-CLOSED:`
  with the customer's own verification steps and exits 3. Deliver that block verbatim
  and stop. Do not substitute guessed cloud state for the missing reads.

## User Confirmation (MANDATORY, two independent gates)

1. **In-guest read** (`--allow-guest-read`): Cloud Assistant executes the collector
   inside the customer's instance and leaves a task record there, so consent for the
   diagnosis as a whole does not cover it. Without the flag the script prints
   `CONSENT-REQUIRED:`, still runs every cloud-side read, and marks guest-derived
   fields `not collected`. Ask which command would run and what it returns; if the
   customer declines, hand them the command to run themselves and report that layer as
   unverified.
   The agent's answerability is read **before** dispatching, from
   `describe-cloud-assistant-status`: when that call reports the agent as `offline`
   (flag false) or `unresponsive` (its last heartbeat is older than the 900-second
   threshold documented in `references/report-template.md`), the collector is not
   dispatched at all and the reason is logged, because
   an invocation against a dead agent is created only to fail. `unknown` (no status row,
   or the status call itself failed) still attempts the read: absence of a status is not
   evidence of an offline agent. The same pre-flight refuses to dispatch this collector
   to a non-Linux guest and prints `OS-TYPE-LIMIT:`, because the frozen payload is a
   Linux shell script and an invocation of it on Windows can only fail.
2. **Swap change** (`--confirm-swap-change enable|disable`): the one mutating action.
   Before passing it, present the five preconditions one by one (Linux, memory at most
   8 GiB, memory-pressure evidence, free disk space at least 5 GiB after the change,
   system disk not a basic cloud disk), the exact command, and the I/O trade-off, then
   wait for an explicit yes in this turn. Without that confirmation, or when any
   precondition fails or is unknown, the script prints `SWAP-CHANGE-BLOCKED:` and
   delivers guidance from [references/swap.md](references/swap.md) instead. An
   unconfirmed request is never delivered: the report keeps the recommendation and the
   delivered command count stays zero.
   Never pass the flag on your own initiative and never re-run with it after a refusal.
   The same confirmation applies to `disable`: rolling Swap back is a change too.
   A confirmed `enable` is additionally refused with `SWAP-CHANGE-ALREADY-CONFIGURED:`
   when the guest reading shows Swap already configured with free space left: adding a
   second Swap file is not the missing fix, so the report points at the memory holder,
   the runtime limit or the instance spec instead.

Rebooting, `kill`, `pkill`, `systemctl restart` and the ECS reboot action are never
executed by this skill; a restart is guided in [references/restart-guide.md](references/restart-guide.md) only.

## Trigger Conditions

See the description. Intake is classified into one symptom branch by `--symptom`:
`oom`, `iops`, `hang`, `cpu`, `root-cause`, or `auto` when the customer did not say.

## Input Parameters

| Parameter | Required | Notes |
|---|---|---|
| `--region-id` | yes | Region of the instance, e.g. `cn-hangzhou` |
| `--instance-id` | yes | One `i-...` Linux instance id |
| `--symptom` | no | `auto` (default), `oom`, `iops`, `hang`, `cpu`, `root-cause` |
| `--window-minutes` | no | CloudMonitor look-back for the metric reads (sets `start-time` and `end-time`), default 60 minutes |
| `--allow-guest-read` | no | Customer consented to the in-guest collector in this turn |
| `--confirm-swap-change` | no | `enable` or `disable`, only after explicit confirmation |
| `--verify` | no | Re-collect after the customer's remediation and print the before/after verdict; required for any recheck / re-verification request |
| `--ssh-unreachable` | no | The customer reports SSH will not log in (routes the hang lane) |
| `--selftest` | no | Pure-function boundary assertions, no cloud call |

## Module Index

| Document | Content |
|---|---|
| [references/swap.md](references/swap.md) | Swap preconditions, official command set, rollback, guidance path |
| [references/atop.md](references/atop.md) | atop install, live view, history replay, high-memory process location |
| [references/node-runtime.md](references/node-runtime.md) | `--max-old-space-size` advice and launch variants |
| [references/restart-guide.md](references/restart-guide.md) | Staged restart guidance and data-loss risk |
| [references/guest-observation-catalog.md](references/guest-observation-catalog.md) | Every key the collector returns and how it is judged |
| [references/report-template.md](references/report-template.md) | Fixed report fields and order |
| [references/ram-policies.md](references/ram-policies.md) | Permission inventory and the gated action |

## Execution Flow

1. Run the entry command with the region and instance id:

   ```bash
   python3 scripts/memory_diagnosis.py --region-id cn-hangzhou --instance-id i-example0000000001
   ```

2. Read the routing block: spec gate, Cloud Assistant availability, memory-pressure
   evidence, and which layers are `not collected`.
3. If the customer asked for a Swap change, walk the *User Confirmation* gate 2 before
   re-running with `--confirm-swap-change`, and report the outcome from the invocation
   result, not from intent. A delivered change re-collects in the same run and prints the
   before/after verdict per key (`EASED`, `WORSENED`, `STILL PRESENT`, `CONFIGURED`,
   `REMOVED`, `UNCHANGED`, `UNVERIFIED`, `NO BASELINE`); quote that verdict, and never
   turn `CONFIGURED` into a claim that the pressure eased.
4. Deliver the report in the fixed field order of
   [references/report-template.md](references/report-template.md), naming the evidence
   source (cloud read, in-guest collector, atop replay, or not collected) for every claim.
   Delivery is governed by the *Final Answer Delivery Contract* below: the report block
   must appear verbatim in the final chat reply itself, not only in a saved file.
5. After any remediation the customer performed, or for any recheck / re-verification request,
   re-run the entry command **with `--verify`** (plus `--allow-guest-read` when consented)
   so the script re-collects and prints the before/after verdict per key (`EASED`,
   `WORSENED`, `UNCHANGED`, `CONFIGURED`, `UNVERIFIED`, `NO BASELINE`). Quote that verdict
   and never claim the pressure eased without it. Re-running without `--verify` takes only
   a single sample and prints no comparison block.

## Final Answer Delivery Contract (MANDATORY)

The final chat reply is the deliverable. A report that exists only in a saved file, or a
paraphrased summary of it, is **not** a delivered report.

- Embed the entry script's two code blocks **verbatim** in the final reply: the ```text
  report block (from the `=== ECS MEMORY OOM REMEDIATION REPORT ===` header through
  `STATUS:`/`NEXT_ACTION:` and every guidance/warning line) and the trailing ```json block.
  Copy them character-for-character; do not paraphrase, translate, reorder, or drop any
  line. Do not add a plain-language summary, introduction, or closing remark before or
  after the blocks: the final message is the blocks themselves and nothing else.
- Keep every literal label and verdict exactly as printed: the `STATUS:` line, the
  `NEXT_ACTION:` line, each Swap precondition name with its `PASS`/`FAIL`/`UNKNOWN`
  verdict (e.g. `memory_at_most_8gib: PASS`), the instance spec line, the evidence-source
  label on each conclusion, and any `before=`/`after=` verification verdict.
- Also quote verbatim every guidance or warning block the script emitted in that run,
  because each is part of the finding: `CONSENT-REQUIRED:`, `SWAP-CHANGE-BLOCKED:`,
  `SWAP-CHANGE-ALREADY-CONFIGURED:`, `SWAP-CHANGE-AGENT-UNREACHABLE:`, `OS-TYPE-LIMIT:`,
  `CREDENTIAL-FAIL-CLOSED:`, `ENVIRONMENT-DEPENDENCY:`, `PERMISSION-GAP:`, the
  `[Degradations]` lines (including CloudMonitor `no datapoint` / missing-agent warnings
  and any named API error code such as `InvalidParameter`, `InvalidRegionId`,
  `Throttling`, `InternalError`), the atop history-replay guidance, and the staged-restart
  risk wording (data loss / power-loss equivalent) when a restart is advised.
- When the script masked a credential in a process command line, keep the `<redacted>`
  marker in the quoted output; never restore or re-print the secret.
- If a layer was not collected, the quoted block already says `not collected` /
  `unverified`; keep that wording instead of substituting a guess.

## Observability

Every CLI call carries the User-Agent template
`AlibabaCloud-Agent-Skills/{skill}/{session-id} skill-version/{skill-version}`,
where the version comes from `references/manifest.json` and session-id is a
32-character hex string generated once per run (`uuid.uuid4().hex`) and reused for all
calls of that run. The flag is `--user-agent`; no other channel is used.

## Examples

- Customer: "My 2C2G instance runs out of memory when I deploy Docker." → run with
  `--symptom oom`, report the spec gate, the memory-pressure evidence and the Swap
  preconditions one by one; if all hold, offer the confirmed change, otherwise guide.
- Customer: "which process used up the memory and when?" → `--symptom root-cause`; if
  atop history covers the window, guide the replay in [references/atop.md](references/atop.md);
  if it does not, state that the moment cannot be reconstructed and label the current
  `ps` snapshot as a point-in-time reading.
- Customer declines the in-guest read: keep every cloud-side conclusion, print
  `CONSENT-REQUIRED:` evidence, and hand over the collector command to run manually.

## Important Notes

- Runtime dependency: the Alibaba Cloud CLI in plugin mode. When a product plugin is
  missing the entry command prints `STATUS: ENVIRONMENT-DEPENDENCY` with the one-time
  install hint and reads nothing. That outcome is distinct from a permission error
  (which names the denied action) and from a credential error (`CREDENTIAL-FAIL-CLOSED:`).
- Relative paths only; every asset lives in this package.
- All subprocess and API calls carry explicit timeouts; transient failures are retried
  with backoff, other failures stop the layer and are logged as degradations.
- Process command lines returned by the collector are masked: any argument that looks
  like a password, token, secret or credential is replaced with `<redacted>`.
- Swap is a mitigation, not a replacement for a larger instance spec; the report always
  says so when it recommends Swap.
