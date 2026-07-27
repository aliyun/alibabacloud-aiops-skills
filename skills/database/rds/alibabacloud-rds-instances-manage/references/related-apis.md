# Related APIs - RDS Instances Manage

## Contents

- [Command conventions](#command-conventions)
- [Read-only capability map](#read-only-capability-map)
- [Mutating capability map](#mutating-capability-map)
- [Read-only command examples](#read-only-command-examples)
- [Mutating command templates](#mutating-command-templates)
- [Official references](#official-references)

## Command conventions

The tables use exact OpenAPI parameter names. Command examples use lowercase-hyphenated plugin flags. Capability names are user-facing aliases and are not CLI commands.

Every business call must add:

```bash
--user-agent 'AlibabaCloud-Agent-Skills/alibabacloud-rds-instances-manage/{session-id}' \
--profile <profile>
```

Region rules:

- Use plugin flag `--biz-region-id <region_id>` when the Action defines OpenAPI parameter `RegionId`.
- Otherwise use CLI global `--region <region_id>` for RDS instance-bound Actions.
- Use CLI global `--region cn-shanghai` for all DAS 2020-01-16 calls. DAS does not take the target RDS region as `RegionId`.
- Default the user's RDS/VPC target region to `cn-hangzhou` only when omitted.

Pagination rules:

- Follow `NextToken` until empty for token-based Actions.
- Follow `PageNumber`/`PageSize` until the returned page is incomplete for page-based Actions.
- Report queried regions and filters with the result.

## Read-only capability map

| Capability | Product / version / Action | Required API inputs | Important optional inputs |
|---|---|---|---|
| `describe_db_instances` | Rds / 2014-08-15 / `DescribeDBInstances` | `RegionId` | `DBInstanceId`, `Engine`, `EngineVersion`, `DBInstanceStatus`, `VpcId`, `ZoneId`, `PageNumber`, `PageSize`, `NextToken`, `MaxResults` |
| `describe_db_instance_attribute` | Rds / 2014-08-15 / `DescribeDBInstanceAttribute` | `DBInstanceId` | CLI global `--region` |
| `describe_regions` | Rds / 2014-08-15 / `DescribeRegions` | none | `AcceptLanguage` (`zh-CN`/`en-US`, default `en-US`); response may include deregistered regions |
| `describe_available_zones` | Rds / 2014-08-15 / `DescribeAvailableZones` | `RegionId`, `Engine` | `EngineVersion`, `Category`, `CommodityCode`, `ZoneId` |
| `describe_available_classes` | Rds / 2014-08-15 / `DescribeAvailableClasses` | `RegionId`, `ZoneId`, `Engine`, `EngineVersion`, `DBInstanceStorageType`, `Category` | `InstanceChargeType`, `OrderType`, `DBInstanceId`, `CommodityCode` |
| `describe_price` | Rds / 2014-08-15 / `DescribePrice` | `RegionId`, `Engine`, `EngineVersion`, `DBInstanceClass`, `DBInstanceStorage`, `Quantity` | `PayType`, `ZoneId`, `DBInstanceStorageType`, `CommodityCode`, `TimeType`, `UsedTime`, `InstanceUsedType`; `DBInstanceId` plus `OrderType` (`BUY`/`RENEW`/`UPGRADE`/`DOWNGRADE`) for upgrade or renewal pricing |
| `describe_db_instance_performance` | Rds / 2014-08-15 / `DescribeDBInstancePerformance` | `DBInstanceId`, `Key`, `StartTime`, `EndTime` | `NodeId`; CLI global `--region` |
| `describe_monitor_metrics` | DAS / 2020-01-16 / `GetPfsMetricTrends` | `InstanceId`, `Metric`, `StartTime`, `EndTime` | `NodeId`; fixed CLI global `--region cn-shanghai` |
| `describe_slow_log_records` | Rds / 2014-08-15 / `DescribeSlowLogRecords` | `DBInstanceId`, `StartTime`, `EndTime` | `DBName`, `SQLHASH`, `NodeId`, `PageNumber`, `PageSize`; CLI global `--region` |
| `describe_error_logs` | Rds / 2014-08-15 / `DescribeErrorLogs` | `DBInstanceId`, `StartTime`, `EndTime` | `PageNumber`, `PageSize`; CLI global `--region` |
| `describe_db_instance_parameters` | Rds / 2014-08-15 / `DescribeParameters` | `DBInstanceId` | CLI global `--region` |
| `describe_db_instance_databases` | Rds / 2014-08-15 / `DescribeDatabases` | `DBInstanceId` | `DBName`, `DBStatus`, `PageNumber`, `PageSize`; CLI global `--region` |
| `describe_db_instance_accounts` | Rds / 2014-08-15 / `DescribeAccounts` | `DBInstanceId` | `AccountName`, `PageNumber`, `PageSize`; CLI global `--region` |
| `describe_db_instance_net_info` | Rds / 2014-08-15 / `DescribeDBInstanceNetInfo` | `DBInstanceId` | CLI global `--region` |
| `describe_db_instance_ip_allowlist` | Rds / 2014-08-15 / `DescribeDBInstanceIPArrayList` | `DBInstanceId` | `WhitelistNetworkType`; CLI global `--region` |
| `describe_vpcs` | Vpc / 2016-04-28 / `DescribeVpcs` | `RegionId` | `VpcId`, `VpcName`, `PageNumber`, `PageSize`, `ResourceGroupId`, tags |
| `describe_vswitches` | Vpc / 2016-04-28 / `DescribeVSwitches` | `RegionId` for this skill | `VpcId`, `ZoneId`, `VSwitchId`, `PageNumber`, `PageSize`, tags |
| `describe_bills` | BssOpenApi / 2017-12-14 / `DescribeInstanceBill` | `BillingCycle` | `ProductCode=rds`, `InstanceID`, `BillingDate`, `Granularity`, `NextToken`, `MaxResults` |
| `describe_all_whitelist_template` | Rds / 2014-08-15 / `DescribeAllWhitelistTemplate` | `MaxRecordsPerPage`, `PageNumbers` | `RegionId`, `TemplateName`, `FuzzySearch`, `ResourceGroupId` |
| `describe_instance_linked_whitelist_template` | Rds / 2014-08-15 / `DescribeInstanceLinkedWhitelistTemplate` | `InsName` | `RegionId`, `ResourceGroupId`; CLI global `--region` |
| `get_current_time` | Local operation | none | Use the user's timezone when known |
| `describe_sql_insight_statistic` | DAS / 2020-01-16 / `GetPfsSqlSummaries` | `InstanceId`, `StartTime`, `EndTime` for this skill | `SqlId`, `Keywords`, `OrderBy`, `Asc`, `PageNo`, `PageSize`, `NodeId`; fixed CLI global `--region cn-shanghai` |

### Time and metric constraints

- RDS performance and log Actions use the time format required by their API, normally UTC such as `2026-07-13T00:00Z`.
- DAS `GetPfsMetricTrends` and `GetPfsSqlSummaries` use Unix timestamps in milliseconds.
- `GetPfsMetricTrends` supports the documented Performance Insight metrics `count`, `avgRt`, `rtRate`, and `rowsExamined`. Call it once per requested metric.
- Use `DescribeDBInstancePerformance` for RDS CPU, memory, IOPS, disk, connection, and engine performance keys.
- `GetPfsMetricTrends` and `GetPfsSqlSummaries` require an RDS MySQL instance with DAS Performance Insight (new version) enabled.
- For cluster-series RDS MySQL, provide `NodeId` when required.

### SQL insight aggregation

To implement `describe_sql_insight_statistic`, query `GetPfsSqlSummaries` with the requested time window. For a top-N summary, use `PageNo=1`, `PageSize=<top_n>`, `Asc=false`, and execute the requested ranking:

- `OrderBy=count` for execution count.
- `OrderBy=avgLatency` for average response time.
- `OrderBy=rowsExamined` for total scanned rows.

Do not call the internal/unpublished `DescribeSqlInsightStatistic` RPC. It is not part of the public DAS CLI Action list.

## Mutating capability map

Every Action in this table requires the mutation gate in `SKILL.md`.

| Capability | Rds Action | Required API inputs | Important optional inputs and risks |
|---|---|---|---|
| `create_db_instance` | `CreateDBInstance` | `RegionId`, `Engine`, `EngineVersion`, `DBInstanceClass`, `DBInstanceStorage`, `DBInstanceStorageType`, `DBInstanceNetType`, `PayType`, `SecurityIPList` | `InstanceNetworkType`, `VPCId`, `VSwitchId`, `ZoneId`, category, period; creates an order and may charge automatically |
| `modify_parameter` | `ModifyParameter` | `DBInstanceId` plus `Parameters` or `ParameterGroupId` | `Forcerestart`, `SwitchTimeMode`, `SwitchTime`; parameter changes can restart or destabilize the instance |
| `modify_db_instance_spec` | `ModifyDBInstanceSpec` | `DBInstanceId` plus at least one target spec field | class, storage, category, pay type, effective time; may create an order, charge, restart, or cause a transient connection impact |
| `modify_db_instance_description` | `ModifyDBInstanceDescription` | `DBInstanceId`, `DBInstanceDescription` | metadata-only but still mutating |
| `create_db_instance_account` | `CreateAccount` | `DBInstanceId`, `AccountName`, `AccountPassword` | `AccountType`, `AccountDescription`; password is secret |
| `modify_security_ips` | `ModifySecurityIps` | `DBInstanceId`, `SecurityIps` | `DBInstanceIPArrayName`, `ModifyMode`, network/security type; replacing the wrong group can remove access |
| `allocate_instance_public_connection` | `AllocateInstancePublicConnection` | `DBInstanceId`, `ConnectionStringPrefix`, `Port` | public exposure; whitelist remains an independent control |
| `attach_whitelist_template_to_instance` | `AttachWhitelistTemplateToInstance` | `InsName`, `TemplateId` | `RegionId`, `ResourceGroupId`; template contents affect access |
| `add_tags_to_db_instance` | `TagResources` | `RegionId`, `ResourceType=INSTANCE`, `ResourceId.n`, `Tag.n.Key`, `Tag.n.Value` | modifies resource metadata |
| `restart_db_instance` | `RestartDBInstance` | `DBInstanceId` | `NodeId`; causes a service interruption or connection reset |
| `delete_db_instance` | `DeleteDBInstance` | `DBInstanceId` | `DeletionProtection` must be off; irreversible; Postpaid releases immediately, Prepaid may issue refund order |

## Read-only command examples

### List RDS instances

```bash
aliyun rds describe-db-instances \
  --biz-region-id cn-hangzhou \
  --page-size 100 \
  --user-agent 'AlibabaCloud-Agent-Skills/alibabacloud-rds-instances-manage/{session-id}' \
  --profile <profile>
```

### List RDS regions and zones

Use this to enumerate regions for an all-region inventory. Do not use it as a substitute for `DescribeAvailableZones` when validating zone-level engine availability before instance creation.

```bash
aliyun rds describe-regions \
  --user-agent 'AlibabaCloud-Agent-Skills/alibabacloud-rds-instances-manage/{session-id}' \
  --profile <profile>
```

The response may include deregistered regions; skip regions that fail with region-unavailable errors instead of aborting the whole inventory.

### Query instance attributes

```bash
aliyun rds describe-db-instance-attribute \
  --db-instance-id rm-example \
  --region cn-hangzhou \
  --user-agent 'AlibabaCloud-Agent-Skills/alibabacloud-rds-instances-manage/{session-id}' \
  --profile <profile>
```

### Query an order price estimate

Use this read-only action to present the billing impact before a creation, upgrade, downgrade, or renewal confirmation. For upgrade/downgrade or renewal pricing, add `--db-instance-id <id>` and the matching `--order-type` (`UPGRADE`, `DOWNGRADE`, or `RENEW`).

```bash
aliyun rds describe-price \
  --biz-region-id cn-hangzhou \
  --engine MySQL \
  --engine-version 8.0 \
  --db-instance-class <class-code> \
  --db-instance-storage 50 \
  --db-instance-storage-type cloud_essd \
  --pay-type Postpaid \
  --quantity 1 \
  --user-agent 'AlibabaCloud-Agent-Skills/alibabacloud-rds-instances-manage/{session-id}' \
  --profile <profile>
```

### Query RDS performance

```bash
aliyun rds describe-db-instance-performance \
  --db-instance-id rm-example \
  --key 'MySQL_MemCpuUsage,MySQL_IOPS' \
  --start-time '2026-07-13T00:00Z' \
  --end-time '2026-07-13T01:00Z' \
  --region cn-hangzhou \
  --user-agent 'AlibabaCloud-Agent-Skills/alibabacloud-rds-instances-manage/{session-id}' \
  --profile <profile>
```

### Query a DAS Performance Insight metric

```bash
aliyun das get-pfs-metric-trends \
  --instance-id rm-example \
  --metric avgRt \
  --start-time 1783872000000 \
  --end-time 1783875600000 \
  --region cn-shanghai \
  --user-agent 'AlibabaCloud-Agent-Skills/alibabacloud-rds-instances-manage/{session-id}' \
  --profile <profile>
```

### Query SQL insight statistics

```bash
aliyun das get-pfs-sql-summaries \
  --instance-id rm-example \
  --start-time 1783872000000 \
  --end-time 1783875600000 \
  --order-by avgLatency \
  --asc false \
  --page-no 1 \
  --page-size 10 \
  --region cn-shanghai \
  --user-agent 'AlibabaCloud-Agent-Skills/alibabacloud-rds-instances-manage/{session-id}' \
  --profile <profile>
```

### Query RDS instance bills

```bash
aliyun bssopenapi describe-instance-bill \
  --billing-cycle 2026-07 \
  --product-code rds \
  --instance-id rm-example \
  --max-results 100 \
  --user-agent 'AlibabaCloud-Agent-Skills/alibabacloud-rds-instances-manage/{session-id}' \
  --profile <profile>
```

### Get current local time

```bash
date '+%Y-%m-%d %H:%M:%S %z'
```

Do not add `get_current_time` to `related_apis.yaml`.

## Mutating command templates

These templates describe command construction. Do not execute them without the exact mutation confirmation required by `SKILL.md`.

### Create an RDS instance

Perform API-level validation first:

```bash
aliyun rds create-db-instance \
  --biz-region-id cn-hangzhou \
  --engine MySQL \
  --engine-version 8.0 \
  --db-instance-class <class-code> \
  --db-instance-storage <storage-gb> \
  --db-instance-storage-type <storage-type> \
  --db-instance-net-type Intranet \
  --pay-type Postpaid \
  --security-ip-list '<cidr-list>' \
  --instance-network-type VPC \
  --vpc-id <vpc-id> \
  --vswitch-id <vswitch-id> \
  --zone-id <zone-id> \
  --dry-run true \
  --user-agent 'AlibabaCloud-Agent-Skills/alibabacloud-rds-instances-manage/{session-id}' \
  --profile <profile>
```

After validation, remove `--dry-run true` only after the user confirms the same parameters and billing impact.

### Modify parameters

```bash
aliyun rds modify-parameter \
  --db-instance-id rm-example \
  --parameters '{"max_connections":"1000"}' \
  --forcerestart false \
  --region cn-hangzhou \
  --user-agent 'AlibabaCloud-Agent-Skills/alibabacloud-rds-instances-manage/{session-id}' \
  --profile <profile>
```

### Modify instance specification

```bash
aliyun rds modify-db-instance-spec \
  --db-instance-id rm-example \
  --db-instance-class <target-class> \
  --db-instance-storage <target-storage-gb> \
  --pay-type Postpaid \
  --region cn-hangzhou \
  --user-agent 'AlibabaCloud-Agent-Skills/alibabacloud-rds-instances-manage/{session-id}' \
  --profile <profile>
```

### Modify description

```bash
aliyun rds modify-db-instance-description \
  --db-instance-id rm-example \
  --db-instance-description '<new-description>' \
  --region cn-hangzhou \
  --user-agent 'AlibabaCloud-Agent-Skills/alibabacloud-rds-instances-manage/{session-id}' \
  --profile <profile>
```

### Create database account

```bash
aliyun rds create-account \
  --db-instance-id rm-example \
  --account-name <account-name> \
  --account-password '<redacted>' \
  --account-type Normal \
  --region cn-hangzhou \
  --user-agent 'AlibabaCloud-Agent-Skills/alibabacloud-rds-instances-manage/{session-id}' \
  --profile <profile>
```

Replace `<redacted>` only at execution time. Never persist or echo the real password.

### Modify IP whitelist

```bash
aliyun rds modify-security-ips \
  --db-instance-id rm-example \
  --db-instance-ip-array-name default \
  --security-ips '10.0.0.0/24,192.0.2.10' \
  --modify-mode Cover \
  --region cn-hangzhou \
  --user-agent 'AlibabaCloud-Agent-Skills/alibabacloud-rds-instances-manage/{session-id}' \
  --profile <profile>
```

### Allocate a public connection

```bash
aliyun rds allocate-instance-public-connection \
  --db-instance-id rm-example \
  --connection-string-prefix <unique-prefix> \
  --port 3306 \
  --region cn-hangzhou \
  --user-agent 'AlibabaCloud-Agent-Skills/alibabacloud-rds-instances-manage/{session-id}' \
  --profile <profile>
```

### Attach a whitelist template

```bash
aliyun rds attach-whitelist-template-to-instance \
  --ins-name rm-example \
  --template-id <template-id> \
  --biz-region-id cn-hangzhou \
  --user-agent 'AlibabaCloud-Agent-Skills/alibabacloud-rds-instances-manage/{session-id}' \
  --profile <profile>
```

### Add tags

```bash
aliyun rds tag-resources \
  --biz-region-id cn-hangzhou \
  --resource-type INSTANCE \
  --resource-id rm-example \
  --tag Key=environment Value=production \
  --user-agent 'AlibabaCloud-Agent-Skills/alibabacloud-rds-instances-manage/{session-id}' \
  --profile <profile>
```

### Restart an instance

```bash
aliyun rds restart-db-instance \
  --db-instance-id rm-example \
  --region cn-hangzhou \
  --user-agent 'AlibabaCloud-Agent-Skills/alibabacloud-rds-instances-manage/{session-id}' \
  --profile <profile>
```

### Delete an instance

```bash
aliyun rds delete-db-instance \
  --db-instance-id rm-example \
  --region cn-hangzhou \
  --user-agent 'AlibabaCloud-Agent-Skills/alibabacloud-rds-instances-manage/{session-id}' \
  --profile <profile>
```

## Official references

- [RDS OpenAPI 2014-08-15 overview](https://help.aliyun.com/zh/rds/developer-reference/api-rds-2014-08-15-overview)
- [RDS Alibaba Cloud CLI reference](https://api.aliyun.com/api-tools/cli/Rds/2014-08-15)
- [DAS OpenAPI 2020-01-16 overview](https://help.aliyun.com/zh/das/developer-reference/api-das-2020-01-16-overview)
- [GetPfsMetricTrends](https://help.aliyun.com/zh/das/developer-reference/api-das-2020-01-16-getpfsmetrictrends)
- [GetPfsSqlSummaries](https://help.aliyun.com/zh/das/developer-reference/api-das-2020-01-16-getpfssqlsummaries)
