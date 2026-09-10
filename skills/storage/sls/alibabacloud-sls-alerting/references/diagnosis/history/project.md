# Project execution history

`internal-alert-history` in the rule's owning Project records executions,
including evaluations that do not fire.

Filter by `AlertName`, the rule's stable name (`--alert-name`), to find its
executions. Filter by `AlertID` to retrieve events for one execution, with a
time range wide enough to include related events. See
[execution fields](execution-fields.md) for result meanings.

## First-time Project history activation

The first visit to an alert detail page in the **SLS console** automatically
creates `internal-alert-history` in that Project and enables **free** recording.
This is needed only once. If the Logstore is absent and history is needed,
generate this URL and ask the user to visit it:

```text
https://sls.console.aliyun.com/lognext/project/<projectName>/alert/<AlertName>
```

Use the actual Project and stable rule `AlertName`, not `AlertDisplayName` or
the execution `AlertID`; URL-encode each path segment.
