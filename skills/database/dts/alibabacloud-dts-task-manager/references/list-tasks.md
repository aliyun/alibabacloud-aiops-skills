# View Task List

## Query Method

**Important**: The `--JobType` parameter defaults to `MIGRATION`, so omitting it only returns migration tasks. Query by type separately:

```bash
# Query migration tasks
aliyun dts DescribeDtsJobs --RegionId <region> --PageSize 50 --PageNumber 1 --JobType MIGRATION --read-timeout 30 --connect-timeout 10 --user-agent AlibabaCloud-Agent-Skills
# Query sync tasks
aliyun dts DescribeDtsJobs --RegionId <region> --PageSize 50 --PageNumber 1 --JobType SYNC --read-timeout 30 --connect-timeout 10 --user-agent AlibabaCloud-Agent-Skills
# Query subscription tasks
aliyun dts DescribeDtsJobs --RegionId <region> --PageSize 50 --PageNumber 1 --JobType SUBSCRIBE --read-timeout 30 --connect-timeout 10 --user-agent AlibabaCloud-Agent-Skills
```

**Note**: Do not pass the `--Type` parameter (confirmed to cause InvalidParameter error). The correct parameter name is `--JobType`.

## Multi-Region Query

If querying across multiple Regions, query common regions such as cn-beijing, cn-hangzhou, cn-shanghai sequentially and consolidate the results.

## Output Format

Output in table format: Task ID, Task Name, Type, Status, Source, Destination, Delay(ms)
