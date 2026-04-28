# Acceptance criteria: alibabacloud-elasticsearch-instance-diagnosis

**Scenario**: Elasticsearch instance diagnosis  
**Purpose**: Skill test / acceptance checklist

---

> **Version notes (2026-03)**
> - Control-plane OpenAPI collection uses the `aliyun` CLI only.
> - Health diagnosis entry point: `python3 scripts/check_es_instance_health.py ...`.
> - Engine-level deep collection uses `curl` against ES REST APIs (no `invoke_es_api.py`).

## 1. Environment dependencies

### 1.1 CLI dependency

#### ✅ CORRECT
```bash
aliyun version
```

#### ❌ INCORRECT
```bash
# Error: aliyun CLI not available
aliyun: command not found
```

---

## 2. Credential configuration

### 2.1 OpenAPI credentials (CLI profile)

#### ✅ CORRECT
```bash
aliyun configure list
aliyun --profile <profile_name> sts get-caller-identity
```

#### ❌ INCORRECT
```bash
# Error: profile does not exist
aliyun --profile not-exist sts get-caller-identity
```

### 2.2 Direct ES credentials

#### ✅ CORRECT
```bash
[[ -n "$ES_ENDPOINT" ]] && echo "ES_ENDPOINT: SET" || echo "ES_ENDPOINT: NOT SET"
[[ -n "$ES_PASSWORD" ]] && echo "ES_PASSWORD: SET" || echo "ES_PASSWORD: NOT SET"
```

#### ❌ INCORRECT
```bash
# Error: ES password not configured
unset ES_PASSWORD
```

---

## 3. Running the diagnosis

### 3.1 Main health-check entry

#### ✅ CORRECT
```bash
python3 scripts/check_es_instance_health.py \
  -i es-cn-xxxxx -r cn-hangzhou \
  --data-source cli \
  --profile <profile_name>
```

**Expected output**:
- Structured report (P0/P1/P2, evidence, remediation)
- When multiple major dimensions fire, an **incident timeline (recency-ordered)** section aligning narrative with **when** signals peaked in the window (see §6.6)
- Summary of key monitoring metrics
- No dependency on deprecated scripts

### 3.2 Injected-input + auto backfill

#### ✅ CORRECT
```bash
python3 scripts/check_es_instance_health.py \
  -i es-cn-xxxxx -r cn-hangzhou \
  --data-source auto \
  --input-json-file /path/to/diag-input.json \
  --profile <profile_name>
```

**Expected output**:
- Input JSON fields take precedence when present
- Missing fields are backfilled via CLI OpenAPI

---

## 4. OpenAPI coverage

### 4.1 Elasticsearch OpenAPI

#### ✅ CORRECT
```bash
aliyun --profile <profile_name> elasticsearch describe-instance \
  --region cn-hangzhou \
  --instance-id es-cn-xxxxx

aliyun --profile <profile_name> elasticsearch list-search-log \
  --region cn-hangzhou \
  --instance-id es-cn-xxxxx \
  --type INSTANCELOG \
  --query "*" \
  --begin-time <epoch_ms> \
  --end-time <epoch_ms>

aliyun --profile <profile_name> elasticsearch list-action-records \
  --region cn-hangzhou \
  --instance-id es-cn-xxxxx

aliyun --profile <profile_name> elasticsearch list-all-node \
  --region cn-hangzhou \
  --instance-id es-cn-xxxxx
```

#### ❌ INCORRECT (legacy CLI — do not use for this skill)

Do **not** copy old tutorials that put a **PascalCase OpenAPI action name** as the `aliyun <product> <verb>` verb, or use **CamelCase** query flags. The **✅ CORRECT** block above is the only canonical shell shape for this skill.

### 4.2 CMS OpenAPI

#### ✅ CORRECT
```bash
aliyun --profile <profile_name> cms describe-metric-list \
  --region cn-hangzhou \
  --namespace acs_elasticsearch \
  --metric-name ClusterStatus \
  --dimensions '[{"clusterId":"es-cn-xxxxx"}]' \
  --start-time <epoch_ms> \
  --end-time <epoch_ms> \
  --period 300

aliyun --profile <profile_name> cms describe-system-event-attribute \
  --region cn-hangzhou \
  --product elasticsearch \
  --search-keywords es-cn-xxxxx \
  --start-time <epoch_ms> \
  --end-time <epoch_ms>

aliyun --profile <profile_name> cms describe-metric-meta-list \
  --region cn-hangzhou \
  --namespace acs_elasticsearch
```

**Expected output**:
- Success shape (`Code=200` or `Success=true`)
- Key fields present (instance status, logs, metrics, events, nodes, change records)

---

## 5. Engine-level ES API checks (`curl`)

If calls fail or return **401** / timeouts, classify the failure using **[es-api-call-failures.md](es-api-call-failures.md)** before judging PASS / PARTIAL.

### 5.1 Calls

#### ✅ CORRECT
```bash
curl -sS -u "${ES_USERNAME:-elastic}:${ES_PASSWORD}" \
  "http://${ES_ENDPOINT#http://}/_cluster/health?pretty"

curl -sS -u "${ES_USERNAME:-elastic}:${ES_PASSWORD}" -H "Content-Type: application/json" \
  -X POST "http://${ES_ENDPOINT#http://}/_cluster/allocation/explain?pretty" -d '{}'

curl -sS -u "${ES_USERNAME:-elastic}:${ES_PASSWORD}" \
  "http://${ES_ENDPOINT#http://}/_nodes/stats/thread_pool?pretty"
```

#### ❌ INCORRECT
```bash
# Error: wrong URL path (missing leading /)
curl -sS -u "${ES_USERNAME:-elastic}:${ES_PASSWORD}" \
  "http://${ES_ENDPOINT#http://}_cluster/allocation/explain"
```

---

## 6. Report format

### ✅ CORRECT report shape

```markdown
## Diagnosis summary

**Instance**: es-cn-xxxxx (cn-hangzhou)
**Window**: 2026-03-24 10:00 ~ 2026-03-24 12:00

### Incident timeline (recency-ordered)

- Optional in minimal reports; **required** when search vs write vs GC show **different** emphasis over time (SKILL Step 4).

### Findings (by priority)

#### P0 - Critical (immediate action)
- [HealthCheck.ClusterUnhealthy] Cluster status Red
  - Evidence: ClusterStatus=2, UNASSIGNED primary shards
  - Likely cause: shard allocation failure
  - Immediate action: run `POST /_cluster/allocation/explain`
```

### 6.1 Cluster Red / Yellow — optional “full checklist” (acceptance-style)

Use when you want the report to align with **structured acceptance rubrics** (control plane vs data plane already correct). These are **additive**, not a substitute for `allocation/explain` + `sop-cluster-health.md`.

| Item | What to add (one line each when data exists) |
|------|-----------------------------------------------|
| **Red vs Yellow (B5)** | State **`unassigned_primary_shards` > 0** (or equivalent: “at least one **primary** shard is `UNASSIGNED`”) for **Red**; for **Yellow**, primaries assigned but replicas unassigned. |
| **Shard arithmetic (B6)** | e.g. `number_of_shards=3`, `number_of_replicas=1` → **3 primary shard copies + 3 replica shard copies** (one **replica shard** per primary), **6** logical copies → all may show `UNASSIGNED` when allocation cannot place any copy. Avoid wording that sounds like “`number_of_replicas` = 3”. |
| **`unassigned.reason` (C4)** | From `GET /_cat/shards` / explain: cite reason when present (`ALLOCATION_FAILED`, filter / require deciders, etc.). **Optional (stricter scoring):** mention **`INDEX_CREATED`** when it appears — often consistent with “shard never allocated since creation” under a failing filter (e.g. `require._name` to a non-existent node). |
| **Blast radius (B8)** | Name affected indices (from `_cat/shards`); if only one hot index, say other indices were not failing (if `_cat/shards` supports that claim). |
| **Scale-out vs `total_shards_per_node` (B9)** | Do not promise Green from “add a few nodes” when a **per-index per-node cap** stays tight — verify **(data nodes × cap) ≥** total shard copies for that index (see `sop-cluster-health.md` §2 Yellow; e.g. **cap=1** + **2p/1r** ⇒ **4** copies ⇒ **3** nodes often still Yellow). |
| **Post-fix verification (D3)** | After remediation, suggest re-check: `GET /_cluster/health`, `GET /_cat/shards/{index}?v` (and `allocation/explain` if any shard still unassigned). |
| **Ruling out disk / node / CPU** | Prefer: “**In this report’s metrics window and collected evidence**, disk / node loss / CPU are **not** the dominant driver” — not an absolute “unrelated everywhere” claim (other clusters or later windows may differ). |
| **ClusterStatus single voice** | If one paragraph cites **CMS `ClusterStatus` max = Yellow** (or Red) for **`{begin} ~ {end}`** and another cites **`GET /_cluster/health` = green** at a **single** probe time, **reconcile in one sentence**: e.g. **worst status in the monitoring window** vs **snapshot after recovery** vs **instantaneous engine API** — do not leave **Green** and **Yellow** side by side without **time / aggregation** qualifier (parallel sections should not contradict). |
| **CMS `ClusterShardCount` (or total-shard) swings** | If **CMS** shows **large step changes** in **total shard count** (e.g. **76 → 38 → 76**) within or across windows, **do not** imply **“half the shards were lost”** unless **`GET /_cat/shards`** / engine health **confirms** loss — **reconcile** with **Alibaba Cloud console** change / ops events, **metric definition** (scope: data nodes vs cluster, replication, aggregation lag), and **instance lifecycle**. Prefer wording such as **“pending cross-check with ops records and engine shard view”** when the drop is **not** explained by allocation state. |

### 6.2 Read-heavy CPU + search pool (optional checklist)

Optional lines when **query-driven** overload is present (e.g. `_tasks` shows `*search*` on a hot index with `match_all`-style bodies):

| Item | What to add |
|------|-------------|
| **CPU ↔ same workload** | One explicit sentence: **NodeCPU / `hot_threads` and `search` pool queue or `rejected` stem from the same concurrent search load** (name index + task shape when known). |
| **Shard counts / layout in prose** | Once **`GET {index}/_settings`** (and templates) and **`_cat/shards`** **confirm** counts and placement, **use those values consistently** in the report — they override assumptions from any other environment. Optionally one line on **provenance** (template, console, legacy index). |
| **Hot node vs skew + `rejected`** | Summarize the overloaded side as a **hot node** when **`rejected` / heap / GC** align there. Cite **primary/replica skew** as **one factor** in **local** work and pressure, **plus** **parallel** read-path explanations (coordinator / single client path / `preference=_primary` / routing) — not “primaries necessarily answer most default searches.” See [sop-query-thread-pool.md](sop-query-thread-pool.md) §2. |
| **CMS vs thread_pool time alignment** | State whether **CMS CPU** overlaps the **search queue / reject** episode — including **CPU no longer high** while **`rejected` is cumulative** and **`queue` already zero** (post-spike phenomenology). |
| **CMS CPU metric hygiene** | If CMS **NodeCPU** looks modest vs strong **`search.rejected`**, add **one reconciliation block**: burst **early in window** vs CMS **whole-window** stat; metric **name + `Dimensions`** (this instance’s **data nodes**, not wrong rollup); optional **`_nodes/stats/os`** vs sample period. See [sop-cpu-load.md](sop-cpu-load.md) decision-tree notes. |
| **Per-node CPU % vs search “hot” node** | If a **per-node CPU table** (e.g. **5-minute mean** or **window aggregate**) shows **lower** CPU on the node that **logs / `thread_pool.search` / `EsRejectedExecutionException`** identify as the **search hotspot**, add **one sentence** so readers are not stuck: **spike moment ≠ coarse mean**; **CMS bucket / dimension** may not align with **sub-minute** pool saturation; **engine or INSTANCELOG lines** anchor **which node** ran the saturated **`search` pool** — the table is **imbalance context**, not a disproof of pool rejections on that node. |
| **Shard placement phrasing** | Use **consistent** qualifiers — **all** vs **N / N** vs **almost all** — title and tables must match; do not imply exceptions without a shard row to cite. |
| **Short / ambiguous index names** | For generic names (e.g. **`stats`**), add **purpose** (built-in / monitoring vs business-owned) or **full index pattern** so readers do not conflate unrelated indices. |
| **`rejected` counter** | Call out **cumulative since process start** (unless you show a **delta**); do not imply the full counter equals rejects “only in the report window.” |
| **`hot_threads` / logs** | Say whether **`hot_threads` ran successfully** vs **timeout / empty** after spike; for OpenAPI logs, **success vs failure** (e.g. metrics API unavailable). Treat failures as **evidence gaps**, not silent omissions. |
| **Slow-log node vs search-pool node in other logs** | **SEARCHSLOW** / **fetch**-phase lines may name **one data node** while **INSTANCELOG** / **thread_pool** lines at **another minute** name a **different node** as **`search` saturated** — both can be **true**: **query routing**, **primary/replica**, **coordinator vs data role**, and **time skew**. Add **one sentence**: each line reflects **that phase / time / shard copy**; ground **routing** with **`GET /_cat/shards/{index}`** (and **which shard** the slow query hit) so the report does **not** read as **self-contradictory**. |
| **Wording** | Prefer **co-occurring signals** over a strict single-arrow causal chain unless ordering is evidenced. |
| **P0 / P1 band** | Match the **strongest fired rule** in the window (often **P0** CPU and/or **P0** `ThreadPool.Search*` per [health-events-catalog.md](health-events-catalog.md)); avoid a **P1-only** headline when **P0** rules already fired. |

### 6.3 JVM / fielddata / circuit breakers (optional checklist)

Use when **heap**, **GC**, **breaker**, or **fielddata** signals appear — cluster may still be **Green**.

| Item | What to add |
|------|-------------|
| **`_cluster/settings` first-class** | **`GET _cluster/settings?include_defaults=true`** — read **transient** and **persistent** for **`indices.breaker.fielddata.limit`**, **`indices.breaker.request.limit`**, and related keys; they are often changed **together**. |
| **Headline vs Old GC** | If settings show **very low breaker limits** and/or **`_nodes/stats/breaker`** shows **`tripped` > 0** / logs show **`CircuitBreakingException`**, lead with **breaker + settings + query/mapping** — **Old GC rate** as **parallel** or **secondary**, not the only story. See [sop-memory-gc.md](sop-memory-gc.md) §5. |
| **`tripped` vs P2-only wording** | Low **`fielddata.limit`** without trips is **config risk**; **`tripped` > 0** or matching exceptions → **incident-grade** narrative (usually alongside **P0**-class breaker handling in the catalog). |
| **Index-level closure** | Name **indices** and **mapping** culprits (`text` + **`fielddata`**, large **`terms` / `cardinality`**, deep paging) when engine evidence exists. |
| **Heap skew across nodes** | Correlate uneven **heap** with **`_nodes/stats/breaker`**, **`_nodes/stats/indices/fielddata`**, **`_cat/shards`** — not **only** shard counts. |

### 6.4 Write-path saturation + CPU + JVM (optional checklist)

Use when **ingest / bulk**, **`ThreadPool.WriteRejected`**, **CPU peaks**, and/or **Old GC / heap** signals **co-occur** — for example **sustained high-QPS bulk** indexing that stresses the **write** pool.

**Write-queue / bulk prompts (rubric alignment):** Graders often treat **`ThreadPool.WriteRejected`** + **`_nodes/stats/thread_pool`** as the **primary** storyline. A conclusion that **only** headlines **Old GC / heap** while relegating **write-pool saturation** to “P1 / participating factor” can read as a **JVM/GC report**, not a **write-capacity** diagnosis. Prefer one of:

- **Dual P0 (parallel):** **Opening** treats **quantified write-pool stress** (**`write` `rejected`** **and** **`completed`**, or **reject share** per node or cluster) **and** **Old GC wall-clock / `GCTimeRatioTooHigh`** as **co-equal** P0-class signals (see [health-events-catalog.md](health-events-catalog.md) **`ThreadPool.WriteRejected`** / **`HealthCheck.ThreadPoolSaturation`**).
- **Causal chain (upstream first):** **First sentence** states **bulk / ingest saturates the `write` pool** → **merges / heap** → **Old GC + CPU** — so **`write.rejected`** is in the **lead**, not buried below a GC headline.

Add **at least one line of numbers**: e.g. **`rejected` / `completed`** on the **busiest node(s)**, optional **reject share** (approximately `rejected / (rejected + completed)`) for the same pool, and **rule / event names** when citing CMS (e.g. **`ThreadPool.WriteRejected`**).

Align structured reports with **[health-events-catalog.md](health-events-catalog.md)**: CMS **P0** for write rejects usually requires **sustained reject rate + traffic**, not cumulative counters alone — **human-written** reports should still **quote cumulative `rejected`/`completed` with context** so the **data-plane** story is concrete.

**Engine snapshot (`check_es_instance_health.py`):** **`rejected` > 0** is emitted as **P1** when **`JVMMemory.GCTimeRatioTooHigh`** is **not** in the same finding set. When **`GCTimeRatioTooHigh` (P0)** **does** fire, the script **promotes `ThreadPool.WriteRejected` from P1 → P0** so severity bands match a **dual-P0** or **causal-chain** narrative — see table below. **Co-occurrence is not proof of causation**; use **`hot_threads`** / **`_tasks`** to confirm an **ingest-heavy** path before asserting **write overload → GC** as the only story.

| Item | What to add |
|------|-------------|
| **Headline priority (dual P0)** | When **write-path evidence** and **`JVMMemory.GCTimeRatioTooHigh` / Old GC** are **both** material, prefer **two P0 headlines** (or **one causal chain**, not JVM-only): e.g. **write pool saturation / rejects** **and** **Old GC wall-clock share** — not “GC only.” Optional chain: **write overload → merge / heap → Old GC → CPU spikes** (only if evidence supports ordering). |
| **GC collector wording** | Do **not** assume **G1** vs **CMS** (or other) from ES/JDK version alone. Prefer **“old-generation / Old GC”** or cite **`GET _nodes/stats/jvm`** (`gc.collectors.*`) / node GC logs — avoids technical challenges from a wrong collector name. |
| **Script vs narrative** | If the checker still prints **WriteRejected as P1** (no `GCTimeRatioTooHigh` in the window) but CMS/catalog would grade **P0**, say so in one line — **do not** silently downgrade the user-facing conclusion. |
| **`rejected` + `completed` + `queue` / `active`** | Include **`completed`** (same pool, per node or total) next to **`rejected`** to size **reject share**; state **cumulative since node start** for **`rejected`** / **`completed`**; add **current** `queue` / `active` so readers do not confuse **history** with **ongoing** overload. |
| **Per-node skew** | When **`rejections_by_node`** is uneven, tie to **hot shards / routing / transient skew** — same direction as **CPU imbalance** checks. |
| **Shard count vs `write.rejected` skew** | If **shards per data node** are **even** (e.g. similar counts from **`_cat/shards`** / routing) but **`write.rejected`** is **much higher on one node**, state explicitly: imbalance is **unlikely** from **shard count alone** — favor **hot shards / routing / client targets**; cite **numbers** for both **shards/node** and **per-node `rejected`** when available. |
| **Parent breaker `tripped`** | **`tripped`** is **cumulative** (breaker semantics: trips **since JVM start**). A **non-zero** **`parent.tripped`** (e.g. **183**) is **aligned with historical peaks** / past pressure and need **not** contradict **current** `_cat/nodes` heap **~50%** — add **half a sentence** that **`tripped` reflects cumulative history**, not instantaneous heap %. Relate to **historical** heap pressure alongside **`rejected`**; reconcile with **current** heap **in one sentence**. |
| **Bulk / client guidance** | Under **reject / capacity-tight** conditions, prefer: **lower parallel bulk streams**, **smaller per-request bytes/doc count**, **backoff / fewer in-flight bulks**; align total throughput to SLO. If mentioning **larger batches**, **immediately** caveat **timeouts / memory spikes / OOM** — avoid implying “bigger single requests” as the fix. See [sop-write-performance.md](sop-write-performance.md) §2 (*bulk QPS → write pool*). |

### 6.5 Read-heavy scenarios (search pool vs GC-only headline)

Use when the **incident** is **query-driven** (high concurrent search, terms / QPS patterns, “search reject → cascade” timelines). **Section 6.4** already guards **write-path** vs **GC-only** headlines; **section 6.2** covers **search pool + CPU** alignment — this subsection fixes the **remaining gap**: **Old GC / CPU as the only lead** when **`search` pool saturation** is the **primary** plausible storyline. **Long-form narrative, Chinese templates, and evidence closure:** [sop-query-thread-pool.md](sop-query-thread-pool.md) **Report narrative: search pool vs GC / CPU headlines** (keep this section as a **short rubric**; avoid duplicating those paragraphs here).

**Search-pool-primary vs write (both pools have cumulative `rejected`):** For **query-saturation** cases where the catalog targets **`ThreadPool.SearchRejected`** and **`_nodes/stats/thread_pool`** shows **`search.rejected` ≫ `write.rejected`** on the same data nodes, the **executive lead** and **first P0 bullets** must **not** read like a **write-primary** report with search as a footnote — put **`search` pool / query concurrency** **first** (or **before** write in the same band). **`write.rejected`** may remain **P0/P1** as **parallel** or **secondary** (bulk, catch-up, historical ingest); **say so explicitly** so readers do not infer “mainly an ingest/write incident.” Tie the **search** lead to **high concurrent query / terms / slow query** and **hot index name** when verified.

| Item | What to add |
|------|-------------|
| **Headline order** | Do **not** make **“Old GC (P0) + CPU spike (P1)”** the **sole** executive story when **`ThreadPool.SearchRejected`** / **`search` pool capacity** is still plausible — treat **query concurrency > `search` pool** as **first or co-equal**; **GC/CPU** as **co-stress, cascade, or second wave** unless engine evidence proves otherwise. **Parallel to §6.4:** **dual P0** (search capacity + Old GC) or **causal chain** with **`search.rejected` / queue in the first sentence** when the prompt is read-heavy — mirror [sop-write-performance.md](sop-write-performance.md) §2 ordering, swap **`write` → `search`**. |
| **P0 / executive order vs `search` ≫ `write` (cumulative)** | If **`search.rejected` ≫ `write.rejected`** per node (or cluster totals) and **`ThreadPool.SearchRejected`** applies, **do not** place **`ThreadPool.WriteRejected`** **above** search in the **opening summary** or **first P0 line** unless **time-resolved** evidence shows **write** dominated the window. **Script print order** (e.g. checker listing write before search) is **not** narrative order — override for human-facing text when data-plane magnitudes and scenario type say **search-first**. |
| **Quantification** | Same spirit as **§6.4**: cite **`search.rejected`** with **`search.completed`** (optional reject share, cumulative semantics) when stating capacity — not only “queue was high.” |
| **Rules + summary** | If **both** **GC P0-class** and **`ThreadPool.SearchRejected`** (or catalog equivalent) appear in the **same window**, **list both** in the opening summary — do not imply **only GC** is P0. |
| **Engine API incomplete** | Use the **self-limiting** templates in [sop-query-thread-pool.md](sop-query-thread-pool.md) (**Report narrative: search pool vs GC / CPU headlines**): state **`GET /_nodes/stats/thread_pool` (`search`)** as **pending verification** when timeouts prevented collection. |
| **Customer-facing wording** | Prefer **“引擎层必查清单（SKILL 文档第 5 节）”** over **§**-prefixed section labels in external deliverables. |

### 6.6 Timeline vs severity (recency-ordered narrative)

Use when **multiple** of: **`ThreadPool.WriteRejected`**, **`ThreadPool.SearchRejected`**, **GC / heap / CPU** appear together. **Severity bands (P0/P1)** are **not** a substitute for **when** each path stressed the cluster inside `{begin} ~ {end}`.

| Item | What to add |
|------|-------------|
| **Section present** | An **`### Incident timeline (recency-ordered)`** (or equivalent) with **time-ordered** or **“latter-window emphasis”** bullets — unless the report is explicitly minimal **and** recency cannot be distinguished (then one **uncertainty** line). |
| **No false recency from counters** | **`search.rejected` / `write.rejected`** are **cumulative since node start** — do **not** say “write happened first” from **counter magnitude alone**; use **CMS series**, **slow logs**, or **paired deltas** on `rejected`/`completed`. |
| **CMS peaks** | Where available, cite **which metric** peaked **when** (e.g. CPU vs GC duration vs pool-related CMS names) relative to **window start vs end**. |
| **Executive order** | **Whichever path peaked or persisted closer to window end** should **lead** the **opening summary** (recency-weighted): e.g. if **search-path** pressure is **more recent** than **write-path**, **lead** with **search / query concurrency** (and co-stress) **as appropriate**; if **write-path** is **more recent**, **lead** with **write / bulk**. Same **time-over-magnitude** rule as **§6.5** row **P0 / executive order vs `search` ≫ `write`** (override when **time-resolved** evidence shows the **other** path dominated). Do **not** drop **P0** findings for the **other** path from **Findings (by priority)**. |
| **Script print order** | **`check_es_instance_health.py` listing order** is **not** proof of temporal order — override for narrative when **time-resolved** evidence supports it. |

---

## 7. Common mistakes

| Issue | Bad example | Correct approach |
|-------|-------------|------------------|
| Hard-coded secrets | AK/SK/password in command line | CLI profile + environment variables |
| Wrong scheme | `http://` vs `https://` mismatch | Match the instance endpoint |
| Unconfirmed params | Guessing region / instance id | Confirm with the user first |
| Skipping RAM | Ignoring permission errors | Validate RAM Actions first |
| P0 order = time order | Listing write-path P0 before search P1 because “P0 first” when CMS shows **search stress later** in the window | Add **Incident timeline**; **lead** the executive summary with **recency-weighted** impact; keep full **Findings by priority** |
