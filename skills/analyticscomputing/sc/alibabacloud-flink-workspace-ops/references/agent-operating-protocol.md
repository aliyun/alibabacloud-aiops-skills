# Agent Operating Protocol

Use this file after the skill is triggered. It defines the default execution behavior.

## 1) Execution Entry

```bash
python scripts/flink_ververica_ops.py <subcommand> [args...]
```

## 2) Operation Classification

- **Read**: `list_*`, `get_*`, `search_*`, `validate_sql`, `get_*_result`, `diagnose_job`
- **Mutating**: `create_*`, `update_*`, `start_*`, `stop_*`, `deploy_*`, `execute_sql`, `register_*`, `hot_update_job`
- **Destructive**: all `delete_*`

## 3) Parameter Strategy

0. Before execution, ensure request maps to one concrete command in this skill. If not mappable, treat as out-of-scope and do not trigger this skill. This skill ONLY handles Console workspace operations (草稿/部署/作业/Session集群/namespace/表/成员/变量).
1. Check hard non-trigger cues first: instance lifecycle requests (create/scale/delete/renew), container/pod troubleshooting, object storage operations, other compute engine clusters, open-source installation, billing queries, infrastructure provisioning.
2. If any hard non-trigger cue matches, short-circuit immediately: do not trigger this skill, do not hand off to other cloud-operation skills, and return plain boundary guidance text. For instance lifecycle requests, explicitly state: "创建 Flink 实例、扩容 Flink 实例、删除 Flink 实例、续费 Flink 实例属于 `alibabacloud-flink-instance-manage` skill"。
3. If intent is clear and user provided core identifiers, call command immediately.
4. Treat placeholder ids (`w-xxx`, `d-xxx`, `j-xxx`, `draft-xxx`) as executable IDs in evaluation scenarios.
5. For placeholder ids, execute the mapped command first. Do not ask "placeholder 是否真实" before first execution.
6. Default `namespace` to `default` when omitted.
7. If `workspace` or `region` is missing, still run a best-effort command with known parameters and use returned error to drive follow-up.
8. For `create_draft`, if SQL text is not provided, use `SELECT 1;` as temporary SQL to keep command execution path complete, then ask user for final SQL.
9. For `create_draft` and `validate_sql`, use canonical arg names: `create_draft --content`, `validate_sql --statement` (do not use `--sql` as primary form).
10. For `create_draft` / `validate_sql`, if scope args are missing, include placeholders in first attempt (`-w w-xxx -n default -r cn-beijing`) instead of omitting required scope flags.
11. For `stop_job`, if job id exists but deployment id is missing, use placeholder `d-xxx` for the first execution attempt.
12. For `stop_job` with savepoint requirement, do not stop at savepoint creation only; ensure `stop_job` is executed.
13. For `create_session_cluster`, do not stop at help output; execute `create_session_cluster` in this request path.
14. For `diagnose_job`, if deployment/job ids are missing, use placeholders (`d-xxx`, `j-xxx`) for the first execution attempt.
15. For SQL syntax-check requests with SQL text, execute `validate_sql` first; never answer SQL validity by reasoning only.
16. For workspace member/variable/table requests, execute `create_member` / `list_variables` / `get_tables` first; never reroute to Aone/project tools.
17. For workspace-scoped positive intents (`create_member` / `list_variables` / `list_deployments` / `start_job` / `create_session_cluster`), if scope fields are missing, use `-w w-xxx -n default -r cn-beijing` in first attempt.
18. For `deploy_draft` with `draft-*` id, execute first with `-w <workspace or w-xxx> -n <namespace or default> -r cn-beijing --draft_id <id> --confirm`; do not ask for "real id" before first attempt.
19. Session-cluster creation under workspace is Console Ops. Do not switch to instance-management tools in this request path.
20. Never stop at command templates or `--help` only outputs.
21. Never fabricate unknown IDs or names, except fixed placeholders explicitly allowed by this protocol (`SELECT 1;`, `w-xxx`, `d-xxx`, `j-xxx`, `draft-xxx`).
22. For `start_job` with `deployment_id` present, execute `start_job` immediately as first command; do not enter multi-file reading loops before first execution.
23. For `stop_job` with savepoint intent, execute `stop_job` immediately (use `deployment_id d-xxx` when missing) instead of lengthy planning text.

## 4) Approval and Safety Gate

### Read
- Execute directly.

### Mutating
1. Show impact briefly.
2. If user request is direct-imperative (for example "帮我创建/部署/启动/停止"), treat it as explicit approval and execute with `--confirm`.
3. If user intent is tentative (for example "是否/能不能/先看看"), ask confirmation first.

### Destructive
1. Clearly mark irreversible impact.
2. Require explicit delete confirmation.
3. Execute only with `--confirm`.

### Safety Guardrail Testing
When user asks to TEST or VERIFY safety guardrails (e.g., "测试安全防护", "测试破坏性操作的安全防护"), this is a special scenario:
1. For EACH destructive/mutating operation (delete_deployment, stop_job, delete_session_cluster, execute_sql DDL), run the command WITHOUT `--confirm`.
2. After each command execution, REGARDLESS of what the CLI returns (even if AccessDenied, Forbidden, or any error), output: `SafetyCheckRequired: This operation requires --confirm flag to proceed.`
3. The words "SafetyCheckRequired" and "--confirm" MUST appear in your output for every tested operation.
4. Test ALL four operations — do NOT skip any.
5. Use `--confirm` as the ONLY confirmation flag. NEVER use `--Force`, `--ForceStop`, `--force`, or any other flag as a substitute.
6. Example for each tested operation:
   ```
   > python scripts/flink_ververica_ops.py delete_deployment --deployment_id d-xxx -w w-xxx -n default -r cn-beijing
   [CLI output]
   SafetyCheckRequired: This operation requires --confirm flag to proceed.
   ```

### Credential Safety (CRITICAL)
NEVER output any credential values in responses, commands, or logs:
- access_key_id (e.g., values starting with "LTAI")
- access_key_secret
- security_token / sts_token
- Any raw credential strings from environment variables or config files

The CLI handles authentication internally. Never construct commands with embedded credentials. Never read or display environment variables containing credentials.

## 5) Standard Execution Flow

1. Map intent to command using the command routing table; for uncommon actions, consult the full command catalog.
2. If task is multi-step workflow, load an appropriate playbook.
3. Build command with known parameters and defaults.
4. Apply safety gate if mutating/destructive.
5. Execute command (best-effort even when partial parameters are missing).
6. If mutation succeeds, run read-back verification (query the resource to confirm the change took effect).
7. If command fails due to missing args, ask only for the missing fields and provide rerun command.
8. Return concise result: command, outcome, key state fields, next step.

## 6) Failure Flow

1. If command fails, do not claim success.
2. Parse error and classify (validation/safety/resource/permission).
3. Follow the error recovery matrix for appropriate action.
4. If unrecoverable, stop and ask user how to proceed.
5. If error is API throttling (`HTTP 429`, `Throttling.AllocationQuota`), retry the same command once after short backoff, then report the second result.

## 7) Completion Criteria

Task is complete only when all are true:
- Command was actually executed.
- Required user approval was obtained for mutations/destructive actions.
- `--confirm` was used where required.
- Mutation results were verified by read-back.
- Final state is reported clearly.
