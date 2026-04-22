# Success Verification Method

Verification steps to confirm successful execution of MaxCompute Project Management operations.

---

## 1. Create Project Verification

### Expected Outcome
A new MaxCompute project is created and available for use.

### Verification Steps

**Step 1: Verify project creation response**
```bash
# The create-project command should return the project name
aliyun maxcompute create-project \
  --body '{"name":"test_project","defaultQuota":"os_PayAsYouGoQuota","productType":"payasyougo"}' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-odps-project-manage

# Expected response:
# {
#   "requestId": "xxx",
#   "data": "test_project"
# }
```

**Step 2: Query the created project**
```bash
aliyun maxcompute get-project \
  --project-name test_project \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-odps-project-manage
```

**Success Indicators:**
| Check | Expected Value |
|-------|----------------|
| HTTP Status | 200 |
| `data.name` | Matches the project name |
| `data.status` | `AVAILABLE` |
| `data.productType` | Matches specified product type |

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| `ProjectAlreadyExist` | Project name already taken | Choose a different name |
| `InvalidProjectName` | Name format invalid | Use 3-28 chars: lowercase, numbers, underscores |
| `QuotaNotFound` | Specified quota doesn't exist | Verify quota alias or use default |

---

## 2. Get Project Verification

### Expected Outcome
Project details are returned with accurate information.

### Verification Steps

**Step 1: Query project details**
```bash
aliyun maxcompute get-project \
  --project-name <project-name> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-odps-project-manage
```

**Success Indicators:**
| Check | Expected Value |
|-------|----------------|
| HTTP Status | 200 |
| `data.name` | Matches query parameter |
| Response contains | `owner`, `status`, `defaultQuota`, `productType` |

### Validation Script

```bash
#!/bin/bash
PROJECT_NAME="your_project_name"

# Get project and extract status
RESPONSE=$(aliyun maxcompute get-project --project-name $PROJECT_NAME --user-agent AlibabaCloud-Agent-Skills/alibabacloud-odps-project-manage 2>&1)

# Check if response contains expected fields
if echo "$RESPONSE" | grep -q '"status"'; then
  echo "✅ Get project successful"
  echo "$RESPONSE" | jq '.data | {name, status, owner, productType}'
else
  echo "❌ Get project failed"
  echo "$RESPONSE"
  exit 1
fi
```

---

## 3. List Projects Verification

### Expected Outcome
A list of projects is returned, optionally filtered by quota.

### Verification Steps

**Step 1: List all projects**
```bash
aliyun maxcompute list-projects \
  --max-item 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-odps-project-manage
```

**Step 2: List with quota filter (optional)**
```bash
aliyun maxcompute list-projects \
  --quota-nick-name os_PayAsYouGoQuota \
  --max-item 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-odps-project-manage
```

**Success Indicators:**
| Check | Expected Value |
|-------|----------------|
| HTTP Status | 200 |
| Response contains | `data.projects` array |
| Projects array | Contains project objects with `name`, `status` |

### Validation Script

```bash
#!/bin/bash

# List projects
RESPONSE=$(aliyun maxcompute list-projects --max-item 10 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-odps-project-manage 2>&1)

# Check if response contains projects array
if echo "$RESPONSE" | grep -q '"projects"'; then
  echo "✅ List projects successful"
  PROJECT_COUNT=$(echo "$RESPONSE" | jq '.data.projects | length')
  echo "Found $PROJECT_COUNT projects"
  echo "$RESPONSE" | jq '.data.projects[] | {name, status}'
else
  echo "❌ List projects failed"
  echo "$RESPONSE"
  exit 1
fi
```

---

## 4. Delete Project Verification

### Expected Outcome
Project is deleted and no longer accessible.

> ⚠️ **Warning:** This operation is irreversible. Use with caution.

### Verification Steps

**Step 1: Delete the project**
```bash
aliyun maxcompute delete-project \
  --project-name <project-name> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-odps-project-manage
```

**Step 2: Verify deletion**
```bash
# Attempting to get the deleted project should fail
aliyun maxcompute get-project \
  --project-name <project-name> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-odps-project-manage

# Expected: ProjectNotFound error
```

**Success Indicators:**
| Check | Expected Value |
|-------|----------------|
| Delete response | HTTP 200 with project name |
| Get after delete | `ProjectNotFound` error |

---

## End-to-End Verification Script

Complete verification of all operations:

```bash
#!/bin/bash
set -e

# Configuration
PROJECT_NAME="test_project_$(date +%s)"
QUOTA_NAME="os_PayAsYouGoQuota"

echo "=== MaxCompute Project Management Verification ==="
echo "Test Project: $PROJECT_NAME"
echo ""

# Step 1: Create Project
echo "1. Creating project..."
CREATE_RESULT=$(aliyun maxcompute create-project \
  --body "{\"name\":\"$PROJECT_NAME\",\"defaultQuota\":\"$QUOTA_NAME\",\"productType\":\"payasyougo\"}" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-odps-project-manage)
echo "✅ Project created"

# Step 2: Wait for project to be available
echo "2. Waiting for project to be available..."
sleep 5

# Step 3: Get Project
echo "3. Getting project details..."
GET_RESULT=$(aliyun maxcompute get-project \
  --project-name $PROJECT_NAME \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-odps-project-manage)
STATUS=$(echo $GET_RESULT | jq -r '.data.status')
echo "✅ Project status: $STATUS"

# Step 4: List Projects
echo "4. Listing projects..."
LIST_RESULT=$(aliyun maxcompute list-projects \
  --max-item 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-odps-project-manage)
echo "✅ Projects listed"

# Step 5: Cleanup (Optional - uncomment to delete)
# echo "5. Cleaning up..."
# aliyun maxcompute delete-project \
#   --project-name $PROJECT_NAME \
#   --user-agent AlibabaCloud-Agent-Skills/alibabacloud-odps-project-manage
# echo "✅ Project deleted"

echo ""
echo "=== Verification Complete ==="
echo "All operations successful for project: $PROJECT_NAME"
```

---

## Quick Reference

| Operation | Verification Command | Success Indicator |
|-----------|---------------------|-------------------|
| Create | `get-project` returns details | `status` = `AVAILABLE` |
| Get | Response contains project info | HTTP 200 |
| List | Response contains `projects` array | Array length ≥ 0 |
| Delete | `get-project` returns error | `ProjectNotFound` |
