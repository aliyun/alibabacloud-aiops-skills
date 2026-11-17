# Decision tree

What `triage` actually walks, and why each branch is where it is. Every arrow
below was observed in a real case for this tier; nothing is a theoretical branch.

## Before any branch: fix the region

The very first question is which region the alarm or bill names, and it is asked
out loud. `add_region_note` prints the region under query and, when
`--alarm-region` is supplied, hard-fails the conclusion when the two differ.
One source case was closed purely by switching the console to the right region.

## S1: a backup job failed

```
alarm text
  |
  +-- classify() -> category
        |
        +-- ECS_RELEASED
        |     DescribeInstances(region, instance)
        |       empty  -> historical record from the release moment; deleting a
        |                 policy does not clear history; 0 protected resources
        |                 means no new alarm. Manual cleanup path with the
        |                 permanent-data-loss warning.        [T-EF99E331]
        |       found  -> the alarm contradicts the control plane: re-check the
        |                 region before believing the text.
        |
        +-- CLOUD_ASSISTANT_UNREACHABLE
        |     DescribeInstances -> still present?
        |     DescribeInvocations -> any history? recent records final?
        |       |
        |       +-- no history / nothing final -> agent-side confirmed
        |       +-- history present and final  -> the plan side, not the agent;
        |                                         fall through to
        |                                         BACKUP_TASK_ABNORMAL
        |     then emit the four case-backed candidates:
        |       overlay network range conflict      [T-0DDE6FAC, T-29709FD4]
        |       resolver overwritten by a client    [T-4149C679]
        |       Aliyun Assist service stopped       [T-9005CD95]
        |       CPU saturation                      [T-9ED3CF6E]
        |
        |   *** Guest probes are withheld on this branch on purpose. ***
        |   RunCommand is delivered by the component that is failing, so a probe
        |   here produces a false negative that reads as "the network is fine".
        |   Route and resolver inspection is for the customer or an authorised
        |   engineer; see guest-commands.md.
        |
        +-- DISK_SPACE_INSUFFICIENT
        |     DescribeDisks -> provisioned capacity baseline (cloud side only)
        |     guest-probe df_h (or get_volume on Windows)   -> consent, once
        |     guest-probe df_i                              -> second consent
        |     guest-probe du_top --target <path>            -> third consent
        |     snapshot-guard --disk-id <disk>               -> consent, billed
        |     hand the deletion itself to the customer
        |
        |   Cloud API never reports used space. That is the whole reason class B
        |   exists in this skill.
        |
        +-- anything else -> BACKUP_TASK_ABNORMAL or UNKNOWN
              no verified query explains it; collect alarm text, screenshot,
              plan id, region, request id; hand off to Cloud Backup
```

### Why the disk-space branch runs in that order

Measure, then attribute, then protect, then hand over. Taking a snapshot before
measuring wastes a billed resource on a volume that turned out to be fine;
measuring without ever snapshotting is what support refused to do in every case
where data was about to be touched.

### Why the CPU candidate stays a hypothesis

CloudMonitor is not in the verified API surface for this tier, and its action
name differs from its RAM name, so guessing either would be an invented call.
The agent's invocation history is the proxy that is available: a healthy agent
that stops reporting at predictable hours points at saturation. The source case
for that candidate is also the one case whose dialogue could not be retrieved,
which is the second reason it is marked `confidence: medium` and worded as
something to test rather than something found.

## S2: a restore that did not restore

```
triage -> RESTORE_TARGET_OCCUPIED
  1. read the restore result details, including the tooltip behind the icon
       skipped files > 0 -> a process holds the target files
       skipped files = 0 -> go to step 2 anyway
  2. Browse the backup point, expanding level by level to the exact path
       path absent from every point -> the deletion predates retention;
         no restore mode can create it. Say that plainly.
       path present -> step 3
  3. manual SOP: snapshot the disk, stop the holding service, restore in
     overwrite mode, restart the service, verify inside the application
```

Stopping a service is class D and is never automated, even though it is the single
step that resolved the source case. [T-BC432E90]

## S3: what is this charge and how do I stop it

```
triage -> ROLE_OR_BILLING_BLOCKED   (or billing-attribution directly)
  DescribeInstances  -> does anything exist in this region, and how is it billed
  DescribeDisks      -> pay-as-you-go data disks, burst-capable disks
  DescribeSnapshots  -> is snapshot storage present at all
  then map each line through billing-map.md

  a job list that is empty, unclickable and undeletable while the balance is
  negative is a service-linked-role creation failure, not a UI fault: the
  resource inventory still returns, the console does not.   [T-9046C4E1]

  "stop billing" = delete plans, then vaults = the backed-up data is gone for
  good. Guidance only, with that sentence, every time.
```

## S4: concepts, enablement and console state that lies

No query branch. `explain --topic concepts|enable|restore|upgrade|retention|
alarm-states|guest-fallback` prints the block. These are the cases where human
support won by phone or remote session, so the ceiling is honest: the skill can
give the region-correct console path, the mechanism-selection table and the
officially sourced quota wording. It cannot watch the customer's screen.

## Degradation contract

Each branch that cannot complete says so instead of filling the gap:

| Missing | Behaviour |
| --- | --- |
| credentials absent or denied | `check-env` returns `STATUS: FAIL`; other commands continue with `account=unverified` |
| an informational query fails | a `[WARN]` line, `STATUS: DEGRADED`, remaining queries still run |
| RunCommand delivery fails | the exact command is printed for the customer to run and paste, and the branch continues |
| polling budget exhausted | the invoke id is reported so the read can be retried, with a fresh consent |
| alarm text unclassifiable | `STATUS: DEGRADED`, `--category` list printed, no guess |
| HBR task internals needed | `STATUS: DEGRADED`, evidence-collection list printed, hand-off named |

A degraded report is a correct report about a partial picture. It is not an error
to be retried into an `OK`.

## Known gaps

| Gap | Consequence | Do not |
| --- | --- | --- |
| No verified Cloud Backup action, not even a listing one | backup plans, jobs, vaults and restore results cannot be read from the API; they come from the customer's screenshots | call an HBR action because its OpenAPI page is publicly reachable |
| No verified billing, balance or overdue query | arrears are read by the customer in the expense centre | infer a balance from a symptom |
| CloudMonitor not verified (action, RAM name, namespace, metric, dimensions) | CPU and memory saturation is a hypothesis, never a reading | guess a metric name |
| Route, resolver and service-state inspection is outside the guest whitelist | the three most common S1 root causes cannot be measured, only offered as candidates | widen the whitelist to close this |
| No verified `DeleteBackupPlan` | cancelling a backup is a console or manual-API path | automate it |
