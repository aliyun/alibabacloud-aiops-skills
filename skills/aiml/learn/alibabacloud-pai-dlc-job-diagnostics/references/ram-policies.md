# RAM Permissions

This skill invokes APIs across two products.

---

## Minimum Read-Only Policy (diagnostics scenario)

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "pai:GetJob",
        "pai:GetPodLogs",
        "pai:GetJobEvents",
        "pai:GetPodEvents",
        "pai:ListJobSanityCheckResults",
        "pai:GetJobSanityCheckResult"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "paistudio:GetQuotaWorkloadDiagnosis"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## Permission Reference

### PAI-DLC permissions (`pai-dlc` plugin)

| Operation | Action | Purpose |
|-----------|--------|---------|
| View job details | `pai:GetJob` | Fetch job status, metadata, Pods |
| Get pod logs | `pai:GetPodLogs` | Failure diagnosis and hang detection |
| Get job events | `pai:GetJobEvents` | Lifecycle timeline |
| Get pod events | `pai:GetPodEvents` | Pod-level Kubernetes events |
| Sanity check | `pai:ListJobSanityCheckResults` / `pai:GetJobSanityCheckResult` | Hardware health checks |

### PAI Studio permissions (`paistudio` plugin)

| Operation | Action | Purpose |
|-----------|--------|---------|
| Resource diagnosis | `paistudio:GetQuotaWorkloadDiagnosis` | Queuing-stuck root cause analysis |

---

## Permission Failure Handling

> **[MUST] Permission Failure Handling:** When any command or API call fails due to
> permission errors at any point during execution, follow this process:
> 1. Read this file (`references/ram-policies.md`) to get the full list of permissions required
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

---

## Common Permission Errors

| Error code | Cause | Resolution |
|------------|-------|------------|
| `Forbidden.RAM` | RAM user lacks the required action | Ask the admin to attach the policy above |
| `OperationForbidden` | Not authorized for this job | Verify access to the job's workspace |
| `NoPermission` | Missing `paistudio` permission | Add `paistudio:GetQuotaWorkloadDiagnosis` |
