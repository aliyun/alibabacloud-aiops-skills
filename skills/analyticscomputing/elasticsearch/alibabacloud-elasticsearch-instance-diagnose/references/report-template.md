# Structured diagnosis report (skeleton)

Use with **[acceptance-criteria.md](acceptance-criteria.md)** (§6.x) and repo root **[SKILL.md](../SKILL.md)** §5 Step 4. Copy the block below and fill placeholders.

**Before publish:** Reconcile **ClusterStatus** wording if CMS **window max** (e.g. Yellow) and a **single** `/_cluster/health` snapshot (e.g. green) both appear — qualify **time vs aggregation** ([acceptance-criteria.md](acceptance-criteria.md) **§6.1**). If **per-node CPU %** seems to contradict **which node** was **`search` pool**–bound, add **one sentence** on **sampling / window mean vs spike** ([acceptance-criteria.md](acceptance-criteria.md) **§6.2**). If **slow-log node name** ≠ **node named in pool-rejection / INSTANCELOG** lines, add **one sentence** on **routing / phase / time** ([acceptance-criteria.md](acceptance-criteria.md) **§6.2**). If **CMS `ClusterShardCount`** (or similar) **jumps** (e.g. half then back), **do not** imply shard loss without **`_cat/shards`** + **ops record** cross-check ([acceptance-criteria.md](acceptance-criteria.md) **§6.1**).

```text
## Diagnosis summary

**Instance**: {instance_id} ({region_id})
**Analysis window**: {begin} ~ {end}

### Cross-layer root cause (required when `activating` coexists with Red / unassigned)

**One-line root cause**: {Chain per `sop-activating-change-stuck.md` section 4: change waiting for recovery ← Red ← allocation explain}

(Omit or mark “N/A” if there is no `activating` or the cluster is Green.)

### Incident timeline (recency-ordered)

{Earlier → later, or “latter-window emphasis”: which dimensions (search / write / GC / CPU / disk) peaked or persisted when; cite CMS peak times or log alignment}

### Findings (by priority)

#### P0 - Critical (immediate)
- [Event code] Description
  - Evidence: {metrics / log keywords / events}
  - Root-cause reasoning: {analysis}
  - Immediate actions: {commands or steps}

#### P1 - Warning (within 30 minutes)
...

### Root-cause chain diagram
{Propagation path, e.g. disk full → shards cannot allocate → cluster Red}

### Open questions / follow-ups
{Uncertainties and next checks}
```
