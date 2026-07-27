# Acceptance Criteria - RDS Instances Manage

## 1. Environment readiness

### Correct

- Check Alibaba Cloud CLI and require version `3.3.3` or newer.
- Verify the exact product Action exists before use.
- Verify the selected profile and account identity without exposing secrets.
- Use `cn-hangzhou` only as the omitted RDS/VPC target-region default.
- Use CLI global `--region cn-shanghai` for DAS 2020-01-16.

### Incorrect

- Call an API before credential readiness checks.
- Guess an internal RPC when CLI help rejects an Action.
- Treat a profile name as proof of account identity.
- Print raw signed CLI dry-run output.

## 2. Capability coverage

The skill must expose exactly the requested capability surface:

- 20 read-only aliases from the supplied specification.
- 11 mutating aliases from the supplied specification.
- 30 cloud APIs in `related_apis.yaml`.
- One local-only `get_current_time` capability excluded from `related_apis.yaml` and RAM policy.

`describe_monitor_metrics` must use public DAS `GetPfsMetricTrends`. `describe_sql_insight_statistic` must use public DAS `GetPfsSqlSummaries`. The skill must not claim the unpublished `DescribeSqlInsightStatistic` Action is available through Alibaba Cloud CLI.

## 3. Observability

Every business API example and invocation must contain:

```text
AlibabaCloud-Agent-Skills/alibabacloud-rds-instances-manage/{session-id}
```

The session ID must be 32 lowercase hexadecimal characters, generated once per task and reused in that task.

System, install, upgrade, help, and credential-configuration commands must not receive the skill User-Agent.

## 4. Read-only behavior

### Correct

- Run reads after readiness gates without an extra mutation confirmation.
- Follow pagination when claiming complete results.
- Report filters and regions queried.
- Preserve resource and request IDs.
- Use RDS performance APIs for CPU, memory, IOPS, disk, and connection metrics.
- Explain DAS Performance Insight prerequisites and metric limitations.

### Incorrect

- Claim one region is the whole account.
- Claim the first page is a complete result.
- Report an empty result without checking region and filters.
- Send arbitrary CPU/IO metric names to `GetPfsMetricTrends`.

## 5. Mutation confirmation

Before every mutating call, the agent must:

1. Query current state.
2. Validate required and dependent parameters.
3. Show the exact target and non-secret parameter set.
4. State billing, downtime, connectivity, exposure, or access impact.
5. Receive explicit confirmation for that exact mutation.
6. Execute once.
7. Verify through a read-only API and report `RequestId`.

General statements such as “manage my RDS,” “implement the skill,” or “I accept the safety design” do not confirm a later live mutation.

## 6. High-risk cases

- `CreateDBInstance`: disclose automatic order/payment behavior and prefer API `DryRun=true` before final confirmation.
- `ModifyDBInstanceSpec`: disclose order, charge, restart, and transient connection risks.
- `ModifyParameter`: disclose dynamic/static parameter behavior and restart risk; do not force restart unless explicitly approved.
- `CreateAccount`: never echo or persist the real password.
- `ModifySecurityIps`: show before/after CIDRs and warn on `0.0.0.0/0`.
- `AllocateInstancePublicConnection`: disclose Internet exposure and preserve whitelist controls.
- `RestartDBInstance`: disclose service interruption and connection reset.
- `DeleteDBInstance`: query `DeletionProtection` before deletion; warn that the operation is irreversible; disclose Postpaid immediate release and Prepaid refund behavior; verify via `DescribeDBInstances` that the instance is gone; never auto-retry a failed deletion.

## 7. Ambiguous write outcomes

When a mutating request times out or the connection closes before a clear response:

- Mark the result as unknown.
- Query current state with a read-only API.
- Do not automatically retry.
- Require fresh confirmation before any retry.

## 8. Secret handling

Acceptance fails if tracked files or reported test output contain any real:

- AccessKey ID or AccessKey secret.
- STS token.
- Signed request signature or signed URL.
- Database account password.

Placeholders such as `<profile>`, `<redacted>`, and `{session-id}` are allowed.

## 9. Testing

- Standard skill validation passes.
- Required artifact and capability contract checks pass.
- All JSON and YAML artifacts parse successfully.
- CLI recognizes every documented Action.
- All 11 mutating command templates pass sanitized local dry-run construction checks.
- STS identity matches `1605970185337904` before account tests.
- Representative RDS and VPC live read-only calls pass.
- Billing and DAS live calls are marked passed, failed, or skipped based on actual permission/data prerequisites.
- No cloud resource is created, modified, exposed, restarted, deleted, or charged during acceptance testing.
