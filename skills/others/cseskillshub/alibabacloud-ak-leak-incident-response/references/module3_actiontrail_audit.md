# Module 3: ActionTrail Dangerous Operation Audit

## Purpose
Query ActionTrail event logs for dangerous operations performed via the leaked AK. First identify sub-accounts created by the leaked AK, then recursively trace the operation chains of those sub-accounts and any new AKs across 14 high-risk Alibaba Cloud services.

## API — Public LookupEvents

```
Product: actiontrail  (endpoint actiontrail.{region}.aliyuncs.com, version 2020-07-06)
Action:  LookupEvents  (via _cli.call / _cli.paginate_next_token)
```

## Authentication

All calls go through the dual-backend layer in `scripts/_cli.py` (aliyun CLI preferred, direct V3-signed HTTPS fallback). No product SDK is used; credentials are resolved by the active backend — CLI profile (`~/.aliyun/config.json`), or env `ALIBABA_CLOUD_ACCESS_KEY_ID` / `ALIBABA_CLOUD_ACCESS_KEY_SECRET` (+ optional `ALIBABA_CLOUD_SECURITY_TOKEN`).

## Request Parameters

### Filter Modes (Priority Order)

The public `LookupEvents` API supports up to 2 `LookupAttributes`. The script uses 5 mutually exclusive filter modes:

| Priority | Filter Key | Usage | Step |
|----------|-----------|-------|------|
| 1 | `SourceIpAddress` | Filter by attacker IP | Supplementary |
| 2 | `EventAccessKeyId` | Filter by AK — **PRIMARY for Step 2** | Step 2 |
| 3 | `User` | Filter by sub-account executor — **MANDATORY for Step 4a** | Step 4a |
| 4 | `ServiceName` | Filter by service | Step 3 fallback |
| 5 | (none) | All events | Baseline |

### Pagination

The public API uses `NextToken`-based pagination with `MaxResults` (max 50 per call):

```python
events = _cli.paginate_next_token(
    "actiontrail", "LookupEvents",
    {
        "StartTime": "2026-05-04T05:26:27Z",
        "EndTime": "2026-06-03T05:26:27Z",
        "MaxResults": 50,
        "LookupAttribute.1.Key": "EventAccessKeyId",
        "LookupAttribute.1.Value": "<AK>",
    },
    region=region, profile=profile, items_key="Events",
)
# paginate_next_token follows NextToken automatically until exhausted
```

> **CRITICAL**: Only `User` (exact casing) works for sub-account executor queries. `UserName` / `Username` / `userName` are BROKEN (always return 0 results).

## Quick Confirmation: Query by AK or Source IP

### By AK (PRIMARY — Step 2 of the SOP)

```bash
python query_actiontrail_audit.py --account <UID> --ak <AK> --days 30
```

Answers: What did the leaked AK do? Which sub-users were created? Which new AKs were generated? This query drives the entire chain-following logic.

### By Source IP (SUPPLEMENTARY)

```bash
python query_actiontrail_audit.py --account <UID> --source-ip <IP> --days 1
```

Answers: Was the AK actually used from this IP? Useful for quick confirmation.

---

## Chain-Following Audit Logic (Steps 2-5)

> **Core principle**: Every `CreateUser` and `CreateAccessKey` spawns a new tracing branch. The audit is complete only when ALL branches have been exhausted.

### Step 2: Leaked AK Operation Audit

The FIRST and MOST IMPORTANT query. Use `EventAccessKeyId=<leaked_AK>` to get every operation performed with the leaked AK.

From the results, extract:

| Look For | Action | Next Step |
|----------|--------|-----------|
| `eventName: CreateUser` | Record sub-user name | → Step 4 |
| `eventName: CreateAccessKey` | Record `responseElements.AccessKey.AccessKeyId` and target `UserName` | → Step 4b or Step 5 |
| `eventName: AttachPolicyToUser` | Record policy name + target user | Document |
| ECS/DNS/SMS/Billing operations | Group by `eventSource` | → Step 3 |

### Step 3: Cross-Product Operation Grouping

From Step 2 results, group events by `eventSource` prefix to understand which products were touched:

```python
SERVICE_SOURCE_PREFIXES = {
    'ecs': 'ECS',
    'ram': 'Ram',
    'alidns': 'Alidns',
    'dysms': 'SMS',
    'bss': 'BssOpenApi',
    'sts': 'STS',
    'cloudsso': 'CloudSSO',
    # ...
}
```

### Step 4: Sub-User Chain Tracing

**Trigger**: Step 2 found `CreateUser(sub-userX)`

#### Step 4a: Query sub-user's own operations

Use the `User` filter to find actions performed BY the sub-account after logging in:

```python
params = {"LookupAttribute.1.Key": "User", "LookupAttribute.1.Value": "<sub-userX>"}
```

> **CRITICAL DISTINCTION**:
> - `User` filter returns events where the sub-account is the **executor** (logged in and performed actions)
> - Other query methods only find events where the sub-account is the **target** (operated upon by the leaked root AK)

#### What this catches that other methods miss

| Service | Event | Description |
|---------|-------|-------------|
| AasSub | `BindMFADevice` | Attacker binds MFA to lock the backdoor account |
| CloudSSO | `CreateAccessConfiguration` | Creates persistent SSO access with 12h session |
| CloudSSO | `AddPermissionPolicyToAccessConfiguration` | Attaches AdministratorAccess to SSO config |
| CloudSSO | `CreateAccessAssignment` | Binds SSO config to target accounts |
| Notifications | `UpdateUserSubscription` | Anti-detection: disables alert notifications |
| Notifications | `DelMessage` | Evidence destruction: deletes notification messages |

#### Step 4b: Sub-user created new AK?

Scan Step 4a results for `CreateAccessKey`. If found:

```
Extract: responseElements.AccessKey.AccessKeyId → <NEW_AK>
Run: EventAccessKeyId=<NEW_AK> (recursive — same as Step 2)
```

### Step 5: New AK Chain Tracing (Existing User / Root)

**Trigger**: Step 2 found `CreateAccessKey` where `requestParameters.UserName` is an EXISTING sub-user or empty (root).

Query the new AK the same way with `EventAccessKeyId=<new_AK>`. If this new AK also performed `CreateUser` → go back to Step 4. If `CreateAccessKey` → recurse Step 5.

### Complete Chain Exhaustion Check

The audit is complete ONLY when:

```
[x] All leaked AKs traced (EventAccessKeyId)
[x] All created sub-users traced (User=<name>)
[x] All sub-user AKs traced (EventAccessKeyId)
[x] All new AKs for existing users traced (EventAccessKeyId)
[x] No unvisited branches remain in the chain
```

## Dangerous Services List

| Service | Primary Risk | Visible Via |
|---------|-------------|-------------|
| `Ram` | Sub-account creation, privilege escalation | ALL/AK/IP/Service |
| `CloudSSO` | **Advanced persistence** | **User filter ONLY** |
| `ECS` | Unauthorized instance creation | ALL/AK/IP/Service |
| `AasSub` | Console signin, MFA binding | **User filter ONLY** |
| `Eci` | Container group spawning | ALL/AK/IP/Service |
| `SMS` | SMS abuse / spam | ALL/AK/IP/Service |
| `ECD` | Cloud desktop provisioning | ALL/AK/IP/Service |
| `BDRC` | Backup / restore tampering | ALL/AK/IP/Service |
| `RdsData` | Database data exfiltration | ALL/AK/IP/Service |
| `PTS` | Load testing abuse | ALL/AK/IP/Service |
| `Alidns` | DNS hijacking | ALL/AK/IP/Service |
| `EHPC` | HPC cluster abuse | ALL/AK/IP/Service |
| `Dms` | Data export / import abuse | ALL/AK/IP/Service |
| `Notifications` | **Anti-detection** | **User filter ONLY** |

## Risk Classification Rules

| Risk Level | Event Name Patterns | Example Events |
|------------|---------------------|----------------|
| **HIGH** | `CreateUser`, `CreateAccessKey`, `AttachPolicyToUser`, `RunInstances`, `CreateInstance`, `SendSms`, `AddDomainRecord` | Account creation, privilege escalation, resource provisioning |
| **MEDIUM** | `Modify*`, `Update*`, `Delete*`, `Remove*`, `Stop*`, `Release*` | Configuration changes, resource deletion |
| **LOW** | `Describe*`, `List*`, `Get*`, `Query*` | Read-only reconnaissance |

## Event Execution Result Judgment

**CRITICAL**: Every event MUST be checked for execution success/failure before concluding impact.

```python
error_code = event.get("errorCode", "")
success = not bool(error_code)  # empty errorCode = success
```

| `errorCode` value | Meaning | Impact |
|-------------------|---------|--------|
| (empty/absent) | Operation executed successfully | Causes real damage |
| `InvalidAccessKeyId.Inactive` | AK already disabled | No damage |
| `EntityAlreadyExists.User` | Sub-account already exists | No new user — do NOT trace |
| `NoPermission` / `Forbidden.RAM` | Insufficient permissions | Operation blocked |

### Impact on Chain Tracing

- **Only successful `CreateUser`** spawns Step 4
- **Only successful `CreateAccessKey`** spawns Step 5
- Failed attempts are recorded but do NOT trigger recursive branches

## Known Blind Spots & Workarounds

| Blind Spot | Workaround |
|-----------|------------|
| `UserName` filter returns 0 | Use `User` (exact casing) in Step 4a |
| Sub-account console ops invisible to AK/IP/ALL/Service | Step 4a `User=<sub-account>` is the ONLY way |
| CloudSSO persistence invisible | Only Step 4a User filter catches these |
| Console operations lack `accessKeyId` | Correlate via `userAgent` + `sourceIpAddress` |

## Investigation Checklist

- [ ] **Step 2 executed**: `EventAccessKeyId=<leaked AK>` queried
- [ ] **Step 3 completed**: Events grouped by product/service
- [ ] **Step 4 for each sub-user**: `User=<name>` queried for every CreateUser target
- [ ] **Step 4b recursive**: Every sub-user's CreateAccessKey → new AK traced
- [ ] **Step 5 for each new AK**: CreateAccessKey on existing users/root traced
- [ ] **Chain fully exhausted**: No unvisited branches remain
- [ ] **CloudSSO operations checked**
- [ ] **Notification tampering checked**
- [ ] **BindMFADevice checked**
- [ ] **High-risk API checklist run**: All 82 APIs checked
- [ ] **Error codes reviewed**: Failed calls reveal attacker intent
