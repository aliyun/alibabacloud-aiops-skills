# Memory Domain: Quick Triage and SysOM Deep Diagnosis (Agent Addendum)

This page does **not** repeat the capability overview table in [SKILL.md](../SKILL.md). It only summarizes **memory-related commands** and **what to read next**.

## Which Entry to Use

**Principle**: first match whether the user intent maps to a specific diagnosis item (top rows in the table). If intent is unclear, use the fallback **`memory classify`**.

| Intent | Recommended command |
|------|------|
| High memory usage; need full-machine/app memory panorama and breakdown; suspected **high TCP memory / socket queue backlog**; or user reports **latency/stalls** and `ss` shows high Send-Q/Recv-Q | `./scripts/osops.sh memory memgraph` |
| Explicit suspicion of OOM / need oom-killer kernel clues | `./scripts/osops.sh memory oom` |
| Explicit Java memory / JVM issue | `./scripts/osops.sh memory javamem` |
| Weak Go signals or language-level details needed (non-Java) | `./scripts/osops.sh memory memgraph` (panorama); use `javamem` once Java is confirmed |
| Unknown symptom, requires integrated classification (meminfo + OOM clues + RSS) | `./scripts/osops.sh memory classify` |

From each command stdout envelope, focus on **`agent.next`** (often a single deep-diagnosis command if environment is ready; otherwise may include precheck steps), **`agent.findings`** (key metrics), and **`data.routing`** / **`data.local`**.  
For routes to **oomcheck**, also see "Agent Operating Conventions" in [oomcheck.md](./diagnoses/oomcheck.md). The **`data`** section does not carry `next_steps`; **`--verbose-envelope`** only expands **`agent.summary`**.

## Optional: One-Step Deep Diagnosis

Add **`--deep-diagnosis`** on **`memory memgraph` / `oom` / `javamem` / `classify`** (plus options such as `--region`, `--instance`, **`--params` / `--params-file`** as documented in [invoke-diagnosis.md](./invoke-diagnosis.md)) to trigger deep diagnosis.

For **`memory oom`**, you can also pass **`--oom-time`**, which is written to oomcheck `time`.

When `--deep-diagnosis` is used, remote diagnosis is primary and merged results appear under **`data.remote`**.

Do **not** include `--region` / `--instance` for **current-instance** diagnosis examples. Include them only when diagnosing **another ECS instance** and the user has provided both values.

The remote path includes the same environment checks as precheck. You can also run **`./scripts/osops.sh precheck`** independently for self-check or troubleshooting.

## Diagnosis Params and Contract

For each `service_name` `params` and boundaries, read only the corresponding file under [diagnoses/](./diagnoses/).  
For request-body and metadata completion details, see [invoke-diagnosis.md](./invoke-diagnosis.md).
