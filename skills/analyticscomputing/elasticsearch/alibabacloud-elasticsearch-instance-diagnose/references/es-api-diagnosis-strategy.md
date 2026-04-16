# Elasticsearch REST API diagnosis strategy (MUST rules)

This note captures Q&A from skill usage: when `SKILL.md` says ES APIs are **MUST**, why some paths still rely on control plane + CMS only, and how skill text relates to tooling.

**When `curl` fails** (401, timeouts, refused): use the progressive guide [es-api-call-failures.md](es-api-call-failures.md) first, then return here for MUST / SHOULD rules.

**SKILL alignment:** MUST-trigger workflow (**reachability** including `ES_*` and endpoint match, then **required `curl` per fired row**) is **normative** in `SKILL.md` §5 (*Binding rule (MUST triggers)*), Step 2, and §7. The CMS tables in this file are supplementary; if workflow nuance differs, follow **`SKILL.md`** for agent execution.

---

## 1. Decision rules in the skill (evidence-driven)

Calling engine-layer `curl` (REST) needs **both**:

| Condition | Meaning |
|-----------|---------|
| **Executable** | `ES_ENDPOINT` and `ES_PASSWORD` are set, path to port `9200` works (scheme, allowlists, security group, etc.). |
| **Necessary** | Root-cause reasoning needs engine-layer proof that control plane / CMS cannot supply or refute. |

### Summary

- **MUST (run ES APIs)**  
  - Cluster Red/Yellow: unassigned shard reasons, allocation filters.  
  - Search/write performance: thread pools, rejections, hot threads, breakers, task backlog.  
  - Cases where control plane looks fine but the engine is not.

- **SHOULD (prefer ES APIs)**  
  - CPU/memory/load anomalies that disagree with control-plane signals — cross-check.  
  - Post-change incidents — confirm stuck recovery or long-running tasks on the engine.

- **CAN SKIP**  
  - Root cause is already closed on the control plane and engine data would not change the answer (e.g. clear RAM denial, instance in a controlled change window, billing/resource state making the instance unavailable).

---

## 2. MUST trigger signals (CMS)

**Treat as MUST when any of the following CMS signals appear:**

| CMS signal | MUST theme | Typical ES API evidence |
|------------|------------|-------------------------|
| `ClusterStatus` max ≥ 1 (Yellow) or ≥ 2 (Red) | Cluster health | `/_cluster/allocation/explain`, `/_cat/shards` |
| `ClusterDisconnectedNodeCount` max > 0 | Node loss | `/_cat/nodes`, `/_cluster/health` |
| `NodeCPUUtilization` max > 80% | CPU overload | `/_nodes/hot_threads`, `/_tasks` |
| `NodeHeapMemoryUtilization` max > 85% | Memory pressure | `/_nodes/stats/jvm`, `/_nodes/stats/breaker` |
| `NodeDiskUtilization` max > 85% | Disk pressure | `/_cat/allocation`, `/_cat/shards` |
| Thread pool `rejected` > 0 on any node | Performance | `/_nodes/hot_threads`, `/_nodes/stats/thread_pool` |
| CPU / memory / disk CV > 0.3 across nodes | Imbalance | `/_cat/shards`, `/_cat/allocation` |
| **Every diagnosis (ALWAYS)** | **Disk watermarks / index read-only** | `/_cluster/settings`, `/_all/_settings?filter_path=*.settings.index.blocks`, `/_cat/allocation` |
| Intermittent ES API timeouts + `NodeCPUUtilization` > 80% | Possible meltdown | `/_nodes/hot_threads`, `/_nodes/stats/thread_pool`, `/_tasks` |

**Mandatory hint:** If a MUST situation is detected and `ES_ENDPOINT` is **not** set, the report **must** start with a warning listing the missing engine-layer evidence.

---

## 2.5 ALWAYS checks (when ES is reachable)

**These do not wait on CMS thresholds; run whenever `ES_ENDPOINT` (and password) is available:**

| Check | ES API | What it catches | Why |
|-------|--------|-----------------|-----|
| Watermark settings | `GET _cluster/settings?include_defaults=true&filter_path=**.watermark` | Absolute-byte or bad % watermarks | CMS disk % can look fine while transient watermarks already force read-only |
| Index read-only blocks | `GET _all/_settings?filter_path=*.settings.index.blocks` | `read_only_allow_delete: true` | Cluster can be Green with “normal” disk % while indices are already read-only from flood_stage |
| Free space vs absolute watermark | `GET _cat/allocation?format=json&bytes=b` | Free bytes below absolute `flood_stage` | Only needed when watermarks use absolute bytes; % breach is compared to CMS in the script |

**Rationale (watermark edge case):** Low disk utilization and cluster Green can still coexist with transient absolute-byte watermarks that block writes. CMS-only views miss that class of misconfiguration.

---

## 3. Why sometimes only control plane + CMS?

**MUST addresses necessity:** in the situations above, methodology says you **should** use engine APIs for deep proof.

But the skill **also** states **executable** preconditions. If `ES_ENDPOINT` / `ES_PASSWORD` are missing, or TCP to `9200` fails, `curl` **cannot** run. Then you can only:

- Use `aliyun` CLI + CMS + logs;  
- State the **evidence boundary** in the report: no ES REST path — no engine-level root cause.

So: **not** “MUST can be skipped on purpose”, but **“MUST cannot run until preconditions hold.”**

---

## 3.5 Connection failures — differentiate patterns

> **Full playbooks** (credential probe, HTTP 401 meaning, exit 28 triage, intermittent timeouts, evidence boundary, report checklist): [es-api-call-failures.md](es-api-call-failures.md)

**Summary table** (read the linked doc for steps):

| Pattern | Typical symptom | First pointer |
|---------|-----------------|---------------|
| **Refused** | curl exit 7 | Process / port / public access — `sop-cluster-health.md` |
| **Persistent timeout** | exit 28, all calls | Allowlist + CMS triage — **not** “network only by default” |
| **Intermittent timeout** | mixed success | Overload / meltdown — `sop-service-avalanche.md` |
| **Auth failure** | HTTP 401 | `ES_PASSWORD` / `ES_USERNAME` / scheme |
| **TLS mismatch** | wrong version errors | `http://` vs `https://` on `ES_ENDPOINT` |

---

## 4. Documentation vs `check_es_instance_health.py` today

When `ES_ENDPOINT` and `ES_PASSWORD` are set, `_check_cluster_config_optional` **automatically** calls:

| Area | API | Role |
|------|-----|------|
| Liveness | `GET /_cluster/health` | Fail fast if ES is unreachable |
| Settings | `GET /_cluster/settings?include_defaults=true` | Fielddata breaker + disk **watermark** rules (incl. absolute-byte branch with `/_cat/allocation?format=json&bytes=b` when needed) |
| Replicas | `GET /_cat/indices?h=index,rep&format=json` | Business indices with `number_of_replicas=0` |
| Read-only | `GET /_all/_settings?filter_path=*.settings.index.blocks` | `read_only_allow_delete` blocks |
| Thread pools | `GET /_nodes/stats/thread_pool` | Non-zero `rejected` counters |

Finding **remediation** text may recommend `/_cluster/allocation/explain`, `/_cat/shards`, `/_nodes/hot_threads`, etc. Those are **operator / agent next steps** — the script does **not** HTTP-fetch **hot_threads** or **allocation/explain** bodies by itself. When rule findings imply a **§5 MUST** row, `check_es_instance_health.py` prints a short **§5 MUST — engine APIs** footer (deduped paths); the agent must still **execute** those calls after §2.2 reachability.

**Skill / agent workflow:** for Red/Yellow, thread-pool saturation, and other MUST rows in `SKILL.md`, the agent should still run the listed `curl` (or Console) steps to collect engine evidence beyond what the script auto-pulls.

### Planned vs implemented

Older drafts described stderr banners such as `[MUST采集] … auto allocation/explain`. **That auto-fetch is not in the current script** — allocation/explain and hot_threads bodies remain **manual MUST**. The script may print a **§5 MUST — engine APIs** footer (stdout) when findings map to `SKILL.md` §5; that is a checklist, not an HTTP substitute.

---

## 5. Summary

| Question | Answer |
|----------|--------|
| MUST scenarios — must ES APIs be used? | **Methodologically yes**, for evidence control plane/CMS cannot replace. |
| Why sometimes not? | Usually **executable** preconditions fail (no creds, no route, wrong endpoint). |
| What does the health script auto-call? | Health + cluster settings (breakers/watermarks) + zero-replica cat + read-only settings + thread-pool stats — **not** allocation/explain or hot_threads bodies. |
| Practical advice | When `9200` is reachable, set env vars; run additional MUST curls from `SKILL.md` / SOPs where the script stops at recommendations. |

---

## 6. Related references

- Main skill: `../SKILL.md` (workflow, credentials, direct ES access)
- **REST call failures (progressive):** [es-api-call-failures.md](es-api-call-failures.md)
- Cluster health SOP: `sop-cluster-health.md`
- Performance SOPs: `sop-write-performance.md`, `sop-query-thread-pool.md`
