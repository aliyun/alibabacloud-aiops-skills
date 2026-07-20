# Execution Order & State Machine

> Defines the invocation order, dependencies, state transitions, AskUser checkpoints, and failure handling for ECS Cloud Assistant deploy operations.
> All invocations go through `cadt-deploy-on-aliyun -run <Op> '<JSON>'`; parameters are authoritative as per `cadt-deploy-on-aliyun -d <Op>`.
> **Parameters must be a single JSON object** (e.g., `'{"regionId":"cn-hangzhou","instanceId":"i-xxx"}'`). Flag-style (`--regionId cn-hangzhou`) is NOT supported and causes `VALIDATION_FAILED`.

## State Machine

```
[S0] Initial
  └── Collect from user: regionId, instanceIds, appName
         ↓
[S1] cadt-deploy-on-aliyun -run EcsGetDesc '{"regionId":"cn-hangzhou","instanceId":"i-xxx"}'
     or cadt-deploy-on-aliyun -run EcsGetDescList '{"regionId":"cn-hangzhou","instanceIds":["i-xxx","i-yyy"]}'
     → Verify all instances are in Running state
     → ❌ If any instance is not Running: abort, report status to user
         ↓
[S2] Build Application Package (Local build)
     1. Build locally (mvn/gradle/pip/npm/go build)
     2. Script injection (start.sh/stop.sh) + repackage tar.gz
     3. InstallApplication with filePath (auto-upload + deploy)
     → returns invokeId
         ↓
[ASK-1] Present to user: artifactUrl + instanceIds + appName → confirm deployment
         ↓
[S3] cadt-deploy-on-aliyun -run InstallApplication '{"regionId":"cn-hangzhou","instanceIds":["i-xxx"],"appName":"my-app","artifactUrl":"oss://bucket/app-v1.zip"}'
     → Returns invokeId → internal Cloud Assistant polling (~10min)
     → ❌ On failure: return invokeId + instanceResults, user checks Cloud Assistant logs
         ↓
[S3.5] wait_ready (V14) — MANDATORY, see [step-3] §3.2
       T0~T60s: hard wait (no probes)
       T60s: first probe + initial log snapshot
       T60s~T5min: probe at 5s intervals until HTTP 200
       → HTTP 200 hit: proceed to S4
       → T5min timeout: mark FAILURE:not-ready → enter [step-3] §3.3 root cause classification
       ⚠️ Skipping this state is a critical violation — do NOT jump directly to S4 or S4.5
         ↓
[S4] cadt-deploy-on-aliyun -run EcsGetDesc '{"regionId":"cn-hangzhou","instanceId":"i-xxx"}'
     → Get public IP of deployed instance(s)
         ↓
[S4.5] Post-Deploy Verification (V18) — see [step-3] §3.2.1
       cadt-deploy-on-aliyun -run EcsRunCommandSync '{"regionId":"...","instanceIds":["i-xxx"],"command":"..."}'
       → Composite check: V-PORT (port listening) + V-PROC (process alive) + V-HEALTH (health endpoint)
       → Log scan: V-LOG (fatal/exception keyword scan)
       → ❌ Any layer fails: route to [step-3]-post root cause classification (F27)
           ↓
[S5] Complete — Assemble endpoint URL: http://<PublicIP>:<port>
```

## Dependency Matrix

| Operation | Prerequisites |
|-----------|---------------|
| EcsGetDesc / EcsGetDescList | None — valid regionId and instanceId(s) required |
| InstallApplication | Instances are Running; filePath provided; appName provided |
| S3.5 wait_ready (V14) | InstallApplication -poll returned SUCCESS; MANDATORY before V18 |
| V18 Post-Deploy Verification | InstallApplication SUCCESS; **S3.5 wait_ready HTTP 200 passed (mandatory)**; listenerPort known |

## AskUser Hard Checkpoints

| Checkpoint | Trigger | What to present to user |
|------------|---------|-------------------------|
| ASK-1 | Before InstallApplication | artifactUrl + instanceIds + appName |

> Checkpoints are enforced by the main Skill; the `cadt-deploy-on-aliyun` package itself is unaware of business checkpoints.

## Failure Handling

| Scenario | Action |
|----------|--------|
| Op returns FAILURE | Pass through Message + operationId/invokeId, **do not auto-retry** |
| RAM permission error | Report exact Managed Policy name, stop |
| EcsGetDesc / EcsGetDescList fails | Report instance status, abort if not Running |
| InstallApplication fails | Return invokeId + instanceResults; user checks Cloud Assistant logs |
| Timeout | Preserve invokeId; use `cadt-deploy-on-aliyun -poll` for follow-up queries |
| wait_ready (V14) skipped | **Critical violation** — MUST re-run §3.2 probing cycle before V18 |
| wait_ready (V14) timeout | Mark FAILURE:not-ready → enter [step-3] §3.3 root cause classification |
| V18 verification fails | Route failed layer to root cause classification (F27); do NOT proceed to endpoint assembly |
