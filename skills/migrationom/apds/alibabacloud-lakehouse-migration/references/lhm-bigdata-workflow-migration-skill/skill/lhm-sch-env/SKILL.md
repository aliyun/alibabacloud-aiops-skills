---
name: lhm-sch-env
description: |
  Environment and session preparation skill for LHM schedule migration (non-interactive execution stage). It does three things:
  (1) Install the lhm-sch-* CLIs as needed; (2) read the **already filled-in** user configuration
  (business fields must come from the config file; credentials are NOT collected here), validate it, and
  transcribe it into a temporary session config file that subsequent sub-skills load directly;
  (3) run environment checks (network connectivity / resource group status / Agent online status).

  Triggers: validate and transcribe migration configuration, prepare the schedule migration session
  environment, check LHM API connectivity / DataWorks resource group / service agent status,
  a credential error surfacing from the aliyun CLI default credential chain, lhm-sch-ds /
  lhm-sch-read-exec / lhm-sch-deploy command not found, install or uninstall the lhm schedule migration
  CLIs, confirm whether the current target is staging or production, clean up the session config after
  migration ends.

  Do not trigger for: guiding the user to fill in the configuration template (handled by the upper-level
  entry flow); and concrete migration business operations (creating data sources, exploring/converting
  workflows, deployment & upload), which are handled by lhm-sch-ds, lhm-sch-read-exec, and
  lhm-sch-deploy respectively.
---

# LHM Schedule Migration Environment and Session Preparation

The four stages of schedule migration (data source preparation → exploration → conversion → deployment) share the same environment. This skill is the **only** place that handles environment preparation and the session config (credentials themselves are resolved by the aliyun CLI default credential chain):

```
User-filled lhm_credentials.json ─→ Validation (business fields required) ─→ Session config (temp directory) ─→ Environment check (full) ─→ Sub-skills load it directly
```

**Responsibility boundaries**:
- This skill is responsible for: **the `aliyun-cli-lhm` plugin pre-gate (see below)**, installing CLIs, validating existing configuration, transcribing the session config, environment checks (connectivity / resource group / Agent), and session cleanup. **It contains no user interaction whatsoever**.
- The upper-level flow (main process) is responsible for: delivering the template to the user, explaining the fields, waiting for the user to fill them in, and handling the blockers reported by this skill.
- The three execution sub-skills: **perform no environment validation at all** and execute business commands directly; their CLIs load the session config automatically. The single exception is the plugin pre-gate, which they must honour as a hard stop rather than re-validate themselves.
- The session config only needs to be prepared once; unless the user changes the configuration or the credentials expire, re-transcription is unnecessary. However, **the CLIs must be reinstalled every time** (see "CLI Installation Strategy" below).

> **⚠️ CLI Installation Strategy (must be followed)**
>
> All `lhm-sch-*` CLIs (including this skill's own `lhm-sch-env`) are installed via `uv tool install` as
> **non-editable** packages — they cannot detect whether the source code has changed. Therefore, **every
> time this skill is invoked, all CLIs required by the current stage must be reinstalled unconditionally**
> before running `setup_session.sh`.
>
> **⚠️ Serial Execution Required (No Parallelism)**: The CLI installation scripts **must be executed serially — one at a time, in any order**. They **cannot be run in parallel or concurrently**. Each `install.sh` script must fully complete before the next one begins. There is **no required ordering** among the scripts; they may be executed in any sequence, but never simultaneously. This prevents race conditions and resource conflicts during package installation.

## Execution

> ⛔ **Plugin pre-gate — runs before Step 0 (mirrors the LHM dispatcher's Step 2.1 Hard Stop Gate)**
>
> Every `lhm-sch-*` CLI reaches the service through `aliyun lhm <command>`, which requires the
> `aliyun-cli-lhm` plugin (>= 0.1.1). Confirm that `~/.aliyun/plugins/aliyun-cli-lhm/manifest.json`
> exists **before** reinstalling any CLI. If it is missing, run the dispatcher's
> `scripts/install_lhm_plugin.sh` once and treat a non-zero exit as fatal: report the environment error
> verbatim — including its printed installation instructions — and stop.
>
> On such a failure do **not** proceed to Step 0. Reinstalling the CLIs cannot repair a missing plugin:
> they all shell out to `aliyun lhm` and would fail at the first call, so a successful `uv tool install`
> is never evidence that the environment is usable. Equally, do **not** ask the user for the source/target
> data source name or any other business parameter while the plugin is unavailable — collecting an answer
> that cannot be used only wastes a round trip.

**Every invocation must follow this order** (the plugin pre-gate and Step 0 must not be skipped):

```bash
# ── Step 0: unconditionally reinstall all CLIs required by the current stage (mandatory every time) ──
# stage all (default): install all four CLIs
(cd skill/lhm-sch-env      && bash install.sh)
(cd skill/lhm-sch-ds       && bash install.sh)
(cd skill/lhm-sch-read-exec && bash install.sh)
(cd skill/lhm-sch-deploy   && bash install.sh)

# If only a specific stage is needed, install only the CLIs it uses:
#   --stage ds        → only lhm-sch-env + lhm-sch-ds
#   --stage read-exec → only lhm-sch-env + lhm-sch-read-exec
#   --stage deploy    → only lhm-sch-env + lhm-sch-deploy
#
# ⚠️ --stage also decides which business fields are mandatory:
#   --stage ds  → migration source/target data source names are NOT required (a data-source-only
#                 session never runs the migration chain, so demanding them would falsely report
#                 "session not ready" and push the caller into asking the user for unrelated
#                 migration parameters)
#   any other stage (or no --stage) → both names remain mandatory blockers

# ── Step 1: validate config + transcribe session file + environment check ──
bash scripts/setup_session.sh                    # all stages: transcribe session config + environment check
bash scripts/setup_session.sh --stage ds         # data source management only (no migration names needed)
bash scripts/setup_session.sh --stage read-exec  # stages 2-3
bash scripts/setup_session.sh --stage deploy     # stage 4
bash scripts/setup_session.sh --from <path>       # explicitly specify the user config file
bash scripts/setup_session.sh --check-only       # validate only, no session file written, no checks
bash scripts/setup_session.sh --skip-env-check   # skip the environment check (not recommended)
bash scripts/setup_session.sh --json             # machine-readable output
bash scripts/setup_session.sh --print-path       # print the session config file path
bash scripts/setup_session.sh --cleanup          # delete the session config after migration ends
```

**Exit codes: `0` = session ready, business stages may proceed; `1` = blockers exist (missing required configuration or environment check failed); handle them per the "Remediation Guidance" below and rerun.**

## Input: The Filled-In User Configuration

> **Guiding the user to fill in the configuration is NOT part of this skill.** Template distribution,
> field explanations, and waiting for the user's input are completed in the upper-level flow (main
> process). This skill only reads an **existing** configuration and transcribes it; it does not ask the
> user questions, does not fill in fields on the user's behalf, and does not collect or echo any
> credentials (they are resolved by the aliyun CLI default credential chain at call time).

Config file lookup order: `--from` > `$LHM_CREDENTIALS_FILE` > `./config/lhm_credentials.json` > `~/.lhm/credentials.json`. Placeholders `<YOUR_...>` are always treated as unfilled.

Fields that are read (`config/lhm_credentials.template.json` serves as the structural reference).
**Business config fields are mandatory and must be written in the config file**; placeholders `<YOUR_...>` and template example values (such as the example value standing in for the name of the data source to be migrated) are always treated as unfilled. Credential fields are NOT part of the config file; credentials are resolved through the default credential chain (environment variables, RAM Role, or `~/.alibabacloud/credentials`).

> **Note**: `endpoint` and `region_id` are read from the `lhm` section of the config file (`lhm.endpoint` / `lhm.region_id`; the flat top-level keys are also accepted) and transcribed into the session config, so that every sub-skill attaches them to **each** `aliyun lhm` call as the fixed parameters `--endpoint` / `--region`. When they are absent, the CLIs fall back to the environment variables (`LHM_ENDPOINT` / `REGION_ID`) and then to built-in defaults; explicit CLI arguments (`--endpoint` / `--region`) always take the highest precedence.

| Field | Required | Behavior when missing |
|-------|----------|----------------------|
| `migration.source_data_source_name` | Yes — migration stages only (not `--stage ds`) | Report a blocker; the upper level extracts it from the trigger phrase and back-fills it |
| `migration.target_data_source_name` | Yes — migration stages only (not `--stage ds`) | Same as above |
| Credentials | N/A | Resolved via the aliyun CLI default credential chain; not collected or stored here |

> **Stage-scoped requirements**: `--stage ds` prepares a session for **data source management only** (create / name check / metadata upload / connectivity test). The migration chain never runs in such a session, so the two migration data source names are neither required nor reported as blockers — the script records a warning stating that they were not validated. Every other stage keeps them mandatory. Callers must pass the stage that matches their actual scope; a data-source-only flow must **not** run the stage-less (`all`) form.

> `migration.convert_task_id` is **not filled in by the user**: it is automatically written back into the
> session config after stage 3 (lhm-sch-read-exec's `convert-start`) succeeds, so stage 4 can use it
> directly. When rerunning this script, the already-written-back value is **preserved**; but if the
> source/target data source has changed, the old task no longer matches and is discarded with a warning.

## Output: The Session Config

After validation passes, the script **creates a dedicated directory for this session** and writes:

```
/tmp/lhm-sch-session-<uid>/s-<timestamp>-<random>/session.json   # directory 0700, file 0600
/tmp/lhm-sch-session-<uid>/current                               # pointer: absolute path of the current session
```

- Every session preparation generates a new session subdirectory, preventing multiple QoderWork sessions
  from sharing one directory and overwriting each other's configurations or mistakenly reusing leftover
  `readexec.json`/result packages.
- The root directory is **fixed and derivable**, independent of `$TMPDIR` (whose value is inconsistent
  across terminal/CI/sandbox, which would cause sub-skills to compute a different path and silently ignore
  the session config).
- Sub-skill CLIs resolve in the order `$LHM_SESSION_FILE` > `current` pointer > legacy fixed path; no
  parameters need to be passed for serial usage. When **parallel** sessions run on the same machine, the
  pointer points to the last prepared session; in that case each session should prefix its commands with
  `LHM_SESSION_FILE=<its own session.json>` to avoid interference.
- Located in the system temp directory, it naturally expires after a machine reboot; the `uid` suffix
  avoids risks in a shared `/tmp`.

The session config uses the same **flat structure** as `config/lhm_credentials.template.json` (sub-skills read by top-level keys of the same names and no longer need to care about environment variables); keys starting with `_` are metadata, and `convert_task_id` / `convert_task_created_at` are written back at runtime by stage 3:

```json
{
  "_generated_by": "lhm-sch-env/scripts/setup_session.sh",
  "_generated_at": "...",
  "_source": "config/lhm_credentials.json",
  "_note": "Credentials are resolved via default credential chain, not stored here",
  "endpoint": "...",
  "region_id": "...",
  "source_data_source_name": "...",
  "target_data_source_name": "...",
  "convert_task_id": "written back by stage 3",
  "convert_task_created_at": "written back by stage 3"
}
```

Sub-skill reads/writes of this file:

| Sub-skill | Behavior |
|-----------|----------|
| lhm-sch-ds / lhm-sch-read-exec / lhm-sch-deploy | Read `endpoint` / `region_id`; credentials resolved via default credential chain |
| lhm-sch-read-exec (when `convert-start` succeeds) | Write back the top-level `convert_task_id`, preserving the other fields and the 0600 permissions |
| lhm-sch-deploy | Preferentially obtain task_id from `convert_task_id` |

### Field Value Precedence

**Business config fields must come from the config file**. Credentials are resolved through the default credential chain independently of the config file.

Read order on the sub-skill side: **session config > user config file** for business fields; **default credential chain** for credentials; explicit CLI arguments (`--endpoint` / `--region`) still take highest precedence.

## Environment Check (lhm-sch-env check)

After the session config is written successfully, `setup_session.sh` **automatically runs** `lhm-sch-env check --profile full`; the session is considered ready (exit 0) only when all three checks pass. It is not run with `--check-only` / `--skip-env-check`. It can also be rerun manually on its own (the CLI is installed via `bash install.sh` in this skill's directory; credentials are loaded automatically per the precedence above):

```bash
lhm-sch-env check                            # default profile=schedule
lhm-sch-env check --profile full             # all three checks mandatory
lhm-sch-env check --session-file <path>      # explicitly specify session.json
lhm-sch-env check --json                     # machine-readable output
```

**Exit codes: `0` = no blocking failures; `1` = blocking failures exist; handle them per each item's remediation guidance and rerun.**

### Check Items

| Check item | Content | Pass condition | Remediation direction on failure |
|------------|---------|----------------|----------------------------------|
| Network connectivity `api_connectivity` | Uses `GetDataCheckTaskList` as a probe to verify the LHM API is reachable | Call succeeds | Verify the aliyun CLI default credential chain is configured (`aliyun configure` / environment variables / RAM Role), that RAM permissions include LHM, and that the network can reach Alibaba Cloud APIs |
| Resource group status `resource_group` | Calls `GetLhmDWResourceGroupStatus` to query the DataWorks resource group binding status | Status is `Normal` | Not bound: bind a Serverless resource group in the LHM console; abnormal status (Creating/CreateFailed/Stop, etc.): handle it in the DataWorks console |
| Agent online status `agent` | Calls `GetLhmAgentStatus` to query the service agent's online status | Status is `Online` | Not configured: apply for a License and install the service agent in the LHM console; offline: log in to the ECS and check the Agent process and logs |

The probes always run; credentials are resolved by the aliyun CLI default credential chain at call time. If credentials are missing or wrong, the affected check fails with the real API error (marked `blocking`) rather than being skipped, and the CLI prints the corresponding remediation guidance (including console links) alongside the results.

### Profiles

| profile | Mandatory items | Optional items |
|---------|-----------------|----------------|
| `schedule` (default) | api_connectivity | resource_group, agent |
| `data-validation` | all three | — |
| `full` | all three | — |

Only blocking failures of **mandatory items** cause exit code `1`; failures of optional items only produce a notice and do not block. `setup_session.sh` always uses `full` for its automatic check; for manual reruns, `schedule` suffices for day-to-day use.

## Remediation Guidance

### 1. CLI Installation

All CLIs are installed via `uv tool install` as **non-editable** packages, which cannot detect whether the source code has changed. Therefore, **every invocation of this skill must unconditionally reinstall all CLIs required by the current stage** (even if `command -v` already finds them). If `uv` is not installed, install it first:

```bash
curl -LsSf --connect-timeout 10 --max-time 120 https://astral.sh/uv/install.sh | sh
```

Installation commands (relative to the `../../../../skill` directory containing this skill):

| CLI | Install command |
|-----|-----------------|
| `lhm-sch-env` | `cd skill/lhm-sch-env && bash install.sh` |
| `lhm-sch-ds` | `cd skill/lhm-sch-ds && bash install.sh` |
| `lhm-sch-read-exec` | `cd skill/lhm-sch-read-exec && bash install.sh` |
| `lhm-sch-deploy` | `cd skill/lhm-sch-deploy && bash install.sh` |

CLIs required by each stage:
- Stage all (default): lhm-sch-env + lhm-sch-ds + lhm-sch-read-exec + lhm-sch-deploy
- `--stage ds`: lhm-sch-env + lhm-sch-ds
- `--stage read-exec`: lhm-sch-env + lhm-sch-read-exec
- `--stage deploy`: lhm-sch-env + lhm-sch-deploy

Uninstallation is `bash uninstall.sh` in the same directory for each.

### 2. Missing Required Fields (source/target data source names)

The business fields (source/target data source names) are not filled in the config file (environment variables are not accepted as fallbacks for them). **This skill does not solicit credentials from the user** — credentials are resolved by the aliyun CLI default credential chain; it only reports missing business fields via exit 1 + blockers, and the upper-level flow is responsible for having the user complete them and rerunning this script.

These two fields are blockers **only for migration stages**. Under `--stage ds` they are out of scope and never block — a data-source-only session is ready without them, and the upper level must therefore not treat such a session as "blocked on migration parameters" nor ask the user for those names.

The report may include locating information: the config file path that was tried (the `user_config` field) and each field's origin, to help the upper level determine whether the fields were "not filled" or "filled in the wrong place".

### 3. Common Warnings

| Warning | Handling |
|---------|----------|
| Config file and environment variables disagree | The config file's values were used; report the differences to the upper level for confirmation |
| Config file unparseable, skipped | The JSON is malformed; report the specific path and error location |
| A field is still a `<YOUR_...>` placeholder or template example value | Treated as unfilled; report the field names awaiting completion |
| User config file not found | The business fields are reported as blockers; check whether the correct working directory and path were used |
| Data source changed, convert_task_id discarded | Stage 4 must obtain the task_id again; if the old task should still be deployed, the upper level passes `--task-id` explicitly |

### 4. Environment and Region

Execute according to the parsed configuration; **do not switch environments on your own**. Decision basis: an `endpoint` starting with `lhm-pre.` is staging; one starting with `lhm.` is production. The summary must state which environment is currently targeted.

## Cleanup After the Session Ends

The session config lives in the system temp directory. After migration completes, the upper-level flow triggers cleanup:

```bash
bash scripts/setup_session.sh --cleanup
```

A machine reboot also clears it naturally (it lives in `/tmp`). **Do not copy the session config into the workspace or commit it to the repository.**

## Output Rules (must be followed)

This skill is a **non-interactive execution stage**: it does not ask the user questions, does not wait for user input, and only returns results to the upper level.

- When ready, return a one-line summary for the upper level to relay, e.g.:

  > Environment ready (environment: staging cn-hangzhou; source=dolphin_prod target=dw_target)

- When the environment check passes, likewise return a one-line summary, e.g.:

  > Environment check passed (3/3 items passed: API reachable / resource group Normal / Agent online)

- When not ready, report via exit 1 + a blocker list; **do not expose raw error text, `err_code`, or `request_id`**.
- Under no circumstances print secret values, nor OSS temporary credentials (`ak`, `signature`, `security_token`).
