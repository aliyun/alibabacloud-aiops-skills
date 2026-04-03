# View Task Status

## Query Command

```bash
aliyun dts DescribeDtsJobDetail \
  --RegionId <region> \
  --DtsInstanceID <from-user-parameter> \
  --DtsJobId <from-user-parameter> \
  --read-timeout 30 --connect-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills
```

## API Parameter Case Sensitivity

- `DescribeDtsJobDetail` uses `--DtsInstanceID` (uppercase ID)
- `DeleteDtsJob` / `ConfigureDtsJob` etc. use `--DtsInstanceId` (lowercase d)
- API parameter casing is inconsistent; verify with `aliyun dts <API-name> help` before calling

## ID Handling

If the user provides only one ID, first try it as DtsJobId to look up the corresponding DtsInstanceId via DescribeDtsJobs.
If the task has no DtsInstanceID field (may be empty for some tasks), you can pass only `--DtsJobId`.

## Delay Unit

The `Delay` field returned by the API is in **milliseconds (ms)**. Convert to a more readable format for display (e.g., 518ms, 1.2s).

## Output Content

Display detailed status including task information, migration progress, synchronization delay, etc.
