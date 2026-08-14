# Account Management APIs

PolarDB-X database account management APIs. All CLI examples use the `aliyun polardbx` subcommand in plugin mode.

> **Security:** Account passwords are sensitive. NEVER echo, log, or hardcode password values. Always use placeholders and let the user supply the real value at execution time.

> Note: Region flag is `--biz-region-id`; instance identifier flag is `--db-instance-name` (format `pxc-********`).

---

## CreateAccount

Create a standard (privileged) database account.

> **[MUST] Secondary confirmation required.** Creating an account changes access control. Confirm account name, target database, and privilege with the user before executing. See the **Mandatory Secondary Confirmation** section in `SKILL.md`.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region, e.g. `cn-hangzhou` |
| `db-instance-name` | String | Instance name/ID |
| `account-name` | String | Account name to create |
| `account-password` | String | Account password (use a placeholder; never echo) |

### Optional parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `account-privilege` | String | Privilege: `ReadWrite` / `ReadOnly` / `DMLOnly` / `DDLOnly` |
| `db-name` | String | Database to authorize |
| `account-description` | String | Account description |
| `security-account-name` | String | Security admin account (required if rights separation enabled) |
| `security-account-password` | String | Security admin password (required if rights separation enabled) |

> **`account-privilege` and `db-name` are optional server-side** (verified against the official OpenAPI metadata). The kebab-case plugin form (`create-account`) marks them as `(required)` client-side. Verified workaround: pass the target database name and privilege anyway, even when the database does not exist yet — the server creates the account and ignores the not-yet-existing grant (tested: `Success: true`). Then create the database afterwards with `create-db` to apply the actual grant:

```bash
aliyun polardbx create-account \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-name pxc-******** \
  --account-name <account> \
  --account-password '<password>' \
  --db-name <database-to-grant-later> \
  --account-privilege ReadWrite \
  --connect-timeout 3 --read-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### CLI example

```bash
aliyun polardbx create-account \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-name pxc-******** \
  --account-name <account> \
  --account-password '<password>' \
  --account-privilege ReadWrite \
  --db-name <database> \
  --client-token $(uuidgen) \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:CreateAccount`

---

## DeleteAccount

Delete a database account.

> **[MUST] Secondary confirmation required.** Deleting an account revokes access permanently. Confirm the account name with the user before executing.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region where the instance resides |
| `db-instance-name` | String | Instance name/ID |
| `account-name` | String | Account name to delete |

### Optional parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `security-account-name` | String | Security admin account (required if rights separation enabled) |
| `security-account-password` | String | Security admin password (required if rights separation enabled) |

### CLI example

```bash
aliyun polardbx delete-account \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-name pxc-******** \
  --account-name <account> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:DeleteAccount`

---

## DescribeAccountList

Query the account list of an instance.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region where the instance resides |
| `db-instance-name` | String | Instance name/ID |

### Optional parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `account-name` | String | Filter by a specific account |
| `account-type` | String | Account type filter; empty returns all |

### CLI example

```bash
aliyun polardbx describe-account-list \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-name pxc-******** \
  --connect-timeout 3 --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:DescribeAccountList`

---

## CreateSuperAccount

Create the high-privilege (super) account. Only one super account is allowed per instance.

> **[MUST] Secondary confirmation required.** Confirm with the user before creating a privileged account.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region ID |
| `db-instance-name` | String | Instance name/ID |
| `account-name` | String | Account name |
| `account-password` | String | Account password (use a placeholder; never echo) |

### Optional parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `account-description` | String | Account description |

### CLI example

```bash
aliyun polardbx create-super-account \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-name pxc-******** \
  --account-name <dba> \
  --account-password '<password>' \
  --client-token $(uuidgen) \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:CreateSuperAccount`

---

## ResetAccountPassword

Reset the password of an account.

> **[MUST] Secondary confirmation required.** Password reset affects active connections. Confirm the target account with the user; never echo the new password.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region ID |
| `db-instance-name` | String | Instance name/ID |
| `account-name` | String | Account name |
| `account-password` | String | New password (use a placeholder; never echo) |

### Optional parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `security-account-name` | String | Security admin account |
| `security-account-password` | String | Security admin password |

### CLI example

```bash
aliyun polardbx reset-account-password \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-name pxc-******** \
  --account-name <account> \
  --account-password '<new-password>' \
  --client-token $(uuidgen) \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:ResetAccountPassword`

---

## ResetAccountPasswordRestrict

Reset password(s) for standard account(s) under rights-separation constraints. Supports resetting standard accounts only.

> **[MUST] Secondary confirmation required.** Same as `ResetAccountPassword`; confirm accounts and never echo passwords.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region ID |
| `db-instance-name` | String | Instance ID |
| `account-name` | String | Standard account name(s) to reset |
| `account-password` | String | New password(s), comma-separated for multiple (never echo) |

### Optional parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `security-account-name` | String | Account name for security context |
| `security-account-password` | String | Security admin password (required if rights separation enabled) |

### CLI example

```bash
aliyun polardbx reset-account-password-restrict \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-name pxc-******** \
  --account-name <account> \
  --account-password '<new-password>' \
  --client-token $(uuidgen) \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:ResetAccountPasswordRestrict`

---

## ModifyAccountDescription

Modify an account's description/remark.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region ID |
| `db-instance-name` | String | Instance name/ID |
| `account-name` | String | Account name |

### Optional parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `account-description` | String | New account description |

### CLI example

```bash
aliyun polardbx modify-account-description \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-name pxc-******** \
  --account-name <account> \
  --account-description "app service account" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:ModifyAccountDescription`

---

## ModifyAccountPrivilege

Modify the privileges of a standard account.

> **[MUST] Secondary confirmation required.** Privilege changes affect access control. Confirm the account, database, and target privilege with the user.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region ID |
| `db-instance-name` | String | Instance ID |
| `account-name` | String | Account name |
| `account-privilege` | String | `ReadWrite` / `ReadOnly` / `DMLOnly` / `DDLOnly` |
| `db-name` | String | Database name |

### Optional parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `security-account-name` | String | Security admin account |
| `security-account-password` | String | Security admin password |

### CLI example

```bash
aliyun polardbx modify-account-privilege \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-name pxc-******** \
  --account-name <account> \
  --db-name <database> \
  --account-privilege ReadOnly \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:ModifyAccountPrivilege`
