# Start/Resume Task

## Command

```bash
aliyun dts StartDtsJob \
  --RegionId <region> \
  --DtsInstanceId <instance-id> \
  --DtsJobId <job-id> \
  --read-timeout 30 --connect-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills
```

## ID Handling

If the user provides only one ID, first try it as DtsJobId to look up the corresponding DtsInstanceId via DescribeDtsJobs.
If the task has no DtsInstanceID field (may be empty for some tasks), you can pass only `--DtsJobId`.
