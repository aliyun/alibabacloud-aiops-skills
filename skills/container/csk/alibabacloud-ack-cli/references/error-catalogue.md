# ACK CLI Error Catalogue

Quick-lookup table of the errors you'll actually hit running `aliyun cs ...`.
Meant to be grepped — find the symptom on the left, follow the action on
the right. SKILL.md cross-refs (§6, §7, etc.) point back to the relevant
instruction section.

## Contents

- [Plugin / parameter / format](#plugin--parameter--format)
- [Region / routing](#region--routing)
- [Auth / RAM](#auth--ram)
- [Async tasks (post-success but resource unhealthy)](#async-tasks-post-success-but-resource-unhealthy)
- [Sample dry-run output](#sample-dry-run-output)

## Plugin / parameter / format

| Error pattern | Probable cause | First thing to try |
| ------------- | -------------- | ------------------ |
| `Error: plugin 'cs' not found` | `cs` plugin not installed | `aliyun plugin install --names cs` (or `./scripts/install-cs-plugin.sh`) |
| `required parameter '--cluster-id' not provided` | Missing required arg | Run `aliyun cs <cmd> --help` to see the required set |
| `required parameter '--biz-region-id' not provided` (on a `*ForRegion` command) | Passed `--region` (or omitted region) where the API's own business parameter is required | Pass `--biz-region-id` (business region, required on `*ForRegion` calls); see SKILL §6. `--region` is endpoint routing, not the API parameter |
| `Error: unknown flag: --region-id` | Wrote `--region-id` (does not exist in the `cs` plugin) | Use `--region <region>` for endpoint routing, or `--biz-region-id <region>` if it's a `*ForRegion`/`create-cluster` business parameter; see SKILL §6 |
| `InvalidParameter.Format` on `addons` / `config` / `--body` | JSON-string-inside-JSON escaping wrong | Rebuild via `jq -nc '... \| tojson'` (see SKILL §5) |
| Field rejected with "deprecated" / "no longer supported" | Hit a deprecated field | Drop or replace per SKILL §7 |

## Region / routing

| Error pattern | Probable cause | First thing to try |
| ------------- | -------------- | ------------------ |
| `ErrorClusterNotFound` | Wrong region for that cluster | Check region with `cs describe-clusters-for-region --biz-region-id <r>`; pass `--region` matching the cluster |
| Stale or partial cluster list | Hitting global aggregator | Switch to `cs describe-clusters-for-region --biz-region-id <r>` (SKILL §6 Rule A) |
| Slow request → eventual success | Routing through default endpoint | Pass `--region <region>` (SKILL §6 Rule B); avoids cross-region hop |

## Auth / RAM

| Error pattern | Probable cause | First thing to try |
| ------------- | -------------- | ------------------ |
| `InvalidAccessKeyId.NotFound` | Wrong AK or AK deleted | `aliyun configure set --access-key-id ... --access-key-secret ...` |
| `SignatureDoesNotMatch` | Wrong AK secret, or whitespace in credentials | Re-paste the secret carefully |
| `Forbidden.RAM` / `NoPermission` on a `cs` Action | Caller's RAM identity lacks the Action | Attach a RAM policy that grants the required `cs` Action — consult ACK RAM documentation |
| `InvalidSecurityToken.Expired` | STS token expired | Re-issue STS credentials or switch to AK mode |

## Async tasks (post-success but resource unhealthy)

| Symptom | First thing to do |
| ------- | ----------------- |
| `task_id` returns `state=failed` | Inspect `error.code` / `error.message` from `describe-task-info` (see SKILL §4). Common causes: quota exceeded, vSwitch IP exhaustion, image pull, RAM permissions on dependent products (VPC / ECS) |
| `state=success` but resource not actually working | Check `task_result[*].data` for per-subtask status (e.g. addon install with multiple addons; one may have failed silently) |
| Task stuck in `running` for much longer than typical | For node-pool ops, inspect `task_result` for the stuck node — likely PDB / unkillable pod / taint |
| Long pause on `create-cluster` | Normal — cluster creation routinely takes 10–15 min. Track via `task_id`, don't re-issue |

## Sample dry-run output

`--cli-dry-run` prints the exact payload the CLI *would* have sent — useful
for catching JSON escaping mistakes (SKILL §5) before spending the API call:

```text
[DRY-RUN] API call would be made with the following details:
  Endpoint: https://cs.cn-hangzhou.aliyuncs.com
  Method:   POST
  Path:     /clusters
  Headers:
    Content-Type: application/json
  Body:
    {"region_id":"cn-hangzhou","cluster_type":"ManagedKubernetes",...}
```

Inspect the `Body` block to confirm your JSON-string-inside-JSON escaping
(addon `config`, Terway `PodVswitchId`, etc.) is what you intended.
