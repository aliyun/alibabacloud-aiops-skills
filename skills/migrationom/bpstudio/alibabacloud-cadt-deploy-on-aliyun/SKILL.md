---
name: alibabacloud-cadt-deploy-on-aliyun
description: >
  Build and deploy applications to Alibaba Cloud ECS — Local build + script injection + InstallApplication async deployment.
  Triggers: build, deploy, CI/CD, compile & package, publish to Alibaba Cloud, diagnose, troubleshoot, root cause, 502, 503, service not started, deployment failed.
license: Apache-2.0
---

# Alibaba Cloud Application Build & Deploy

Standalone deployment Skill: **Build + Deploy** pipeline orchestration. User directly provides ECS instance IDs, region, and application information — no project/environment hierarchy dependency.

## Workflow

### Path A: Build + Deploy (new deployment)

```
[step-1] Session init + collect deployment info  ->  [step-2] Compile, package & upload  ->  [step-3] Application deploy + failure recovery + result output
```

### Path B: Diagnose + Fix + Redeploy (troubleshoot previous deployment)

```
[step-1] Session init + detect diagnose intent  ->  [step-3] §3.0-D Run diagnostics + classify root cause  ->  ⛔ ASK-USER "fix and re-deploy?" (mandatory STOP)  ->  [step-2] Build fix (config/scripts only, NOT new source code)  ->  [step-3] G4 checklist + InstallApplication
```

> **Path B scope**: "Build" in Path B means applying the diagnosed fix to **existing deployment configuration** (e.g., `application.yml` port, JVM flags, start/stop scripts, env vars) and re-packaging — NOT writing new application source code from scratch. The application already exists on the ECS instance.
>
> **Path B re-deploy mandate**: After the user confirms [1] "fix and re-deploy", the **full pipeline** (step-2 build → G4 checklist → InstallApplication → wait_ready) is **always required** — even when the diagnosed fix is infrastructure-level (e.g., security group rules, DNS, firewall). The ASK-USER says "re-deploy", which means InstallApplication. Applying infra fixes manually and then testing with ad-hoc `curl` is NOT a substitute for the deployment pipeline.

| Step | Phase | File |
|------|-------|------|
| [step-1] | Session init + collect deployment info | CLI Bootstrap + PATH validation + cadt-deploy-on-aliyun -doctor + ASK-USER collect regionId/instanceIds/appName + **intent detection** | [steps/step-1-session-init.md](steps/step-1-session-init.md) |
| [step-2] | Build | Local build + script injection + repackaging (output artifact file) | [steps/step-2-build.md](steps/step-2-build.md) |
| [step-3] | Deploy + Output | **G4 install checklist (HITL, mandatory)** -> InstallApplication (async: `-run` + `-poll`) -> wait_ready -> **V18 post-deploy verification** -> root cause analysis -> result output | [steps/step-3-deploy.md](steps/step-3-deploy.md) |

> **Intent detection** (in [step-1]): If the user's request mentions "diagnose", "troubleshoot", "root cause", "502", "service not started", "deployment failed", or similar troubleshooting keywords — route to **Path B**. Otherwise route to **Path A**. See [step-1] §6 for the decision logic.

## ⛔ Pre-Deploy Hard Gates (MANDATORY — do NOT call InstallApplication without these)

Before calling `InstallApplication`, you MUST complete ALL of the following gates. Each gate is independently verifiable from the execution transcript. Skipping any gate is a **critical violation**.

| # | Gate | When | Evidence Required in Transcript |
|---|------|------|-------------------------------|
| **G0** | ASK-USER for `regionId` + `instanceIds` when not in initial request | [step-1] before §5.4 | Transcript MUST contain an explicit ASK-USER question for each missing field AND the user's response. Auto-discovery from CLI config, API enumeration, or env vars is a **critical violation** (see [step-1] §5.1–5.2). |
| **G0a** | `cadt-deploy-on-aliyun -doctor` run and passed | [step-1] §5 before §5 (Collect Deployment Info) | Transcript MUST contain `cadt-deploy-on-aliyun -doctor` invocation with `all_ok: true` result. `doctor.json` MUST be persisted. Skipping entirely is a **critical violation** (see [step-1] §5). |
| **G1** | `COPYFILE_DISABLE=1` on ALL `tar -czf` commands | [step-2] packaging | Every `tar` command in transcript MUST have `COPYFILE_DISABLE=1` prefix (required on ALL platforms — no-op on Linux, prevents AppleDouble on macOS) |
| **G2** | G4 Install Checklist presented + user confirmed `[1]` | [step-3] before InstallApplication | `decisions.json` with `userResponse: "1"` + `userResponseAt` timestamp. Agent text output alone is NOT sufficient. |
| **G3** | wait_ready loop executed after `-poll SUCCESS` | [step-3] after InstallApplication | Transcript MUST contain `[wait_ready] T0:` and `[wait_ready] probe:` markers. Ad-hoc `curl` or `ps aux` calls are NOT acceptable substitutes. |
| **G4** | ECS instance info queried via skill CLI only | [step-1] §5.4 | Transcript MUST contain `cadt-deploy-on-aliyun -run EcsGetDesc` or `EcsGetDescList`. Direct `aliyun ecs describe-instances` calls are a **critical violation** — no exceptions, even when CLI bootstrap failed (fix it first). |

### Gate Details

**G0 — ASK-USER for regionId + instanceIds (mandatory when not in initial request)**
```
# CORRECT — user explicitly provided region and instance in their request
User: "Deploy to cn-beijing, instance i-bp1xxx"

# CORRECT — agent asks user when info is missing
Agent: "请提供部署目标的地域 (regionId)，例如 cn-hangzhou, cn-beijing"
User: "cn-hangzhou"
Agent: "请提供目标 ECS 实例 ID (instanceId)"
User: "i-bp1ai3ai0rpvx965zpw0"

# WRONG — agent auto-discovers region from CLI config (critical violation)
Agent runs: aliyun configure list → reads "cn-hangzhou" → proceeds without asking

# WRONG — agent auto-selects instance from API enumeration (critical violation)
Agent runs: aliyun ecs describe-instances → finds "order-api-ecs" → selects it without asking
```

**G0a — `-doctor` check (mandatory before collecting deployment info)**
```bash
# CORRECT — doctor run and evidence persisted
DOCTOR_RESULT=$(cadt-deploy-on-aliyun -doctor)
echo "$DOCTOR_RESULT" | jq .
# → all_ok: true, then persist to doctor.json

# WRONG — skipping doctor entirely (critical violation)
Agent reads SKILL.md → asks user for regionId → proceeds to EcsGetDesc without ever running -doctor

# WRONG — CLI bootstrap failed, agent abandons CLI and skips doctor (critical violation)
Agent runs: cadt-deploy-on-aliyun.sh -version → fails → uses raw aliyun CLI → never runs -doctor
```
> If CLI bootstrap fails, you MUST fix the bootstrap first, then run `-doctor`. Abandoning the skill CLI and falling back to raw `aliyun` commands cascades into G0a and G4 violations.

**G1 — COPYFILE_DISABLE=1 (all tar commands, all platforms)**
```bash
# CORRECT — always use this prefix
COPYFILE_DISABLE=1 tar -czf "$ARTIFACT" -C "$STAGE_DIR" .

# WRONG — missing prefix (critical violation)
tar -czf "$ARTIFACT" -C "$STAGE_DIR" .
tar czf /tmp/app.tar.gz app scripts/
```

**G2 — G4 Install Checklist (HITL gate — MUST present and STOP)**
```
Before deployment, please confirm the install checklist:
  Application: {appName}
  Target instance(s): {instanceIds}
  Region: {regionId}
  Start command: {start.sh content}
  Stop command: {stop.sh content}
  Artifact: {ARTIFACT_FILE}

  [1] Checklist OK, proceed with deployment
  [2] I have additions / modifications
  [3] Cancel deployment
```
> After presenting this checklist, you MUST STOP. No additional tool calls permitted. Wait for user response.
>
> **Deferred-modification rule**: If the user responds [1] but the initial task prompt specified custom start/stop commands that were deferred (per §2.3 pre-baking prohibition), you MUST apply those commands, repackage, and **re-present this checklist** with the modified scripts before proceeding to InstallApplication. The user MUST see and confirm the actual commands that will run.

**G3 — wait_ready loop (60s hard wait + 5s-interval probes)**
```bash
# T0~T60: hard wait
echo "$(date '+%H:%M:%S') [wait_ready] T0: 60s hard wait"
sleep 60
# T60~T300: probe every 5s
# ... (full script in step-3 §3.2)
```
> You MUST execute the FULL loop script from step-3 §3.2 using `EcsRunCommandSync` (probes `localhost` from inside the ECS). Ad-hoc single `curl` or `ps aux` commands are NOT acceptable. **Do NOT substitute with a direct `curl` to the ECS public IP** — security groups typically block inbound application ports, causing false timeouts even when the service is healthy internally.

**G4 — Skill CLI required for ECS instance queries (no exceptions)**
```bash
# CORRECT — use skill CLI
cadt-deploy-on-aliyun -run EcsGetDesc '{"regionId":"cn-hangzhou","instanceId":"i-bp1xxx"}'

# WRONG — direct ECS API bypass (critical violation, ALL forms forbidden)
aliyun ecs describe-instances --region-id cn-hangzhou
aliyun ecs describe-instances --region-id cn-hangzhou --instance-ids '["i-bp1xxx"]'
aliyun ecs describe-instance-attribute --instance-id i-bp1xxx
```
> All ECS instance information queries MUST go through `cadt-deploy-on-aliyun -run EcsGetDesc` (single) or `EcsGetDescList` (batch). The skill CLI ensures normalized responses, `--user-agent` propagation, and auditable operation logs. **If the skill CLI is unavailable (e.g., bootstrap failed), you MUST fix it before querying ECS info — using raw `aliyun ecs` as a workaround is still a critical violation.**

## Context Budget Management

This workflow has 3 major context-consuming phases: [step-1] init, [step-2] build, [step-3] deploy. Long builds (Maven downloading dependencies, npm install, etc.) can consume a large portion of the context window, leaving insufficient room for step-3.

**Rules:**

1. **After any build that takes more than 30 seconds**, immediately proceed to step-3 without re-reading SKILL.md or step files. The build output is already in context — do not re-summarize it.

2. **Do NOT re-read step-2-build.md or step-3-deploy.md after the build completes.** These files are large and will consume critical context budget. Read them ONCE during step-1/step-2, then proceed from memory.

3. **Minimum context reservation for step-3**: Before starting step-2 build, estimate the build size. If the build will produce verbose output (Maven downloading hundreds of JARs, npm install with thousands of packages), use `-q` (quiet) flags to suppress progress output:
   ```bash
   mvn -DskipTests package -q          # Maven quiet mode
   npm install --silent && npm pack    # npm silent mode
   pip install build -q                # pip quiet mode
   ```

4. **If context is running low after build**: Skip re-verification of build artifacts (the build exit code is sufficient) and proceed directly to script injection + repackaging + G4 + InstallApplication.

## Standalone Entry Point

The user directly provides the following information:

- **`regionId`** (required): ECS instance region, e.g. `cn-hangzhou`
- **`instanceIds`** (required): ECS instance IDs, e.g. `i-bp1xxxxx`
- **`appName`** (required): application name, e.g. `my-app`
- **Build info** (optional, if building from source): `language`, `languageVersion`, `buildTool`

All data is user-provided; no project/environment ID lookups needed.

> **⛔ No auto-discovery (critical)**: `regionId` and `instanceIds` MUST come from the user's explicit input. Do NOT auto-discover them from CLI configuration (`aliyun configure list`), API enumeration (`aliyun ecs describe-instances`), environment variables, or any other automated source. If not provided by the user, you MUST ASK-USER. See [step-1] §5.1–5.2 for details. Deploying to an auto-selected region or instance is a critical violation.

## Dependencies

| Tool | Purpose |
|------|------|
| `cadt-deploy-on-aliyun` CLI (built-in) | Operation dispatch (`cadt-deploy-on-aliyun -run <Op>`) |
| `aliyun` CLI | STS / OSS / ECS API |
| `jq` | JSON parsing |
| `bash` 4.0+ | Script execution |

## Observability (MUST follow for every aliyun command)

Upon loading this skill, generate a random session ID (32-char lowercase hex string) once for the entire session. Use it as `{session-id}` below.

**Rule: Every `aliyun` CLI command that calls a cloud API MUST include the `--user-agent` flag.**
Local utility commands (e.g. `configure`, `plugin`, `version`) do not support this flag and should be excluded.

```
--user-agent AlibabaCloud-Agent-Skills/alibabacloud-cadt-deploy-on-aliyun/{session-id}
```

### Propagation paths (choose the right one per context)

| Context | How to propagate | Who adds `--user-agent` |
|---------|-----------------|------------------------|
| `cadt-deploy-on-aliyun -run` / `-poll` | `export SKILL_SESSION_ID={session-id}` once per shell | CLI auto-injects into all internal `aliyun` calls |
| Direct `aliyun` CLI calls | Append `--user-agent ...` inline on every command | You (the agent) must add it manually |
| Python/bash scripts | `SKILL_SESSION_ID={session-id} python3 script.py` | Script reads env var and adds `--user-agent` |

### Path A: cadt-deploy-on-aliyun CLI (recommended)

Export `SKILL_SESSION_ID` **once** at session init (see [step-1] §4). The CLI automatically propagates it to all internal `aliyun` subprocess calls — you do NOT need to add `--user-agent` to each `-run` / `-poll` invocation:

```bash
export SKILL_SESSION_ID={session-id}
cadt-deploy-on-aliyun -run InstallApplication '{"regionId":"cn-hangzhou",...}'
```

Alternatively, pass `--user-agent` directly on the CLI command line (the CLI extracts the session-id and sets it for the current invocation):

```bash
cadt-deploy-on-aliyun -run InstallApplication '{"regionId":"cn-hangzhou",...}' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cadt-deploy-on-aliyun/{session-id}
```

### Path B: Direct aliyun CLI calls

When calling `aliyun` directly (not through `cadt-deploy-on-aliyun`), you MUST append `--user-agent` on every command:

```bash
aliyun bpstudio get-token --api-version 2021-09-31 --region cn-hangzhou \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cadt-deploy-on-aliyun/{session-id}
```

Do not skip, alter the format, or omit `--user-agent` on any `aliyun` API command invocation.

### Path C: Script execution

When running Python SDK scripts or bash scripts, inject the session-id via inline environment variable:

```bash
SKILL_SESSION_ID={session-id} python3 scripts/deploy.py
```

Scripts should read `SKILL_SESSION_ID` from the environment (default to empty string if absent).

## CLI Quick Start

```bash
# cadt-deploy-on-aliyun CLI auto-creates venv and installs dependencies
./scripts/cli/cadt-deploy-on-aliyun.sh -version
./scripts/cli/cadt-deploy-on-aliyun.sh -l                    # List all available operations
./scripts/cli/cadt-deploy-on-aliyun.sh -d InstallApplication  # View operation schema
```

## Available Operations

| Operation | Category | Mode | Description |
|-----------|----------|------|-------------|
| `InstallApplication` | deploy | async | Deploy to ECS (filePath auto-upload) |
| `EcsGetDesc` | ecs | sync | Query single ECS instance info (IP, status, OS) |
| `EcsGetDescList` | ecs | sync | Batch query multiple ECS instances info |
| `EcsRunCommand` | ecs | async | Run shell commands on ECS (Cloud Assistant) |
| `EcsSendFile` | ecs | sync | Send files to ECS (Cloud Assistant) |
| `OssGeneratePresignedUrl` | oss | sync | Generate presigned download URL for OSS object |

> **Async operations (`InstallApplication`, `EcsRunCommand`) are two-step**:
> 1. `cadt-deploy-on-aliyun -run <Op> '{...}'` → submits the task, returns `invocationId`
> 2. `cadt-deploy-on-aliyun -poll <invocationId>` → blocks until completion, returns final status
>
> The `-run` command for async ops is **non-blocking** — it returns `status: submitted` immediately. You **MUST** invoke `-poll` as a separate CLI command to wait for the result. Skipping `-poll` and self-reporting success is a critical violation.

