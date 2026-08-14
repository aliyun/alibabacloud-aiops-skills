# Security & Access Control APIs

PolarDB-X IP whitelist, SSL, TDE, and KMS authorization APIs. All CLI examples use the `aliyun polardbx` subcommand in plugin mode.

> **Security:** NEVER expose the instance to the public internet. Whitelist changes must not open the instance to `0.0.0.0/0`. NEVER echo encryption keys or credentials.

> Note: Region flag is `--biz-region-id`; instance identifier flag is `--db-instance-name` (format `pxc-********`).

---

## DescribeSecurityIps

Query the IP whitelist of an instance.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region where the instance resides |
| `db-instance-name` | String | Instance name/ID |

### CLI example

```bash
aliyun polardbx describe-security-ips \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-name pxc-******** \
  --connect-timeout 3 --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:DescribeSecurityIps`

---

## ModifySecurityIps

Modify the IP whitelist of an instance.

> **[MUST] Do not open the instance to the public internet.** Reject `0.0.0.0/0` or overly broad ranges; confirm the exact CIDR list with the user.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region ID |
| `db-instance-name` | String | Instance ID |
| `group-name` | String | Whitelist group name, e.g. `default` |
| `security-ip-list` | String | IP list, comma-separated |
| `modify-mode` | String | `0` overwrite / `1` append / `2` delete |

### CLI example

```bash
aliyun polardbx modify-security-ips \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-name pxc-******** \
  --group-name default \
  --security-ip-list 192.168.0.0/24 \
  --modify-mode 0 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:ModifySecurityIps`

---

## DescribeDBInstanceSSL

Query the SSL configuration of an instance.

### Optional parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region ID |
| `db-instance-name` | String | Instance ID |

### CLI example

```bash
aliyun polardbx describe-db-instance-ssl \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-name pxc-******** \
  --connect-timeout 3 --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:DescribeDBInstanceSSL`

---

## UpdateDBInstanceSSL

Enable or update the SSL configuration.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `db-instance-name` | String | Instance ID |
| `enable-ssl` | Boolean | Whether to enable SSL |

### Optional parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `cert-common-name` | String | Certificate bound domain name |
| `biz-region-id` | String | Region ID |

### CLI example

```bash
aliyun polardbx update-db-instance-ssl \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-name pxc-******** \
  --enable-ssl true \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:UpdateDBInstanceSSL`

---

## DescribeDBInstanceTDE

Query the TDE (Transparent Data Encryption) details of an instance.

### Optional parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region ID |
| `db-instance-name` | String | Instance ID |

### CLI example

```bash
aliyun polardbx describe-db-instance-tde \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-name pxc-******** \
  --connect-timeout 3 --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:DescribeDBInstanceTDE`

---

## UpdateDBInstanceTDE

Enable TDE for an instance.

> **[MUST] Secondary confirmation required.** Enabling TDE is a security-critical, hard-to-reverse operation. Confirm with the user; never echo the encryption key.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region ID |
| `db-instance-name` | String | Instance ID |
| `tde-status` | Integer | Enable, fixed value `1` |
| `encryption-key` | String | Custom KMS key ID (or omit to auto-generate) |
| `role-arn` | String | RAM role ARN authorizing KMS usage |

### CLI example

```bash
aliyun polardbx update-db-instance-tde \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-name pxc-******** \
  --tde-status 1 \
  --role-arn 'acs:ram::<account-id>:role/<role>' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:UpdateDBInstanceTDE`

---

## DescribeUserEncryptionKeyList

Query the user's TDE key list.

### Optional parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region ID |
| `db-instance-name` | String | Instance ID |

### CLI example

```bash
aliyun polardbx describe-user-encryption-key-list \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-name pxc-******** \
  --connect-timeout 3 --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:DescribeUserEncryptionKeyList`

---

## CheckCloudResourceAuthorized

Check whether the instance is authorized to use the KMS key service.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region ID |
| `db-instance-name` | String | Instance ID |
| `role-arn` | String | ARN of the authorized role |

### CLI example

```bash
aliyun polardbx check-cloud-resource-authorized \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-name pxc-******** \
  --role-arn 'acs:ram::<account-id>:role/<role>' \
  --connect-timeout 3 --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:CheckCloudResourceAuthorized`
