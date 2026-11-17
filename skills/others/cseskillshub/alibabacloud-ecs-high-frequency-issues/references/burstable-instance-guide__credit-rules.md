# M1: CPU Credit Rules for Burstable Instances (t-series)

Distilled from this tier's official-document hits and support-ticket
transcripts. **Freshness rule:** every statement below must be relayed with
its linked official document; the current version of that document is the
final authority (human re-verification required before release).

## Disk-side burst credits (check before calling a charge CPU-side)

- A "performance burst" fee is not automatically CPU. Heavy disk I/O —
  formatting a freshly attached data disk (`mkfs`), a large copy, image
  deployment, snapshot restore — can exceed the instance's baseline disk
  throughput; the excess is converted into **IOPS credits** and billed even
  when vCPU utilization is near zero.
- Real ticket T-96728BB0: a 1T data disk was formatted immediately after
  purchase, reaching about 500 MB/s for ~30 s against a 350 MB/s baseline.
  The excess was billed as roughly 350k IOPS credits at 0.02 CNY per 10k
  credits, about 0.5 CNY, while the instance ran no application workload.
- Ordering rule: read the charge timestamp against disk operations first;
  read disk category/size and the type's baseline disk throughput; if CPU was
  low and disk throughput was high, attribute to disk-side burst credits.
  The exact credit count and rate are bill dimensions — the customer confirms
  them on the bill or official fee page; never invent them.
- Only when disk I/O cannot explain the timing should the CPU-credit
  explanation below be used.

## What a burstable instance is

- Burstable instances are the ECS `t5` / `t6` families (pattern `ecs.t<d>`).
  They are cheap because their CPU is only guaranteed at a per-type
  **baseline** percentage of the instance's own vCPU capacity; above the
  baseline the instance "bursts" by spending **CPU credits**.
- Credits accrue while usage stays below the baseline and are consumed while
  above it. When the credit balance reaches **zero** in the standard
  (performance-constrained) mode, the instance is throttled to its baseline
  performance.
- Sources:
  - https://help.aliyun.com/zh/ecs/user-guide/burst-performance-instance-overview.md
  - https://help.aliyun.com/document_detail/59977.html#section-6ut-bug-7h0
  - https://help.aliyun.com/document_detail/59977.html#af710c5244av5

## The constraining trigger (common misconception #1)

- The "performance constrained" notification fires when credits are
  **exhausted**, NOT when usage crosses some warning threshold — customers
  who ask "the credits still look plentiful, why was I constrained?" are
  usually seeing the curve after repayment, or conflating percent-usage with
  credit balance (ticket T-3612BE31).
- How long the instance stays constrained depends on the workload and the
  accrual rate of that instance type: below-baseline usage rebuilds credits
  slowly. Never quote a made-up recovery time; point to the worked credit
  examples: https://help.aliyun.com/document_detail/90635.html#section-vrz-uqg-06z
- Notification meaning ("instance system event: burstable instance
  performance constrained"):
  https://help.aliyun.com/document_detail/143663.html#section-glx-g6x-cn4

## What the constraint is NOT (misconception #2)

- It is not an attack, not memory exhaustion, not disk exhaustion
  (support-verified wording, ticket T-584B88C6).
- It throttles sustained CPU above baseline; a constrained web service is
  "slow", and a service that appears fully dead usually has an additional
  problem — that belongs to the connectivity hand-off route
  ([handoff-map.md](burstable-instance-guide__handoff-map.md), ticket T-DCC05ABE).
- "Panel says 46% CPU, looks normal": for a t6 with a 20% baseline, running
  at 46% **continuously drains credits**; the alert that followed was the
  exhaustion consequence, not a false positive (ticket T-02B83E44).

## Baseline math (the "how much CPU do I actually have" answer)

- Effective sustained capacity = baseline percent x vCPU count. Evidence
  example: a 4-vCPU instance with a 25% baseline can use about the equivalent
  of **1 core** (ticket T-BEE1DF3D verbatim reasoning).
- Baseline percent is per instance type. This skill machine-verifies it only
  where its evidence provides a reading (e.g. `ecs.t5-c1m2.xlarge` = 25%);
  otherwise read the value from the console instance-type page or the
  overview document — the script and this module refuse to guess.

## Repayment order (misconception #3: "credits are not accumulating")

- In unlimited mode, newly accrued credits are consumed **first by repayment
  of advanced credits** (and settlement of excess usage), so the visible
  balance can stay flat even at low CPU usage (ticket T-E42721B9). This is
  normal accounting, not a metering fault.

## What is not machine-readable by this skill

- Current performance-mode switch state, credit balance / advanced / excess
  credit values: read them in the console or CloudMonitor (customer provides;
  the injected API contract exposes no verified credit field — see
  [monitoring-setup.md](burstable-instance-guide__monitoring-setup.md)).
- Which process consumed the credits: not replayable cloud-side; see the
  attribution hand-off sentence in [handoff-map.md](burstable-instance-guide__handoff-map.md).

## Decision summary for the entry script

| First branch | Consequence |
|---|---|
| Family is `ecs.t<d>` (t5/t6 confirmed; pattern tolerates later t-series) | Credit rules apply; report baseline math and constraint semantics |
| Family is not t-series | Credit symptoms do not apply; route by real symptom via [handoff-map.md](burstable-instance-guide__handoff-map.md) |
| Family not derivable from the record | State UNKNOWN; ask the customer for the console-shown instance type before concluding |
