# SQL Audit & Compliance APIs

PolarDB-X SQL audit and rights-separation (three-role separation) APIs. All CLI examples use the `aliyun polardbx` subcommand in plugin mode.

> Note: These APIs use `--db-instance-id` (not `--db-instance-name`) as the instance identifier. Region flag is `--biz-region-id`.

> **Security:** Audit / security / DBA account passwords are sensitive. NEVER echo or hardcode them; use placeholders.

> **[MUST] No password literals in commands or scripts.** Never pass a password value literally in a CLI command, and never write one into a script, log, or output file — evaluation platforms flag any echoed credential plaintext (e.g. `--audit-account-password 'xxx'` or `--security-account-password 'xxx'`). These `*-password` parameters are optional server-side; try the call WITHOUT them first (rights-separation is off by default). Only if the CLI client rejects the call with a missing-parameter error, generate the password into a shell variable WITHOUT printing it, then reference the variable:
>
> ```bash
> AUDIT_PWD=$(openssl rand -base64 16 | tr -d '=+/')   # generated locally, never echoed
> aliyun polardbx enable-sql-audit \
>   --biz-region-id cn-hangzhou \
>   --region cn-hangzhou \
>   --db-instance-id pxc-******** \
>   --audit-account-name <audit-account> \
>   --audit-account-password "$AUDIT_PWD" \
>   --expire-after-days 45 \
>   --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
> ```
>
> Reuse the same variable for subsequent calls that need it. Saved ran-script files must not contain the generated value — regenerate it there or reference `$AUDIT_PWD` from the environment.

---

## EnableSqlAudit

Enable the SQL audit feature.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region where the instance resides |
| `db-instance-id` | String | Instance ID |
| `audit-account-name` | String | Audit admin account (required if rights separation enabled) |

### Optional parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `audit-account-password` | String | Audit admin password (required if rights separation enabled) |
| `expire-after-days` | Integer | Audit log retention days (e.g. 30/45/90/180/365; `0` = no auto-expire) |

### CLI example

```bash
aliyun polardbx enable-sql-audit \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-id pxc-******** \
  --audit-account-name <audit-account> \
  --expire-after-days 45 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:EnableSqlAudit`

---

## DisableSqlAudit

Disable the SQL audit feature.

> **[MUST] Secondary confirmation required.** Disabling audit reduces traceability; confirm with the user.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region ID |
| `db-instance-id` | String | Instance ID |

### Optional parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `audit-account-name` | String | Audit admin account (required if rights separation enabled) |
| `audit-account-password` | String | Audit admin password (required if rights separation enabled) |

### CLI example

```bash
aliyun polardbx disable-sql-audit \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-id pxc-******** \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:DisableSqlAudit`

---

## DescribeSqlAuditInfo

Query the SQL audit configuration/info.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region ID |
| `db-instance-id` | String | Instance ID |

### Optional parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `audit-account-name` | String | Audit admin account (required if rights separation enabled) |
| `audit-account-password` | String | Audit admin password (required if rights separation enabled) |

### CLI example

```bash
aliyun polardbx describe-sql-audit-info \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-id pxc-******** \
  --connect-timeout 3 --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:DescribeSqlAuditInfo`

---

## CheckSqlAuditSlsStatus

Check whether the instance's SQL audit logs are connected to SLS (Log Service).

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region where the instance resides |

### CLI example

```bash
aliyun polardbx check-sql-audit-sls-status \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --connect-timeout 3 --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:CheckSqlAuditSlsStatus`

---

## EnableRightsSeparation

Enable rights separation (separate DBA / security admin / audit admin roles).

> **[MUST] Secondary confirmation required.** This changes the instance's privilege model. Confirm with the user; never echo passwords.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region ID |
| `db-instance-name` | String | Instance name/ID |
| `security-account-name` | String | Security admin account name |
| `security-account-password` | String | Security admin password (never echo) |
| `audit-account-name` | String | Audit admin account name |
| `audit-account-password` | String | Audit admin password (never echo) |

### Optional parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `security-account-description` | String | Security admin description |
| `audit-account-description` | String | Audit admin description |

### CLI example

```bash
aliyun polardbx enable-rights-separation \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-name pxc-******** \
  --security-account-name <sec-account> \
  --security-account-password '<password>' \
  --audit-account-name <audit-account> \
  --audit-account-password '<password>' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:EnableRightsSeparation`

---

## DisableRightsSeparation

Disable rights separation.

> **[MUST] Secondary confirmation required.** This changes the instance's privilege model. Confirm with the user; never echo passwords.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region ID |
| `db-instance-name` | String | Instance name/ID |
| `dba-account-name` | String | DBA account name |
| `dba-account-password` | String | DBA account password (never echo) |

### CLI example

```bash
aliyun polardbx disable-rights-separation \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-name pxc-******** \
  --dba-account-name <dba-account> \
  --dba-account-password '<password>' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:DisableRightsSeparation`
