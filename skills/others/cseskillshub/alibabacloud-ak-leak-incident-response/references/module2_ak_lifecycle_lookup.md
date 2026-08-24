# Module 2: AK Information Query

## Purpose

Query the detailed metadata of the leaked AccessKey to establish baseline facts: creation time, status, owner, type, and account context.

## API Endpoints (Public)

| Data / Capability | Public API | Product (via `_cli.call`) |
|-------------------|-----------|---------------------------|
| AK last-used time / service | RAM `GetAccessKeyLastUsed` (last-used time/service only) | `ram` (2015-05-01) |
| List an account's AccessKeys | RAM `ListAccessKeys` | `ram` |
| Account summary | IMS `GetAccountSummary` | `ims` (2019-08-15) |
| List RAM users | RAM `ListUsers` | `ram` |
| List recycled (deleted) users | IMS `ListUsersInRecycleBin` | `ims` |
| List RAM roles | RAM `ListRoles` | `ram` |
| Password policy + security preference | RAM `GetPasswordPolicy` + `GetSecurityPreference` | `ram` |
| CloudSSO service status | CloudSSO `GetServiceStatus` | `cloudsso` (2021-05-15) |

### Not Available via Public API

| Data / Capability | Status | Workaround |
|-------------------|--------|------------|
| AK's last-used products list | No direct equivalent | Use ActionTrail to infer last-used products |
| Full AK lifecycle traces (create/disable/delete timestamps, actor, IP) | No public API | Check ActionTrail for CreateAccessKey/DeleteAccessKey events |
| Service account (service UID) list | No public API | Manual identification of service UIDs |
| Account-bound domains | No public API | Not supported |

## Authentication

All calls go through the dual-backend layer in `scripts/_cli.py` (aliyun CLI preferred, direct V3-signed HTTPS fallback). No product SDK is used; credentials are resolved by the active backend — CLI profile (`~/.aliyun/config.json`), or env `ALIBABA_CLOUD_ACCESS_KEY_ID` / `ALIBABA_CLOUD_ACCESS_KEY_SECRET` (+ optional `ALIBABA_CLOUD_SECURITY_TOKEN`).

```python
body = _cli.call("ram", "ListAccessKeys", {}, region=region, profile=profile)
```

## AK Info Query — RAM GetAccessKeyLastUsed

The public RAM API has **no way to fetch an arbitrary AK's owner / create time / status**. The closest public signal is `GetAccessKeyLastUsed`, which returns when and by which service the AK was last used:

```python
body = _cli.call("ram", "GetAccessKeyLastUsed",
                 {"UserAccessKeyId": ak}, region=region, profile=profile)
last_used = body.get("AccessKeyLastUsed") or {}
# last_used.get("LastUsedDate"), last_used.get("ServiceName")
```

### Key Fields

| Field | Source | Significance |
|-------|--------|-------------|
| `lastUsedTime` | `AccessKeyLastUsed.LastUsedDate` | When the AK was last used |
| `lastUsedService` | `AccessKeyLastUsed.ServiceName` | Which service last used it |
| `status` / `createTime` / `owner` / `type` | **Not available via public RAM** — cross-referenced from ActionTrail | Derived downstream (Steps 2-5) |

### Handling Deleted / Unknown AKs

If the AK is unknown or deleted, `GetAccessKeyLastUsed` returns an error (captured as `basic_error`). This is not fatal — ActionTrail still retains the full operation history:

1. Record status as "Deleted/Unknown" (a **positive signal** if it means the AK was already remediated).
2. Check ActionTrail for `CreateAccessKey` / `DeleteAccessKey` events to reconstruct the lifecycle.
3. Continue — owner / create-time / status are all inferred from ActionTrail (`ak_first_seen`, the `CreateAccessKey` target user).

**Note**: There is no public API that recovers the full deleted-AK lifecycle (create/disable/delete timestamps, who deleted it, from which IP). Use ActionTrail event filtering by `EventAccessKeyId` or `ServiceName=Ram` to find related events.

## Execution Flow

```
AK Information Query
         |
         v
  RAM GetAccessKeyLastUsed(ak)
         |
         +---> Success
         |       |
         |       v
         |   Parse response:
         |   - accessKeyId
         |   - lastUsedTime (LastUsedDate)
         |   - lastUsedService (ServiceName)
         |   (owner / createTime / status → inferred from ActionTrail)
         |
         +---> Error (AK deleted / unknown)
         |       |
         |       v
         |   Record status as "Deleted"
         |   Check ActionTrail for lifecycle events
         |   Continue to Step 3 (ActionTrail still has history)
         |
         +---> Other Failure
                 |
                 v
          Log error, proceed with user-provided account
```

## Cross-Validation

Compare the AK info with ActionTrail findings:

- If `status` is still `Active`, flag as immediate remediation target.
- If the AK was recently created (within the attack window), it may be an attacker-created AK.

## Output to Next Step

This data supports Steps 2-5 chain tracing (see module3):

- `ak_status`: Active / Inactive / Deleted
- `ak_owner`: Owning user name
- `ak_create_time`: AK creation timestamp

## Account Profiling

Query account-level metadata for context during incident response.

### Account Summary — IMS GetAccountSummary

Returns current RAM resource counts and quota status:
- `Users`: Active RAM users count
- `Roles`: Roles count
- `Policies`: Custom policies count
- `MFADevices` / `MFADevicesInUse`: MFA status
- `AccessKeys`: Active AccessKeys count

**Risk indicators**:
- `MFADevicesInUse = 0` → No 2FA on the account (high risk)
- `Users` count unexpectedly high → check for attacker-created sub-accounts

### Live AccessKeys — RAM ListAccessKeys

Returns ALL currently existing AKs for the account:
```json
[
  {
    "accessKeyId": "LTAI5t...",
    "status": "Active",
    "createDate": "2026-05-18T12:00:00Z",
    "type": "SYMMETRIC"
  }
]
```

**Critical for investigation**: Immediately identifies AKs that are still ENABLED and should be disabled. Compare against known leaked AKs from Step 1.

### Active RAM Users — RAM ListUsers

Returns all active RAM sub-accounts with Marker-based pagination. Cross-check with ActionTrail `CreateUser` events to verify no attacker-created users remain active.

### Recycled/Deleted Users — IMS ListUsersInRecycleBin

**Critical**: Deleted sub-accounts go to a recycle bin (30-day retention). Attacker-created accounts appear here after cleanup:

```json
{
  "recycledUserList": [
    {
      "userName": "attacker-user@example.onaliyun.com",
      "userId": "...",
      "recycleTime": "2026-06-03T11:13:00Z",
      "originCreateTime": "2026-05-08T05:55:47Z"
    }
  ]
}
```

The `originCreateTime` directly correlates with ActionTrail `CreateUser` events — use this to confirm attacker sub-accounts were properly cleaned up.

### Security Policy — RAM GetPasswordPolicy + GetSecurityPreference

Shows account security posture:
- Password complexity requirements
- MFA enforcement settings
- Session duration policies
- Whether users can self-manage AKs

### Roles — RAM ListRoles

All IAM roles with Marker-based pagination. Check for attacker-created roles (suspicious names, recent `createDate` within attack window, overly permissive trust policies).

### Cloud SSO Status — CloudSSO GetServiceStatus

If CloudSSO is enabled, the attacker may use it for persistence (see SKILL.md Rule 8). Check for attacker-created `AccessConfiguration` and `AccessAssignment` entries via ActionTrail `User` filter.
