# Verification Method — PAI Workspace Management

## Scenario Verification

**Expected outcome**: PAI workspace is successfully created with `ENABLED` status and is ready for use.

---

## Step 1: Extract WorkspaceId from Create Response

After the create command succeeds, the response contains a `WorkspaceId`. Extract and save it:

```bash
# Execute create command and extract WorkspaceId
WORKSPACE_ID=$(aliyun aiworkspace create-workspace \
  --region <RegionId> \
  --workspace-name <WorkspaceName> \
  --description "<Description>" \
  --env-types prod \
  --user-agent AlibabaCloud-Agent-Skills | jq -r '.WorkspaceId')

echo "WorkspaceId: $WORKSPACE_ID"
```

**Success criteria**: `WorkspaceId` is a non-empty string (e.g., `"1234"`)

---

## Step 2: Verify Workspace Status

```bash
aliyun aiworkspace get-workspace \
  --workspace-id $WORKSPACE_ID \
  --user-agent AlibabaCloud-Agent-Skills
```

> **Note**: `get-workspace` only accepts `--workspace-id` and `--verbose` parameters. The region is specified via the global `--region` parameter (if overriding the default region).

**Expected response fields**:

| Field | Expected Value | Description |
|-------|---------------|-------------|
| `WorkspaceName` | Matches creation input | Workspace name |
| `Status` | `ENABLED` | Workspace is operational |
| `EnvTypes` | Matches creation input | Environment types |
| `GmtCreateTime` | Non-empty | Creation time is recorded |

**Success criteria**: `Status` field value is `ENABLED`

---

## Step 3: Verify via List (Optional)

```bash
aliyun aiworkspace list-workspaces \
  --region <RegionId> \
  --workspace-name <WorkspaceName> \
  --user-agent AlibabaCloud-Agent-Skills
```

**Success criteria**: Response has `TotalCount >= 1` and contains the target workspace.

---

## Step 4: Console Verification (When CLI/Code Verification Is Not Possible)

> **Note**: The following verification steps require manual operation in the console and cannot be automated via CLI or code.

1. Log in to [PAI Console](https://pai.console.aliyun.com/)
2. Select the corresponding region in the left navigation
3. Find the newly created workspace in the Workspace list
4. Confirm the status is "Enabled"
5. Click the workspace name to verify the environment (dev/prod) configuration is correct

---

## Quick Verification Script

```bash
#!/bin/bash
# Quick verification: check if workspace was created successfully

WORKSPACE_ID="<WorkspaceId>"

STATUS=$(aliyun aiworkspace get-workspace \
  --workspace-id $WORKSPACE_ID \
  --user-agent AlibabaCloud-Agent-Skills | jq -r '.Status')

if [ "$STATUS" = "ENABLED" ]; then
  echo "Workspace created successfully, Status: $STATUS"
else
  echo "Workspace status abnormal: $STATUS"
  exit 1
fi
```
