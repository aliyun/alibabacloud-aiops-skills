# Prerequisites, Preflight Gates & Input Contract

## 1. Preflight gates (run before any Observe/Plan/Execute)

Aliyun CLI and SLS plugin setup follow the [shared requirements](../../SKILL.md#requirements).
Run `bash scripts/loongcollector/preflight.sh` or check the following manually:

1. **Credentials**: `aliyun configure list` shows a valid profile (AK / STS / OAuth). Never read or print AK/SK. If no valid profile is configured, stop and ask the user to configure credentials outside the conversation.
2. **Scope**: confirm profile/account, region, project (and cluster/host for `install.deploy`). Keep operations within the authorized scope; changing it requires user authorization.
3. **Install adapters (only when `install.deploy` needs them)**: `bash scripts/loongcollector/preflight.sh --need-ecs` (ECS) / `--need-cs` (ACK) / `--need-kubectl` (**self_k8s install** or user-requested CRD). **`run-command` / kubectl missing is a warn, not a hard fail.** For missing kubectl on self_k8s **install**, request a usable kubectl/kube-context before Observe/Plan/create-bind. ACK collection uses SLS API — do not ask for kubeconfig. For missing usable SSH for `self_host` (including an alias that does not resolve), request a working host/alias; do not create cloud resources. ECS uses `aliyun ecs run-command`; absence of Workbench is not a preflight failure.

Blocking check failure (CLI / SLS plugin / credentials / required ACK CS plugin or failed ACK availability probe) -> report the failed gate and reason, and do not proceed.

With `--need-cs`, a successful CS availability probe passes. Explicit not-enabled responses (`ErrorNotEnabled` / `cskpro` / `NotEnabled`) are warnings and allow first-use setup after installation confirmation. Other probe failures block preflight; the JSON `errors` records identify the failed step, error code and request ID when available.

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
- Exact project prefix/locator but no full name: run one exact `project list --project <prefix>` lookup; one candidate is auto-completable and must pass `project get`, zero blocks, multiple candidates require selection.
- A constructed project name is not existence proof. Observe should run `project get --project <full-name>` before `logstore get` / other resource gets, including on an idempotent path.
- Missing target host/group/config that changes the execution object.
- User-provided handoff file failed and its exact fallback prefix returns zero candidates -> stop and report failed resource resolution; never broaden the prefix, select an unrelated resource from another task/environment, synthesize a name, or create a replacement.
- Exact lookup returns multiple candidates -> list them and require explicit selection.
- `machine_group` needed but unknown (e.g. heartbeat/binding) -> ask; never omit `--machine-group`.
- `scenario` or `machine_identify_type` undetermined for create/onboarding.
- Collector version unconfirmed (`machine-group list-machines` empty / no `.binary` and user did not give a version string) → ask the user for the collector version. Do not assume a plugin family. Never ask Lens only to learn the version.

## 4. Scope boundaries

- Cloud collection/query: `aliyun sls` + local validators.
- `install.deploy` may use Cloud Assistant (ECS), user SSH (self-host), `aliyun cs` (ACK), and `kubectl` (self-k8s install; opt-in CRD). Never print kubeconfig.
- ACK first-use is in-skill: `scripts/loongcollector/ensure_ack_prereq.sh` (`open-ack-service --type propayasgo` + CS RAM roles). `create-cluster` only when the user asked; use the user-specified cluster and existing VPC.
- Forbidden: `kubectl exec`, `docker exec`, unbounded root shell, OOS/ChatOps, creating ECS, Windows, Sidecar, uninstall/rollback.
- No admin project, no `starops`, no internal MCP, no private console API.
- Cloud-only capabilities (`onboarding.cloud` without install, `config.*`, `lens.query`) still must not SSH/kubectl.
