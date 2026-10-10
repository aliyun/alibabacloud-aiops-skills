# DTS Job Lifecycle

## Contents

- [Lifecycle operations and effects](#lifecycle-operations-and-effects)
- [Pre-execution review and confirmation](#pre-execution-review-and-confirmation)
- [Rename a job](#rename-a-job)
- [Start or resume](#start-or-resume)
- [Suspend](#suspend)

Before any write, locate the target by job ID or [exact job name](job-status.md#job-name-resolution). Stop when the name has zero or multiple matches, or the response is invalid. After one exact match, use the job and instance IDs returned by the query for later commands. Then verify from the current job details that the source and destination databases satisfy the [database instance access boundary](database-instance-configuration.md#database-instance-access-boundary). If not, stop after the read-only inspection.

> Applies to renaming, starting, resuming, or suspending one supported one-way `SYNC` job at a time. Renaming does not change the job's run state, so it is not a lifecycle operation and its command is `dtscli job rename`, but it follows the same review and confirmation requirements.

<a id="lifecycle-operations-and-effects"></a>
## Lifecycle operations and effects

| Intent | Command | Retain instance | Retain configuration/position | Risk |
| --- | --- | --- | --- | --- |
| Start/resume | `start-dts-job` | Yes | Yes | High |
| Suspend | `suspend-dts-job` | Yes | Yes | Medium |

<a id="pre-execution-review-and-confirmation"></a>
## Pre-execution review and confirmation

Before a lifecycle operation:

1. Query by ID with `dtscli job get --job-id <job-id> --region <region-id>`. When only a name is known, resolve it with `dtscli job list --region <region-id> --job-name <job-name>` per [exact job name](job-status.md#job-name-resolution), then `job get`.
2. Check `management.eligible` and review the instance ID, type, direction, endpoint engines, access types, instance IDs, regions, and account relationship in `management.scope`. When eligibility is `false`, explain `management.reasons` and stop before writing. Do not apply a second inference on top of the CLI assessment: the CLI already folds case and display-name engines, treats a blank one-way direction as Forward, and treats missing owner IDs without roles as same-account. Unknown states, two-way or compound jobs, reverse jobs, one-sided owner IDs, and unregistered links cannot pass. The CLI checks scope again before writing.
3. Show current state, expected state, and the operation-specific impact below.
4. Obtain explicit authorization for the exact redacted target, parameters, state transition, and impact. Only the creation workflow's `job create test` → purchase → configure → start sequence runs under the combined create-flow confirmation; pause, resume, and rename are confirmed separately, and a user message that names the job region and the job name (or job ID) and explicitly approves one of them counts as that operation's confirmation. One authorization covers only that job and that operation: a change to the target, direction, or operation requires new confirmation, and it never carries over to another job or another operation.
5. Execute the reviewed operation, then query the job again.

Start and pause run in one step:

```bash
dtscli job <start|pause> \
  --job-id <job-id> \
  --region <region-id>
```

When `redundant` is `true`, the operation would have no effect in the current state — for example the job is already in a terminal state — and no write is sent: explain why and stop.

The Alibaba Cloud CLI can be configured with a safety policy (`~/.aliyun/safety-policy.json`) that requires interactive confirmation for operations such as `dts:suspend*`. `dtscli` issues writes non-interactively and skips that prompt. Never work around this by running a CLI command with `--yes` outside `dtscli`.

Use the API-specific requirements in the [API allowlist](api-allowlist.md). Use the validated current profile; do not independently select or replace it.

In execution results, `accepted=true` means only that the API explicitly accepted the request. `verified=true` means readback verified the corresponding state transition. DTS applies starts and suspensions asynchronously, so the command polls the readback within the `--settle-seconds` window and reports `verified=true` only once the transition lands. The flag defaults to 20 seconds and accepts 0 to 60, where 0 keeps a single readback; this Skill leaves it unset and uses the default window. A lifecycle no-op sets `accepted` and `verified` to `false` and adds `redundant=true`. When the window expires without confirming the change, the command retains its result, sets `error_class=indeterminate`, and exits nonzero: report “accepted, not yet verified,” query read-only status first, and never automatically retry the write. Explicit business rejection is a failure; missing success evidence or an invalid response leaves the outcome indeterminate.

<a id="rename-a-job"></a>
## Rename a job

Renaming must follow this complete sequence: when only a name is known, first use `job list` for exact resolution; before the first rename, use `job get` to read current details and complete the management-scope review; run one `job rename`; then verify the new name with `job get`. The initial `job get` is a precondition for the write and cannot be replaced by the readback after renaming. When the user explicitly requests a temporary rename followed by restoration, run the second `job rename` only after the first readback succeeds, then use one final `job get` to confirm that the original name is restored.

```bash
dtscli job rename \
  --job-id <job-id> \
  --region <region-id> \
  --new-name <new-name>
```

The rename result reports names rather than states: `job_name_before` is the name before the change and `job_name_after` is the name read back. When the job already has the requested name, no write is sent, `accepted=false`, `verified=true`, and `note` says why. Report it as "no rename needed" and do not retry.

<a id="start-or-resume"></a>
## Start or resume

`start-dts-job` has two modes selected by whether the instance is purchased. Run `dtscli job get --job-id <job-id> --region <region-id>` first and branch on whether an instance ID is present:

| Mode | When | What `start-dts-job` does | Billing |
| --- | --- | --- | --- |
| Precheck only | Instance not yet purchased (legacy workflow that configures before purchase) | Runs **precheck only**; does not start synchronization | No charge |
| Full start | Instance already purchased (the standard workflow) | Triggers precheck; when precheck does not fail, the service continues the selected transfer stages automatically | Billing follows payment type and incremental-module state; request acceptance alone does not indicate that billing has started |

Inform the user which mode applies before the call. For the creation chain's start, see [job creation](job-creation.md#6-start-evaluate-precheck-and-finish).

Before executing a start:

1. Query and verify job ID, instance ID presence or absence, job type, CLI request and business regions, current state, direction, and enabled stages.
2. Show a redacted review containing the selected mode, target job and instance, current and expected state, direction, and billing impact. For precheck-only mode, state that it runs only precheck and causes no instance fee. For full start, state the applicable billing boundary without claiming billing begins on request acceptance.
3. Obtain explicit authorization for that exact start or precheck operation. Within the purchase-before-configuration workflow, the still-valid combined create-flow confirmation satisfies this step; every standalone start, including resume, requires its own confirmation, and a user message that names the job region and the job name (or job ID) and explicitly approves the resume counts as that confirmation. Then execute the reviewed `dtscli job start`.
4. Query server state: for the precheck-only mode continue with precheck polling; for the full-start mode confirm the job left its pre-start state, report it as started, and stop there. Do not retry a start in an unknown execution state.

The command starts only in the `Forward` direction. This Skill does not support bidirectional synchronization or a reverse sub-job; stop when a request targets one.

- A successful call means only that the request was accepted, not that the job is running, billable, or finished. For the **pre-purchase precheck-only** branch, continue with [precheck](job-status.md#precheck). For the **purchased full-start** branch, report the job as started once the `--settle-seconds` window reads the change back as `verified=true`, without claiming transfer progress or completion, and end the workflow there; this Skill does not poll a started job toward a stable-incremental or zero-delay state.
- Do not repeatedly start a job in an unknown failure state.

<a id="suspend"></a>
## Suspend

Use `dtscli job pause` to retain configuration and runtime position. Show latency, stage, and direction.

After `dtscli job pause` is accepted, the command polls the readback within the `--settle-seconds` window (default 20 seconds, accepts 0 to 60) and reports `verified=true` only once it observes the suspension. When suspension completes, DTS retains `Suspending` as the top-level job status; the official enum does not define `Suspended`. When `Suspending` is returned, preserve the raw API value and report the job as suspended. Never keep polling for a nonexistent `Suspended` state. When the window expires with the job still in its previous state, report `error_class=indeterminate` and confirm with a read-only query instead of sending another pause. Resuming uses the same `dtscli job start` as a full start. Apply the suspension rule in the [billing requirements](instance-classes-and-pricing.md#billing-and-quote-requirements).
