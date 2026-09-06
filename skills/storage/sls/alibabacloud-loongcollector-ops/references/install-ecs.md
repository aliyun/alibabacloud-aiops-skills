# ECS install (Linux)

Official host script: [LoongCollector Linux installation](https://help.aliyun.com/zh/sls/loongcollector-installation-linux).
Render commands with `scripts/render_loongcollector_install_cmd.py`. Execute via `aliyun ecs run-command` (Cloud Assistant), not OOS, not Workbench.

## Required inputs

- `region`, ECS `instance_id` (resolve by name with `aliyun ecs describe-instances` plus the §4 two-token `--user-agent`)
- account relation: same-account same-region vs cross-region / cross-account
- `machine_identify_type` (IP or userdefined) before creating a machine group
- collection path (`log_path`) or a Docker scenario before onboarding

Missing instance id → ask. Missing collection path after install → ask; do not invent `/var/log/...`.

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
- Preflight: `bash scripts/preflight.sh --need-ecs --region <r>` (`run-command` missing is a warn). Still ask the ECS install HITL. Do not emit `[BLOCKED: PREFLIGHT_FAILED]` before that question.

## Command selection

| Relation | Action |
|---|---|
| Same account, same region | `./loongcollector.sh install ${region}` |
| Cross-region | `install ${region}-internet` or `${region}-acceleration` |
| Cross-account | also `touch /etc/ilogtail/users/${aliuid}` |
| Upgrade | `./loongcollector.sh upgrade` only — never re-run `install` to overwrite |

Userdefined identity (after user confirms): write `/etc/ilogtail/user_defined_id` through the same `run-command`.

## Stage gate then onboard

Accept install only when status is `loongcollector is running` (or `ilogtail is running`). That is **not** full-loop success.

Then `onboarding.cloud`:

1. Reuse or create Project / Logstore / Index / machine group (IP or userdefined).
2. Pipeline `input_file` (or user-stated `docker_stdio` / `docker_file`).
3. Bind, then U1–U6 and business `get-logs-v2`.

For empty U5, use the exact no-data and reason tokens defined by the Verify contract in `SKILL.md`; never report collection success.

## HITL

Use the fixed ECS install approval subject from `SKILL.md`, followed by `[AWAITING: INSTALL_CONFIRMATION]`.
Render `scripts/render_loongcollector_install_cmd.py` before the question.
After install, use the fixed create-and-bind approval subject.
If the user cancels that second gate, emit `[CANCELLED: R2_CONFIRMATION_REJECTED]`, report that only installation completed and collection was not onboarded, and issue no `create-*` / `apply-config-*`.
