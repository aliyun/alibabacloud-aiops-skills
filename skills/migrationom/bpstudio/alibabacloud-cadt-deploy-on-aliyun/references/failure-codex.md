# Failure Codex — Build/Deploy Phase Root Cause Index

> Failure root cause classification for [step-2] compile/package/upload and [step-3] application deployment phases.

## Index Structure

```
Symptom → Checkpoint → Root Cause ID → Diagnosis Method → Recovery Path
```

---

## [step-2] Compile, Package & Upload

| ID | Checkpoint | Symptom | Root Cause | Recovery Path |
|---|---|---|---|---|
| F21 | [step-2] | `BUILD FAILURE` / `mvn` / `gradle` compilation failed | Source code compilation issue (missing dependency / syntax error) | Fix source → re-run [step-2] |
| F22 | [step-2] | OSS upload failed: STS expired | Token 15min short-lived | Re-run `InstallApplication` with filePath (pre-hook auto re-fetches token) |
| F23 | [step-2] post | OSS stat Content-Length ≠ local wc -c | Upload truncated / network interruption | Re-run `InstallApplication` with filePath (pre-hook auto overwrites upload) |
---

## [step-3] Deploy (InstallApplication) Phase

### Entry Decision Tree (Cross-Stack, Exit the Repackage Trap)

> **Principle**: Before entering [step-3]-post, you must complete this decision tree first to avoid any "startup failure → repackage" path skipping. Repackaging ([step-2]) is the **most expensive recovery path** — **only R3 with strict match is allowed** (and hostname must be a literal in code, not from KV/config, not a compose service name placeholder).
>
> The decision tree below looks only at **error keywords**, regardless of distro or language — cross-stack applicable:

```
Entering [step-3]-post:
├─ V18 verification failure (from [step-3] §3.2.1):
│    ├─ V-PORT FAIL: port not listening → R6 (port mismatch) or R15 (process never started)
│    ├─ V-PROC FAIL but V-PORT OK: no matching process → R14 (fork-then-exit, process name differs) or R15
│    ├─ V-HEALTH FAIL but V-PORT+V-PROC OK: health endpoint unreachable → R6 (health path mismatch) or app returning non-200
│    └─ V-LOG FAIL: fatal/exception keywords in deploy log → pull full log, enter V15 analysis flow below
├─ Contains "Port * was already in use" / "EADDRINUSE" / "Address already in use" / `ss -tlnp` shows another process on target port
│    → R6 (port conflict — target port occupied by another process) — kill stale process / change app port → [step-3] re-run
├─ First error line is "missing env *" / "KV xxx not found" / NPE pointing to uninjected env
│    → R1 (env missing) — EcsRunCommand write KV → single-hop [step-3] re-run
├─ Contains "Authentication failed" / 401 / 403 + KV exists but value is wrong
│    → R2 (KV value wrong) — upsert rewrite → single-hop [step-3]
├─ Contains "Connection refused" / "Connection timeout" / "UnknownHostException"
│    ├─ Hostname in error is valid ECS internal IP but middleware status=Creating → R4 (wait for ready polling)
│    ├─ Hostname in error is docker-compose service name / `localhost` / hardcoded IP
│    │    ├─ Project `runtime.hostnameRefs[]` is non-empty and literal code evidence exists → R3 (only repackage path)
│    │    └─ Otherwise → 'project has not been adapted for cloud migration', use R5 / EcsRunCommand add KV without repackage
│    └─ Middleware itself auth failure + credential not in KV → R5 / R5b
├─ Contains "NoClassDefFoundError: sun/awt/X11FontManager"
│    ├─ Contains "command not found: ffmpeg|wkhtmltopdf|libreoffice|tesseract|chromium|7z|unrar"
│    ├─ Contains "Could not find tesseract" / "error while loading shared libraries: lib*.so"
│    → R8b (native dependency missing) — no repackage. Add nativeDeps → EcsRunCommand → [step-3]
├─ Contains "NoClassDefFoundError: javax/xml/bind" / "Unsupported class file major version"
│    → R8 (JDK mismatch) — no repackage. Install matching JDK + JAVA_HOME KV → [step-3]
├─ Contains "BadSqlGrammarException" / "Table * doesn't exist" / "relation * does not exist"
│    → R9 (DB schema not imported) — no repackage. Follow startup checklist §3 three-state
├─ Contains "health probe failed: HTTP 404" but app log shows Started
│    → R6 (probe path/port mismatch) — no repackage. Fix listenerPort + healthcheck.path → [step-3]
├─ Contains "health check timeout after 120s" but app actually Started
│    → R7 (120s timeout hardcoded, platform limitation) — no repackage
├─ wait_ready TIMEOUT but `ss -tlnp` + `curl localhost:PORT/health` inside ECS returns OK
│    → Probe method issue (external/public-IP curl vs EcsRunCommandSync localhost). Security group blocks inbound port.
│    → Service is healthy. Re-run wait_ready with EcsRunCommandSync loop, or report success + advise user to open security group port.
│    → Do NOT classify as R-series — the service is not failed.
├─ Contains "python: command not found" / "ModuleNotFoundError" / process instant death exit=4
│    → R10 (interpreter path mismatch) — fix Python path in deployScripts.start → [step-2] re-inject script → [step-3]
├─ Process instant death, deploy.log has no stdout, `[ -f xxx.py ]` short-circuits
│    → R11 (entry file name mismatch) — fix entry filename in deployScripts.start → [step-2] re-inject script → [step-3]
├─ ECS direct HTTP 200 + ALB domain timeout
│    → R12 (infrastructure missing step) — no repackage. Manually configure listener+TG
├─ `Permission denied` / `cannot execute binary file` / symlink broken / config replaced by directory
│    → R13 (uploaded as .zip which doesn't preserve permission bits) — repackage with .tar.gz (required repackage, but issue is packaging medium, not source code error)
├─ `[PROCESS_DIED] exit=0` triggered within 1-2s / `* Restarting with stat` / pgrep still hits
│    → R14 (fork-then-exit-0 misjudgment) — fix deployScripts.start to disable reloader → [step-2] re-inject script → [step-3]
├─ InstallApplication 600s timeout / `deploy.log` tail has no `Start script completed` / `Deploy completed` line
│    → R15 (start.sh foreground blocking) — fix deployScripts.start to use nohup + & background launch → [step-2] re-inject script → [step-3]
└─ None of above matched → first pull deploy.log + journalctl for full output, report ASK-USER;
     **Do not** default to R3; defaulting to R3 = unnecessary repackage × problem won't be fixed
```

**R3 Strict Admission Criteria (all must be met)**:

1. The hostname appearing in the error has a match in the project's `runtime.hostnameRefs[]`
2. That name is a **literal** in the code (grep yields line numbers), not read from KV / env var / config file
3. inject-aliyun-config L0/L1/L2 surface plugins cannot cover it (requires L3 source code modification)

If any of the above conditions is not met → do not take R3; redirect to other branches in the table above or ASK-USER.

---

### Root Cause Detail Table

| ID | Checkpoint | Symptom | Root Cause | Recovery Path |
|---|---|---|---|---|
| **R1** | [step-3]-post | `missing env XXX` / NPE pointing to uninjected env | Runtime KV missing | EcsRunCommand write .env file to ECS → single-hop [step-3] re-run |
| **R2** | [step-3]-post | `Authentication failed` / 401/403 pointing to app-level credentials | KV value wrong | EcsRunCommand Delete + Create upsert → single-hop [step-3] re-run |
| **R3** | [step-3]-post | `UnknownHostException` / `Connection refused` pointing to docker-compose service name | Source code hostname hardcoded | **inject-aliyun-config L3 modify source** → EcsRunCommand write KV → [step-2] repackage → [step-3] re-run |
| **R4** | [step-3]-post | `Connection timeout` pointing to valid IP but middleware status Creating | Dependent resource not ready | Poll resource healthy → single-hop [step-3] re-run |
| **R5** | [step-3]-post | Middleware itself auth failure + corresponding password **not in** KV | Credential loop disconnected | ResetAccountPassword + EcsRunCommand update .env → [step-3] re-run |
| **R5b** | [step-3]-post | Same as R5 but `pendingCredentials[]` explicitly exists | Expected behavior when user chose to defer | Let user complete console operation → record back → [step-3] re-run |
| **R6** | [step-3]-post | `health probe failed: HTTP 404` but app log shows Started OK; or `Port * was already in use` / `EADDRINUSE` / `Address already in use` (target port occupied by another process) | Health probe path / port mismatch, or port conflict with stale process | Fix listenerPort + healthcheck.path, or kill stale process / change app port → [step-3] re-run |
| **R7** | [step-3]-post | `health check timeout after 120s` but app actually Started | BPStudio 120s timeout hardcoded (platform limitation) | JAVA_OPTS to reduce startup time / add readinessProbe / accept re-run |
| **R8** | [step-3]-post | `NoClassDefFoundError: javax/xml/bind` / `Unsupported class file major version` | ECS JDK version doesn't match application | Install matching JDK (Dragonwell 8) + JAVA_HOME KV → [step-3] re-run |
| **R8b** | [step-3]-post | `NoClassDefFoundError: sun/awt/X11FontManager` / `command not found: ffmpeg\|wkhtmltopdf\|libreoffice\|tesseract\|chromium` / `Could not find ...` / `error while loading shared libraries: lib*.so` | OS-level native dependencies not installed (fonts/audio-video/PDF/OCR/browser/locale, etc.) | **Do not take R3 repackage**. Add nativeDeps → EcsRunCommand upsert KV → [step-3] single-hop re-run. If error keyword not in known table → ASK-USER to supplement `category=unknown` osPackages |
| **R9** | [step-3]-post | `BadSqlGrammarException` / `Table 'xxx.yyy' doesn't exist` / `relation "xxx" does not exist` | DB schema not imported (RDS only created empty DB, DDL not executed) | EcsRunCommand to run mysql client import (redline 14 whitelist exemption ② + user authorization) / user goes to DMS / enable Flyway migration → [step-3] re-run |
| **R10** | [step-3]-post | `python: command not found` / `ModuleNotFoundError: No module named 'flask'` / process instant death exit=4 + deploy.log has no stdout | Python interpreter path mismatch | Fix Python path in `deployScripts.start` (e.g., `/usr/local/bin/python3 app.py`) → [step-2] re-inject script + repackage → [step-3] re-run |
| **R10b** | [step-3]-post | `scripts/start.sh` content doesn't match actual language (e.g., Java project but start.sh runs npm) | Language detection error during script generation | Check if `services[i].deployScripts` matches the correct service → fix script content → [step-2] re-inject + repackage → [step-3] re-run |
| **R11** | [step-3]-post | `[ -f xxx.py ]` short-circuits silently exit 0 / process instant death with no deploy.log output / pip-installed site-packages inconsistent with startup interpreter | start.sh entry filename wrong | Fix entry filename in `deployScripts.start` → [step-2] re-inject + repackage → [step-3] re-run |
| **R12** | [step-3]-post | ECS direct `http://ip:port` HTTP 200 but ALB domain `Connection timeout` | ALB created but listener+TG not auto-configured for `listenerPort` (infrastructure missing step) | Check ALB configuration via aliyun CLI or console, then manually configure listener:80 → TG:listenerPort |
| **R13** | [step-3]-post | Startup script `Permission denied` / shell script has no +x / `cannot execute binary file` / symlink broken / config file replaced by directory | Uploaded as `.zip` instead of `.tar.gz`: zip doesn't preserve Unix permission bits, symlinks, file types | Go back to [step-2], use `COPYFILE_DISABLE=1 tar -czf` to repackage → re-run [step-2]→[step-3] |
| **R14** | [step-3]-post | `[PROCESS_DIED] exit=0` triggered within 1-2s of startup / deploy.log only shows `* Restarting with stat` / `kill -0 $START_PID` fails but `pgrep -f appName` still hits child process | Application starts in **fork-then-exit-0 mode** (typical: Flask `app.run(debug=True)` Werkzeug Reloader, Django `runserver --reload`, `supervisord` foreground mode) — parent process forks child then **normally exits 0**, gateway only tracks parent PID and misjudges PROCESS_DIED | **Preferred**: fix `deployScripts.start` to disable reloader → [step-2] re-inject + repackage → [step-3] re-run; **Fallback**: inject-aliyun-config L3 disable debug in source → re-run [step-2]→[step-3]; **Use with caution**: pass `skipRollback=true` to preserve state, then `EcsRunCommand` to run `pgrep -f <appName>` to confirm child process |
| **R15** | [step-3] | InstallApplication 600s timeout / `deploy.log` tail has no `Start script completed` line / task killed by Cloud Assistant | `start.sh` runs application process in foreground (e.g., `python3 app.py`, `java -jar app.jar`), deploy script `bash "scripts/start.sh"` blocks permanently, killed by Cloud Assistant after 600s, task marked FAILURE | Fix `deployScripts.start`: use `nohup <cmd> >> log 2>&1 &` or framework-native `--daemon` for background launch (see [`steps/step-2-build.md`](../../steps/step-2-build.md) §2.3.1) → [step-2] re-inject script + repackage → [step-3] re-run |
| F25 | [step-3] | InstallApplication returns FAILURE (not [step-3]-post) | Deploy script layer failure (network / corrupted package / script error) | Check operationId to locate → re-run [step-3] |
| F26 | [step-3] §3.2 | wait_ready HTTP 200 timeout 5min | Slow startup / dependency not ready / **external probe method used instead of EcsRunCommandSync localhost** | Mark `FAILURE:not-ready` → enter [step-3]-post R-series diagnosis. **First check**: verify probe was executed via `EcsRunCommandSync` targeting `localhost` inside the ECS. If the probe used a direct `curl` to the ECS public IP from outside, the timeout is caused by security group blocking the port — NOT a service failure. Re-run the §3.2 loop using the prescribed `EcsRunCommandSync` script before classifying as R-series. See [step-3] §3.2 anti-pattern "external/public-IP probe substitution". |
| F27 | [step-3] §3.2.1 | V18 verification layer failure (V-PORT/V-PROC/V-HEALTH/V-LOG) | wait_ready passed but structured verification caught issue | Route by failed layer: V-PORT→R6/R15, V-PROC→R14/R15, V-HEALTH→R6, V-LOG→V15 log analysis |

---

## General Principles

1. **Never blindly retry write Ops** — first check operationId or List to confirm whether the previous attempt succeeded
2. **Never skip a failed step** — serial dependency; subsequent IDs won't exist if any step fails
3. **F/R IDs are stable** — new root causes are only appended with new IDs; existing IDs are never changed
4. **Verification first** — if a read-only Op can confirm the result, don't rely on "retry succeeded" inference
