# Error Troubleshooting Scenarios

Follow this guide when users encounter error codes, exceptions, or error messages.

## Trigger Conditions

- "An error occurred: InvalidParameter.InstanceId"
- "Connection failed: Connection refused"
- "Why does it show AuthenticationFailed?"
- "SQL error: error code 1045"
- "What does this error mean?"

## Core Principles

1. **Agent extracts key information**: error code, error meaning, and solution steps.
2. **Provide executable troubleshooting steps**, not only documentation links.
3. **Combine with instance status** to provide targeted recommendations.

---

## Error Type Classification

| Error Type | Example | Handling Method |
|---------|------|---------|
| **CLI/API error** | InvalidParameter, Forbidden.RAM, InstanceNotFound | Quick reference table 1 |
| **Connection error** | Connection refused, Timeout, Retry exhausted | Quick reference table 2 |
| **SQL error** | Error 1045, 1146, 1064, 3024 | Quick reference table 3 |
| **Performance/throttling** | Quota exceeded, Too many connections | Quick reference table 4 |

---

## Quick Reference Table 1: CLI/API Error Codes

| Error Code | Meaning | Possible Cause | Solution |
|--------|------|---------|---------|
| `InvalidParameter.InstanceId` | Invalid instance ID | Incorrect format, nonexistent instance, or released instance | Confirm the `ld-xxx` format and run `aliyun lindorm v1 instance describe <id>` |
| `InstanceNotFound` | Instance does not exist | Incorrect ID or released instance | Run `aliyun lindorm v1 instance describe <id>` |
| `InstanceStatusInvalid` | Instance status does not support the operation | Instance is not running | Wait until the instance reaches `ACTIVATION` |
| `InstanceLocked` | Instance is locked | Overdue payment, security issue, or maintenance in progress | Check the account balance or contact technical support |
| `QuotaExceeded` | Insufficient quota | Regional quota exceeded | Submit a ticket to request a quota increase |
| `Instance.IsNotValid` | The ID format is valid but the instance does not exist | Incorrect ID or released instance | Confirm with `aliyun lindorm summary` |
| `InvalidAccessKeyId.NotFound` | AccessKey does not exist | Incorrect AccessKey ID | Check the AccessKey configuration |
| `SignatureDoesNotMatch` | Signature mismatch | Incorrect AccessKey secret | Verify the secret |
| `Forbidden.RAM` | Insufficient RAM permissions | Lindorm permissions are missing | Add `AliyunLindormReadOnlyAccess` |
| `UnauthorizedOperation` | Unauthorized operation | A specific action permission is missing | Ask the primary account to grant permission |
| `Throttling.User` | User-level throttling | Request rate is too high | Reduce the rate and add retries |
| `Throttling.System` | System-level throttling | System load is high | Retry later |

---

## Quick Reference Table 2: Connection Errors

### Network Errors

| Error Message | Cause | Troubleshooting Steps |
|---------|------|---------|
| `Connection refused` | Port is unreachable | 1. Check whitelist 2. Check security group 3. Test the port with telnet |
| `Connection timeout` | Network is unreachable | 1. Confirm network type, VPC or public network 2. Check routes 3. Test with ping |
| `Unknown host` | DNS resolution failed | Check the spelling of the connection address |
| `Network is unreachable` | Network is unreachable | Confirm VPC configuration and check cross-VPC or cross-region access |

### Authentication Errors at the SQL Layer

| Error Message | Cause | Solution |
|---------|------|---------|
| `Authentication failed` (Error 1045) | Username or password is incorrect | Check the password. If forgotten, reset it in the console. |
| `Access denied` (Error 1227) | Insufficient permissions | Check user permission configuration |

### HBase Client Errors (Official Connection Errors)

| Error Message | Cause | Solution |
|---------|------|---------|
| `Retry exhausted when update config from seedserver` | Connection address or port is incorrect. Official HBase-compatible port is 30020. | Confirm that the port is correct. For ports, see SKILL.md → "Port number quick reference". Check the network. |
| `Failed to connect to jdbc:lindorm:table:url=****` | SQL connection failed. ⚠️ The Avatica protocol is only maintained for existing users. | Confirm that the port is correct. Migration to the MySQL protocol is recommended. |
| `DoNotRetryIOException: Detect inefficient query` | Full table scan is intercepted. Official reason: WHERE condition column has no index. | See sql-usage-notes.md → "Low-efficiency query interception" |

> Official connection troubleshooting order: whitelist → security group → network type matching → public network / Express Connect.

### Time Series Engine Errors

| Error Message | Cause | Solution |
|---------|------|---------|
| `TSDB error: table not found` | Table does not exist | Check the table name |
| `TSDB error: invalid timestamp` | Timestamp format is incorrect | Use millisecond-level timestamps |
| `Write limit exceeded` | Write throttling | Reduce write frequency or scale out |

---

## Quick Reference Table 3: SQL Error Codes (Official Reference)

The following are MySQL-compatible error codes and Lindorm extended error codes from the official documentation. For the complete list, see https://help.aliyun.com/zh/lindorm/developer-reference/common-error-codes-reference

### Common MySQL-compatible Error Codes

| Error Code | Meaning | Official Handling Suggestion |
|--------|------|------------|
| 1040 | Too many connections on a single node | Revisit how connections are used. The limit is 1000 before 2.7.0.0 and 4000 in 2.7.0.0 and later. |
| 1045 | Authentication failed | Confirm whether the authentication information is correct |
| 1049 | Unknown database | Specify the correct database name |
| 1050 | Table already exists | Use another table name or IF NOT EXISTS |
| 1054 | Unknown column name | Confirm whether the column name in SQL actually exists |
| 1064 | SQL syntax error | Correct it according to the SQL syntax documentation |
| 1146 | Table does not exist | Check whether the table name is entered incorrectly |

### Common Lindorm Extended Error Codes

| Error Code | Meaning | Official Handling Suggestion |
|--------|------|------------|
| 3024 | Query timeout | Retry. If it still times out, contact technical support. |
| 8005 | Table does not exist | Check the table name |
| 8008 | Resource limit exceeded | Query: narrow the time range or add WHERE conditions. Write: limit TPS. |
| 9001 | Unsupported syntax | Compare with SQL syntax documentation and avoid unsupported syntax |
| 9003 | Authentication method is not applicable to old-version users | Refer to MySQL protocol compatibility documentation and specify a supported authentication method |

---

## Quick Reference Table 4: Monitoring Metric Exceptions

| Metric Exception | Possible Cause | Troubleshooting Suggestion | V2 Note |
|---------|---------|---------|--------|
| `cpu_idle < 10%` | CPU utilization is too high | Check slow query logs and consider scaling out | — |
| `mem_used_percent > 90%` | Memory pressure | Check cache configuration and scale out | ⚠️ V2 returns no data; calculate `1 - mem_free/mem_total` |
| `storage_used_percent > 85%` | Insufficient storage | Clean up data or scale out | ⚠️ For V2, run `aliyun lindorm v2 instance storage` |
| `read_rt_p99 > 1000ms` | High query latency | Analyze slow queries and create indexes | ⚠️ V2 returns no data |
| `write_rt_p99 > 500ms` | High write latency | Check the write pattern and consider scaling out | ⚠️ V2 returns no data |

---

## Common Error Handling Examples

### Example: InvalidParameter.InstanceId

```text
[Error Analysis] InvalidParameter.InstanceId

[Error Meaning] The instance ID parameter is invalid.

[Possible Causes]
1. The instance ID format is incorrect. It should be ld-xxx.
2. The instance does not exist or has been released.

[Troubleshooting Steps]
Step 1: Verify the ID format and confirm that it starts with `ld-`.
Step 2: Confirm that it exists: aliyun lindorm v1 instance describe <id> --lindorm-region <instance-region>
Pass the region explicitly. In plugin mode, the parent aliyun CLI consumes `--region` silently. Without `--lindorm-region`, the active profile region is used and an instance in another region is reported as NotFound.

[Official Documentation] https://help.aliyun.com/zh/lindorm/developer-reference/common-error-codes-reference
```

### Example: Authentication Failed (Error 1045)

```text
[Error Analysis] Access denied / Authentication failed (Error 1045)

[Error Meaning] The username or password is incorrect.

[Troubleshooting Steps]
Step 1: Confirm that the password is correct. If it is forgotten, reset it in the console.
Step 2: Check RAM permissions and make sure `AliyunLindormReadOnlyAccess` is granted.
Step 3: Verify the fix with `aliyun lindorm summary`.

[Common Mistakes]
❌ Using a RAM user without Lindorm authorization
❌ Incorrect instance ID format or instance does not exist
```

---

## Official Documentation

- **Error code reference**: https://help.aliyun.com/zh/lindorm/developer-reference/common-error-codes-reference
- **Connection errors and solutions**: https://help.aliyun.com/zh/lindorm/support/lindorm-connection-errors-and-solutions
- **Connection issues and solutions**: https://help.aliyun.com/zh/lindorm/support/lindorm-connection-issues-and-solutions
- **SQL FAQ**: https://help.aliyun.com/zh/lindorm/developer-reference/sql-faq
- **Technical support**: Submit a ticket through the Alibaba Cloud ticket system

---

## Related Scenarios

- Connection issues → `connection-troubleshoot.md`
- Performance issues → `monitoring-guide.md`
- SQL usage → `sql-usage-notes.md`
