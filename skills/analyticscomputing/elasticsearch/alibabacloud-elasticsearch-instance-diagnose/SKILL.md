---
name: alibabacloud-elasticsearch-instance-diagnose
description: |
  Alibaba Cloud Elasticsearch instance diagnosis skill. Use for cluster health checks, troubleshooting, and performance analysis on Elasticsearch instances.

  Triggers (English): Elasticsearch diagnosis, ES instance issues, slow search, write failures, cluster Red/Yellow, unassigned shards, node disconnected, load imbalance, thread pool 429, JVM/OOM/circuit breaker, disk watermark / read-only index, instance activating / change stuck, service avalanche / all shards failed.

  触发词（中文）: ES诊断、阿里云ES、Elasticsearch诊断、ES集群/实例故障排查、ES健康检查、集群红灯/变红/黄灯/变黄、集群异常、分片未分配、主分片未分配、节点掉线/离线、负载不均衡、搜索/查询变慢、慢查询、写入失败/变慢/拒绝、线程池打满、HTTP 429、内存过高、OOM、断路器、磁盘满/水位、索引只读、实例激活中/activating、变更卡住/未完成、雪崩、服务不可用、all shards failed。
---

# Alibaba Cloud Elasticsearch Instance Diagnosis

Collect signals from **Alibaba Cloud OpenAPI (control plane)** and the **Elasticsearch REST API (data plane)**, combine them with the SOP knowledge base under `references/`, and produce **root-cause analysis**, an **evidence chain**, **prioritized remediation guidance**, and—when multiple dimensions fire—a **recency-ordered incident timeline** (severity vs time in window; see **Timeline and recency (MUST)** in §5 Step 4).

**Architecture**: Alibaba Cloud Elasticsearch OpenAPI + Alibaba CloudMonitor (CMS) + Elasticsearch REST API + diagnostic SOPs

**Closure**: If MUST applies and `ES_*` is set, finish authenticated ES API evidence before the final report (see **Feasibility order** in §5).

---

## 1. Prerequisites

### 1.1 Aliyun CLI

> **Pre-check: Aliyun CLI >= 3.3.1 required** (for RAM permission checks and OpenAPI CLI fallback)
> Run `aliyun version` to verify the version is >= 3.3.1. If the CLI is missing or too old, see `references/cli-installation-guide.md`.
> After installation, run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation (**do not** pass plaintext AccessKey pairs on this command line; see §1.2).

### 1.2 Alibaba Cloud account authentication and security (MUST)

> **Security rules (mandatory):**
> - **NEVER** read, echo, or print AccessKey ID or AccessKey Secret values.
> - **NEVER** prompt or ask the user to paste plaintext AccessKeys in the conversation.
> - **NEVER** embed AccessKeys in scripts, CLI arguments, or `curl` URLs.
> - **NEVER** use `aliyun configure set` (or similar) to pass **literal** AccessKey ID/Secret on the command line.
> - **NEVER** accept AccessKeys that the user pastes into the chat, even if offered voluntarily.
> - **ONLY** use configured CLI profiles (`aliyun configure`) or environment variables such as `ALIBABA_CLOUD_ACCESS_KEY_ID` / `ALIBABA_CLOUD_ACCESS_KEY_SECRET` that the user has set **in their local shell** (the agent **must not** echo those values in the session).

> **⚠️ If the user provides AccessKeys in the chat (e.g. “my AK is xxx”)**
>
> 1. **Stop immediately**: do not run any Alibaba Cloud command that requires credentials.
> 2. **Decline politely** and give **only** the names of approved configuration methods (**do not** repeat any secret the user may have leaked):
>    - Recommended: run `aliyun configure` in a local terminal and enter credentials when prompted; credentials are stored in the local profile file.
>    - Alternatively: set `ALIBABA_CLOUD_ACCESS_KEY_ID` / `ALIBABA_CLOUD_ACCESS_KEY_SECRET` in the local shell (the user types values **only in the terminal**, not in chat).
> 3. Resume the diagnosis request only after credentials are configured correctly.

> **Verify credentials without exposing secrets:**
>
> ```bash
> aliyun configure list
> aliyun --profile <profile_name> sts get-caller-identity
> ```
>
> **Credential policy:**
> 1. Prefer an `aliyun configure` profile (default or `--profile`).
> 2. If there is no valid identity (`configure list` / `get-caller-identity` fails), **STOP** and guide the user to configure locally; **do not** guess or fabricate credentials.
> 3. Never pass plaintext AccessKeys through the conversation.

### 1.3 Elasticsearch direct-connect credential boundary

> - **NEVER** ask the user to paste `ES_PASSWORD` in chat; **NEVER** echo, print, or log the password; **NEVER** copy a password from chat into commands, hooks, or repo files.
> - Shell expansion for `curl -u "$ES_USERNAME:$ES_PASSWORD"` (or equivalent) is **allowed** when vars are **pre-exported in the user’s local shell**; **NEVER** put the secret as a literal in chat, scripts checked into repos, or command output.
> - If the user tries to send a password in chat: **STOP** as well and ask them to set `ES_PASSWORD` only locally via `export` (see §2.2).

---

## 2. Environment setup

### 2.1 Control plane OpenAPI (via Aliyun CLI)

All control-plane and CMS data collection for this skill uses the **Aliyun CLI**.

**User-Agent (required)**: set a User-Agent for Alibaba Cloud API calls:
```bash
export ALIBABA_CLOUD_USER_AGENT="AlibabaCloud-Agent-Skills"
```

**CLI hardening (recommended)**: when authoring raw `aliyun` commands, add **`--connect-timeout 3 --read-timeout 10`** (increase `read-timeout` for large responses or CMS), consistent with the instance-management skill examples, to avoid indefinite hangs on network faults. If the global User-Agent is not set, add **`--user-agent AlibabaCloud-Agent-Skills`** per invocation. For **optional Elasticsearch probes** inside `check_es_instance_health.py` (when `ES_*` is set), the same knobs exist as **`--connect-timeout`** / **`--read-timeout`** on that script — they map to `curl` for engine calls only, not to the Aliyun OpenAPI client.

Run before diagnosis:

```bash
aliyun version
aliyun configure list
aliyun --profile <profile_name> sts get-caller-identity
```

### 2.2 Elasticsearch API direct access (`curl`)

Have the user set connection variables in a **local terminal** after you confirm the Elasticsearch endpoint (VPC or public) and admin credentials—**do not** hardcode user-specific values in chat:

```bash
export ES_ENDPOINT="http://<elasticsearch-endpoint-ip>:9200"
export ES_USERNAME="elastic"
export ES_PASSWORD="<elasticsearch-admin-password>"
```

> **Public access and `http` vs `https`:** From **`DescribeInstance`**, use **`publicDomain`** / **`domain`** and the reported **`protocol`**. When **`protocol` is `HTTP`** (typical public listener), set **`ES_ENDPOINT` to `http://<publicDomain>:9200`**. Using **`https://`** against an **HTTP-only** endpoint causes **TLS** errors (e.g. **`WRONG_VERSION_NUMBER`**). Use **`https://`** only when **`protocol` is `HTTPS`** (or TLS is actually enabled on the port you use), and supply CA / fingerprint options as in **HTTPS options** below.
>
> **If `http://` “does not work” — when to try `https://`:** Treat **`DescribeInstance` `protocol`** as the **source of truth** for the **REST listener**. **`000`**, **timeouts**, or **connection refused** on **`http://`** usually mean **network path / allowlist / security group / wrong host or port** — **not** “try HTTPS next” when **`protocol` is still `HTTP`**. **Do** switch to **`https://`** when **`protocol` is `HTTPS`** (or the console / product doc states TLS on that endpoint) and the failure on `http://` is a **TLS or scheme** symptom (e.g. **`WRONG_VERSION_NUMBER`**, **`error:0A00010B`**, immediate SSL alert while probing with the wrong scheme). If **`protocol` is `HTTP`** and only **plain TCP** is advertised, **HTTPS is not a fallback** for reachability.

> **Credential safety**
> - **NEVER** echo, print, or log `ES_PASSWORD`; **NEVER** copy credentials from chat into shell history or saved files.
> - **NEVER** ask the user to paste the password in plaintext in chat.
> - **ONLY** use the following checks to verify that variables are set:
> ```bash
> [[ -n "$ES_ENDPOINT" ]] && echo "ES_ENDPOINT: $ES_ENDPOINT" || echo "ES_ENDPOINT: NOT SET"
> [[ -n "$ES_PASSWORD" ]] && echo "ES_PASSWORD: SET" || echo "ES_PASSWORD: NOT SET"
> ```

> **Network connectivity and access control**
>
> | Issue | How to check | Mitigation |
> |------|--------------|------------|
> | Public network access disabled | Elasticsearch console → **Network** | Enable public access or use the VPC endpoint |
> | Public access allowlist | Console → **Security** → **Public access allowlist** | Add the agent host’s public IP |
> | VPC isolation | e.g. `telnet <ES_IP> 9200` | VPC peering, Express Connect, or equivalent |
> | Security group | Inbound rules on the ECS/security group hosting Elasticsearch | Allow TCP **9200** (or the configured port) |

> **Connectivity probe**: `curl -sS -o /dev/null -w "%{http_code}" --connect-timeout 5 "${ES_ENDPOINT}"` — HTTP code `000` usually means the path is unreachable. **`401` without `-u` is normal** (auth required); if `ES_PASSWORD` is SET, proceed to **authenticated** `GET /_cluster/health` (§7). **`401` with `-u`** → wrong credentials. **`000` / refused / timeout** → network, allowlist, or TLS/scheme mismatch.

> **HTTPS — prerequisites (what must be true)**
> 1. **Listener:** The Elasticsearch HTTP port you call (**9200** unless changed) must actually speak **TLS** — align with **`DescribeInstance` `protocol`** (**`HTTPS`**) or console/network documentation.
> 2. **URL:** **`https://<host>:<port>`** with the same **host** (e.g. **`publicDomain`**) you would use for HTTP.
> 3. **Client trust of the server certificate:** Your client must trust the cluster’s certificate chain (cluster / cloud **CA PEM**, or corporate proxy CA if TLS is intercepted). **`curl`**: prefer **`curl --cacert /path/to/ca.crt ...`**; **`-k` / `--insecure`** only for **short, non-production** diagnosis.
> 4. **Auth:** Same **`ES_USERNAME` / `ES_PASSWORD`** as for HTTP (Basic auth over TLS).
>
> **HTTPS — how this skill documents it**
> - **Manual `curl` (§7 and [es-api-call-failures.md](references/es-api-call-failures.md)):** Add **`--cacert`** (or **`-k`** for testing) to every **`curl`** when using **`https://`** if the default trust store does not include your cluster CA.
> - **`check_es_instance_health.py` optional ES probes:** They invoke **`curl`** with **`-u`** only; they **do not** read **`ES_CA_CERTS`** / **`ES_SSL_FINGERPRINT`** / **`ES_VERIFY_CERTS`** (those names are common for **Python Elasticsearch** clients). For **HTTPS** instances, use **§7 `curl`** with **`--cacert`** for deep checks, or extend the script later to pass **`--cacert`** from an env var.
> - **Python-style env vars (reference for other tooling):** `ES_CA_CERTS`, `ES_SSL_FINGERPRINT`, `ES_VERIFY_CERTS=false` (testing only) — **not** wired into this repo’s optional **`curl`** path today.

---

## 3. RAM permission check

> **[MUST] RAM permission pre-check**
>
> Before running this skill, verify the principal has the required RAM permissions.
> See `references/ram-policies.md` for the full list.
> If the user reports insufficient permissions, direct them to attach the corresponding policies in the RAM console.

---

## 4. Parameter confirmation

> **IMPORTANT: Parameter confirmation**
> Confirm the following with the user **before** any command or API call.
> Do not assume undeclared defaults or hardcode user-specific parameters.

> **Boundary controls (MUST)**
> - **`region-id` and `instance-id` must not be guessed** or taken from unverified defaults; if they disagree with `DescribeInstance` or the user’s explicit statement, reconfirm.
> - **Do not** apply metrics, logs, or `DescribeInstance` conclusions from **instance A** to **instance B**; `ES_ENDPOINT` must match the instance under diagnosis (see **Pre-flight validation for Elasticsearch API** below).
> - This skill is **read-only diagnosis**: **do not** invoke mutating control-plane APIs (create, resize, restart, delete instance, etc.). If the user requests a change, provide recommendations only; execution belongs in the console or an approved change workflow.

| Parameter | Required | Description | Default |
|-----------|----------|-------------|---------|
| `instance-id` | Yes | Elasticsearch instance ID, e.g. `es-cn-xxxxx` | - |
| `region-id` | Yes | Region ID, e.g. `cn-hangzhou` | - |
| `profile` | No | Aliyun CLI profile (explicit `--profile` recommended) | `default` |
| `ES_ENDPOINT` | No | Elasticsearch endpoint (direct API access only) | - |
| `ES_PASSWORD` | No | Elasticsearch admin password (direct API access only) | - |
| `--window` | No | `check_es_instance_health.py`: analysis window in minutes (default **60**) | 60 |
| `--connect-timeout`, `--read-timeout` | No | `check_es_instance_health.py`: `curl` timeouts for optional **ES engine** probes when `ES_*` is set (`--connect-timeout` → `curl --connect-timeout`; **`--read-timeout`** contributes to **`curl -m`** together with connect). Defaults **5** / **10** seconds. | 5 / 10 |

---

## 5. End-to-end diagnostic workflow

### Agent hard rules (non-negotiable)

> **OpenAPI/CMS cannot replace MUST engine APIs.** For any **§5 MUST** table row or **`check_es_instance_health.py` rule-engine MUST**, Alibaba Cloud OpenAPI and CloudMonitor do **not** replace the listed Elasticsearch REST calls for engine-level root cause—when **feasibility** holds, run those `curl` endpoints (see §7); they are complementary layers, not interchangeable.
>
> **Feasibility is decided only by checks, not by assumption.** Whether the agent may call Elasticsearch **must** be determined by actually running the **Feasibility order** (§5): at minimum verify `ES_ENDPOINT` / `ES_PASSWORD` per §2.2, align `ES_ENDPOINT` with `DescribeInstance`, then authenticated `GET /_cluster/health`. **Do not** assume `ES_*` is unset or the path is unreachable without performing these steps in the session.

For Elasticsearch incidents, follow these **four steps**; each has a distinct role.

### Execution strategy (root-cause driven)

> Full policy: [es-api-diagnosis-strategy.md](references/es-api-diagnosis-strategy.md)

Data-plane `curl` collection requires **both**:

1. **Feasibility**: `ES_ENDPOINT` and `ES_PASSWORD` are set and the network path works.
2. **Necessity**: root-cause analysis needs data-plane evidence that the control plane or CMS cannot establish alone.

> For endpoints **listed** under a fired **MUST** table row **or** **rule-engine MUST**, **necessity** for those calls is **already satisfied** by the trigger—still require **feasibility** (**Feasibility order**). For **optional** engine `curl` **not** in those lists, apply **feasibility** and **necessity** per [es-api-diagnosis-strategy.md](references/es-api-diagnosis-strategy.md).

**MUST triggers** (if **any** CMS condition below holds, collect the listed Elasticsearch evidence):

| Trigger | Scenario | Required Elasticsearch evidence |
|---------|----------|----------------------------------|
| `ClusterStatus` max ≥ Yellow / Red | Cluster health | `allocation/explain`, `_cat/shards` |
| `NodeCPUUtilization` max > 80% | CPU overload | `_nodes/hot_threads`, `_tasks` |
| `NodeHeapMemoryUtilization` max > 85% | Memory pressure | `_nodes/stats/breaker`, `GET /_cluster/settings?include_defaults=true` ( **`indices.breaker.*`** in transient / persistent ) |
| Thread pool `rejected` > 0 | Performance | `_nodes/hot_threads`, `_nodes/stats/thread_pool` |
| Inter-node resource CV > 0.3 | Load imbalance | `_cat/shards`, `_cat/allocation` |
| Write failures or index read-only | Disk / watermark / blocks | `_cluster/settings`, `_all/_settings?filter_path=*.settings.index.blocks`, `_cat/allocation` |
| Intermittent Elasticsearch API timeouts + CMS CPU > 80% | Possible cascading failure | `_nodes/hot_threads`, `_nodes/stats/thread_pool`, `_tasks` |

> **Thread-pool row:** interpret **search** vs **write** / **bulk** using [sop-query-thread-pool.md](references/sop-query-thread-pool.md) vs [sop-write-performance.md](references/sop-write-performance.md) (see also **Write-path / bulk saturation** below).

> **Rule-engine MUST:** If `check_es_instance_health.py` prints a **§5 MUST / §5–§7** callout for this run, treat it like a row above—collect that listed ES evidence when feasibility holds.

> **Binding rule (MUST triggers):** If **any** MUST-trigger row **or** the **rule-engine MUST** line above applies, **necessity is satisfied** for that evidence set—OpenAPI/CMS cannot replace those calls for engine-level root cause (cluster-health: `allocation/explain` + `_cat/shards` for Yellow/Red). Confirm **feasibility** per **Feasibility order** below. If reachable with auth, **run the MUST-listed endpoints in Step 2** in parallel with control-plane collection. If still blocked **after authenticated** `GET /_cluster/health`, lead with **blocking reason**: unset `ES_*`; transport failure (`000`, refused, timeout); **401 with `-u`**; scheme/TLS mismatch—not **401 on an unauthenticated probe** when `ES_PASSWORD` is SET.

### Write-path / bulk saturation

> If **`ThreadPool.WriteRejected`** or **`write`** pool stress matches **high-QPS bulk** indexing, read and follow **`references/sop-write-performance.md` — §2**, subsection **“Evidence interpretation: bulk QPS → write pool”** for the evidence chain, **`rejected`** semantics (cumulative since node start), **report ordering vs Old GC / heap** (causal chain or dual P0 — write path before JVM-only headline), **per-node `rejected`/`completed` numbers** (reject share), per-node asymmetry, and write-only vs search. **Do not** lead with a JVM-only narrative when that subsection applies. For **write-queue–style** acceptance prompts, the **opening conclusion** should read as **write-capacity** (data-plane counters + optional CMS rule names), not **only** a GC/heap headline.

### Search-primary vs write (both pools show cumulative `rejected`)

> When **`_nodes/stats/thread_pool`** shows **`search.rejected` ≫ `write.rejected`** on the same node(s) and **`ThreadPool.SearchRejected`** / **query-driven** overload applies, **lead** the **executive summary** and **P0 ordering** with **`search`** (high concurrent query / terms / slow query; hot index when verified) — **not** **`write`** first. **`write.rejected`** may remain **P0/P1** as **parallel** or **secondary** (bulk, catch-up); **Old GC / CPU / node disconnect** stay **co-stress or cascade**. Checker **listing order** is not proof of narrative order — see [acceptance-criteria.md](references/acceptance-criteria.md) **§6.5** and [sop-query-thread-pool.md](references/sop-query-thread-pool.md) *Report narrative*.
>
> **Recency overrides this magnitude default** when **time-resolved** evidence exists: **do not** rank the opening story by **`search.rejected` vs `write.rejected` alone** — cumulative counters lack timestamps. Full rubric: [acceptance-criteria.md](references/acceptance-criteria.md) **§6.5** (*P0 / executive order vs `search` ≫ `write`*: **unless** write dominated **by time**) and **§6.6** (*Executive order*, *No false recency from counters*). **Binding:** **Timeline and recency (MUST)** below (same skill).

### `activating` / change workflow stuck (cross-layer root cause)

> When an instance stays in **`activating`**, a change is unfinished, and **Red** or unassigned shards coexist, follow **`references/sop-activating-change-stuck.md`** end-to-end (**MUST** includes `ListActionRecords`, `DescribeInstance` before/after remediation, collection order **section 3.1**, reporting **section 4**).

### Pre-flight validation for Elasticsearch API

> **[IMPORTANT] `ES_ENDPOINT` must match the diagnosed instance**
>
> Compare `publicDomain` / `domain` and **`protocol`** from `DescribeInstance` with `ES_ENDPOINT`.
> If they differ, warn: `⚠️ ES_ENDPOINT does not match the current instance; run export ES_ENDPOINT="http://{publicDomain}:9200"` when **`protocol` is `HTTP`**, or `https://…` only when **`protocol` is `HTTPS`** (adjust host/port to match the deployment).

### When Elasticsearch credentials are missing or connections fail

> **[CRITICAL]** Guide the user to fix connectivity explicitly; **classify** failure modes (do not default persistent timeouts to “allowlist only”). **Do not imply the agent “forgot” Elasticsearch** — if the first answer is CMS/OpenAPI-heavy, give the **blocking reason** per **Feasibility order** below: unset `ES_*`; transport errors; **401 with valid `-u`**; TLS/scheme—not **401** on a probe **without** `-u` when `ES_PASSWORD` is SET (use authenticated `curl` first).

**Progressive playbook (read in order):** [references/es-api-call-failures.md](references/es-api-call-failures.md) (sections **1 → 4**).  
**MUST / strategy context:** [references/es-api-diagnosis-strategy.md](references/es-api-diagnosis-strategy.md) (sections 1–3 and **3.5** summary table).

### Mandatory warning when MUST applies but Elasticsearch is not configured

> **[CRITICAL] If a MUST trigger fires but data-plane evidence is missing, put a warning at the top of the report:** follow **section 4** of [references/es-api-call-failures.md](references/es-api-call-failures.md) (blocking reason first, then MUST list, missing evidence; if `ES_*` unset, pointer to **section 2.2** of this SKILL; if vars are set, use es-api-call-failures **sections 1–2** for auth vs transport).

### Step 1: Quick health scan (initial signals)

Run the lightweight rules engine (17 metric rules) to list P0 / P1 / P2 findings and steer deeper collection:

```bash
python3 scripts/check_es_instance_health.py -i <InstanceId> -r <RegionId> [--window <minutes, default 60>] [--profile <profile_name>]
```

### Feasibility order (agent)

1. **Run** §2.2 `ES_*` checks (password = SET only)—**do not skip**; never infer feasibility without this step.  
2. `ES_ENDPOINT` matches `DescribeInstance` `domain` / `publicDomain` (scheme/port).  
3. **Authenticated** `GET /_cluster/health`—do not stop at **401** on an unauthenticated probe if `ES_PASSWORD` is SET.  
4. MUST scope: **table rows** and/or **rule-engine MUST** line in §5.

### Step 2: Collect evidence in parallel

Based on Step 1, run collection in parallel (prioritize dimensions with signals).  
If a **MUST-trigger** row **or rule-engine MUST** applies: run **Feasibility order**, then **run that Required Elasticsearch evidence** via `curl` in the **same** round (see §7). If **no** MUST applies, add optional data-plane `curl` only when **feasibility** and **necessity** both hold per the strategy doc.

Re-run **`check_es_instance_health.py`** with the same invocation pattern as Step 1; for this parallel round, **`--window 120`** and explicit **`--profile <profile_name>`** are common.

To backfill control-plane evidence (`DescribeInstance`, `ListSearchLog`, CMS-style calls), use **`aliyun`** patterns in [references/verification-method.md](references/verification-method.md) (epoch times, profiles, namespaces).

> Note: data-plane access still requires `ES_ENDPOINT` / `ES_PASSWORD`; the Aliyun CLI **cannot** replace `curl` to the cluster.
>
> For **MUST-trigger** rows, necessity for the **listed** endpoints is **already** established—do **not** skip them when feasibility including reachability holds. **Outside** those rows, avoid unrelated bulk `curl` solely because `ES_*` is set; use the strategy doc’s feasibility + necessity test instead.

### Step 3: Read SOPs by signal

Map signals to SOPs and read for deeper reasoning. With multiple signals, process **P0 → P1 → P2** for **severity**, then apply **Timeline and recency (MUST)** in Step 4 so the **narrative order** matches **when** signals mattered in the window—not only static rule-engine print order.

| Observed signal | Read |
|-----------------|------|
| Cluster Red/Yellow, node loss, pending tasks | `references/sop-cluster-health.md` |
| Long `activating`, unfinished change records, Red / unassigned shards | `references/sop-cluster-health.md` + `references/sop-activating-change-stuck.md` |
| High CPU, load, imbalance | `references/sop-cpu-load.md` |
| Per-node load imbalance (CPU/memory/disk/shard count) | `references/sop-node-load-imbalance.md` |
| JVM pressure, GC, circuit breaker, OOM | `references/sop-memory-gc.md` |
| Disk watermark, IO, write failures (read-only) | `references/sop-disk-storage.md` |
| Watermark misconfiguration, index blocks, “normal” disk % but write failures | `references/sop-disk-storage.md` (Section 3 — watermark misconfiguration) |
| Write timeouts / rejections / latency / QPS drop | `references/sop-write-performance.md` |
| Query timeouts / rejections / slow queries | `references/sop-query-thread-pool.md` |
| Nodes look down but CPU still reported; `all shards failed` | `references/sop-service-avalanche.md` |
| Intermittent Elasticsearch timeouts + CMS CPU > 80% | `references/sop-service-avalanche.md` |
| Risky settings, Ngram issues, API anomalies | `references/sop-configuration.md` |
| Event code definitions | `references/health-events-catalog.md` |

### Step 4: Synthesize and write the structured report

> **Acceptance-style optional checklists:** [references/acceptance-criteria.md](references/acceptance-criteria.md) **§6.1**–**§6.6** — Red/Yellow; read-heavy CPU + `search` pool (+ CMS alignment); JVM / breakers / fielddata; write-queue vs GC + **`rejected`/`completed`**; read-heavy **search pool vs GC-only** headline (expand in [sop-query-thread-pool.md](references/sop-query-thread-pool.md) *Report narrative: search pool vs GC / CPU headlines*); timeline/recency. **Bulk/write:** [references/sop-write-performance.md](references/sop-write-performance.md) §2. **Shard `reroute`:** [references/sop-node-load-imbalance.md](references/sop-node-load-imbalance.md) §1.3 (allocator / change control only).

> **[CRITICAL] Remediation must match the diagnosed root cause** — avoid generic templates. Wrong breaker or concurrency fixes (e.g. `in_flight_requests` vs `request`, “split query” when concurrency is the issue) → see **`sop-memory-gc.md`** and the fired signal’s SOP.

> **`activating` + data-plane anomaly**: include the **one-line cross-layer root cause**; see `references/sop-activating-change-stuck.md` **section 4**.

**Report skeleton (copy/fill):** [references/report-template.md](references/report-template.md).

### Timeline and recency (MUST for synthesized reports)

> **Problem:** `check_es_instance_health.py` and P0/P1/P2 bands express **severity**, not **when** a signal mattered most within the analysis window. **Cumulative** engine counters (`search.rejected`, `write.rejected`) do **not** encode recency—**write** and **search** issues can both be “real” while **only one path dominated the recent past** (e.g. search pressure **closer to window end** than write pressure).

**Binding rules for the agent:**

1. **Two axes** — Treat **severity** (P0/P1/P2) and **temporal relevance** (proximity to window end / “now”) as **orthogonal**. Do **not** infer recency from priority alone (e.g. “write is P0 so it must be the current headline”) when time-resolved evidence says otherwise.
2. **Mandatory human-facing section** — When more than one major finding fires (e.g. **write pool + search pool + GC/CPU**), the synthesized report **must** include an **`### Incident timeline (recency-ordered)`** (or equivalent) block **before or immediately after** the executive summary, unless the user explicitly asks for a minimal report. In that block:
   - Order **bullets or rows by time** (earlier → later), or state **which signal cluster peaked / persisted in the **latter** portion of `{begin} ~ {end}`**.
   - Call out **divergence**: e.g. “write-path stress **earlier** in window; search-path / CPU **more recent**” when CMS or logs support it.
3. **Evidence for recency** (use what exists; do not invent timestamps):
   - **CloudMonitor**: per-metric time series — note **peak timestamp** or **sustained-high interval** for `NodeCPUUtilization`, `NodeHeapMemoryUtilization`, GC-related metrics, `ThreadPool.*` **if** exposed as rates or non-cumulative series in the collected JSON.
   - **Slow logs / `ListSearchLog`**: correlate **query vs index** slow entries to minutes.
   - **Engine (optional):** two `_nodes/stats/thread_pool` samples at **known times** to show **delta** on `rejected` / `completed`; or **`_tasks`** / **`hot_threads`** for **current** skew vs historical cumulative counters.
4. **Executive summary ordering** — The **opening 2–4 sentences** should reflect **recency-weighted** user impact: if **search** pressure is **closer to current** than **write** pressure, **lead** with search/query concurrency and co-stress (GC/CPU) **as appropriate**, and place **historical write saturation** as **context** or **second wave**—**without** dropping P0 write findings if they remain valid for remediation backlog.
5. **Explicit uncertainty** — If only cumulative counters exist and **no** time series differentiates paths, state **one line**: recency is **undifferentiated**; recommend **narrower window**, **slow logs**, or **delta sampling** for the next run.

---

## 6. Data collection details (CLI OpenAPI + injected input)

### One-shot entry

Use the same **`check_es_instance_health.py`** command as **§5 Step 1** (optional **`--window`** / **`--profile`**; default window **60** minutes if omitted).

### Injected input mode (paired with CLI)

`check_es_instance_health.py` accepts external JSON to avoid duplicate calls:

```bash
python3 scripts/check_es_instance_health.py \
  -i <InstanceId> -r <RegionId> \
  --data-source input \
  --input-json-file /path/to/diag-input.json
```

Input JSON shape:

```json
{
  "status_info": {},
  "metrics": {},
  "events": [],
  "logs": []
}
```

`--data-source` modes:
- `auto`: prefer injected fields; backfill gaps via Aliyun CLI.
- `cli`: ignore injection; fetch everything via CLI.
- `input`: injection only; no OpenAPI calls.

### Manual control-plane CLI backfill

For additional OpenAPI examples, see `references/verification-method.md`.

---

## 7. Elasticsearch direct API access (data-plane deep dive)

When **feasibility** holds (including reachability), execute the REST calls **required by any MUST-trigger row** (§5). For endpoints **not** listed in a fired MUST row, call them only when **feasibility** and **necessity** both hold per the strategy doc.

> `ES_ENDPOINT` may be `host:port` or a full URL. For the samples below, normalize to `http://${ES_ENDPOINT#http://}` (use `https://` consistently when the cluster serves TLS).
>
> **Timeouts**: every `curl` must use `--connect-timeout 10 --max-time 30`.

### Red / Yellow (MUST) — recommended set

**Scope:** The cluster-health MUST row uses `ClusterStatus` max ≥ **Yellow** (includes **Red**). Use this set for **unassigned / misallocated shard** root cause on the engine.

```bash
curl -sS --connect-timeout 10 --max-time 30 -u "${ES_USERNAME:-elastic}:${ES_PASSWORD}" \
  "http://${ES_ENDPOINT#http://}/_cluster/health?pretty"

curl -sS --connect-timeout 10 --max-time 30 -u "${ES_USERNAME:-elastic}:${ES_PASSWORD}" \
  -H "Content-Type: application/json" \
  -X POST "http://${ES_ENDPOINT#http://}/_cluster/allocation/explain?pretty" \
  -d '{}'

curl -sS --connect-timeout 10 --max-time 30 -u "${ES_USERNAME:-elastic}:${ES_PASSWORD}" \
  "http://${ES_ENDPOINT#http://}/_cat/shards?v&h=index,shard,prirep,state,node,unassigned.reason&s=state"

curl -sS --connect-timeout 10 --max-time 30 -u "${ES_USERNAME:-elastic}:${ES_PASSWORD}" \
  "http://${ES_ENDPOINT#http://}/_cluster/pending_tasks?pretty"

curl -sS --connect-timeout 10 --max-time 30 -u "${ES_USERNAME:-elastic}:${ES_PASSWORD}" \
  "http://${ES_ENDPOINT#http://}/_nodes/stats/thread_pool?pretty"
```

### Query / write performance (MUST) — recommended set

> Include **`_cluster/settings`** when **heap / GC / breaker** rules fired in Step 1 or **`_nodes/stats/breaker`** shows concern — read **transient** and **persistent** `indices.breaker.*` / `network.breaker.*`.

```bash
curl -sS --connect-timeout 10 --max-time 30 -u "${ES_USERNAME:-elastic}:${ES_PASSWORD}" \
  "http://${ES_ENDPOINT#http://}/_nodes/hot_threads?threads=3"

curl -sS --connect-timeout 10 --max-time 30 -u "${ES_USERNAME:-elastic}:${ES_PASSWORD}" \
  "http://${ES_ENDPOINT#http://}/_nodes/stats/breaker?pretty"

curl -sS --connect-timeout 10 --max-time 30 -u "${ES_USERNAME:-elastic}:${ES_PASSWORD}" \
  "http://${ES_ENDPOINT#http://}/_cluster/settings?include_defaults=true&pretty"
```

> **`/_cluster/pending_tasks`** and **`GET /_nodes/stats/thread_pool`** are also listed under **Red / Yellow (MUST)** above—one call each per session when both sections apply. If you run **only** this performance block, add those two `curl` lines from that block.

### Resource anomalies without a closed loop (SHOULD) — recommended set

```bash
curl -sS --connect-timeout 10 --max-time 30 -u "${ES_USERNAME:-elastic}:${ES_PASSWORD}" \
  "http://${ES_ENDPOINT#http://}/_cat/nodes?v&s=cpu:desc&h=name,ip,cpu,heap.percent,ram.percent,load_1m"

curl -sS --connect-timeout 10 --max-time 30 -u "${ES_USERNAME:-elastic}:${ES_PASSWORD}" \
  "http://${ES_ENDPOINT#http://}/_nodes/stats/jvm?pretty"

curl -sS --connect-timeout 10 --max-time 30 -u "${ES_USERNAME:-elastic}:${ES_PASSWORD}" \
  "http://${ES_ENDPOINT#http://}/_cat/allocation?v&bytes=gb"
```

> **`GET /_cluster/settings?include_defaults=true`** also appears under **Query / write performance (MUST)** above—reuse one response when both blocks apply. If you run **only** this SHOULD block, add the same `curl` line from that block.

**Protocol sanity** (avoid `WRONG_VERSION_NUMBER`): usually **http/https scheme mismatch** on `ES_ENDPOINT` — fix scheme/port and retry.

**Scenario → endpoint** index: [references/es-api-catalog.md](references/es-api-catalog.md).

---

## 8. Diagnostic coverage

The knowledge base covers **48+** health-event-style rules and chained scenarios (e.g. disk pressure → allocation → Red). **Per-category counts, P0/P1/P2 mix, and event codes:** [references/health-events-catalog.md](references/health-events-catalog.md) — scenario runbooks: `references/sop-*.md` (index: [references/README.md](references/README.md)).

---

## 9. Best practices

**Read-only:** no mutating control-plane APIs; no teardown.

1. **Layered + evidence-bound**: scan → SOP depth; every conclusion cites metrics/logs/events; if ES is unreachable, state limits ([es-api-call-failures.md](references/es-api-call-failures.md)).
2. **Priority vs narrative**: **P0→P2** for urgency; **Incident timeline** when multiple dimensions differ in time (Step 4). **Credentials / TLS / parameters:** §1–2 and §4.
3. **Green is not “all clear”** — watermarks, blocks, mis-set limits still matter; **MUST + reachable ES:** do not skip §5/§7 evidence because the cluster is Green or OpenAPI “explains” symptoms.
4. **Thread-pool `rejected`:** **cumulative** unless you show a delta — [sop-query-thread-pool.md](references/sop-query-thread-pool.md) §1–2; write/bulk: [sop-write-performance.md](references/sop-write-performance.md) §2.

---

## 10. Reference links

- `references/verification-method.md` — Verification (how to validate diagnosis; metrics, APIs, workflows)
- `references/report-template.md` — Structured diagnosis report skeleton
- `references/README.md` — **Language map** (reference assets and `sop-*.md` runbooks; English in this repo)
- `references/ram-policies.md` — RAM policy list
- `references/acceptance-criteria.md` — Correct/incorrect patterns and acceptance (includes credential and safety anti-patterns)
- `references/cli-installation-guide.md` — Aliyun CLI installation
- `references/es-api-catalog.md` — Elasticsearch REST API catalog
- `references/health-events-catalog.md` — Health event catalog
- `references/sop-*.md` — Scenario SOPs (e.g. `sop-activating-change-stuck.md` for `activating` / change stuck, cross-layer root cause)
- `references/es-api-diagnosis-strategy.md` — Elasticsearch API diagnosis strategy
