# Clone / Image Task Progress Triage (capability K3)

A clone (or the custom image behind it) sits at 0%, or "has been half an
hour, usually it takes minutes". Decision tree below. Machine-readable
branches live in `scripts/axes/instance_clone_guide/_constants.py` (`TRIAGE_BRANCHES`,
`TRIAGE_COLLECT_FIRST`, `ESCALATION_TEMPLATE`), served by
`scripts/axes/instance_clone_guide/clone_guidance.py --triage`.

## What can and cannot be seen

- This skill's verified contract covers INSTANCE-side reads only. Image and
  snapshot task progress is NOT visible to it; the progress figure comes
  from the customer's console screenshot.
- Platform-side task queues are invisible to this skill and were equally
  invisible to the live agents in the source tickets: sessions that hit a
  real 0%-stuck case collected screenshots and escalated, nothing else.
  Expect parity with a human session on the diagnosis itself; what differs
  is that the collection list below is identical every time and needs no
  queue wait.
- Honesty: the "30 minutes" figure circulating in this tier's tickets is
  customer narration, and one "region under sustained snapshot load"
  explanation had its region name masked in the evidence. There is NO
  official duration standard. All thresholds below are therefore RELATIVE
  to the customer's own normal completion time. Never promise a completion
  time.

## Step 1 - collect (always, before any verdict)

1. source and target instance IDs;
2. a full page screenshot showing the progress bar, the image/clone task
   name and the console region selector;
3. start time and the currently displayed progress percent;
4. whether this is the FIRST custom image for this account and region;
5. rough disk size being captured (system disk plus ticked data disks).

## Step 2 - classify

| Observed facts | Verdict | Action |
|---|---|---|
| progress above 0% and moving | progressing | First custom images take a FULL snapshot and run long; some regions run under sustained snapshot-service load. Wait, re-check with a fresh screenshot. No time promise. |
| progress 0%, elapsed time significantly beyond this account's own history | possible-stuck | No self-service action exists at this layer. Deliver the escalation packet (below) as a human support ticket. Do not declare the task failed; do not retry before the existence check (next row's risk). |
| progress 0%, elapsed within or near this account's normal window | progressing | Treat as moving; re-check with a fresh screenshot. No time promise. |
| progress 0%, no baseline, and this is NOT the first custom image | possible-stuck | The full-snapshot warm-up excuse does not apply. No self-service action exists at this layer: deliver the escalation packet (below). Do not declare the task failed; do not retry before the existence check. |
| progress 0%, elapsed unknown or near-normal, and the first-image answer is yes or unanswered | unknown-duration | Ask whether this is the first image; re-check later; escalate only once it clearly exceeds the customer's own baseline. |
| facts insufficient (no screenshot, region unclear, account mismatch) | insufficient-facts | Withhold any verdict; list what is missing; this is exactly where a live session also stops. |

## Step 3 - before ANY retry: fake-failure loss prevention

A real ticket in this tier showed a "clone failed" page where the
instances and resource stacks had actually been created; the customer
retried and ended up with 25 duplicated instances and an overdue balance.
So a stuck-or-failed task must never end in "just run it again" before:

- `python3 scripts/axes/instance_clone_guide/clone_readiness_check.py --region-id <region>
  [--instance-ids ...]` (read-only existence + region instance count), and
- the console instance list plus resource-stack list under the exact
  account and region.

## Escalation packet template

> Please open a support ticket and attach: (1) source and target instance
> IDs, (2) the clone start time, (3) the full page screenshot showing
> progress and the region selector, (4) whether this is the first custom
> image for the account. Note that no write changes were made while
> waiting.

Related: clone-solution-matrix.md, clone-scope-and-billing.md,
post-clone-checklist.md, handoff-map.md (relative to this directory).
