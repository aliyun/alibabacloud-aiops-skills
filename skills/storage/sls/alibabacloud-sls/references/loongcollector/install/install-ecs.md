# ECS install (Linux)

Official host script: [LoongCollector Linux installation](https://help.aliyun.com/zh/sls/loongcollector-installation-linux).
Render commands with `scripts/loongcollector/render_loongcollector_install_cmd.py`. Execute via `aliyun ecs run-command` (Cloud Assistant), not OOS, not Workbench.

## Required inputs

- `region`, ECS `instance_id` (resolve by name with `aliyun ecs describe-instances` using the [shared observability setup](../workflow.md#4-observability))
- account relation: same-account same-region vs cross-region / cross-account
- `machine_identify_type` (IP or userdefined) before creating a machine group
- collection path (`log_path`) or a Docker scenario before onboarding

Missing instance id → ask. Missing collection path for requested onboarding → ask; do not invent `/var/log/...`.

## Channel

```bash
aliyun ecs run-command --biz-region-id <region> --type RunShellScript --timeout 600 \
  --command-content '<literal-command from render remote_command>' \
  --instance-id <ecs_instance_id>
# returns InvokeId
aliyun ecs describe-invocation-results --biz-region-id <region> --invoke-id <invoke_id> --content-encoding PlainText
```

- One remote command per `run-command`. Poll `describe-invocation-results` until `InvocationStatus` is `Success` / `Failed` / `PartialFailed` (about 10s × 30). If a delay is needed, run the wait and the next poll as separate tool calls; never use `sleep ... && aliyun ecs describe-invocation-results ...`. Read `Output` and exit code, then confirm `loongcollectord status` / `ilogtail is running`.
- Never print AK/SK. Never `StrictHostKeyChecking=no`. Do not create ECS. Do not use `workbench exec` / `aliyun ecs-workbench` / OOS.
- Preflight: `bash scripts/loongcollector/preflight.sh --need-ecs --region <r>` (`run-command` missing is a warn). Installation requires user authorization; a missing `run-command` does not itself block preflight.

## Command selection

| Relation | Action |
|---|---|
| Same account, same region | `./loongcollector.sh install ${region}` |
| Cross-region | `install ${region}-internet` or `${region}-acceleration` |
| Cross-account | also `touch /etc/ilogtail/users/${aliuid}` |
| Upgrade | `./loongcollector.sh upgrade` only — never re-run `install` to overwrite |

Userdefined identity (after user confirms): write `/etc/ilogtail/user_defined_id` through the same `run-command`.

## Installation acceptance and optional onboarding

Accept installation when status is `loongcollector is running` (or `ilogtail is running`). Stop here for installation-only requests.

When collection onboarding was requested, continue to `onboarding.cloud`:

1. Reuse or create Project / Logstore / Index / machine group (IP or userdefined).
2. Pipeline `input_file` (or user-stated `docker_stdio` / `docker_file`).
3. Bind, then U1–U6 and business `query`.

For empty U5, report that collection could not be verified and state the reason; never report collection success.

## Authorization

Installation and collection changes require user authorization. Render the installation command with `scripts/loongcollector/render_loongcollector_install_cmd.py` before execution; showing planned changes as a diff is recommended.
When collection onboarding is requested, continue after installation within the authorized scope.
If the user declines collection changes, report that only installation completed and collection was not onboarded; do not create or bind collection resources.
