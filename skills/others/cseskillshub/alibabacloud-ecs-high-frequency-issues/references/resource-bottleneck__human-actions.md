# Human actions: steps the skill outputs but never performs

Everything on this page is **guidance text handed to the customer or to a human
engineer**. None of it is dispatched, and none of it is "pending an approval" that
this skill can obtain for itself. The reason is documented in the tier's
requirements: the three highest-frequency effective remedies in this ticket corpus
were all performed by a human on the machine — a java service stopped by the
engineer (T-7E06B86C), swap configured by hand (T-D25A9845), and recovery by
reboot (T-B8B16499, T-1BBB1704, T-BF2F77A0).

## Never auto-executed

| Action | Why it stays human | What the skill outputs instead |
| --- | --- | --- |
| `kill` / stopping a service or process | removes the customer's workload; irreversibility is business-level, not technical | the ranked process list, the rule that explains it, and the request that the customer confirm which process is expendable |
| reboot / restart of the instance or a service | interrupts live business; in-memory data not yet flushed is lost | the three-risk notice below, plus the snapshot-first step |
| swap and kernel parameter writes (`sysctl`, `swapoff`, `swapon`, any redirection into config) | changes runtime behaviour persistently and is a common source of "it got worse" | the documented procedure and values below, for the customer to run |
| instance spec upgrade / downgrade | commercial decision with pricing and downtime consequences | the facts: readings, calibers, which area is saturated — **no recommendation** |
| refund, unsubscription, price continuation | commercial | nothing; hand to billing / account manager (see `references/resource-bottleneck__escalation-map.md`) |
| cross-region migration | far-reaching, long-running | nothing; out of scope |
| deleting a snapshot | destroys the only backup of a point in time | the reminder to delete *after* troubleshooting is finished, because snapshots keep billing (doc 128131.html) |
| any formatting, partitioning, mounting change, or data deletion | irreversible data loss | never proposed by this skill at all |
| creating a snapshot | it is a write, and this package deliberately does not hold it: the `create-snapshot` console action is **absent** from `related_apis.yaml` and from the granted policy | the console procedure (doc 25455.html) for the customer to perform, with the billing and deletion caveats |

The last row is a design decision, not an oversight: the requirements document
marks `CreateSnapshot` as an optional low-risk reversible write and leaves its
inclusion open (section 8). While it is open, this package ships with **exactly
one** non-read action — the consent-gated `run-command` — and snapshot-before-reboot is
pure manual guidance. If snapshot creation is later added, `related_apis.yaml`,
`references/ram-policies.md` and the script call surface must all change together.

## Template 1 — snapshot first (always before a reboot)

Use this order, which is how the tickets that closed successfully did it:

1. If the instance holds important data, create a snapshot **before** any
   authorisation or operation. (T-B8B16499, T-0BFCC153)
2. A snapshot whose progress reaches **1%** already protects that point in time —
   the customer does not have to wait for 100% before proceeding. (T-0BFCC153)
3. Say that snapshots are a **paid** resource, and give the billing reference
   with the creation steps, not after the fact.
4. Remind the customer to **delete** the snapshot when troubleshooting is done, or
   it keeps billing. (T-69AEDFA2, T-D25A9845)

References, by provenance from the ticket corpus:
- create a snapshot: `https://help.aliyun.com/document_detail/25455.html`
- how snapshots work: `https://help.aliyun.com/zh/ecs/user-guide/how-do-snapshots-work`
- snapshot billing: `https://help.aliyun.com/document_detail/56159.html` and
  `https://help.aliyun.com/zh/ecs/product-overview/snapshots-1`
- delete a snapshot: `https://help.aliyun.com/document_detail/128131.html`

## Template 2 — reboot, with the three risks in full

A reboot is only proposed after the snapshot step and only by a human. All three
risks must be stated together; quoting one is the pattern that produced disputes:

1. **Business interruption** — schedule it in a low-traffic window.
2. **Unflushed in-memory data is lost** — stop the applications cleanly first.
3. **Create a snapshot beforehand** — and attach the billing notice.

Then ask whether the customer will perform it or authorise the engineer to. The
console-side procedure is `https://help.aliyun.com/zh/ecs/user-guide/restart-instances`
(T-B8B16499). If the instance is frozen so that neither SSH nor RDP nor the
console VNC login responds, the reboot is the only remaining path, and that branch
must be reported as DEGRADED with the diagnosis incomplete
(T-570E51B9, T-1BBB1704) — see `references/resource-bottleneck__evidence-and-privacy.md`.

## Template 3 — Linux swap for small-memory instances

Evidence: the dominant chain of this tier (memory exhausted → kswapd0 paging →
disk IOPS pinned → instance frozen) and the small-spec memory doc, which is the
highest-relevance document in this batch (T-D25A9845, T-B8B16499, T-1BBB1704).

- Recommended shape seen in the tickets: a **2-3 GiB** swap area on an instance
  with 2 GiB or less of RAM, with `vm.swappiness` set to **70**.
- Procedure reference:
  `https://help.aliyun.com/zh/ecs/support/how-do-i-configure-the-swap-partition-of-a-linux-instance`
  (quoted in T-1BBB1704)
- Small-instance memory management reference:
  `https://help.aliyun.com/zh/ecs/user-guide/operation-and-maintenance-of-linux-memory-management-for-small-ecs-instances.md`
- State the tradeoff: swap converts "out of memory, process killed" into "slow,
  disk IO bound". It stops the freeze; it does not add capacity. If the workload
  genuinely needs more memory than the spec has, that is a capacity conversation
  for the customer and their billing, not a diagnosis this skill recommends.
- The commands themselves are **never** dispatched by this skill: `swapon`,
  `swapoff` and `sysctl` writes are on the blocklist in
  `scripts/areas/resource_bottleneck/_constants.py::COMMAND_BLOCK_SUBSTRINGS`.

## Template 4 — Windows virtual memory

For Windows instances with memory pressure:
`https://help.aliyun.com/zh/ecs/support/how-to-configure-virtual-memory-for-windows-instances`
(T-72D9DFCB). Same tradeoff as Template 3 — the page file moves the failure from
process termination to disk IO latency — and the same rule applies: the setting is
changed by the customer, in the GUI or with their own tooling, never by a dispatch
from here.

## Template 5 — application-side memory ceilings (direction, not implementation)

Tickets T-72D9DFCB and the MySQL samples show the effective advice was a
parameterised direction with the customer's own engineer implementing it:

- **MySQL**: `innodb_buffer_pool_size` is the parameter most coupled to memory
  pressure; the ticket's guidance was to size it at roughly **50-70% of available
  memory** (the reported instance was still at the 128 MB default), to check
  `max_connections` is not excessive, and to consider disabling `query_cache_size`.
- **Kernel**: `vm.overcommit_memory` and `vm.swappiness` shape *when* the OOM
  killer fires; enable swap with its performance cost understood.
- **Critical services**: OOM protection via `/proc/<pid>/oom_score_adj`, so the
  victim selection is deliberate rather than incidental.

Do not quote a value as a recommendation for the customer's spec without their own
readings, and do not write to any of these from here — every one of them is a
configuration write.

## Template 6 — install the collection agent *before* the next incident

The largest single cause of unusable evidence in this tier is that nothing was
installed when the incident happened:

- **CloudMonitor agent** — without it, the OS-level memory metric has no data at
  all, and the question "was it memory?" cannot be answered from the cloud side
  (T-D25A9845, T-36BC7559, T-6143D71E, T-BF2F77A0). Process-level checks then
  happen in the host monitoring console:
  `https://cloudmonitornext.console.aliyun.com/hostMonitor/` (T-570E51B9 — a
  console link, not a document).
- **`atop`** — the only way to replay per-process history for a *past* minute. It
  must have been running beforehand; it cannot reconstruct the past after the fact
  (T-CC0FA37F, T-D25A9845, T-BF2F77A0). Two URLs for this topic appear in the
  corpus, `use-cases/use-the-atop-tool-to-monitor-linux-system-metrics` and
  `how-to-use-the-linux-system-atop-monitoring-tools`; which one is current is
  listed as pending confirmation, so quote one and expect a possible redirect
  rather than asserting both are live.
- **`sysstat`** — needed for `iostat -x` and `sar`, both whitelisted for gated
  dispatch and both useless if the package is absent.

Installation is a human action. This skill's role is to state, in the DEGRADED
branch, exactly which of these was missing and what question each would have
answered — so the customer installs the right one.

## Related reading with confirmed relevance

- Load too high, official handling: `https://help.aliyun.com/zh/ecs/user-guide/high-system-load-drills.md`
- Linux high disk IO troubleshooting: `https://help.aliyun.com/zh/ecs/support/troubleshooting-and-solution-for-high-disk-i-o-load-in-linux-system`
- Burstable (t-series) overview / monitoring / billing:
  `https://help.aliyun.com/zh/ecs/user-guide/burst-performance-instance-overview.md`,
  `https://help.aliyun.com/zh/ecs/user-guide/monitor-burstable-instances.md`,
  `https://help.aliyun.com/zh/ecs/user-guide/billing.md`,
  `https://help.aliyun.com/document_detail/59977.html#af710c5244av5` (unlimited /
  performance-constrained mode) and
  `https://help.aliyun.com/document_detail/90581.html#section-lqi-vqf-dsc` (overage
  credit charges) — tickets T-408C886A.
- Console VNC login as the last-resort path when SSH/RDP fail:
  `https://help.aliyun.com/zh/ecs/user-guide/log-on-to-an-instance-by-using-vnc`
  (T-BF2F77A0).
- Credential self-service recovery when the CLI principal is wrong or expired:
  `https://help.aliyun.com/document_detail/25439.html` (T-69AEDFA2, T-441637A1).

No other links are quoted here. Anything not in this file has not been verified in
this batch, and inventing a plausible help-centre URL is the same failure mode as
inventing a resource (rule R8).
