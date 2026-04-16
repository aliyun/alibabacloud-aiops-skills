# SOP: Instance `activating` / change stuck

**Covers:** `ManagementPlane.ActivatingStuck`; often appears together with `HealthCheck.ClusterUnhealthy` (cluster Red) and unassigned shards on the engine.

**Related:** For engine-side Red / allocation, follow [sop-cluster-health.md](sop-cluster-health.md) (Section 1 — cluster Red). **This** SOP explains the **cross-layer causality** between control-plane lifecycle `activating` and engine health — so the report does not only list “one control-plane line + one engine line” without a closed loop.

---

## 1. What `activating` means

`activating` is **not** a random standalone fault. It is the **control-plane lifecycle state** while a change has **not finished** (console / OpenAPI). Typical causes:

- **Rolling orchestration** after `RestartInstance` and similar;
- Tasks still in `updating`, e.g. plugin install/remove or config changes.

User experience: “The instance has been changing / activating for hours.”

---

## 2. Cross-layer causality (closed-loop root cause)

### 2.1 Control-plane facts

- `DescribeInstance`: `status == activating` (or equivalent), often with `updatedAt` to detect “stuck too long” (aligned with rule engine `ManagementPlane.ActivatingStuck`).
- `ListActionRecords`: change type (e.g. rolling restart, plugin op), phase, timeline.
- `ListAllNode`: node roles, whether under rolling, abnormal nodes.

### 2.2 Orchestration constraint (why “change never finishes” shows as `activating`)

Many changes require the **cluster to reach an acceptable health state** (e.g. rolling waits for shard assignment, waits until the cluster is servicable) before the next step. If that condition **cannot be met for a long time**, the orchestration task stays in updating and the instance stays **`activating`**.

### 2.3 Engine-side closure (why “the cluster never recovers”)

**Do not duplicate** `/_cluster/allocation/explain`, `_cat/shards`, `unassigned.reason` playbooks here — use [sop-cluster-health.md](sop-cluster-health.md) (Section 1 — cluster Red).

In the “long `activating`” context, remember: **orchestration is waiting for “cluster can recover / shards can allocate”**; the **engine** Red root cause still comes from **allocation explain** (e.g. allocation filter to a non-existent node, disk, allocation disabled). Until that is fixed, **“wait for cluster recovery” may never succeed** → instance stays `activating`.

> **Takeaway:** On the control plane, `activating` means “change not finished”. The **technical closure** that explains **why** it cannot finish is still **`allocation/explain`**, not a paraphrase of `activating` text instead of engine evidence.

### 2.4 Remediation order

1. **When `activating` is confirmed, complete control-plane evidence before touching the engine:** at least **`DescribeInstance` + `ListActionRecords` (MUST)**, and **`ListAllNode`** is recommended. `ListActionRecords` gives change type (e.g. `RestartInstance`), phase, rolling progress, stuck node / `pendingOperation`, etc. **Reporting only “activating + RestartInstance” without this API is an incomplete control-plane chain** (a common gap when reviews expect full change-task evidence).
2. **Then** follow [sop-cluster-health.md](sop-cluster-health.md) (Red / allocation section) for engine explain / shard root cause and fixes (delete index, change settings, etc.).
3. **Before destructive or recovery actions** (e.g. `DELETE` index, `PUT` allocation-related settings): keep a **pre-action snapshot** — same-moment `DescribeInstance` + `ListActionRecords` summary (or explicit timestamps and key fields) so the report can state “control-plane state while the change was stuck”.
4. **After** engine blockers are cleared, expect **intermediate** Yellow, throttling, `same_shard`, CMS lag, etc. while moving toward Green (see cluster-health SOP) — that is normal. **Re-check control plane after remediation:** **`DescribeInstance`** again (and **`ListActionRecords`** if needed) to see whether `activating` ended and to validate **“engine recovered → change completed → lifecycle normalized”**; if still `activating`, continue from the new records.

---

## 3. Evidence checklist (MUST / SHOULD)

| Dimension | Source | Requirement |
|-----------|--------|-------------|
| Lifecycle | `DescribeInstance` | **MUST:** `status`, `updatedAt`, etc.; at least once before and after remediation |
| Change task detail | `elasticsearch ListActionRecords` | **MUST** whenever `activating` / change-stuck: type, progress, stuck or pending nodes; **do not** skip this call with only Describe text |
| Nodes | `ListAllNode` | **SHOULD:** rolling and abnormal nodes |
| Cluster health (control/CMS) | `DescribeMetricList` (ClusterStatus, etc.) | **SHOULD:** cross-check with engine |
| Engine root cause | `allocation/explain`, `/_cat/shards` | **MUST** when Red / unassigned: steps in **sop-cluster-health** Section 1 |

### 3.1 Recommended collection order

1. `DescribeInstance` → confirm `activating` and instance fields.  
2. **`ListActionRecords`** → task detail (distinguish from “we guessed RestartInstance”: **must come from API**).  
3. `ListAllNode` (recommended) → corroborate with change records.  
4. Engine: `allocation/explain`, `_cat/shards`, etc. (cluster-health Red section).  
5. **Before risky remediation:** another snapshot of `DescribeInstance` + `ListActionRecords` if time has passed since steps 1–2 or you are about to delete indices.  
6. Execute remediation → watch `_cluster/health` / CMS for intermediate states.  
7. **After remediation:** `DescribeInstance` (+ optional `ListActionRecords`) → confirm `activating` cleared.

---

## 4. Report expectations (skill template)

When both **`activating` (or `ManagementPlane.ActivatingStuck`)** and **engine Red / unassigned primary** exist:

- **Do not** write only “control plane and engine in parallel” with no causal link.
- **Evidence** must include a **`ListActionRecords` summary** (change type, phase/progress, abnormal or pending nodes), cross-checked with **`DescribeInstance`**; if remediation ran, add **before/after** control-plane comparison (Section 3.1 recommended collection order).
- **Must** add a **one-line cross-layer root cause** that states explicitly:

  **Change waiting for cluster recovery ← cluster stays Red ← concrete reason from allocation explain (e.g. require points to a non-existent node)**

Example sentence (replace index name and explain conclusion with real values):

> The rolling change on the control plane waits for cluster health; on the engine, index `{index}` has `index.routing.allocation.require._name` pointing at a non-existent node, so primaries cannot allocate and the cluster stays Red — orchestration cannot proceed → instance remains `activating`.

If there is no `activating` or the engine is already Green, write “N/A” or omit this subsection.