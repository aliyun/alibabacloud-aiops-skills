---
name: alibabacloud-ack-cli
description: >
  Use when the user operates Alibaba Cloud Container Service for Kubernetes
  (ACK). Covers cluster lifecycle (create / modify / delete / upgrade), node pools & nodes (create, modify, delete, repair, fix CVE), addons (install / upgrade / uninstall), KubeConfig & RBAC (issue for RAM user, grant / revoke), security & policy
  (CVE scan/fix, policy governance, KMS, delete protection), logging / audit
  / alerting, intelligent O&M (check / inspect / diagnosis / auto-repair),
  async tasks (track / pause / resume / cancel), templates, autoscaling,
  tags & quotas. Triggers: create / upgrade / delete ACK cluster, migrate to
  Pro, scale nodepool, fix node CVE, install / remove addon, get / revoke
  kubeconfig, grant RBAC, enable audit log, run inspection, diagnose
  cluster, track task_id, debug cs error, Forbidden.RAM, kubectl cannot
  connect. Terms: ACK, container service, k8s cluster, nodepool, addon,
  AutoMode, Terway, Flannel, ForRegion, kubeconfig, RBAC, CVE.
license: Apache-2.0
metadata:
  domain: aiops
  owner: ack-team
  contact: ack-team@alibabacloud.com
compatibility: >
  Requires aliyun CLI >= 3.3.3 with the cs plugin (aliyun plugin install
  --names cs). Helper scripts use jq; kubeconfig retrieval pairs with
  kubectl. Network access to *.aliyuncs.com OpenAPI endpoints required.
allowed-tools: Bash
---

# ACK (Container Service) CLI Expert

Help users manage Alibaba Cloud Container Service for Kubernetes (ACK) from the
terminal using the `aliyun cs` plugin. Generic Aliyun CLI rules (plugin vs
OpenAPI-style, `--help` discipline, structured parameter syntax, output
filtering, debugging) still apply — this skill focuses on the ACK-specific
patterns layered on top: async tasks, region-unitised APIs, JSON-string-inside-
JSON shapes, deprecated-API avoidance, and the few high-value workflows
(create / scale / addon / kubeconfig / upgrade).

> **Version note.** Concrete API/parameter lists below were captured against
> `aliyun-cli` 3.3.2 + `cs` plugin 0.2.1. If your plugin is newer, re-run the
> self-discovery commands embedded throughout this skill to refresh:
>
> ```bash
> aliyun cs --help | grep -- '-for-region'              # §6 ForRegion list
> aliyun cs <cmd> --help | grep '废弃'                   # §7 deprecated check per command (CLI marks deprecation only in Chinese)
> aliyun cs --help | awk '/^  [a-z]/{print $1}' | while read c; do   # §11 cursor-paginated commands
>   aliyun cs "$c" --help 2>&1 | grep -q -- '--next-token' && echo "$c"
> done
> ```

## Instructions

### 1. Install the `cs` plugin and confirm CLI version

ACK from the terminal needs the `aliyun` CLI (≥ 3.3.3) plus the `cs` plugin.
Quick path:

```bash
aliyun version                          # require >= 3.3.3
aliyun plugin install --names cs        # idempotent
aliyun plugin update  --names cs        # keep cs plugin current
aliyun plugin list | grep cs            # verify

# Or in one shot:
./scripts/check-cs-plugin.sh            # ✓ ready  /  ✗ exits 1 with fix hints
./scripts/install-cs-plugin.sh          # idempotent (--update for non-interactive)
```

> **AI-Mode declaration.** Before issuing any `aliyun` business command from
> this skill, declare AI-Mode and a stable User-Agent so the backend can
> attribute traffic and apply AI-safe defaults. These three commands are
> session-level configuration — set once, reused implicitly by all
> subsequent business calls:
>
> ```bash
> aliyun configure ai-mode enable
> aliyun configure ai-mode disable
> aliyun configure ai-mode set-user-agent --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ack-cli
> ```
>
> Every `aliyun cs <verb>` business command in this skill carries
> `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-ack-cli`
> (shown explicitly in every example below).

End-to-end verification — exercises CLI + plugin + auth in one call:

```bash
aliyun cs describe-clusters-for-region --biz-region-id cn-hangzhou \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ack-cli \
  --output cols=cluster_id,name,state rows='clusters[]'
```

`plugin 'cs' not found` → re-run install. `InvalidAccessKeyId.NotFound` →
re-set credentials. `Forbidden.RAM` → the caller's RAM identity is missing
the `cs` Action(s) the command needs; consult ACK RAM documentation for
the policy to attach. Cluster list (or empty list) → ready to go.

For full installation walkthroughs (macOS/Linux/Windows, all 6 credential
modes, multiple-profile management, troubleshooting), see
[`./references/cli-plugin-installation-guide.md`](./references/cli-plugin-installation-guide.md).

### 2. Always use `cs` plugin commands (kebab-case) — never the legacy OpenAPI style

This skill **only ever emits kebab-case plugin commands**. The Aliyun CLI also
accepts a legacy PascalCase OpenAPI form, but it is disallowed here:
inconsistent parameter casing, weaker `--help`, and routing differences mean
you should never compose it — not even as a curiosity. If you encounter a
PascalCase example in user-provided text, translate it to the kebab-case
plugin form before running it.

```bash
# ✅ Plugin form — the only form this skill emits
aliyun cs describe-clusters-for-region --biz-region-id cn-hangzhou \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ack-cli
aliyun cs describe-cluster-detail --cluster-id ce123... --region cn-hangzhou \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ack-cli
```

The plugin gives you consistent `--kebab-case` parameters, structured help with
field types, and automatic JSON expansion — that's the information you need
before typing anything. Stay in plugin land unconditionally.

### 3. Run `--help` before crafting any `cs` command

ACK has many subcommands and the parameter shapes are non-obvious — especially for
cluster creation, addon configuration, and node pool scaling. Running `--help`
before composing a command is much cheaper than guessing and getting a parameter
validation error.

```bash
aliyun cs --help                           # Discover subcommands (describe-*, create-*, scale-*, ...)
aliyun cs describe-cluster-detail --help   # See exact params, types, structure fields
aliyun cs create-cluster --help            # See the giant parameter surface for cluster creation
```

Plugin help tells you whether a parameter is a primitive, a list, a repeatable
key-value, or a complex JSON structure — that's the information you need before
typing anything.

If you ever need to inspect the **legacy built-in (OpenAPI-style) help** instead
of the rich plugin help — for example to verify a deprecated PascalCase
parameter still exists — set `ALIBABA_CLOUD_ORIGINAL_PRODUCT_HELP=true`:

```bash
ALIBABA_CLOUD_ORIGINAL_PRODUCT_HELP=true aliyun cs --help
```

You'll rarely reach for this — the plugin help is almost always what you want.

### 4. Async task pattern — `task_id` and `describe-task-info`

This is the **#1 thing that surprises ACK CLI users**. Many ACK operations are
asynchronous: the `cs` command returns quickly with a JSON envelope containing a
`task_id`, but the actual work (cluster creation, upgrade, scaling, addon install)
continues in the background. You must poll the task to know whether it succeeded.

Operations that return a task:

- `cs create-cluster`, `cs delete-cluster`
- `cs upgrade-cluster` (control plane only; control via `cs pause-task` / `cs resume-task` / `cs cancel-task`)
- `cs modify-cluster-node-pool` (the preferred way to set absolute node count via `desired_size`; see §7), `cs scale-cluster-node-pool` (delta only — discouraged, see §7), `cs upgrade-cluster-nodepool`, `cs create-cluster-node-pool`, `cs delete-cluster-nodepool`
- `cs install-cluster-addons`, `cs upgrade-cluster-addons`, `cs un-install-cluster-addons`
- Some component / migration tasks

Once you have a `task_id`, the **task-control commands work uniformly across
task types** — not just upgrades. Pause / resume / cancel any in-flight ACK
task with:

```bash
aliyun cs pause-task  --task-id <tid> --region <region> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ack-cli
aliyun cs resume-task --task-id <tid> --region <region> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ack-cli
aliyun cs cancel-task --task-id <tid> --region <region> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ack-cli
```

Use `cancel-task` to abort a stuck addon install, a runaway node pool scale,
or any other in-flight task.

Typical response:

```json
{
  "cluster_id": "ce914461c0fb4901ae8908be4a10a7a1",
  "request_id": "DDA4DB1A-A7E3-1455-A6FB-77F58F01A43E",
  "task_id": "T-69ce1022aa09ae010300000b"
}
```

Track it with:

```bash
aliyun cs describe-task-info --task-id T-69ce1022aa09ae010300000b --region cn-hangzhou \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ack-cli
```

Pass `--region` matching the cluster's region — task IDs are region-scoped
and looking them up via the default endpoint adds latency.

The task response carries `state` (running / success / failed) and an `error`
field on failure. When polling, **ask the user before starting a long busy-wait
loop** — polling burns tokens and the user may prefer to check back later. A
reasonable default is to poll every 30s with a sensible max (e.g. 30 minutes for
cluster create, 5 minutes for addon install) and surface the `error.message` if
the task fails.

The bundled helper `./scripts/wait-for-task.sh <task-id> <region-id>` polls
with backoff and prints the final state — use it after confirming with the
user. Region is required because task IDs are region-scoped.

See `./references/async-tasks.md` for full details: state machine, error fields,
typical durations per operation, and how to interpret partial-failure responses.

### 5. Complex JSON parameters — Terway, AutoMode, addons

Some ACK parameters can't be expressed cleanly as flat flags. Examples:

**Terway with multi-AZ pod vswitches** (cluster create):

```bash
# Pass the addons array as JSON. Note the nested JSON inside `config` is a STRING.
aliyun cs create-cluster \
  --biz-region-id cn-beijing \
  --region cn-beijing \
  --cluster-type ManagedKubernetes \
  --addons '[{"name":"terway-eniip","config":"{\"PodVswitchId\":{\"cn-beijing-l\":[\"vsw-a\"],\"cn-beijing-h\":[\"vsw-b\"]}}"}]' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ack-cli \
  ...
```

The trap: `config` is a JSON-encoded string inside a JSON document. Build it in a
file or via `jq` rather than hand-escaping — escape errors are the most common
cause of `InvalidParameter.Format` from this API.

**Flannel** (requires `container_cidr`, no `PodVswitchId`):

```bash
--addons '[{"name":"flannel"}]' \
--container-cidr 172.20.0.0/16 \
--service-cidr 172.21.0.0/20
```

**AutoMode** (ACK best-practice profile — single flag turns it on):

```bash
--profile Default \
--cluster-spec ack.pro.small \
--auto-mode '{"enable":true}'
```

When AutoMode is enabled, ACK chooses sensible defaults for VPC, networking,
node pools, and addons — most other knobs become unnecessary. `--cluster-spec`
valid values are only `ack.pro.small` (Pro, recommended for AutoMode) and
`ack.standard` (default if omitted) — don't guess `ack.pro.large` or others.

**Addon install with config**:

```bash
aliyun cs install-cluster-addons --cluster-id <cid> --region <region> \
  --body '[{"name":"logtail-ds","config":"{\"sls_project_name\":\"k8s-log\"}"}]' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ack-cli
```

The nested-JSON-as-string pattern shows up in nearly every addon install. Read
the addon's `config_schema` first (`cs list-addons --cluster-id ...` for the
full list, or `cs describe-addon --cluster-id ... --addon-name ...` for one)
to know valid keys. For full examples, see `./references/cs-scenarios.md`.

### 6. Region-unitised API calling — two rules

ACK has moved to a region-unitised model. Two rules apply:

**Rule A — Prefer `*ForRegion` API variants** (`describe-clusters-for-region`,
`describe-events-for-region`, `list-operation-plans-for-region`). Faster,
higher quotas, resilient when global aggregator degrades. Re-discover with
`aliyun cs --help | grep -- '-for-region'`. These APIs take `--biz-region-id`
(business parameter, required), **not** `--region`.

**Rule B — Pass `--region <region>` on every cluster-id-scoped call**
(`describe-cluster-detail`, `modify-cluster-node-pool`, etc.) once you know
the region. Routes directly to the regional endpoint, avoids default-endpoint
hop.

`--region` (CLI global, endpoint routing) and `--biz-region-id` (API business
parameter) take the same value but play different roles. There is no
`--region-id` flag. Always `--help` first to see which a command expects.

```bash
# Region-unitised + direct routing combined
REGION=cn-hangzhou
aliyun cs describe-clusters-for-region --biz-region-id $REGION --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ack-cli              # Rule A
aliyun cs describe-cluster-detail --cluster-id <cid> --region $REGION --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ack-cli       # Rule B
aliyun cs describe-cluster-node-pools --cluster-id <cid> --region $REGION --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ack-cli   # Rule B
```

### 7. Detect deprecated parameters per command

The CLI marks deprecated parameters in `--help` with the Chinese string
`【该参数已废弃】` (no English equivalent — has to be matched literally).
Run the snippet from the top of this file (`aliyun cs <cmd> --help | grep
'废弃'`) before composing any command — it surfaces both the deprecated
field and the suggested replacement (e.g. `请使用 next_version 参数替代`).
Quote that line back to the user; never silently substitute.

### 8. Common high-value commands

Examples assume the cluster's region is already known (via Rule A discovery or
from the user) and pass it as `--region` per §6 Rule B. Substitute
`<region>` with the actual value.

```bash
# Clusters
aliyun cs describe-clusters-for-region --biz-region-id <region> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ack-cli
aliyun cs describe-cluster-detail --cluster-id <cid> --region <region> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ack-cli
aliyun cs describe-cluster-user-kubeconfig --cluster-id <cid> --region <region> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ack-cli > kubeconfig.yaml
aliyun cs upgrade-cluster --cluster-id <cid> --region <region> --next-version 1.30.1-aliyun.1 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ack-cli

# Node pools
aliyun cs describe-cluster-node-pools --cluster-id <cid> --region <region> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ack-cli
aliyun cs describe-cluster-node-pool-detail --cluster-id <cid> --nodepool-id <npid> --region <region> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ack-cli

# Resize to an ABSOLUTE node count: use modify-cluster-node-pool with desired_size.
# (`scale-cluster-node-pool --count N` adds N nodes — it's a delta, not an
#  absolute target, and is rarely what users mean by "scale to 5". See §7.)
aliyun cs modify-cluster-node-pool --cluster-id <cid> --nodepool-id <npid> --region <region> \
  --scaling-group desired_size=5 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ack-cli

aliyun cs upgrade-cluster-nodepool --cluster-id <cid> --nodepool-id <npid> --kubernetes-version <ver> --region <region> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ack-cli

# Addons
aliyun cs list-addons --cluster-id <cid> --region <region> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ack-cli                       # what's available + config_schema
aliyun cs describe-addon --cluster-id <cid> --addon-name <name> --region <region> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ack-cli  # one addon's metadata + config_schema
aliyun cs list-cluster-addon-instances --cluster-id <cid> --region <region> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ack-cli      # what's installed (versions, status)
aliyun cs install-cluster-addons --cluster-id <cid> --region <region> --body '[{"name":"logtail-ds","config":"{}"}]' --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ack-cli
aliyun cs upgrade-cluster-addons --cluster-id <cid> --region <region> --body '[{"component_name":"logtail-ds","next_version":"1.8.0"}]' --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ack-cli
aliyun cs un-install-cluster-addons --cluster-id <cid> --region <region> --body '[{"name":"logtail-ds"}]' --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ack-cli

# Tasks (task IDs are region-scoped — pass the cluster's region)
aliyun cs describe-task-info --task-id <tid> --region <region> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ack-cli
aliyun cs describe-cluster-tasks --cluster-id <cid> --region <region> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ack-cli     # all tasks under a cluster
aliyun cs describe-cluster-events --cluster-id <cid> --region <region> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ack-cli    # operational events: creates, scales, addon installs
aliyun cs describe-cluster-events --cluster-id <cid> --region <region> --task-id <tid> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ack-cli  # filter to one task's events
```

For "what's been happening on this cluster recently?" / "why did the upgrade
last week fail?", `describe-cluster-tasks` and `describe-cluster-events` are
the answer. They're paginated (`--page-number` / `--page-size`); use `--pager`
for auto-merge across pages.

For any of these, append `--help` to see the full parameter set and structure.

See `./references/cs-scenarios.md` for fuller workflows.

### 9. Kubeconfig retrieval and `kubectl` handoff

```bash
# Default kubeconfig (intranet endpoint depending on cluster network)
aliyun cs describe-cluster-user-kubeconfig --cluster-id <cid> --region <region> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ack-cli \
  | jq -r '.config' > ~/.kube/config.ack

export KUBECONFIG=~/.kube/config.ack
kubectl get nodes
```

Notes:

- Some clusters expose only an intranet API server endpoint; the kubeconfig you
  fetch will only work from inside the VPC. Use `--private-ip-address true|false`
  to choose between intranet and public endpoints when both exist.
- Temporary STS-based kubeconfigs expire — re-run the command to refresh.
- For automation, prefer setting `KUBECONFIG` to a per-cluster file rather than
  overwriting `~/.kube/config`.

### 10. Filter and format output

Same pattern as the rest of the CLI: `--cli-query` (JMESPath) plus `--output`.
Useful with ACK because cluster/nodepool/addon list responses are nested:

```bash
# Just running cluster IDs and names
aliyun cs describe-clusters-for-region --biz-region-id cn-hangzhou \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ack-cli \
  --cli-query "clusters[?state=='running'].{id:cluster_id,name:name,version:current_version}" \
  --output table

# Recent operation plans (auto-upgrade, AutoMode, CVE fixes) for the region
aliyun cs list-operation-plans-for-region --biz-region-id cn-hangzhou \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ack-cli \
  --cli-query "plans[].{id:plan_id,type:type,state:state,scheduled:scheduled_time}"

# Just node pool IDs and current size
aliyun cs describe-cluster-node-pools --cluster-id <cid> --region <region> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ack-cli \
  --cli-query "nodepools[].{id:nodepool_info.nodepool_id,name:nodepool_info.name,size:status.total_nodes}"
```

### 11. Pagination — prefer cursor, auto-merge with `--pager`

Two styles: **cursor** (`--next-token` / `--max-results`, stable under
concurrent writes — preferred) and **offset** (`--page-number` / `--page-size`,
can shift mid-scan). Check `--help` to see which a command supports — cursor
wins if both are listed.

The CLI's `--pager` flag auto-merges pages either way; almost always what users
want. See [`./references/cs-scenarios.md`](./references/cs-scenarios.md)
§9 for `--pager` syntax and a hand-rolled cursor loop example.

### 12. Debugging — and dry-run before any write

ACK write operations provision real cloud resources and many are irreversible.
**Always run a write command with `--cli-dry-run` first** when the parameter
set is non-trivial — it serialises the exact payload and validates parameter
parsing without spending the call:

```bash
aliyun cs create-cluster --biz-region-id cn-beijing --region cn-beijing \
  --cluster-type ManagedKubernetes \
  --profile Default --cluster-spec ack.pro.small --auto-mode '{"enable":true}' \
  --name my-ack-cluster --kubernetes-version 1.30.1-aliyun.1 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ack-cli \
  --cli-dry-run

aliyun cs modify-cluster-node-pool --cluster-id <cid> --nodepool-id <npid> \
  --region <region> --scaling-group desired_size=10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ack-cli --cli-dry-run
```

When a `cs` command does fail, `--log-level debug` reveals the full
request/response so you can see endpoint, body, status, and the raw error:

```bash
aliyun cs describe-cluster-detail --cluster-id <cid> --region <region> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ack-cli --log-level debug
```

For specific error patterns and first-action recipes (plugin / parameter /
format / region / auth / RAM / async-task failures, plus a sample dry-run
output), see [`./references/error-catalogue.md`](./references/error-catalogue.md).

## Response format guidance

When helping a user with `cs` commands:

1. **Read intent first.** Are they investigating ("describe / list"), modifying
   ("scale / upgrade / install"), or creating? Modify/create flows almost always
   produce a `task_id` — surface that pattern early.
2. **Show the full command** with required parameters and explain non-obvious
   ones (`--region`, the JSON-string-inside-JSON for addon config, etc.).
3. **For async ops, mention `describe-task-info`** in the same response — and ask
   before busy-waiting.
4. **Suggest `--help` and `--log-level debug`** when the user is troubleshooting.
5. **Cite the cluster's region** — most "command works in cn-hangzhou but not
   cn-shanghai" issues are missing/wrong `--region`.

## References

Four reference files, all ACK-specific. Generic CLI knowledge (hidden global
flags like `--waiter` / `--header` / `--body` / `--secure`, multi-version API,
full security best practices) is the Aliyun CLI's responsibility — consult its
own documentation when needed.

1. `./references/cs-scenarios.md` — **Most useful day-to-day.** Worked
   end-to-end examples: discovery, kubeconfig, node pools, addons, cluster
   upgrade, delete, the create→wait→kubeconfig pipeline.
2. `./references/async-tasks.md` — `task_id` lifecycle, state vocabulary,
   polling strategy, common `error.code` causes, partial-failure handling.
3. `./references/cli-plugin-installation-guide.md` — Aliyun CLI install
   (macOS/Linux/Windows), credential modes summary, `cs` plugin install,
   end-to-end verification, troubleshooting. Read once at setup; come back
   for "I can't get past `Forbidden.RAM`"-class issues.
4. `./references/ram-policies.md` — RAM Actions and policy templates
   required by this skill's `aliyun cs` calls (cluster / nodepool / addon /
   task scopes).

Scripts:

- `./scripts/check-cs-plugin.sh` — Verify aliyun CLI ≥ 3.3.3 and the `cs` plugin is installed
- `./scripts/install-cs-plugin.sh` — Install or update the `cs` plugin (idempotent; supports `--update` for non-interactive)
- `./scripts/wait-for-task.sh` — Poll `describe-task-info` until terminal state (requires task ID + region)
