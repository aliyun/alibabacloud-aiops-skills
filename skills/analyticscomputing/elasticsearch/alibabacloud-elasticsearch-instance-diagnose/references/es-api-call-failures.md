# Elasticsearch REST API call failures (progressive guide)

Use this document **in order** when `curl` to the data plane fails or returns no useful JSON. For **when** engine APIs are mandatory vs optional, see [es-api-diagnosis-strategy.md](es-api-diagnosis-strategy.md) (sections 1–3: feasibility, necessity, MUST triggers).

**Security:** never print `ES_PASSWORD` or ask for it in chat — only [SKILL.md](../SKILL.md) section 2.2 patterns (local `export` in the same shell the agent uses).

---

## 0. Mandatory order (agents and operators)

Do **not** infer “this environment has no Elasticsearch credentials” from a lone **unauthenticated** `curl` (for example a probe that omits `-u`), even if the response is **401**. **401 without `Authorization` is expected** on secured clusters.

**Always run §1.1 first** in the **same shell** that will execute the diagnosis `curl` chain (for Cursor: the **integrated terminal** session the agent uses). Then:

| Step | Action |
|------|--------|
| 1 | §1.1 presence checks for `ES_ENDPOINT` / `ES_PASSWORD` (and `ES_USERNAME` if you use non-default). |
| 2 | If **both** `ES_ENDPOINT` and `ES_PASSWORD` are **SET** → run authenticated minimal APIs immediately (§1.3). Do not ask the user to export secrets until a **authenticated** attempt fails. |
| 3 | If **either** is **NOT SET** → blocking reason is **missing engine credentials in this shell**; point to [SKILL.md](../SKILL.md) §2.2 and have the user `export` in **that same terminal**, then re-run §1.1 → §1.3. |
| 4 | If authenticated calls return **401** → §1.2 (wrong user/password/realm or URL scheme). |
| 5 | If authenticated calls return **000** / refused / **28** → §2 (transport). |

This order matches **actual runs**: many failures are “agent skipped §1.1” or “wrong `http`/`https`,” not missing cloud APIs.

---

## 1. Preconditions — why the first answer might skip ES JSON

Engine `curl` needs **both**:

| Gate | Meaning |
|------|---------|
| **Executable** | `ES_ENDPOINT` + `ES_PASSWORD` set; TCP/TLS path to Elasticsearch works; authenticated calls return JSON. |
| **Necessary** | The question needs engine proof that CMS / OpenAPI cannot supply (see strategy doc). |

If **Executable** fails, the agent is **not** “forgetting” Elasticsearch: calls either were not possible (no env), were sent **without** auth and got **401**, used the **wrong** auth or **URL scheme**, or hit transport errors — so `_cluster/health`, `/_cluster/allocation/explain`, etc. do **not** yield business JSON.

### 1.1 Default habit (same shell as the agent)

Run **presence only** (never echo secrets):

```bash
[[ -n "$ES_ENDPOINT" ]] && echo "ES_ENDPOINT: SET" || echo "ES_ENDPOINT: NOT SET"
[[ -n "$ES_PASSWORD" ]] && echo "ES_PASSWORD: SET" || echo "ES_PASSWORD: NOT SET"
[[ -n "$ES_USERNAME" ]] && echo "ES_USERNAME: SET" || echo "ES_USERNAME: NOT SET"
```

Interpretation:

- **`ES_ENDPOINT` + `ES_PASSWORD` both SET** → proceed to **§1.3** immediately (minimal authenticated checks). Optional: print **only** the host/scheme for sanity (`echo "$ES_ENDPOINT"` is OK if it contains no secrets; do **not** echo password).
- **Either NOT SET** → state clearly: **this shell has no engine credentials**, not “Elasticsearch is unreachable.” Point to [SKILL.md](../SKILL.md) **section 2.2**; user `export` in the **integrated terminal** (same shell), then you **re-run §1.1 then §1.3** — do not treat an earlier unauthenticated 401 as proof that credentials are absent.

### 1.2 HTTP **401 Unauthorized** (after you know whether auth was sent)

Classify **401**:

| Situation | Meaning | What to do |
|-----------|---------|------------|
| **401** on a request **without** `-u` / `Authorization` | Normal for secured ES; **not** a credential verdict | Run §1.1; if vars SET, retry **with** auth (§1.3). |
| **401** on a request **with** `ES_USERNAME` / `ES_PASSWORD` (or `-u`) | Auth rejected | Fix **local env only**: password, username (often `elastic`), **`http://` vs `https://`** on `ES_ENDPOINT` (must match `DescribeInstance` `protocol` / actual listener), port, or trailing path typos. See [SKILL.md](../SKILL.md) §2.2. |

**Principle:** “We saw 401” is not actionable until the table above is satisfied.

### 1.3 Minimal authenticated checks (run as soon as §1.1 passes)

Use timeouts on every call (see [SKILL.md](../SKILL.md) §7). Normalize base URL once:

- If `ES_ENDPOINT` is `host:port` with no scheme, prepend **`http://`** or **`https://`** consistently with the cluster (Alibaba Cloud `DescribeInstance` reports `protocol` for the ES endpoint).
- Strip trailing `/` before appending paths.

Example pattern (do not log password):

```bash
BASE="${ES_ENDPOINT}"
case "$BASE" in
  http://*|https://*) ;;
  *) BASE="http://${BASE}" ;;
esac
BASE="${BASE%/}"
curl -sS --connect-timeout 10 --max-time 30 -u "${ES_USERNAME:-elastic}:${ES_PASSWORD}" "${BASE}/_cluster/health?pretty"
```

For **`https://`**, add **`--cacert /path/to/ca.pem`** (or **`-k`** for short, non-production tests) if the system trust store does not trust the cluster certificate. **Do not** switch from **`http://` to `https://`** as a blind fix for **`000`/timeout** when **`DescribeInstance` `protocol` is `HTTP`** — prefer allowlist / SG / path checks; see [SKILL.md](../SKILL.md) §2.2 (*If `http://` does not work — when to try `https://`* and *HTTPS — prerequisites*).

When **MUST** triggers require allocation evidence and the cluster is **Red**, prefer **targeted** explain after a quick shard listing — see **§1.4** (empty `explain` body can pick a **replica** while the business-critical failure is an **unassigned primary**).

### 1.4 `POST /_cluster/allocation/explain` — practical pitfall

`POST /_cluster/allocation/explain` with an **empty body** `{}` returns **one** explanatory shard, which may be a **replica** (`"primary" : false`). For **Red** clusters, the P0 signal is usually an **unassigned primary**.

**Runbook:**

1. `GET _cat/shards?v&h=index,shard,prirep,state,node,unassigned.reason&s=state` — find `UNASSIGNED` rows with **`p`** (primary).
2. `POST /_cluster/allocation/explain` with body, for example:

```json
{
  "index": "<index_from_cat>",
  "shard": 0,
  "primary": true
}
```

Then read `allocate_explanation`, `unassigned_info`, and `node_allocation_decisions[].deciders[]` (see [sop-cluster-health.md](sop-cluster-health.md)).

---

## 2. Transport and TLS outcomes (classify before blaming “network”)

| Pattern | Typical symptom | First direction | See also |
|---------|-----------------|-----------------|------|
| **Connection refused** | `curl` exit **7**, `Connection refused` | Process down, public access off, wrong port | [sop-cluster-health.md](sop-cluster-health.md) |
| **Persistent timeout** | exit **28**, **all** calls time out | **Context-dependent** — section 2.1 below | Allowlist + CMS triage |
| **Intermittent timeout** | **some** curls OK, **some** timeout | Often **overload** / meltdown | [sop-service-avalanche.md](sop-service-avalanche.md) |
| **Auth failure** | HTTP **401** **with** auth headers sent | Wrong/missing password, user, or scheme | §1.2 |
| **TLS mismatch** | e.g. `WRONG_VERSION_NUMBER` | `http://` vs `https://` on `ES_ENDPOINT` | Match **`DescribeInstance` `protocol`**: public **HTTP** listener → **`http://<publicDomain>:9200`**; **`https://`** on HTTP-only causes TLS errors. |

### 2.1 Persistent timeout (exit 28) — context-aware

> Do **not** equate exit 28 with “allowlist only.” Exit 28 means the TCP connection did not complete in time — triangulate with control plane + CMS.

Suggested order:

1. **Allowlist:** `DescribeInstance` `publicIpWhitelist` / `networkConfig.whiteIpGroupList` (`whiteIpType=PUBLIC_ES`) vs client egress IP.
2. **If allowlist looks OK but still timing out:**

| If… | Lean toward… | Action |
|-----|---------------|--------|
| CMS `NodeCPUUtilization` > **80%** or `NodeHeapMemoryUtilization` > **85%** | **Server overload** — ES too busy to finish TLS/TCP quickly | Treat as degradation; [sop-service-avalanche.md](sop-service-avalanche.md) |
| CMS OK, security group missing inbound **9200** | Security group | Open path from client |
| CMS OK, allowlist + SG OK | Path / middlebox | `telnet` / `nc` hop check |

**Principle:** exit 28 is a transport-timeout signal, not proof of a firewall drop. If CMS shows resource pressure, prefer **overload** before “pure network.”

### 2.2 Intermittent timeouts

When some `curl` calls succeed and others time out in the same session:

1. Do **not** label as “preconditions not met” if `ES_*` is set.  
2. **Must** cross-check CMS `NodeCPUUtilization`.  
3. If CPU > **80%**, treat as suspected meltdown — [sop-service-avalanche.md](sop-service-avalanche.md).  
4. Use successful responses as **partial** evidence; state coverage limits in the report.

**Principle:** flaky connectivity is itself a signal — often overload with a **live** process, not a simple misconfig.

### 2.3 Flaky API collection tactics

When the cluster is hot: longer `--connect-timeout` / `--max-time`, start with light APIs (`_cat/nodes`, `_cluster/health`), retry `_nodes/hot_threads` a few times — see [sop-service-avalanche.md](sop-service-avalanche.md) (intermittent timeout entry).

---

## 3. Evidence boundary (one screen)

- With **only** control plane + CMS, or with **no successful authenticated engine JSON**, you may still state **high-confidence** facts such as: CMS **`ClusterStatus` = Red ⇒ at least one primary shard is unassigned**.  
- You **cannot** uniquely pin **allocation-explain-class** causes (e.g. bad `routing.allocation.require._name`, exact decider text) **without** at least one **authenticated successful** `/_cluster/allocation/explain` targeting the relevant shard (or equivalent) — see **§1.4**.  
- Say explicitly: the gap is **missing authenticated data-plane evidence** or **wrong shard in explain output**, not “Elasticsearch cannot be diagnosed.”

---

## 4. Report checklist (when MUST data is missing)

Put at the **top** of the report:

1. **One line blocking reason** — only **after** §1.1: e.g. `ES_PASSWORD NOT SET in this shell`, **`401` with authenticated curl** (then scheme/user/password), **connection refused**, **persistent vs intermittent timeout** — **before** a long generic “evidence boundary” paragraph.  
2. Which **MUST** conditions fired (from CMS / script).  
3. Which engine evidence types **would** be collected after auth/path works (`allocation/explain` with **primary** shard if Red, `hot_threads`, …).  
4. Pointer to [SKILL.md](../SKILL.md) **section 2.2** only when §1.1 shows vars **not** set; if vars are set but calls fail, point to **§1.2 / §2** instead.

---

## 5. Related references

| Doc | Role |
|-----|------|
| [es-api-diagnosis-strategy.md](es-api-diagnosis-strategy.md) | MUST / SHOULD / executable vs necessary |
| [verification-method.md](verification-method.md) | `curl` examples and checklists |
| [acceptance-criteria.md](acceptance-criteria.md) | PASS / partial when engine checks blocked |
| [sop-service-avalanche.md](sop-service-avalanche.md) | CPU + intermittent timeouts + `all shards failed` |
| [sop-cluster-health.md](sop-cluster-health.md) | Real node loss vs cluster issues |
