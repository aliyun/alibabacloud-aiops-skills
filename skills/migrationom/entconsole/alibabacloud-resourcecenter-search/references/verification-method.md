# Verification Method - Resource Center

## Step 1: Verify Resource Center is Enabled

```bash
aliyun resourcecenter get-resource-center-service-status \
  --user-agent AlibabaCloud-Agent-Skills
```

**Expected Output:**
```json
{
  "ServiceStatus": "Enabled",
  "InitialStatus": "Finished",
  "RequestId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
}
```

- `ServiceStatus` being `Enabled` indicates that Resource Center is activated.
- `InitialStatus` being `Finished` indicates that Resource index is completed.

**Response fields (per API definition):**

| Field | Meaning | Values |
|-------|---------|--------|
| `ServiceStatus` | Whether Resource Center is turned on for the account. | `Enabled` — service is enabled. `Disabled` — service is disabled. |
| `InitialStatus` | Whether initial resource metadata indexing is complete (only relevant when the service is enabled). | `Pending` — still preparing. `Finished` — ready (indexing complete). |
| `RequestId` | Request identifier for tracing. | Opaque string. |

**How to interpret results:**

- **`ServiceStatus: Enabled`** — Resource Center is activated; you may call search and statistics APIs.
- **`InitialStatus: Pending`** — Data is still being built after enablement (or a large inventory is catching up). Search or counts may be empty or incomplete; **poll this API** until `InitialStatus` becomes `Finished` before treating failures as permission or configuration issues. Allow several minutes (large accounts may take longer), consistent with the main skill workflow.
- **`InitialStatus: Finished`** — Metadata is **ready**; search and `GetResourceCounts` results should reflect inventory within normal service behavior.
- **`ServiceStatus: Disabled`** — Enable Resource Center first (`enable-resource-center`); `InitialStatus` is not applicable for operational search until the service is enabled.

## Step 2: Verify Resource Search is Working

```bash
aliyun resourcecenter search-resources \
  --max-results 5 \
  --user-agent AlibabaCloud-Agent-Skills
```

**Expected Output:** Returns JSON containing a `Resources` array, where each resource includes fields such as `ResourceId`, `ResourceType`, `RegionId`, etc.

## Step 3: Verify Resource Count Statistics

```bash
aliyun resourcecenter get-resource-counts \
  --group-by-key ResourceType \
  --user-agent AlibabaCloud-Agent-Skills
```

**Expected Output:** Returns JSON containing a `Filters` array, where each item includes `FilterKey` (resource type) and `FilterValue` (count).

## Step 4: Verify Cross-Account Resource Center Status (If Applicable)

> This step is only applicable for management accounts that have set up a Resource Directory.

```bash
aliyun resourcecenter get-multi-account-resource-center-service-status \
  --user-agent AlibabaCloud-Agent-Skills
```

**Expected Output:**
```json
{
  "ServiceStatus": "Enabled",
  "RequestId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
}
```

## Step 5: Verify Cross-Account Resource Search (If Applicable)

> The `--scope` parameter is required (Resource Directory ID, Root Folder ID, Folder ID, or Member ID).

```bash
aliyun resourcecenter search-multi-account-resources \
  --scope <ResourceDirectoryId> \
  --max-results 5 \
  --user-agent AlibabaCloud-Agent-Skills
```

**Expected Output:** Returns JSON containing a `Resources` array with resources from multiple member accounts.

## Step 6: Verify Cross-Account Resource Count Statistics (If Applicable)

```bash
aliyun resourcecenter get-multi-account-resource-counts \
  --scope <ResourceDirectoryId> \
  --group-by-key ResourceType \
  --user-agent AlibabaCloud-Agent-Skills
```

**Expected Output:** Returns resource count statistics aggregated across multiple member accounts.

## Common Failure Scenarios

| Symptom | Cause | Fix |
|---------|-------|-----|
| `ServiceStatus: Disabled` | Resource Center not enabled | Execute `enable-resource-center` |
| `ResourceNotFound` | Resource Center service not activated | Enable Resource Center first |
| `NoPermission` | Insufficient RAM permissions | Add corresponding RAM policies |
| `ForbiddenMultiAccountResourceCenter` | Non-management account performing cross-account operations | Use Resource Directory management account |
| Empty `Resources` array | Resource Center data is still building (`InitialStatus` may be `Pending`) or filters exclude all resources | Re-run Step 1; if `InitialStatus` is `Pending`, wait and poll until `Finished`, then retry search |
