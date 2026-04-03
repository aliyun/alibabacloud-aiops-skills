# Release (Delete) Task

## Safety Warning

**Dangerous operation**, double confirmation required! Releasing a task is irreversible.

## Protective Pre-check

**Before deleting, you must first query the current task status:**

```bash
aliyun dts DescribeDtsJobDetail \
  --DtsJobId <job-id> \
  --RegionId <region> \
  --read-timeout 30 --connect-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills
```

Evaluate based on the returned `Status` field:

| Task Status | Handling |
|------------|---------|
| Synchronizing / Migrating | **Active state**, prompt user to suspend the task first before deleting, or explicitly confirm forced deletion |
| InitializingDataLoad | **Initializing**, inform user the task is initializing, confirm whether to abort and delete |
| Suspended / Finished / Error | Can be deleted directly, only standard double confirmation needed |
| NotStarted | Can be deleted directly, only standard double confirmation needed |

If the task is in an active state (Synchronizing/Migrating/InitializingDataLoad), you must clearly inform the user of the current status and risks before proceeding.

## Command

After pre-check passes and user confirms:
```bash
aliyun dts DeleteDtsJob \
  --RegionId <region> \
  --DtsInstanceId <instance-id> \
  --DtsJobId <job-id> \
  --read-timeout 30 --connect-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills
```

## Notes

- The parameter name is `--DtsInstanceId` (lowercase d), not `--DtsInstanceID`
- If the task has no DtsInstanceID (may be empty for some tasks), you can pass only `--DtsJobId`:
```bash
aliyun dts DeleteDtsJob --DtsJobId <job-id> --RegionId <region> --read-timeout 30 --connect-timeout 10 --user-agent AlibabaCloud-Agent-Skills
```

## ID Handling

If the user provides only one ID, first try it as DtsJobId to look up the corresponding DtsInstanceId via DescribeDtsJobs.
