# Related CLI Commands

## DAS Commands

| Product | CLI Command | Description |
|---------|-------------|-------------|
| DAS | `aliyun das get-das-sql-log-hot-data --instance-id {InstanceId} --start {StartMs} --end {EndMs} --max-records-per-page 500 --endpoint das.cn-shanghai.aliyuncs.com` | Query SQL audit hot data (primary data source) |
| DAS | `aliyun das get-dead-lock-history --instance-id {InstanceId} --start-time {StartMs} --end-time {EndMs} --source AUTO --endpoint das.cn-shanghai.aliyuncs.com` | Query deadlock history |
| DAS | `aliyun das get-dead-lock-detail --instance-id {InstanceId} --text-id {TextId} --endpoint das.cn-shanghai.aliyuncs.com` | Get deadlock detail by textId |
| DAS | `aliyun das create-latest-dead-lock-analysis --instance-id {InstanceId} --endpoint das.cn-shanghai.aliyuncs.com` | Trigger latest deadlock analysis |
| DAS | `aliyun das get-mysql-all-session-async --instance-id {InstanceId} --endpoint das.cn-shanghai.aliyuncs.com` | Get MySQL current sessions (async) |
| DAS | `aliyun das describe-sql-log-config --instance-id {InstanceId} --endpoint das.cn-shanghai.aliyuncs.com` | Query SQL Insight configuration |

## Notes

- DAS API endpoint is always `das.cn-shanghai.aliyuncs.com`
- `get-das-sql-log-hot-data` uses `--max-records-per-page`, not `--page-size`
- `get-mysql-all-session-async` is an async API; poll with `ResultId` until `IsFinish: true`
- Time parameters `--start`/`--end` and `--start-time`/`--end-time` use millisecond Unix timestamps
