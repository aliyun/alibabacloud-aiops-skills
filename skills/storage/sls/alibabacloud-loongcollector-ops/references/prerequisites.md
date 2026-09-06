# Prerequisites, Preflight Gates & Input Contract

## 1. Preflight gates (run before any Observe/Plan/Execute)

Run `bash scripts/preflight.sh` or perform manually, in order:

1. **CLI version**: `aliyun version` >= 3.3.3 (>= 3.3.5 recommended). Missing/old -> install/upgrade (see `cli-installation-guide.md`). Installing a dependency is a local environment change; tell the user.
2. **SLS plugin**: `aliyun configure set --auto-plugin-install true`; ensure `aliyun-cli-sls` present (`aliyun plugin install --names aliyun-cli-sls`); `aliyun plugin update`. Verify with `aliyun sls --help`.
3. **Credentials**: `aliyun configure list` shows a valid profile (AK / STS / OAuth). Never read or print AK/SK. No profile -> `[BLOCKED: PREFLIGHT_FAILED] gate=credentials; no valid CLI profile is configured.`
4. **Scope**: confirm profile/account, region, project (and cluster/host for `install.deploy`). These are fixed for the request; changing any requires a new confirmation.
5. **Install adapters (only when `install.deploy` needs them)**: `bash scripts/preflight.sh --need-ecs` (ECS) / `--need-cs` (ACK) / `--need-kubectl` (**self_k8s install** or user-requested CRD). **`run-command` / kubectl missing is a warn, not a hard fail.** Missing kubectl on self_k8s **install** uses the fixed Missing kubeconfig subject from `SKILL.md` followed by `[AWAITING: KUBECONFIG]` as the **first** stop (before Observe/Plan/create-bind) — never `[BLOCKED: PREFLIGHT_FAILED]`. ACK collection uses SLS API — do not ask for kubeconfig. Missing usable SSH for `self_host` (including an alias that does not resolve) uses the fixed Missing SSH subject from `SKILL.md` followed by `[AWAITING: SSH]`; do not create cloud resources. ECS uses `aliyun ecs run-command` — do not emit `[BLOCKED: PREFLIGHT_FAILED] gate=workbench` / `gate=ecs`.

Hard-gate failure (CLI / SLS plugin / credentials / ACK CS plugin) -> emit `[BLOCKED: PREFLIGHT_FAILED] gate=<gate>; <reason>` and do not proceed.

## 2. Input contract by scenario

Collect only what the capability needs; do not use defaults for scope-changing fields.

- Cloud scope: profile, `region`, `project`, `logstore`.
- Collection scope: `scenario` (host/docker/k8s/host_agentsight), OS/arch (informational), collector version (read at runtime, see version_discovery).
- Resource objects: `machine_group`, `config_name`, target path, target logstore. `host_agentsight` uses fixed `runtime-ebpf-agentsight-config` / `ebpf-event`.
- Management plane: SLS API by default (host/Docker/K8s). Use `ClusterAliyunPipelineConfig` only when the user explicitly asks for GitOps/CR management, the kube-apiserver is reachable, RBAC allows creation, and the controller is running. Never use both planes for one config.
- Risk scope: single vs batch, prod vs test, maintenance window.
- Troubleshooting inputs: symptom, start time, sample log, expected fields, recent change.

## 3. Hard stop conditions (ask, do not guess)

- Missing `region`, or missing full `project` with no exact locator.
- Exact project prefix/locator but no full name: run one exact `list-project --project-name <prefix>` lookup; one candidate is auto-completable and must pass `get-project`, zero blocks, multiple candidates require selection.
- A constructed full name (`<prefix>-<EVAL_ACCOUNT_ID>`) is not existence proof. Observe must run `get-project --project <full-name>` before `get-log-store` / other resource gets. Skipping `get-project` on an idempotent path is a task failure.
- Missing target host/group/config that changes the execution object.
- User-provided handoff file failed and its exact fallback prefix returns zero candidates -> `[BLOCKED: RESOURCE_RESOLUTION_FAILED]`; never broaden the prefix, select an unrelated resource from another task/environment, synthesize a name, or create a replacement.
- Exact lookup returns multiple candidates -> list them and require explicit selection.
- `machine_group` needed but unknown (e.g. heartbeat/binding) -> ask; never omit `--machine-group`.
- `scenario` or `machine_identify_type` undetermined for create/onboarding.
- Collector version unconfirmed (`list-machines` empty / no `.binary` and user did not give a version string) → use the fixed Missing collector version subject from `SKILL.md` followed by `[AWAITING: COLLECTOR_VERSION]`. Do not assume a plugin family. Never ask Lens only to learn the version.

## 4. Scope boundaries

- Cloud collection/query: `aliyun sls` + local validators.
- `install.deploy` may use Workbench (ECS), user SSH (self-host), `aliyun cs` (ACK), and `kubectl` (self-k8s install; opt-in CRD). Never print kubeconfig.
- ACK first-use is in-skill: `scripts/ensure_ack_prereq.sh` (`open-ack-service --type propayasgo` + CS RAM roles). Eval hooks may do the same to pre-warm a fixture cluster; do not treat hook-only as “Skill cannot open ACK”. `create-cluster` only when the user asked; never invent `sls-eval-loop-ack` or create ECS/VPC.
- Forbidden: `kubectl exec`, `docker exec`, unbounded root shell, OOS/ChatOps, creating ECS, Windows, Sidecar, uninstall/rollback.
- No admin project, no `starops`, no internal MCP, no private console API.
- Cloud-only capabilities (`onboarding.cloud` without install, `config.*`, `lens.query`, existing evals that say no SSH) still must not SSH/kubectl.
