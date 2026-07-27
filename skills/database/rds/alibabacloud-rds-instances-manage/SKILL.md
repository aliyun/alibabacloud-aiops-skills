---
name: alibabacloud-rds-instances-manage
description: |
  Query and manage Alibaba Cloud RDS instances in the user's own account through Alibaba Cloud CLI and official RDS, VPC, BssOpenApi, and DAS OpenAPIs.
  Use for listing or inspecting RDS instances, zones, classes, performance, logs, parameters, databases, accounts, networks, whitelists, bills, and SQL insight statistics, or for explicitly requested instance creation, parameter/specification/description changes, account creation, whitelist changes, public endpoint allocation, whitelist-template attachment, tagging, restart, and instance deletion.
  Do not use this skill to diagnose incidents, troubleshoot performance anomalies, or perform root-cause analysis; it only queries current RDS instance state and executes the explicitly supported instance-management operations.
---

# Alibaba Cloud RDS Instances Manage

Serve as an RDS instance inventory and lifecycle operations agent. Use Alibaba Cloud CLI as the only cloud API execution layer. Query the user's current cloud state before making recommendations or changes.

## Architecture

Use these boundaries:

- `aliyun rds <lowercase-command>` for RDS 2014-08-15 instance APIs.
- `aliyun vpc <lowercase-command>` for VPC 2016-04-28 network discovery.
- `aliyun bssopenapi <lowercase-command>` for BssOpenApi 2017-12-14 billing queries.
- `aliyun das <lowercase-command>` for DAS 2020-01-16 performance insight queries.
- Local `date` for `get_current_time`; do not represent it as OpenAPI.

Keep detailed action parameters in [references/related-apis.md](references/related-apis.md). Read the relevant action section before constructing a command.

## Agent Execution Contract

Make the local environment ready when command execution is available. Do not ask the user to install or upgrade Alibaba Cloud CLI when the agent can do it after obtaining any required tool approval.

Do not run a business API until all readiness gates pass:

1. `aliyun` exists and `aliyun version` is `3.3.3` or newer.
2. The required product plugin and action appear in `aliyun <product> --help` and `aliyun <product> <lowercase-command> -h`.
3. The selected Alibaba Cloud CLI profile is configured and valid.
4. The region and all required action parameters are known.

If a current public action is absent from an old CLI, upgrade the CLI. Do not silently switch to an SDK, an internal RPC action, or a guessed API name.

Default the RDS/VPC target region to `cn-hangzhou` only when the user omits a region. Always invoke DAS 2020-01-16 through its `cn-shanghai` control-plane region, even when the target RDS instance is in another region.

## Installation and Preflight

Run the readiness checks once at the start of every task:

```bash
command -v aliyun
aliyun version
aliyun configure set --auto-plugin-install true
aliyun plugin list
aliyun rds --help
aliyun configure list
```

Upgrade versions below `3.3.3` before using this skill. Re-run the checks after an upgrade.

Check only the products needed for the user's request:

```bash
aliyun rds describe-db-instances -h
aliyun vpc describe-vpcs -h
aliyun bssopenapi describe-instance-bill -h
aliyun das get-pfs-sql-summaries -h
```

If a required product plugin is unavailable, install its short name with `aliyun plugin install --names <product>` and repeat the action check.

Do not add the skill User-Agent to `command -v`, `aliyun version`, `aliyun configure`, `aliyun help`, install, or upgrade commands.

## Credential Configuration

Use an existing valid profile when possible. Prefer interactive configuration when credentials are missing:

```bash
aliyun configure --mode AK --profile rds-manage
```

Use `cn-hangzhou` as the configured region unless the user chooses another default.

Never:

- Put AccessKey IDs, AccessKey secrets, STS tokens, database passwords, or signatures in tracked files.
- Ask the user to export long-lived credentials as environment variables.
- Print raw `--cli-dry-run` output without reviewing it for sensitive request parameters.
- Infer that a profile belongs to a requested account solely from its name.

When identity must be verified, call STS and compare the returned `AccountId` with the expected account before any cloud operation:

```bash
aliyun sts get-caller-identity --profile <profile>
```

## Observability

Generate one 32-character lowercase hexadecimal session ID per user task and reuse it across all business API calls in that task:

```bash
openssl rand -hex 16
```

Use this per-command User-Agent:

```text
AlibabaCloud-Agent-Skills/alibabacloud-rds-instances-manage/{session-id}
```

Example:

```bash
aliyun rds describe-db-instances \
  --biz-region-id cn-hangzhou \
  --user-agent 'AlibabaCloud-Agent-Skills/alibabacloud-rds-instances-manage/{session-id}' \
  --profile <profile>
```

Do not use a deprecated global User-Agent configuration.

## Core Workflow

### 1. Resolve Intent and Parameters

Classify the request as read-only or mutating. Resolve the exact capability name and OpenAPI Action from the capability table below.

For every regional request:

- Preserve the user's explicit region.
- Use `cn-hangzhou` only when omitted.
- Pass plugin flag `--biz-region-id` when the action defines the OpenAPI `RegionId` parameter.
- Otherwise pass the Alibaba Cloud CLI global `--region` option.

Convert user-facing snake_case fields to the lowercase-hyphenated plugin flags documented by Alibaba Cloud CLI. Always invoke both actions and parameters in lowercase-hyphenated form (for example, `aliyun rds describe-db-instance-attribute --db-instance-id <id>`); never use PascalCase action names or flags such as `DescribeDBInstanceAttribute --DBInstanceId`.

### 2. Execute Read-only Operations

Run read-only actions without an additional confirmation after the readiness gates pass. Before claiming results are complete:

- Follow `NextToken` or page-number pagination when the request asks for all results.
- State the regions queried for regional APIs.
- Preserve resource IDs, status, engine, class, storage, network, and request IDs needed for follow-up work.
- Treat an empty result as a valid result only after checking the requested filters and region.

For all-region instance inventory, first obtain the RDS region list via `DescribeRegions`, then query `DescribeDBInstances` in each intended region. `DescribeRegions` may include deregistered regions; skip regions that fail with region-unavailable errors instead of aborting the whole inventory. Do not call a single regional page an account-wide inventory.

### 3. Enforce the Mutation Gate

Treat these 11 capabilities as mutating:

- `create_db_instance`
- `modify_parameter`
- `modify_db_instance_spec`
- `modify_db_instance_description`
- `create_db_instance_account`
- `modify_security_ips`
- `allocate_instance_public_connection`
- `attach_whitelist_template_to_instance`
- `add_tags_to_db_instance`
- `restart_db_instance`
- `delete_db_instance`

Before every mutating call:

1. Collect all required parameters. Do not invent a password, class, storage size/type, pay type, whitelist, port, VPC, vSwitch, zone, or template ID. For `delete_db_instance`, check `DeletionProtection` via `DescribeDBInstanceAttribute` first; if it is `true`, instruct the user to disable it before proceeding.
2. Query current state and validate dependencies with read-only APIs. For `create_db_instance`, call `DescribeAvailableZones` (not `DescribeRegions`) with Engine parameter to verify zone-level engine availability, then call `DescribeAvailableClasses` to query available specifications. `DescribeRegions` returns region-level zones without engine filtering and must not be used as a substitute. Use `DescribePrice` to estimate the order price when presenting the billing impact of a creation, upgrade, downgrade, or renewal.
3. Show the profile/account, region, target resource, Action, non-secret parameters, expected impact, billing or downtime risk, and read-after-write verification.
4. Ask for explicit confirmation for this exact mutation, and gate execution on the reply:
   - General approval to use the skill or implement a workflow is not execution approval; each distinct mutation in a workflow (e.g., create then delete) needs its own explicit HITL confirmation, and supplying a parameter (such as a password) is not execution approval.
   - Treat a failed, timed-out, empty (for example `[empty]`), missing, or ambiguous answer as not approved: do not execute. A confirmation tool may return an immediate empty acknowledgment while the user has not answered yet—that is a pending question, never an approval and never a final refusal; state that you are waiting for the user's reply and end the turn instead of aborting the task or re-asking in a loop. The answer may arrive as a later user message. Non-approval stands until a new explicit affirmative user reply arrives—never resume, re-decide, or re-justify the mutation in a later step of the same turn without it.
   - Before executing, quote the user's affirmative reply word-for-word; the quote must actually exist in this conversation as a real user message or a non-empty confirmation-tool answer. Never quote, claim, or record a confirmation that was not received—that is fabrication and a critical violation.
   - Stopping to wait for confirmation is the correct and complete outcome for that turn; never execute in order to finish the task.
5. Execute the command once after confirmation.
6. Verify through the mapped read-only API and return the OpenAPI request ID.

Do not automatically retry a mutation after a timeout, connection reset, or response-parsing failure. Treat it as an unknown state, inspect the resource with a read-only API, and ask before any retry.

Use API-level dry-run when an action supports it. For `CreateDBInstance`, prefer `--dry-run true` before asking for final confirmation. For other actions, CLI `--cli-dry-run` validates local command construction only; it does not prove authorization, inventory, pricing, or business validation. Review dry-run output for sensitive request parameters before presenting it.

### 4. Handle Sensitive Parameters

For `CreateAccount`, collect the password only when execution is imminent. The plaintext password may appear in exactly one place: the command argument passed to the CLI at execution time. Everywhere else—previews, confirmation checklists, chat replies, summaries, errors, and every saved file including action logs and execution records—write it as `<redacted>`. Never write the received password back in any note or log entry, and never store it in an eval, reference, shell script, or commit.

For whitelist changes, display the exact before/after CIDR sets. Warn before adding broad ranges such as `0.0.0.0/0`. Do not describe a broad whitelist as safe. Before executing `modify_security_ips`, explicitly list the full target `security-ips` parameter value and cross-check it against the user's original request. Ensure all IP/CIDR strings in confirmation messages, summaries, and output are character-exact matches to the intended values; do not abbreviate or truncate any octet.

For public endpoints, state that allocation exposes an Internet-reachable address but does not replace whitelist controls.

For instance deletion, warn that the operation is irreversible. Postpaid instances are released immediately; Prepaid instances may generate a refund order.

### 5. Parse Results and Errors

Return concise results with resource IDs and `RequestId`. Classify failures before recommending a next action:

- Authentication: invalid AccessKey, expired STS token, or invalid profile.
- Authorization: missing RAM action.
- Validation: missing/invalid parameter or unsupported engine/region combination.
- Capacity/quota: insufficient inventory, quota, or unsupported class.
- Billing/order: insufficient balance, unpaid order, or charge-type conflict.
- Throttling/transient service failure: wait and retry reads; do not automatically retry writes.

When an authentication, authorization, or validation error is returned, immediately stop, report the exact error type and the specific missing permission or invalid parameter to the user, and request corrective input. Do not retry the same call, and do not switch to a different API, product, or interface to obtain the data another way. Only throttling and transient service failures may be retried, and only for read-only operations. In every failure case, report the actual error; never fabricate, guess, or partially synthesize results the API did not return. Never modify the execution environment—environment variables, local configuration, simulation or test switches, or fixtures—to turn a failing call into a passing one, and never substitute locally injected or altered data for the API's real response.

Do not expose signed URLs, credentials, passwords, response headers containing secrets, or stack traces.

## Capability Map

### Read-only capabilities

| Capability | Product / Action | Key user inputs |
|---|---|---|
| `describe_db_instances` | Rds / `DescribeDBInstances` | `region_id`; optional filters and pagination |
| `describe_db_instance_attribute` | Rds / `DescribeDBInstanceAttribute` | `region_id`, `db_instance_id` |
| `describe_regions` | Rds / `DescribeRegions` | none; optional `accept_language` (`zh-CN`/`en-US`) |
| `describe_available_zones` | Rds / `DescribeAvailableZones` | `region_id`, `engine`; optional version/category |
| `describe_available_classes` | Rds / `DescribeAvailableClasses` | region, zone, engine, version, storage type, category |
| `describe_price` | Rds / `DescribePrice` | region, engine, engine version, class, storage, quantity; optional pay type, zone, storage type; `db_instance_id` plus `order_type` for upgrade/renewal pricing |
| `describe_db_instance_performance` | Rds / `DescribeDBInstancePerformance` | instance, comma-separated performance keys, UTC time range |
| `describe_monitor_metrics` | DAS / `GetPfsMetricTrends` | instance, one or more supported PFS metrics, Unix-ms time range |
| `describe_slow_log_records` | Rds / `DescribeSlowLogRecords` | instance and UTC time range |
| `describe_error_logs` | Rds / `DescribeErrorLogs` | instance and UTC time range |
| `describe_db_instance_parameters` | Rds / `DescribeParameters` | instance |
| `describe_db_instance_databases` | Rds / `DescribeDatabases` | instance; optional database and pagination |
| `describe_db_instance_accounts` | Rds / `DescribeAccounts` | instance; optional account and pagination |
| `describe_db_instance_net_info` | Rds / `DescribeDBInstanceNetInfo` | instance |
| `describe_db_instance_ip_allowlist` | Rds / `DescribeDBInstanceIPArrayList` | instance |
| `describe_vpcs` | Vpc / `DescribeVpcs` | region; optional VPC filters and pagination |
| `describe_vswitches` | Vpc / `DescribeVSwitches` | region; optional VPC/zone filters and pagination |
| `describe_bills` | BssOpenApi / `DescribeInstanceBill` | billing cycle; optional RDS instance and pagination |
| `describe_all_whitelist_template` | Rds / `DescribeAllWhitelistTemplate` | pagination; optional region/name filters |
| `describe_instance_linked_whitelist_template` | Rds / `DescribeInstanceLinkedWhitelistTemplate` | instance; optional region |
| `get_current_time` | Local `date` | none |
| `describe_sql_insight_statistic` | DAS / `GetPfsSqlSummaries` | instance, Unix-ms time range; optional SQL ID/keywords/top N |

`GetPfsMetricTrends` and `GetPfsSqlSummaries` support RDS MySQL instances with DAS Performance Insight (new version) enabled. Invoke DAS with CLI global `--region cn-shanghai`. Use `DescribeDBInstancePerformance` for RDS CPU, memory, IOPS, disk, connection, or other RDS performance keys.

### Mutating capabilities

| Capability | Rds Action | Required business inputs |
|---|---|---|
| `create_db_instance` | `CreateDBInstance` | region, engine/version, class, storage size/type, net type, pay type, initial whitelist; VPC/zone fields when applicable |
| `modify_parameter` | `ModifyParameter` | instance and parameter JSON or parameter-group ID |
| `modify_db_instance_spec` | `ModifyDBInstanceSpec` | instance and at least one target class/storage/category/pay field |
| `modify_db_instance_description` | `ModifyDBInstanceDescription` | instance and description |
| `create_db_instance_account` | `CreateAccount` | instance, account name, password |
| `modify_security_ips` | `ModifySecurityIps` | instance and exact security IP/CIDR list |
| `allocate_instance_public_connection` | `AllocateInstancePublicConnection` | instance, connection-string prefix, port |
| `attach_whitelist_template_to_instance` | `AttachWhitelistTemplateToInstance` | instance and template ID |
| `add_tags_to_db_instance` | `TagResources` | region, instance resource ID, tag key/value |
| `restart_db_instance` | `RestartDBInstance` | instance; optional node ID |
| `delete_db_instance` | `DeleteDBInstance` | instance; check DeletionProtection first. Verification MUST use `DescribeDBInstances` to confirm the instance is no longer listed or shows Released status |

## Verification

Validate the skill with [references/verification-method.md](references/verification-method.md) and [references/acceptance-criteria.md](references/acceptance-criteria.md).

Never create, change, expose, restart, delete, or charge a cloud resource solely for acceptance testing. Use live calls only for read-only capabilities. Validate mutating command structure with API dry-run or sanitized CLI dry-run.

## RAM Permissions

Grant only the actions required for the requested capabilities. See [references/ram-policies.md](references/ram-policies.md) for read-only and mutation policy examples. Do not recommend a wildcard mutation policy when a narrower policy is possible.

## References

- [references/related-apis.md](references/related-apis.md): capability-to-Action mapping, parameters, and command examples.
- [references/ram-policies.md](references/ram-policies.md): least-privilege RAM actions and policies.
- [references/verification-method.md](references/verification-method.md): static, dry-run, and live read-only verification.
- [references/acceptance-criteria.md](references/acceptance-criteria.md): required and forbidden behavior.
- [Alibaba Cloud RDS OpenAPI 2014-08-15](https://help.aliyun.com/zh/rds/developer-reference/api-rds-2014-08-15-overview)
- [Alibaba Cloud CLI RDS 2014-08-15](https://api.aliyun.com/api-tools/cli/Rds/2014-08-15)
- [Alibaba Cloud DAS OpenAPI 2020-01-16](https://help.aliyun.com/zh/das/developer-reference/api-das-2020-01-16-overview)

## Constraints

1. Obtain a separate explicit affirmative confirmation for every single mutating call. General approval to use the skill or a workflow never authorizes a mutation, one approval never covers the next mutation in a multi-mutation workflow, and supplying a parameter such as a password is not execution approval.
2. Treat a failed, timed-out, empty (such as `[empty]`), missing, or ambiguous confirmation as not approved: do not execute. An immediate empty tool acknowledgment means the user has not answered yet—it is a pending question, not a final refusal; state that you are waiting for the reply and end the turn, since the answer may arrive as a later user message. Non-approval stands until a new explicit affirmative user reply arrives—never resume the mutation without it. Ending the turn to wait is the correct and successful outcome; never execute in order to finish the task.
3. Before executing a confirmed mutation, quote the user's affirmative reply word-for-word; the quote must actually exist in this conversation. Never quote, claim, or record a confirmation that was not received—that is fabrication and a critical violation.
4. Before `create_db_instance`, call `DescribeAvailableZones` with the Engine parameter and then `DescribeAvailableClasses`. Never use `DescribeRegions` as a substitute for zone-level engine availability; use it only to enumerate regions, such as for an all-region inventory.
5. On an authentication, authorization, or validation error: stop immediately, report the exact error type and the specific missing permission or invalid parameter, and request corrective input. Never retry the same call, never switch to another API, product, or interface to obtain the data another way, never fabricate or partially synthesize results the API did not return, and never modify environment variables, configuration, or test switches to turn a failing call into a passing one.
6. Never automatically retry a mutation after a timeout, connection reset, or response-parsing failure. Treat it as an unknown state, inspect the resource with a read-only API, and ask the user before any retry.
7. Always invoke DAS 2020-01-16 through the `cn-shanghai` control-plane region, regardless of the target instance's region. Default RDS/VPC to `cn-hangzhou` only when the user omits a region; always preserve an explicit user region.
8. Never store or print AccessKey IDs, AccessKey secrets, STS tokens, or database passwords in tracked files, logs, or output. Collect the `CreateAccount` password only when execution is imminent; the plaintext password may appear only as the CLI command argument at execution time—in every other place, including every preview, checklist, summary, error, action log, and saved file, write it as `<redacted>`.
9. Collect all required parameters before a mutating call; never invent a password, class, storage size/type, pay type, whitelist, port, VPC, vSwitch, zone, or template ID.
10. For all-region inventory, first obtain the RDS region list via `DescribeRegions`, query every intended region, and follow `NextToken` or page-number pagination to completion. Never present a single regional page as an account-wide inventory.
11. Before `modify_security_ips`, display the exact before/after CIDR sets character-exact and cross-check the full target `security-ips` value against the user's original request. Warn before adding broad ranges such as `0.0.0.0/0` and never describe a broad whitelist as safe.
12. Before `delete_db_instance`, check `DeletionProtection` via `DescribeDBInstanceAttribute`; if it is `true`, instruct the user to disable it first. Warn that deletion is irreversible, and verify afterwards with `DescribeDBInstances` that the instance is no longer listed or shows Released status.
