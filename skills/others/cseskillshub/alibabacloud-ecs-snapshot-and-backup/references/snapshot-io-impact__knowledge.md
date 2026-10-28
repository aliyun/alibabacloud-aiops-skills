# Diagnosis knowledge: snapshot activity and business performance

This file is the reasoning layer of the skill. It holds the symptom table, the
decision tree the entry script implements, and the interpretation rules the
agent must apply when it reads the script's report. Nothing here is a live
reading: every number in an answer must come from a script call in the same
run.

Scope of this tier is narrow by design. It answers one question: **does the
reported performance problem line up with snapshot activity on this instance's
disks, or does it run independently of it?** Symptoms belonging to another axis
are identified and handed off, not diagnosed - see [handoffs.md](handoffs.md).

## 1. What the tier covers

| Code | Question the customer is really asking | Cloud evidence used |
|---|---|---|
| S1 | "Did it get slow *because* a snapshot was running?" - time-window attribution | `DescribeSnapshots` task spans against the symptom window |
| S2 | "Was there any headroom left, or was the disk already at its limit?" | `DescribeInstanceTypes` storage fields plus CloudMonitor disk BPS/IOPS |
| S3 | "What do we do about it, and is a change safe to attempt?" | Guidance from the S1/S2 result; optional disclosed restore point |

S1 and S2 are evidence-producing. S3 never introduces a new mechanism the
package has not verified; it only re-states what S1/S2 showed and points at the
console.

## 2. Symptom to cause to evidence

Customer wording is on the left. Never put the right-hand column's vocabulary
into a customer-facing question; the customer describes effects, not mechanisms.

| Customer-observable symptom | Candidate causes worth testing | Evidence that decides it |
|---|---|---|
| Everything on the box crawls at the same time each day | Scheduled snapshot set starts on several disks at once | `DescribeSnapshots`: several task spans starting at the same minute, recurring on the policy's weekday pattern |
| A database or search index stalls while a snapshot is running | Snapshot read pressure meeting a saturated disk | Overlap plus CloudMonitor IOPS/BPS sitting at the instance-type ceiling in the same window |
| One disk is slow but the rest of the instance is fine | Single-disk snapshot, or that disk's own category limit | `DescribeDisks` category/size for that disk, `DescribeSnapshots` filtered to that disk, per-disk metric with the `diskId` dimension |
| Latency-sensitive jobs miss their deadline only during a backup window | Background read pressure stealing queue depth | Overlap plus headroom reading; guest-side latency evidence is *not* obtainable from the cloud, see section 6 |
| It is slow all the time, snapshots included | Nothing to do with snapshots | No overlap at all, or the readings stay high outside every snapshot span - hand off, see [handoffs.md](handoffs.md) |
| The disk is nearly full and writes are slow | Capacity pressure, not snapshot activity | No overlap; capacity is a different axis - hand off |
| A snapshot was started before a change and the change window is now tight | Change-related, not performance-related | Restore point only; do not reason about the change's success from snapshot data |
| A snapshot itself is failing or stuck at a percentage | Snapshot creation and policy axis | Out of scope here - hand off, see [handoffs.md](handoffs.md) |

## 3. The decision tree

The entry script implements exactly these four branches; the verdict token in
its report names the one that matched. Do not invent a fifth branch.

| Branch | Verdict token | Condition | What may be concluded |
|---|---|---|---|
| B1 | `SNAPSHOT_WINDOW_AMPLIFIER` | At least one snapshot task overlaps the symptom window **and** a disk reading reaches the internal near-ceiling ratio | Snapshot activity is the dominant amplifier in this window. State it, with the overlap rows and the readings that produced it. |
| B2 | `SNAPSHOT_WINDOW_CORRELATED_HEADROOM_UNCLEAR` | Overlap exists, but the readings stay below the ratio, or no ceiling field came back | Correlation is proven, causation is not. Say both halves. Do not upgrade this to B1 in prose. |
| B3 | `NOT_ATTRIBUTABLE_TO_SNAPSHOT` | No snapshot task overlaps the symptom window | The symptom is not attributable to snapshot activity *in this window*. Route by reading, per [handoffs.md](handoffs.md). |
| B4 | `EVIDENCE_INSUFFICIENT` | A required read failed or returned nothing while no overlap was found | Report `DEGRADED`, name the gap, ask for the missing reading. Never conclude across a gap. |

### 3.1 Window arithmetic

- One snapshot task's span is `StartTime` to `EndTime` when the task finished.
- A task in the `progressing` state has **no end**: the span is open-ended and
  runs to the other window's own bound. An open-ended span overlapping a
  historical symptom window is normal, not a data error.
- When the API gives no `StartTime`, `CreationTime` is used as the span start,
  and the report says so implicitly by echoing the raw fields. Never restate a
  creation time as a completion time.
- The scan range is bounded (see the scan-days constant in `../scripts/_constants.py`).
  "No snapshots found" therefore means "none in the scan range", not "none ever".
  Widen the window and re-run rather than asserting the instance has never been
  snapshotted.

### 3.2 Headroom arithmetic

- CloudMonitor `DescribeMetricLast` is queried for the four disk metrics
  (read/write BPS, read/write IOPS) **inside the symptom window**, using the
  instance dimension and, when a disk id was supplied, the disk dimension too.
- Candidate ceilings are collected by scanning the instance-type record for
  numeric storage or IOPS fields. Field names differ between instance families,
  which is why the scan is generic instead of a hard-coded mapping.
- The near-ceiling ratio is an **internal comparison aid at report time**. It is
  not a published limit. It may appear as "the peak reached N percent of the
  value the API returned"; it may never appear as "the service limit is N".
- If `DescribeInstanceTypes` returns no numeric storage field, there is no
  headroom judgement to make. The run degrades to B2/B4 territory, and the
  ceiling must be read from the block-storage performance page of the console by
  a human before any number is written down.

## 4. Reading the metric table honestly

| Observation in the report | What it supports | What it does not support |
|---|---|---|
| Rows with `overlaps window = YES` | Temporal coincidence, precisely | Any statement about magnitude or causation |
| `progressing` with a `Progress` percentage | A task is still running now | An estimated completion time |
| Metric row with `points = 0` | Nothing collected in that window | "The disk was idle" - it may be a metric-name or dimension mismatch, or collection not enabled |
| A metric read marked `read failed` | A gap to close | Any inference in either direction |
| A ceiling field echoed with its raw value | That the API returned that value for that field | That the value is the enforceable limit for the mounted disk category |

When a table row looks contradictory, quote the row and say it looks
contradictory. Reconciling it by assumption is the main hallucination failure
mode of this tier.

## 5. What may be said to the customer

Allowed, once the evidence exists:

1. Which snapshots overlapped which window, on which disk, with the raw times.
2. What the cloud monitored during that window, with the metric name attached.
3. That spreading snapshot activity away from the business peak reduces the
   overlap - the mechanism is the overlap itself, which was measured.
4. That taking one disk at a time instead of several at once reduces the
   concurrent read pressure.
5. That the schedule lives in the auto snapshot policy of the console and is
   changed by the customer, not by this skill.

Not allowed, in any wording:

- A concurrency count, a throttling percentage, or a rate figure for snapshots.
  No official performance document for that was verified; see section 7.
- A claim that the guest was slow *at* a millisecond level. Nothing in the
  evidence chain measures guest latency.
- A promise that rescheduling will fix the problem. It removes one contributor
  that was measured, which is a different claim.
- A diagnosis inherited from a similar-looking past case. Only this run's rows.

## 6. The one thing the cloud cannot see

There is no cloud API that reports block-device latency, queue depth or
in-flight I/O as the guest experiences it. CloudMonitor is the closest
substitute, and it is aggregated and interval-based.

The inspection commands in
[guest-inspection-commands.md](guest-inspection-commands.md) report file-system
capacity and file-handle state. They are context - a nearly full volume does
slow writes down, which makes a snapshot window hurt more - and they are **not**
latency measurements. Do not let a `df -h` line become an I/O figure in a
customer answer.

When a latency number is genuinely needed, the customer runs the tool themselves
and pastes the output. The agent names the gap instead of filling it.

## 7. Verification items still open for this tier

Recorded honestly so a reviewer does not have to rediscover them, and so the
agent never presents these as settled:

1. **No representative ticket was supplied for this tier.** The symptom table in
   section 2 is derived from the tier's trigger wording and the API surface, not
   from resolved case conversations. Its frequency ordering is therefore
   unverified.
2. **No official snapshot-performance or snapshot-throttling document is cited
   by this package.** Section 5's list is deliberately free of numeric limits.
   If a document is added later, the prohibition on rate figures is lifted only
   for what that document literally says.
3. **No customer-facing error string is confirmed for this tier.** The two
   candidates in the trigger line are the only ones carried, both as phrasings to
   recognise rather than diagnose by. An unmatched code is reported as the raw
   text the customer gave.
4. **The metric names and namespace are working values**, echoed in every report
   so a reviewer can re-check them against the console. A row of zeros is treated
   as a gap, never as an idle disk.
5. **Windows guests are not covered by the in-guest channel** in this release;
   the corresponding guidance stays manual.

## 8. Before writing the answer

- [ ] The region, instance or disk id, and the symptom window are stated, and
      each was supplied by the customer or declared as defaulted.
- [ ] The verdict token is quoted, and the prose matches that token's row in
      section 3 - not a stronger one.
- [ ] Every number in the answer appears in the script's report or is arithmetic
      on numbers that do.
- [ ] Each failed or empty read is named in the answer, not smoothed over.
- [ ] Console guidance names entry points only; no change is described as done.
- [ ] If the verdict is B3, or any read is empty, the hand-off target from
      [handoffs.md](handoffs.md) is named in the answer.
- [ ] `STATUS` and `NEXT_ACTION` from the script are relayed verbatim.
