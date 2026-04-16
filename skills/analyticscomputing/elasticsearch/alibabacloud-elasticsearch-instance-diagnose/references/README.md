# References (`references/`)

Operational knowledge for the **Alibaba Cloud Elasticsearch instance diagnosis** skill: APIs, verification, event catalog, acceptance rules, and scenario SOPs (`sop-*.md`).

**Discoverability:** skill **trigger keywords** (including **中文** for Chinese-speaking users) live in repo root **`SKILL.md`** frontmatter and **`metadata.yaml`** (`triggers`). Markdown here stays **English**; triggers bridge user language to the skill.

---

## Index

### APIs and access

| File | Purpose |
|------|---------|
| [related-apis.md](related-apis.md) | Related Alibaba Cloud OpenAPIs for diagnosis |
| [es-api-catalog.md](es-api-catalog.md) | Elasticsearch REST endpoints used in workflows |
| [ram-policies.md](ram-policies.md) | RAM policy snippets for CLI / OpenAPI |

### Verification, strategy, and quality bar

| File | Purpose |
|------|---------|
| [verification-method.md](verification-method.md) | How to verify diagnosis (metrics, logs, APIs) |
| [report-template.md](report-template.md) | Structured diagnosis report skeleton (Markdown) |
| [es-api-diagnosis-strategy.md](es-api-diagnosis-strategy.md) | When to call which ES API; CMS vs engine; MUST summary |
| [es-api-call-failures.md](es-api-call-failures.md) | **Progressive:** `curl` failures (401, timeouts, refused), evidence boundary, report checklist |
| [acceptance-criteria.md](acceptance-criteria.md) | PASS / PARTIAL / expectations; **§6.1** Red/Yellow + **ClusterStatus** one voice (CMS window vs engine snapshot) + **CMS `ClusterShardCount` swings** (cross-check engine + ops, avoid “half shards lost”); **§6.2** read-heavy CPU + search pool + CPU table vs log hotspot + **slow-log node vs search-pool node** (routing / phase / time); **§6.3** JVM / breakers / fielddata; **§6.4** write-queue narrative (dual P0 or causal lead + `rejected`/`completed` quant) / GC / bulk / `tripped` vs current heap; **§6.5** search vs GC headline; **`search.rejected` ≫ `write.rejected`** → search-first P0/executive order; **§6.6** timeline / recency-weighted executive lead (search vs write by time) |
| [health-events-catalog.md](health-events-catalog.md) | CMS-style events ↔ skill findings |

### Tooling

| File | Purpose |
|------|---------|
| [cli-installation-guide.md](cli-installation-guide.md) | Aliyun CLI install and configure |

### Scenario SOPs (`sop-*.md`)

| File | Typical signals |
|------|-----------------|
| [sop-activating-change-stuck.md](sop-activating-change-stuck.md) | Long `activating`, change records + engine Red |
| [sop-cluster-health.md](sop-cluster-health.md) | Red/Yellow, node loss, pending tasks, master election |
| [sop-configuration.md](sop-configuration.md) | Risky cluster/index settings, API error rate, slow recovery |
| [sop-cpu-load.md](sop-cpu-load.md) | Sustained or peak CPU, load imbalance |
| [sop-disk-storage.md](sop-disk-storage.md) | Disk watermarks, IO bottleneck, read-only / flood |
| [sop-memory-gc.md](sop-memory-gc.md) | Heap pressure, GC, circuit breakers, OOM |
| [sop-node-load-imbalance.md](sop-node-load-imbalance.md) | CPU / traffic / data skew (CV-style imbalance) |
| [sop-query-thread-pool.md](sop-query-thread-pool.md) | Search rejects, queue, slow queries |
| [sop-service-avalanche.md](sop-service-avalanche.md) | “Node down” but process up; `all shards failed` + high CPU |
| [sop-write-performance.md](sop-write-performance.md) | Write rejects, ingest latency, indexing dropped |

---

## For agents

1. Follow the workflow in the repo root **[`SKILL.md`](../SKILL.md)** (especially the signal → SOP routing table).
2. Prefer **`SKILL.md`** over ad-hoc reading order; open SOPs only when the observed signal matches.
3. Report text and evidence keys in **`scripts/check_es_instance_health.py`** are **English** — keep doc examples aligned (e.g. `cluster_status_latest`, `affected_nodes`, `configured_watermark_low`).

---

## Contributing

Edits to references should stay consistent with **`SKILL.md`** and the checker script’s field names. Prefer small, accurate updates over duplicating long procedures that already live in a SOP.
