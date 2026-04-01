# Verification Methods - ADBPG Supabase Management

This document describes how to verify whether ADBPG Supabase management operations are successful.

## Operation Verification Methods

### 1. List Query Verification

**Operation**: `list-supabase-projects`

```bash
aliyun gpdb list-supabase-projects \
  --biz-region-id cn-beijing \
  --user-agent AlibabaCloud-Agent-Skills
```

**Success Indicators**:
- Response JSON contains `Projects` array
- HTTP status code 200
- Response includes `RequestId`

### 2. Detail Query Verification

**Operation**: `get-supabase-project`

```bash
aliyun gpdb get-supabase-project \
  --project-id spb-xxxxx \
  --user-agent AlibabaCloud-Agent-Skills
```

**Success Indicators**:
- Response JSON contains complete project information
- Contains fields: `ProjectId`, `ProjectName`, `Status`, `RegionId`, `CreateTime`

### 3. Create Project Verification

**Operation**: `create-supabase-project`

**Async model**: Create is **asynchronous**. The CLI/API usually returns within the default read timeout (~60s) with a **`ProjectId`**. **3–5 minutes** is the typical **provisioning** time after that — not how long the create HTTP call blocks. Heavy load may need longer; the skill uses **longer polling** and optional extension.

**Before `ProjectId` — create HTTP retries** (see also `create-supabase-project-parameters.md`):

- Generate **`CLIENT_TOKEN`** once; pass **`--client-token`** on every create attempt for this intent.
- **Retry create** (max **3** tries, backoff **5s → 15s → 45s**) only if **no** `ProjectId` and the failure is **transient** (throttle, timeout, connection, `ServiceUnavailable`). Do **not** retry on parameter / quota / `VSwitchIp.NotEnough` style errors.
- If **`ProjectId`** appears → **stop** create; start provisioning poll below.
- If create **times out** with no id → **`list-supabase-projects`** by region/name before a second create.

**After `ProjectId` — provisioning poll**:

1. **Query project status** (use `--read-timeout 90` on each **get**).

2. **Primary tier**: every **30s**, up to **20** attempts (~10 min). **Optional extension**: if status is still non-terminal provisioning, notify user and add up to **10** more attempts (~5 min).

3. **Inner retry per poll cycle**: if **get** fails (network, timeout, throttle), retry the **same** **get** up to **3** times with **5s** between tries, then `sleep 30` and continue the outer loop.

Example (primary tier + inner retries):

```bash
PROJECT_ID="<returned-ProjectId>"
STATUS=""
MAX_PRIMARY=20
SLEEP=30
for attempt in $(seq 1 "$MAX_PRIMARY"); do
  RAW=""
  for inner in 1 2 3; do
    RAW=$(aliyun gpdb get-supabase-project \
      --project-id "$PROJECT_ID" \
      --read-timeout 90 \
      --user-agent AlibabaCloud-Agent-Skills \
      2>/dev/null) && break
    sleep 5
  done
  STATUS=$(echo "$RAW" | jq -r '.Status // empty')
  [ "$STATUS" = "running" ] && break
  sleep "$SLEEP"
done
```

4. **Status handling**: **`running`** → **create / provisioning succeeded** (success). Explicit API **failure/cancelled** states → stop and report (do not claim success). Empty or in-progress → keep polling within tier limits.

**Success Indicators**:
- Create command returns `ProjectId` (format: `spb-` + suffix) — request accepted only
- **`get-supabase-project`** shows **`Status` = `running`** — **provisioning succeeded**; treat as **create success** for user messaging (instance ready)
- If polling exhausts tiers without `running`, report failure honestly (do not claim success)

### 5. Pause Project Verification

**Operation**: `pause-supabase-project`

**Verification Steps**:

```bash
# 1. Execute pause
aliyun gpdb pause-supabase-project \
  --project-id spb-xxxxx \
  --user-agent AlibabaCloud-Agent-Skills

# 2. Query status
aliyun gpdb get-supabase-project \
  --project-id spb-xxxxx \
  --user-agent AlibabaCloud-Agent-Skills
```

**Success Indicators**:
- Project status becomes `Paused` or `Stopped`

### 6. Resume Project Verification

**Operation**: `resume-supabase-project`

**Verification Steps**:

```bash
# 1. Execute resume
aliyun gpdb resume-supabase-project \
  --project-id spb-xxxxx \
  --user-agent AlibabaCloud-Agent-Skills

# 2. Query status
aliyun gpdb get-supabase-project \
  --project-id spb-xxxxx \
  --user-agent AlibabaCloud-Agent-Skills
```

**Success Indicators**:
- Project status becomes `running`

### 7. Reset Password Verification

**Operation**: `reset-supabase-project-password`

**Verification Methods**:
- Command executes successfully
- Can connect to database with new password
- Connection with old password fails

**Note**: Cannot verify password change directly via API, requires actual connection test

### 8. Modify Security IPs Verification

**Operation**: `modify-supabase-project-security-ips`

**Verification Steps**:

```bash
# 1. Execute modification
aliyun gpdb modify-supabase-project-security-ips \
  --project-id spb-xxxxx \
  --security-ip-list "10.0.0.1,10.0.0.2/24" \
  --user-agent AlibabaCloud-Agent-Skills

# 2. Query project details to confirm whitelist
aliyun gpdb get-supabase-project \
  --project-id spb-xxxxx \
  --user-agent AlibabaCloud-Agent-Skills
```

**Success Indicators**:
- `SecurityIPList` in project details has been updated

### 9. API Keys Query Verification

**Operation**: `get-supabase-project-api-keys`

```bash
aliyun gpdb get-supabase-project-api-keys \
  --project-id spb-xxxxx \
  --user-agent AlibabaCloud-Agent-Skills
```

**Success Indicators**:
- Response JSON contains API Keys information
- Contains `AnonKey` and `ServiceRoleKey`

### 10. Dashboard Account Query Verification

**Operation**: `get-supabase-project-dashboard-account`

```bash
aliyun gpdb get-supabase-project-dashboard-account \
  --project-id spb-xxxxx \
  --user-agent AlibabaCloud-Agent-Skills
```

**Success Indicators**:
- Response JSON contains Dashboard account information
- Contains login URL and credentials

## Common Error Handling

| Error Code | Description | Solution |
|------------|-------------|----------|
| InvalidParameter | Invalid parameter | Check parameter format and values |
| InvalidAccessKeyId.NotFound | AK not found | Check credential configuration |
| Forbidden.RAM | Insufficient permissions | Check RAM permissions |
| InvalidRegionId.NotFound | Invalid region | Use a valid region ID |
| InvalidProjectId.NotFound | Project not found | Confirm project ID is correct |
| OperationDenied | Operation denied | Check if project status allows this operation |
