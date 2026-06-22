# Best Practices

> **Important**: The following key lessons are from real diagnosis cases.

### 1. DAS API Parameters Must Be Accurate

- `get-das-sql-log-hot-data` uses `--max-records-per-page`, not `--page-size`
- DAS endpoint is always `das.cn-shanghai.aliyuncs.com`

### 2. LockTime Field Limitations

- `LockTime` only records InnoDB row lock wait time
- `LockTime` does NOT record MDL lock wait time
- `LockTime = 0` with long execution time may indicate MDL lock wait

Decision flow:
```
Long SQL execution time:
  +- LockTime > 0 -> InnoDB row lock wait
  +- LockTime = 0 -> Possible MDL lock wait / network delay / IO wait
```

### 3. Four Types of MDL Lock Holders

| Lock Holder Type | MDL Lock Type | Held When | Released When |
|-----------------|--------------|-----------|---------------|
| DML in uncommitted transaction | MDL_SHARED_WRITE | DML executed in transaction | COMMIT/ROLLBACK/LOGOUT |
| Long-running SELECT | MDL_SHARED_READ | Execution time >= 5s | SELECT completes |
| SELECT in transaction | MDL_SHARED_READ | Transaction uncommitted | COMMIT/ROLLBACK/LOGOUT |
| FLUSH operation (intermediate) | MDL_EXCLUSIVE | Waiting for exclusive lock | FLUSH completes |

### 4. SQL Filtering Rules

**Must filter out**: SHOW DATABASES / SHOW TABLES / USE database / SELECT @@version_comment / login success!

**Must retain**: BEGIN / COMMIT / ROLLBACK / UPDATE / DELETE / INSERT / SELECT FOR UPDATE / LOGOUT / ALTER TABLE / FLUSH

### 5. Time Overlap Analysis

DAS SQL Insight may not record BEGIN in auto-commit mode. Solution: if a thread executed DML before the blocked time with no prior COMMIT, it may be the lock holder.

### 6. DAS SQL Insight Known Limitations

1. BEGIN may not be recorded (in auto-commit mode)
2. SET statements use underscores: `SET TRANSACTION_ISOLATION`
3. LockTime unit is microseconds (divide by 1,000,000 to convert to seconds)
4. DAS hot data retention is approximately 90 seconds
5. SQLText may be empty

### 7. SQL Execution Time Range Validation

- Only SQL where start_time <= blocked_time <= end_time can be the lock holder
- SQL killed (State: 1317) requires checking subsequent operations to determine transaction end time
- A single thread cannot execute two SQL statements simultaneously

### 8. MDL Lock Diagnosis Routing

- MDL is a table-level lock; WHERE conditions are irrelevant
- Check LockTime first to determine analysis path (LockTime > 10ms -> InnoDB, <= 10ms -> MDL)

### 9. DAS API QueryKeyword Server-Side Filtering

When total records exceed 5000, use `QueryKeyword` + `LogicalOperator=or` for server-side pre-filtering with client-side secondary validation.

### 10. Additional Notes

- INSERT without WHERE conditions uses full same-table DML analysis; Gap Lock under RR may block INSERT
- `Code: -404` means the instance has been deleted; expired data shows as successful query with 0 records
- Gap Lock applies under RR but not RC; diagnosis must check `SET transaction_isolation`
