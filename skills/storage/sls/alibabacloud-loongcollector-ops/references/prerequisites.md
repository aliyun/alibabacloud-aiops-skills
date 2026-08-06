# Prerequisites, Preflight Gates & Input Contract

## 1. Preflight gates (run before any Observe/Plan/Execute)

Run `bash scripts/preflight.sh` or perform manually, in order:

1. **CLI version**: `aliyun version` >= 3.3.3 (>= 3.3.5 recommended). Missing/old -> install/upgrade (see `cli-installation-guide.md`). Installing a dependency is a local environment change; tell the user.
2. **SLS plugin**: `aliyun configure set --auto-plugin-install true`; ensure `aliyun-cli-sls` present (`aliyun plugin install --names aliyun-cli-sls`); `aliyun plugin update`. Verify with `aliyun sls --help`.
3. **Credentials**: `aliyun configure list` shows a valid profile (AK / STS / OAuth). Never read or print AK/SK. No profile -> `[BLOCKED: PREFLIGHT_FAILED] gate=credentials; no valid CLI profile is configured.`
4. **Scope**: confirm profile/account, region, project. These are fixed for the request; changing any requires a new confirmation.

Any failed gate -> emit `[BLOCKED: PREFLIGHT_FAILED] gate=<gate>; <reason>` and do not proceed.

## 2. Input contract by scenario

Collect only what the capability needs; do not use defaults for scope-changing fields.

- Cloud scope: profile, `region`, `project`, `logstore`.
- Collection scope: `scenario` (host/docker/k8s), OS/arch (informational), collector version (read at runtime, see version_discovery).
- Resource objects: `machine_group`, `config_name`, target path, target logstore.
- Management plane: SLS API. CRD is read-only awareness (double-write detection); CRD write is out of scope.
- Risk scope: single vs batch, prod vs test, maintenance window.
- Troubleshooting inputs: symptom, start time, sample log, expected fields, recent change.

## 3. Hard stop conditions (ask, do not guess)

- Missing `region`, or missing full `project` with no exact locator.
- Exact project prefix/locator but no full name: run one exact `list-project --project-name <prefix>` lookup; one candidate is auto-completable and must pass `get-project`, zero blocks, multiple candidates require selection.
- Missing target host/group/config that changes the execution object.
- User-provided handoff file failed and its exact fallback prefix returns zero candidates -> `[BLOCKED: RESOURCE_RESOLUTION_FAILED]`; never broaden the prefix, select an unrelated resource from another task/environment, synthesize a name, or create a replacement.
- Exact lookup returns multiple candidates -> list them and require explicit selection.
- `machine_group` needed but unknown (e.g. heartbeat/binding) -> ask; never omit `--machine-group`.
- `scenario` or `machine_identify_type` undetermined for create/onboarding.
- Collector version unconfirmed while a version-gated plugin is required (see `plugin-version-gates.yaml`).

## 4. Scope boundaries

- Execution channel: `aliyun sls` + local validators only.
- No SSH / kubectl / docker exec / scp. Host-side evidence, if truly needed, is described to the user in prose (what to check, not a command to paste) and never executed by this skill.
- No admin project, no `starops`, no internal MCP, no private console API.
- Installation / lifecycle requests: reply that they are out of scope and stop that branch.
