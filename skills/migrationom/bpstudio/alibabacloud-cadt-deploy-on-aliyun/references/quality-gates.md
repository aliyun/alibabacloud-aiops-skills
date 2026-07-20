# Quality Gates (Pre-Check + Post-Verify)

> This document is the dual-gate full map for the deploy-to-aliyun main skill. Both ends of every write-type operation must have **precheck (fail-fast interception)** and **postverify (cloud truth reconciliation)**, ensuring silent errors don't propagate along the main flow.

## Design Principles

1. **Cloud as single source of truth** — postverify must pull ground truth from cloud APIs; don't trust in-memory or local cache (aligned with "data consistency" memory)
2. **fail-fast over best-effort** — don't pass on precision gaps; "let's try and see" is prohibited
3. **Gates must be machine-executable** — every precheck/postverify is written as a callable sub-process (bash function); don't rely on agent improvisation
4. **Gate failure has standard rollback path** — every failure clearly states "which checkpoint to roll back to + whether user intervention is needed"
5. **Side-effect list requires dual-write** — any ID produced by write operations must **simultaneously** be persisted to `collect-info.json` + `decisions.json`; single-write is treated as residual

## Full-Flow Dual-Gate Matrix

| Checkpoint | Write Operation | PRECHECK (Entry Condition) | POSTVERIFY (Completion Confirmation) | Failure Rollback To |
|---|---|---|---|---|
| `[4]` → `[4.5]` | `collect-info.json` assembly complete | **P1** JSON schema precheck (required fields non-empty) / **P2** placeholder regex scan (no `<ASK_*>` / `<PENDING_*>` residual in non-password fields) / **P26** business configurable fields fully collected (config-sop.md §9.0.4 table lists account/password/db-name/topic/group/namespace per-product acceptance) | — | `[4]` reassemble |
| `[4.5]` → `[5]` | User confirms resource review | **P4** root password fields (rds/dds/redis) have real values (not placeholders) / **P5** user tri-state selects [1] confirm | — | `[4.5]` re-ask |
| `[5.5]` | Credential collection | **P12** `decisions.json.pendingCredentialsForecast[]` exists / **P13** mode=B middleware instances already created | **V8** `collectedCredentials[]` ∪ `pendingCredentials[]` = `pendingCredentialsForecast[]` full set (no omissions) | `[5.5]` re-ask |
| `[step-2]` | build + upload | **P17** artifact file exists and size > 0 bytes / **P22** artifact extension ∈ whitelist `{.jar, .war, .whl, .tgz, .tar.gz, .tar.xz}`, .zip forbidden / **P27** `scripts/start.sh` content must include background launch mode (`nohup`/`&` / `setsid` / `screen -dm` / `--daemon` / `--daemonize yes`); foreground direct execution causes 600s timeout (see R15) | **V11** OSS stat Content-Length = local wc -c (verified in InstallApplication pre-hook filePath mode) / **V12** OSS upload completes without error | `[step-2]` re-upload |
| `[step-3]` | InstallApplication | **G4** HITL install checklist tri-state confirmation (see [step-3] §3.0) — **mandatory ASK-USER before InstallApplication; skipping is a critical violation** / **P19** OSS URL reachable (HEAD 200) / **P20** regionId + instanceIds + appName provided | **V13** poll SUCCESS / **V14** wait_ready hits HTTP 200 (see [step-3] §3.2) / **V15** application log has no fatal exceptions (error keyword scan) / **V17** frontend accessibility (only triggered when backend.embedsStatic=true) / **V18** post-deploy 4-layer verification (V-PORT + V-PROC + V-HEALTH + V-LOG all pass, see [step-3] §3.2.1) | `[step-3]-post` root cause classification |

> Note: Items marked **V*** are cloud truth reconciliation; items marked **P*** are local prechecks. All gates must be explicitly executed at their corresponding main flow positions; "agent thinks it's OK so skip" is not allowed.

## Precheck Common Implementation Templates

### P2 / P6 Placeholder Regex Scan

```bash
precheck_placeholder_scan() {
  local FILE="$1"  # collect-info.json or decisions.json
  local RESIDUAL
  RESIDUAL=$(grep -nPo '<(ASK|PENDING|RUNTIME)_[A-Z0-9._]+>' "$FILE" || true)
  if [[ -n "$RESIDUAL" ]]; then
    echo "[FAIL] Placeholder residual:" >&2
    echo "$RESIDUAL" >&2
    echo "Rollback path: [4.5] re-collect real values; for password fields refer to password-rules.md strength spec" >&2
    return 1
  fi
  return 0
}
```

### P7 Password Strength Check

```bash
precheck_password_strength() {
  local PWD="$1" FIELD="$2"  # field name for error reporting only
  # Length >=10
  [[ ${#PWD} -lt 10 ]] && { echo "[FAIL] $FIELD length < 10" >&2; return 1; }
  # Blacklist (synced with password-rules.md)
  case "$PWD" in
    Test@0987|Aa123456!|P@ssw0rd|Password123!|Admin@123)
      echo "[FAIL] $FIELD hits blacklist" >&2; return 1 ;;
  esac
  # Must contain all four character types
  [[ ! "$PWD" =~ [a-z] ]] && { echo "[FAIL] $FIELD missing lowercase" >&2; return 1; }
  [[ ! "$PWD" =~ [A-Z] ]] && { echo "[FAIL] $FIELD missing uppercase" >&2; return 1; }
  [[ ! "$PWD" =~ [0-9] ]] && { echo "[FAIL] $FIELD missing digit" >&2; return 1; }
  [[ ! "$PWD" =~ [^a-zA-Z0-9] ]] && { echo "[FAIL] $FIELD missing special char" >&2; return 1; }
  return 0
}
```

### P22 Artifact Extension Whitelist (zip forbidden)

```bash
precheck_artifact_format() {
  local ARTIFACT="$1"
  case "$ARTIFACT" in
    *.jar|*.war|*.whl|*.tgz|*.tar.gz|*.tar.xz) return 0 ;;
    *.zip)
      echo "[FAIL] Artifact $ARTIFACT is .zip format, upload forbidden" >&2
      echo "Reason: zip doesn't preserve Unix permission bits / symlinks; downstream DeployScriptBuilder unzips without +x, process dies instantly" >&2
      echo "Rollback path: locally unzip then use COPYFILE_DISABLE=1 tar -czf to repackage, or go back to [step-2] to change artifact command" >&2
      return 1 ;;
    *)
      echo "[WARN] Artifact $ARTIFACT extension not in whitelist ({.jar/.war/.whl/.tgz/.tar.gz/.tar.xz}), please verify downstream extractor supports it" >&2
      return 0 ;;
  esac
}
```

### P26 Business Configurable Fields Fully Collected (Redline 18 — App Deployment Phase Credential Omission Guard)

Prevents [step-3] InstallApplication startup from discovering "business account not asked / database name missing / topic written from memory incorrectly". Before entering [4.5], perform per-product verification against config-sop.md §9.0.4 table:

```bash
precheck_business_fields_complete() {
  local CONFIG_JSON="$1"           # collect-info.json draft
  local SERVICE_GRAPH_JSON="$2"     # [1] analyze-application output
  local FAIL=0

  # 1. RDS / DDS / PolarDB
  for k in rds dds polardb_serverless_public_cn; do
    if jq -e --arg k "$k" '.[$k]' <<<"$CONFIG_JSON" >/dev/null 2>&1; then
      for f in account password databases; do
        local V=$(jq -r --arg k "$k" --arg f "$f" '.[$k][$f] // empty' <<<"$CONFIG_JSON")
        if [[ -z "$V" || "$V" == "<"*">" ]]; then
          echo "[FAIL] $k.$f not filled or still a placeholder" >&2; FAIL=1
        fi
      done
      # databases[] must ⊇ db name set scanned from service graph
      local NEEDED=$(jq -r --arg k "$k" '.nodes[] | select(.serviceType==$k) | .databases[]?' <<<"$SERVICE_GRAPH_JSON" | sort -u)
      local PROVIDED=$(jq -r --arg k "$k" '.[$k].databases[]? // empty' <<<"$CONFIG_JSON" | sort -u)
      local MISS=$(comm -23 <(echo "$NEEDED") <(echo "$PROVIDED"))
      [[ -n "$MISS" ]] && { echo "[FAIL] $k.databases[] missing DBs: $MISS" >&2; FAIL=1; }
    fi
  done

  # 2. Redis
  if jq -e '.kvstore_prepaid_public_cn' <<<"$CONFIG_JSON" >/dev/null 2>&1; then
    local PWD=$(jq -r '.kvstore_prepaid_public_cn.password // empty' <<<"$CONFIG_JSON")
    [[ -z "$PWD" || "$PWD" == "<"*">" ]] && { echo "[FAIL] redis.password not filled" >&2; FAIL=1; }
  fi

  # 3. Nacos namespaces[]
  if jq -e '.mse_registryserverless' <<<"$CONFIG_JSON" >/dev/null 2>&1; then
    local NEEDED=$(jq -r '.nodes[] | select(.serviceType=="nacos") | .namespaces[]?' <<<"$SERVICE_GRAPH_JSON" | sort -u)
    local PROVIDED=$(jq -r '.mse_registryserverless.namespaces[]? // empty' <<<"$CONFIG_JSON" | sort -u)
    local MISS=$(comm -23 <(echo "$NEEDED") <(echo "$PROVIDED"))
    [[ -n "$MISS" ]] && { echo "[FAIL] nacos.namespaces[] missing: $MISS" >&2; FAIL=1; }
  fi

  # 4. Kafka topics + consumerGroups
  if jq -e '.kafka_serverless' <<<"$CONFIG_JSON" >/dev/null 2>&1; then
    for f in topics consumerGroups; do
      local NEEDED=$(jq -r --arg f "$f" '.nodes[] | select(.serviceType=="kafka") | .[$f][]?' <<<"$SERVICE_GRAPH_JSON" | sort -u)
      local PROVIDED=$(jq -r --arg f "$f" '.kafka_serverless[$f][]? // empty' <<<"$CONFIG_JSON" | sort -u)
      local MISS=$(comm -23 <(echo "$NEEDED") <(echo "$PROVIDED"))
      [[ -n "$MISS" ]] && { echo "[FAIL] kafka.$f missing: $MISS" >&2; FAIL=1; }
    done
  fi

  # 5. RocketMQ topics + groups
  for k in ons_serverless ons_rmqsrvlesspost; do
    if jq -e --arg k "$k" '.[$k]' <<<"$CONFIG_JSON" >/dev/null 2>&1; then
      for f in topics groups; do
        local NEEDED=$(jq -r --arg f "$f" '.nodes[] | select(.serviceType=="rocketmq") | .[$f][]?' <<<"$SERVICE_GRAPH_JSON" | sort -u)
        local PROVIDED=$(jq -r --arg k "$k" --arg f "$f" '.[$k][$f][]? // empty' <<<"$CONFIG_JSON" | sort -u)
        local MISS=$(comm -23 <(echo "$NEEDED") <(echo "$PROVIDED"))
        [[ -n "$MISS" ]] && { echo "[FAIL] $k.$f missing: $MISS" >&2; FAIL=1; }
      done
    fi
  done

  [[ $FAIL -eq 1 ]] && { echo "Rollback path: go back to [4] ASK-USER to fill in above fields, then re-run Step 3.5" >&2; return 1; }
  return 0
}
```

### P27 start.sh Background Execution Mode Detection (Redline 22)

> **Background**: The platform side calls the startup script via `bash "scripts/start.sh"` in foreground. If `start.sh` itself runs the application process in foreground (e.g., `python3 app.py`, `java -jar app.jar`), the deploy script blocks permanently, gets killed by Cloud Assistant after 600s timeout, and the task is marked FAILURE.
>
> **R15 root cause**: `start.sh` runs the application in foreground → deploy script `bash "scripts/start.sh"` permanently blocks → Cloud Assistant 600s timeout kill → task marked FAILURE. Recovery: fix `deployScripts.start` to use `nohup <cmd> >> log 2>&1 &` or framework-native `--daemon` for background launch (see `steps/step-2-build.md` §2.3.1) → [step-2] re-inject script + repackage → [step-3] re-run.

```bash
precheck_start_script_background() {
  local START_SH="$1"  # start.sh file path
  # Background mode keywords: nohup ... & / setsid / screen -dm / tmux new-session -d / --daemon / --daemonize yes
  # Scan file content (ignore comment lines)
  local CONTENT
  CONTENT=$(grep -vE '^\s*#' "$START_SH" 2>/dev/null || true)
  if [[ -z "$CONTENT" ]]; then
    echo "[FAIL] $START_SH content is empty or only contains comments" >&2
    echo "Rollback path: [step-2] §2.3.1 rewrite start.sh using template" >&2
    return 1
  fi
  # Detect background mode: nohup+& / setsid / screen -dm / tmux new-session -d / --daemon / --daemonize yes
  # Merge multi-line first (tr '\n' ' ') to avoid missing nohup ... \ continuation with & on separate line
  if ! echo "$CONTENT" | tr '\n' ' ' | grep -qE '(nohup\s+\S+[^#]*\&|setsid\s|screen\s+-dm|tmux\s+new-session\s+-d|--daemon\b|--daemonize\s+yes)'; then
    echo "[FAIL] P27: $START_SH no background launch mode detected" >&2
    echo "Script content:" >&2
    echo "$CONTENT" >&2
    echo "Rollback path: [step-2] §2.3.1 rewrite using nohup <cmd> >> log 2>&1 & or framework-native --daemon pattern" >&2
    return 1
  fi
  echo "[OK] P27: $START_SH contains background launch mode"
  return 0
}
```

> **When to run**: [step-2] §2.3 step 2 (P27 gate), after obtaining script content (step 1) and before creating staging directory for packaging (step 3). Execute detection on `$START_SCRIPT` content (or project source `scripts/start.sh`); if it fails, auto-rewrite per §2.3.1 template then re-detect; proceed to staging directory and packaging only after passing.

## Postverify Common Implementation Templates

### V14 wait_ready (see [step-3] §3.2) — MANDATORY

Calls the `wait_ready` probing cycle defined in [step-3] §3.2: 60s hard wait + 5s-interval HTTP probes for up to 5 minutes. **Skipping wait_ready is a critical violation** — it is a hard blocking gate between InstallApplication SUCCESS and V18 post-deploy verification. This section does not re-implement it and serves only as a reference anchor in the postverify matrix.

### V17 Frontend Accessibility Post-Verify (`embedsStatic=true` Only)

> **Background**: In the `shape=monolith-with-static` + `frontendDeploymentMode=embed-in-jar` scenario, [step-2] composite build should copy `vue/dist/*` to backend `src/main/resources/static/` and package it into the JAR's `BOOT-INF/classes/static/`. [step-3] InstallApplication SUCCESS does not prove the frontend actually exists in the JAR: relying solely on V14 wait_ready hitting `/actuator/health` will miss the "frontend not packaged into JAR" class of issues. V17 adds two layers of verification: root path access and response body characteristics.

```bash
postverify_frontend_accessible() {
  local SP="$1" IP="$2" PORT="$3"
  # Only called when [1] services[$SP].embedsStatic=true; caller pre-checks before entering this function
  local URL="http://${IP}:${PORT}/"
  local CT BODY
  CT=$(curl -sI --max-time 10 "$URL" | awk -F': *' 'tolower($1)=="content-type"{print tolower($2)}' | tr -d '\r')
  BODY=$(curl -s  --max-time 10 "$URL" | head -c 4096)

  if [[ "$CT" != *"text/html"* ]]; then
    echo "[FAIL] V17 frontend inaccessible: GET $URL returned Content-Type=$CT (expected text/html)" >&2
    echo "Rollback path: return to [step-2] and check if BOOT-INF/classes/static/index.html exists in backend build output JAR; jar tf <pkg>.jar | grep static" >&2
    return 1
  fi
  if ! grep -qiE '<!DOCTYPE|<html' <<< "$BODY"; then
    echo "[FAIL] V17 root path response is text/html but does not contain <html>/<!DOCTYPE>, possibly backend HealthController.root() hijacked the / route → hiding the fact that frontend was not packaged" >&2
    echo "Rollback path: check if backend added an extra GET / handler for health checks; if so, remove it and re-run [step-2]+[step-3]" >&2
    return 1
  fi
  echo "[OK] V17 frontend accessible: GET $URL returned SPA index.html (Content-Type=$CT)"
  return 0
}
```

> **When to run**: After `[step-3]` InstallApplication poll returns SUCCESS + V14 wait_ready passes, triggered only when [1] services[backend].embedsStatic=true.
> **Reverse logic**: If V17 fails, prioritize checking three points: ① Does the frontend project `package.json` `scripts.build` produce `dist/`; ② Did [step-2] composite build skip (because [1] embedsStatic was not set to true); ③ Did backend code add an extra `@GetMapping("/")` handler hijacking the SPA default route.

### V18 Post-Deploy 4-Layer Verification (see [step-3] §3.2.1)

> **Background**: V14 wait_ready only confirms a single HTTP 200 hit during the probing window. It does not confirm port-level readiness, process stability, health endpoint semantics, or absence of fatal errors in logs. V18 provides a structured, multi-layer verification that catches the gap between "app responded once" and "app is truly healthy". All checks run via `EcsRunCommandSync` (sync, read-only, no new Op needed).

**Composite check (V-PORT + V-PROC + V-HEALTH):**

```bash
postverify_composite_check() {
  local REGION="$1" INSTANCE="$2" PORT="$3" APP_NAME="$4" HEALTH_PATH="${5:-/actuator/health}"
  local RESULT
  RESULT=$(cadt-deploy-on-aliyun -run EcsRunCommandSync "{
    \"regionId\":\"$REGION\",
    \"instanceIds\":[\"$INSTANCE\"],
    \"command\":\"echo [V-PORT]; (ss -tlnp 2>/dev/null || netstat -tlnp 2>/dev/null) | grep -E ':$PORT\\s' && echo VPORT:OK || echo VPORT:FAIL; echo [V-PROC]; pgrep -af '$APP_NAME' && echo VPROC:OK || echo VPROC:FAIL; echo [V-HEALTH]; curl -sf --max-time 10 http://localhost:$PORT$HEALTH_PATH && echo && echo VHEALTH:OK || echo VHEALTH:FAIL\"
  }")
  local OUTPUT=$(echo "$RESULT" | jq -r '.data.attributes.instances | to_entries[0].value.output')
  if echo "$OUTPUT" | grep -q "VPORT:FAIL"; then
    echo "[FAIL] V18 V-PORT: port $PORT not listening on $INSTANCE" >&2
    echo "Rollback path: enter [step-3]-post root cause classification (R6/R15)" >&2
    return 1
  fi
  if echo "$OUTPUT" | grep -q "VPROC:FAIL"; then
    echo "[FAIL] V18 V-PROC: no process matching '$APP_NAME' found on $INSTANCE" >&2
    echo "Rollback path: enter [step-3]-post root cause classification (R14/R15)" >&2
    return 1
  fi
  if echo "$OUTPUT" | grep -q "VHEALTH:FAIL"; then
    echo "[FAIL] V18 V-HEALTH: curl http://localhost:$PORT$HEALTH_PATH failed on $INSTANCE" >&2
    echo "Rollback path: enter [step-3]-post root cause classification (R6)" >&2
    return 1
  fi
  echo "[OK] V18 composite: V-PORT + V-PROC + V-HEALTH passed"
  return 0
}
```

**Log scan (V-LOG):**

```bash
postverify_log_scan() {
  local REGION="$1" INSTANCE="$2" APP_NAME="$3"
  local RESULT
  RESULT=$(cadt-deploy-on-aliyun -run EcsRunCommandSync "{
    \"regionId\":\"$REGION\",
    \"instanceIds\":[\"$INSTANCE\"],
    \"command\":\"echo [V-LOG]; tail -100 /tmp/$APP_NAME\_deploy.log | grep -ciE 'fatal|exception|crash|panic|traceback' && echo VLOG:FAIL || echo VLOG:OK\"
  }")
  local OUTPUT=$(echo "$RESULT" | jq -r '.data.attributes.instances | to_entries[0].value.output')
  if echo "$OUTPUT" | grep -q "VLOG:FAIL"; then
    echo "[FAIL] V18 V-LOG: fatal/exception keywords found in deploy log on $INSTANCE" >&2
    echo "Rollback path: pull full log via EcsRunCommand, enter V15 analysis flow" >&2
    return 1
  fi
  echo "[OK] V18 V-LOG: no fatal errors in deploy log"
  return 0
}
```

> **When to run**: After V14 wait_ready passes (regardless of V17). V18 always runs; V17 runs only when `embedsStatic=true`.
> **Execution order**: V14 → V18 (composite → log scan) → V17 (if applicable) → §3.4 result output.
> **Fail-fast**: First layer failure stops the chain; do NOT continue to subsequent layers. Route to [step-3]-post root cause classification with the failed layer as context.

## Failure Rollback Path Quick-Reference Table

| Failed Gate | Rollback To | User Intervention | Auto-Retry? |
|---|---|---|---|
| G4 install checklist skipped | `[step-3]` §3.0 | Required (user must confirm/modify/cancel) | No — must re-present checklist |
| P2/P6 placeholder residual | `[4.5]` | Required (re-provide real values) | No |
| P7 password strength | `[4.5]` | Required (user re-enters) | No |
| P14 KV placeholder | `[5.5]` | Required (credential collection gate re-asks) | No |
| P27 start.sh no background mode | `[step-2]` §2.3 step 2 | No (agent rewrites per §2.3.1 template) | Yes (re-detect + repackage after rewrite) |
| V11 OSS size mismatch | `[step-2]` | No (agent re-uploads) | Yes (max 3 times) |
| V14 wait_ready skipped | `[step-3]` §3.2 | Required (agent MUST re-run full wait_ready probing cycle) | No — must re-execute full 60s+5s-interval script |
| V14 wait_ready timeout | `[step-3]` §3.3 | No (agent enters FAILURE:not-ready root cause classification) | No (classify R1-R8 then follow recovery path) |
| V17 frontend inaccessible | `[step-2]` | No (agent checks composite build pre-step) | Yes (fix [1] embedsStatic / staticSource then re-run [step-2]+[step-3]) |
| V18 V-PORT / V-PROC / V-HEALTH fail | `[step-3]-post` | No (agent enters root cause classification) | No (classify R6/R14/R15 then follow recovery path) |
| V18 V-LOG fail | `[step-3]-post` | No (agent pulls full log) | No (enter V15 log analysis flow) |

## Coordination with Redlines

- **Redline 6** (no local secret storage): postverify validates key sets only, **never reads actual values**, to avoid plaintext leakage
- **Redline 13/14** (runtime env sole channel + no deploy-class write ops): all postverify goes through `cadt-deploy-on-aliyun -run`; ssh / RunCommand for deploy-class write reconciliation is forbidden (whitelisted exemptions require audit trail)
- **Redline 16** (write-class Op client async): postverify calls are read-only Ops and can use sync; but if stuck, must follow the same rhythm and switch to async polling
- **Redline 17** ([2.5] four-state closure): postverify does not rewrite verdict, only reads `decisions.json`
- **Redline 18** ([5.5] credential collection gate three-state): V8 reconciliation does not bypass the user's [2] defer choice
- **Redline 19** (new): This document's P6 implementation is the concrete realization of Redline 19
- **Redline 21** (G4 install checklist): The G4 gate in this document's `[step-3]` precheck column is the concrete realization of Redline 21 — mandatory HITL tri-state confirmation before InstallApplication; skipping constitutes a critical violation
- **Redline 20** (new): All V* in this document constitute the Redline 20 checklist

## Implementation Notes

- **MUST**: Each V* must be **explicitly called** after the corresponding step in the main flow; agents must not skip any
- **MUST**: V14 (wait_ready) MUST complete its full probing cycle before V18 is attempted. The agent MUST NOT substitute V18's composite check for V14's probing cycle. Skipping V14 and jumping directly to V18 is a critical violation.
- **MUST**: On failure, output `operationId` + `RequestId` (if available) to help users investigate in the console
- **MUST NOT**: On postverify failure → agent silently re-runs write-class Op (violates Redline 16: no blind retry for write-class ops)
- **SHOULD**: After each V* completes, output one line `[OK] V{n} {desc}` to stdout for log traceability

## References

- [`SKILL.md`](../SKILL.md) — Main flow; this document serves as the gate annotations for each step
