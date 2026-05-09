# Command Map Index

Fast intent-to-command routing for common requests.

## CLI Entry

```bash
python scripts/flink_ververica_ops.py <subcommand> [args...]
```

## Common Arguments

```bash
-w, --workspace <id>           # Core scope identifier
-n, --namespace <name>         # Default to 'default' when omitted
-r, --region_id <region>       # Recommended; if missing, run and follow command feedback
-o, --output json|table|text   # Output format (default: json)
```

## High-Frequency Routing Table

| User Intent | Command | Safety |
|-------------|---------|--------|
| "校验 SQL 语法" / "validate SQL" | `validate_sql --statement <sql>` | Read |
| "创建 SQL 草稿" | `create_draft --name <name> --content <sql> --confirm` | Mutation |
| "部署草稿" | `deploy_draft -w <workspace> -n <namespace> -r <region> --draft_id <id> --confirm` | Mutation |
| "列出作业/部署" | `list_deployments` | Read |
| "启动作业" | `start_job --deployment_id <id> --restore_strategy LATEST --confirm` | Mutation |
| "停止作业" | `stop_job --deployment_id <id> --job_id <id> --confirm` | Mutation |
| "删除部署" | `delete_deployment --deployment_id <id> --confirm` | Destructive |
| "列出 Session 集群" | `list_session_clusters` | Read |
| "创建 Session 集群" | `create_session_cluster --name <name> --confirm` | Mutation |
| "启动 Session 集群" | `start_session_cluster --session_cluster_id <id> --confirm` | Mutation |
| "停止 Session 集群" | `stop_session_cluster --session_cluster_id <id> --confirm` | Mutation |
| "删除 Session 集群" | `delete_session_cluster --session_cluster_id <id> --confirm` | Destructive |
| "查看表" | `get_tables --catalog <catalog> --database <database>` | Read |
| "添加工作空间成员" | `create_member --user_id <id> --confirm` | Mutation |
| "查看变量" | `list_variables` | Read |
| "作业诊断" | `diagnose_job --deployment_id <id> --job_id <id>` | Read |

## Disambiguation Rules

- Hard non-trigger cues are checked first. If matched, do not trigger this skill.
- Hard non-trigger cues are absolute deny-list. If matched, do not call this skill and do not hand off to other cloud-operation skills; return plain-text boundary guidance directly.
- Trigger this skill only when request can map to one concrete command in this table.
- "工作空间 + 成员/变量/部署/表/草稿/作业" always maps to this skill commands. Do not reroute to Aone project collaboration tools.
- "工作空间 + Session 集群/部署列表/启动作业/添加成员/变量" always maps to Console Ops. Never switch to `alibabacloud-flink-instance-manage`.
- Instance lifecycle requests (创建实例/购买/规格/计费) are not Console Ops. Return boundary guidance: use `alibabacloud-flink-instance-manage`.
- Other out-of-scope requests (container troubleshooting, object storage, other compute engines, billing, open-source installation) are not Console Ops. Do not trigger this skill.
- For SQL validation requests, prefer `validate_sql` command over direct textual syntax explanation.
- For "工作空间 + 添加成员 + 用户ID", always use `create_member`.
- For "工作空间 + 变量", always use `list_variables` in this skill (never Aone tools).
- For "部署草稿 draft-xxx 到工作空间 w-xxx", force route to `deploy_draft`; do not ask for real IDs before first execution.

### Boundary Check Response (Critical)
When receiving requests about instance management or when testing skill boundaries, you MUST:
1. Explicitly state: "创建 Flink 实例、扩容 Flink 实例、删除 Flink 实例、续费 Flink 实例属于 `alibabacloud-flink-instance-manage`"
2. Explicitly state: "草稿、部署、作业、Session 集群、namespace、表、成员、变量属于 `alibabacloud-flink-workspace-ops`"
3. Both statements must appear in EVERY boundary-related response

## Mandatory First-Call Rules

- For positive intents, the first actionable step after trigger must be a real command execution, not only parameter questioning.
- Do not use help-only execution (`--help`) as the first actionable step when intent is already clear.
- For SQL syntax-check requests with SQL text, the first command must be `validate_sql`.
- For "添加成员 + 用户ID", the first command must be `create_member`.
- For "工作空间 w-xxx + 变量", the first command must be `list_variables`.
- For "工作空间 w-xxx + 表", the first command must be `get_tables`.
- For "创建 Session 集群", the first command must be `create_session_cluster` in this skill (not instance-manage).
- For "部署草稿 draft-xxx 到工作空间 w-xxx default namespace", the first command must be `deploy_draft -w w-xxx -n default -r cn-beijing --draft_id draft-xxx --confirm`.
- For "启动 deployment d-xxx", the first command must be `start_job --deployment_id d-xxx -w w-xxx -n default -r cn-beijing --restore_strategy LATEST --confirm`.
- For "停止作业 j-xxx，先创建 savepoint", the first command must be `stop_job --deployment_id d-xxx --job_id j-xxx -w w-xxx -n default -r cn-beijing` with savepoint option enabled.
- For `create_draft` without SQL body, call with `--content "SELECT 1;"` first.
- For `create_draft` / `validate_sql`, include `-w/-n/-r` in first call; if missing, use placeholders (`w-xxx`, `default`, `cn-beijing`) for best-effort execution.
- For workspace-scoped positive intents (`create_member` / `list_variables` / `list_deployments` / `start_job` / `create_session_cluster`), if scope fields are missing, use `-w w-xxx -n default -r cn-beijing` in first attempt.
- For `stop_job` when deployment id is missing but job id exists, call once with `--deployment_id d-xxx` and provided `--job_id`.
- For `stop_job` with savepoint requirement, still execute `stop_job` in the same request path.
- For `create_session_cluster` requests, do not stop at `--help`; execute `create_session_cluster` command in the first request path.
- For `diagnose_job` when ids are missing, call once with `--deployment_id d-xxx --job_id j-xxx`.
- Treat placeholder ids (`w-xxx`, `d-xxx`, `j-xxx`, `draft-xxx`) as executable test ids; do not block for clarification.
- If first execution fails with `HTTP 429`/`Throttling.AllocationQuota`, retry once with the same command before returning failure.

## Safety Legend

- Read: execute directly
- Mutation: explicit user approval + `--confirm`
- Destructive: explicit delete approval + `--confirm`

## Credential Safety

NEVER output access_key_id, access_key_secret, security_token, or any credential values in commands or responses. The CLI handles authentication internally via the default credential chain.

## Escalate to Full Catalog

For uncommon commands not in this routing table, consult the full command catalog.
For multi-step procedural flows, consult the relevant playbook.
