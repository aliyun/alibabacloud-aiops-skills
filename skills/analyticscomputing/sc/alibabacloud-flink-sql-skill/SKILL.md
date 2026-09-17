---
name: alibabacloud-flink-sql-skill
description: >
  Manage the full lifecycle of Alibaba Cloud Realtime Compute for Apache Flink SQL: analyze schemas, author and validate SQL, manage Drafts, Deployments, Jobs, Savepoints, Session Clusters, Catalogs, Connectors, UDFs, variables, and deployment targets, synchronize configuration to Git, and troubleshoot logs, Metrics, Checkpoints, exceptions, plans, and backpressure. Use when the user asks about Alibaba Cloud Flink, VVR, VVP, Flink SQL, its job lifecycle, or troubleshooting. Operate the platform through the Python CLI; historical Metrics use a user-supplied VVP Cookie. Verify scope and authentication before platform operations. High-risk actions usually require confirmation; explicit confirmation for the resolved target in the same request satisfies the gate.
metadata:
  allowed-tools: Bash Read WebFetch WebSearch
---

# Alibaba Cloud Flink SQL Skill

This skill covers the complete lifecycle of a Flink SQL job, from requirements analysis, SQL authoring, validation, and deployment to operations, performance assessment, and troubleshooting, through a unified CLI.

## Quick Entry

- Unified command: `python3 scripts/flink_sql_manager.py <command> [args...]`.
- Prefer this skill's bundled scripts and references. Fall back to `alibabacloud-flink-workspace-ops` only when a required workspace operation is not covered locally or the documented local path fails; first verify that skill is loaded, otherwise tell the user to install it.
- Before cloud calls, read [references/manifest.json](references/manifest.json) and initialize `SKILL_SESSION_ID` as described in [references/configuration.md](references/configuration.md#skill-identity-and-session). Missing or invalid identity data blocks cloud requests.
- Read [references/lifecycle.md](references/lifecycle.md) before starting a multi-step task.
- Before the first Ververica OpenAPI call, follow [references/configuration.md](references/configuration.md) to check the configuration and optionally initialize Git.
- Read only the references needed for the current stage; do not load all documentation at once.
- If platform commands cannot actually be run, state the missing prerequisite and provide the complete command that remains to be run. Never describe an example command as executed.

## One Lifecycle

Enter at the user's current stage and proceed along the same lifecycle:

1. **Requirements and data contract**: define the computation goal, inputs and outputs, correctness constraints, and runtime requirements.
2. **SQL authoring and static review**: translate the data contract into complete SQL and check semantics, configuration, and version compatibility.
3. **Configuration check and cloud validation**: confirm the target environment, identity, and metadata, and validate the SQL in the cloud environment.
4. **Draft and Deployment**: maintain Drafts and Deployment resources while keeping SQL, configuration, and deployed versions aligned.
5. **Start and acceptance**: start the Job with the required restore behavior and verify its runtime state and requested acceptance criteria.
6. **Operations and changes**: manage running Job instances, state, and supporting resources, and complete changes safely with read-back verification.
7. **Performance assessment and troubleshooting**: evaluate runtime behavior, identify bottlenecks or failures from evidence, and recommend actions.

Complete only the stages required by the user's goal. Do not deploy, start, stop, or delete resources without authorization. See [references/lifecycle.md](references/lifecycle.md) for command ordering.

## Platform Configuration Gate

Before any Ververica OpenAPI operation, run:

```bash
python3 scripts/flink_sql_manager.py config_doctor
```

If the workspace, namespace, or region is missing, follow [references/configuration.md](references/configuration.md): ask only for the missing real scope and save the user's optional Git settings in the same `config_init` call. Run `config_doctor` again after initialization. Continue with cloud operations only when it exits with code 0 and reports an explicit success. For any other outcome, including an unconfirmed result, stop subsequent platform commands, handle the actual error, and run the check again.

For local-only SQL design, authoring, or explanation, complete the current stage without blocking on platform configuration. Apply the gate when entering cloud validation or any later stage.

Historical Metrics use separate Cookie authentication and are not gated by the SDK credential check.

Always use real resource identifiers. When workspace, namespace, or region is missing, use the first-time initialization flow above. When a Draft ID, Deployment ID, or Job ID is missing, obtain it from user-provided information or a read-only query. Never call an API with placeholder IDs. Other than a user-provided Cookie for historical Metrics, do not accept AccessKey IDs, AccessKey secrets, tokens, or passwords. Never echo or commit credentials.

## Safety Gate

The CLI requires `--confirm` for every mutating command. The agent must also apply the following risk rules:

- **Read-only**: execute directly after the scope is clear and `config_doctor` succeeds.
- **Normal mutation**: create, update, deploy after validation, start, register, and similar actions. An explicit request to perform the action is authorization; add `--confirm` to the command. A request for options is not authorization.
- **High risk**: every `stop_*` and `delete_*` command, any restart or deployment flow that includes a stop, and destructive `execute_sql` statements such as `DROP` or `TRUNCATE`. A bare action request is not advance confirmation for a high-risk operation. If the current request explicitly confirms the high-risk action and its impact, and read-only resolution shows that the real target and strategy remain within the confirmed scope, report the resolved target and execute the CLI with `--confirm` without asking again. Otherwise, use [references/output-schemas.md](references/output-schemas.md) to restate the target, impact, strategy or irreversible consequence, and complete command, then wait for explicit confirmation.

Confirmation, including advance confirmation, applies only to the operations and targets in the current request. If multiple targets match, the scope changes, or the strategy is materially ambiguous, ask only for the missing information and do not reuse the confirmation. After a command fails, stop dependent steps. Never fabricate an ID, ticket, state, or successful result.

Automatic Git post-processing follows only an authorized and successful Deployment mutation; it does not authorize the platform mutation itself. A Git failure does not roll back the platform result. See [references/git-sync.md](references/git-sync.md) for the complete rules.

## References by Stage

- Lifecycle, deployment, updates, start/stop, acceptance, and troubleshooting order: [references/lifecycle.md](references/lifecycle.md)
- Configuration, OAuth, default credential chain, and region: [references/configuration.md](references/configuration.md)
- Git configuration, automatic triggers, artifact format, and repository protection: [references/git-sync.md](references/git-sync.md)
- Agent execution, safety, failure stopping, and reporting constraints: [references/execution-protocol.md](references/execution-protocol.md)
- Templates for high-risk confirmation and validation, deployment, start/stop, diagnosis, and failure results: [references/output-schemas.md](references/output-schemas.md)
- CLI command catalog: [references/command-reference.md](references/command-reference.md)
- Read-back and asynchronous result verification: [references/verification.md](references/verification.md)
- Error classification and recovery: [references/error-handling.md](references/error-handling.md)
- RAM and sensitive variables: [references/ram-policies.md](references/ram-policies.md)
- Performance assessment and troubleshooting: [references/diagnosis/README.md](references/diagnosis/README.md)
- Relationships among Draft, Deployment, Job, Session Cluster, and other resources: [references/product-model.md](references/product-model.md)
- OpenAPI mapping: [references/related-apis.md](references/related-apis.md)
- SQL topic index: [references/sql/README.md](references/sql/README.md)

## SQL Source Priority

1. The actual schema, SQL, error, engine version, and platform response supplied by the user.
2. Alibaba Cloud Realtime Compute for Apache Flink documentation matching the target VVR version.
3. Apache Flink documentation matching the corresponding Flink version.
4. The bundled offline references under [references/sql/README.md](references/sql/README.md).

When the user asks for the latest behavior, online support scope, or current Connector options, consult current official online documentation. Offline references alone do not prove current platform behavior.

## Output Gate

Before reporting a platform query, diagnosis, operation result, or operation confirmation, read [references/output-schemas.md](references/output-schemas.md) in the current turn, strictly follow the applicable template, and verify its field names, order, and required fields before sending. Combine results across stages; high-risk confirmation still happens before the operation.

Every conclusion must come from actual command output and read-back evidence. On failure, state the failed stage, key error, completed and unexecuted steps, and the next executable recovery action. Do not describe an accepted request, timeout, partial completion, or unconfirmed state as complete success.

## Development and Evaluation

- Agent evaluation uses `bash evals/run_skill_up.sh`; both `eval.yaml` and the cases use Skill Up v1alpha1 and produce JSON and HTML reports.
- Run live end-to-end tests with `python3 tests/live_api_e2e.py` only when authorized. Explicitly set `RUN_LIVE_FLINK_E2E=1` first, initialize `SKILL_SESSION_ID`, and use a test workspace.
