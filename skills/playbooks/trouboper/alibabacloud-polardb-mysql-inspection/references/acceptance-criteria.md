# Acceptance Criteria

## CORRECT Script Invocation Patterns

### Single Instance Inspection
```bash
SKILL_SESSION_ID={session-id} SKILL_VERSION={skill-version} python3 scripts/health-inspect.py pc-bp1715bzkcrateo69
```

### Multi-Instance Inspection
```bash
SKILL_SESSION_ID={session-id} SKILL_VERSION={skill-version} python3 scripts/health-inspect.py pc-bp1715bzkcrateo69 pc-bp12n05ogr61b5929
```

### Full Account Inspection
```bash
SKILL_SESSION_ID={session-id} SKILL_VERSION={skill-version} python3 scripts/health-inspect.py --all
```

### Specific Inspection Items
```bash
SKILL_SESSION_ID={session-id} SKILL_VERSION={skill-version} python3 scripts/health-inspect.py pc-bp1715bzkcrateo69 --item resource --item slowlog
```

## INCORRECT Patterns (violation = immediate failure)

1. **Calling `aliyun polardb` directly to collect inspection data:**
   ```bash
   # WRONG — must use health-inspect.py
   aliyun polardb describe-db-cluster-performance --db-cluster-id pc-xxx ...
   ```

2. **Using CloudMonitor (cms) as a substitute for PolarDB native APIs:**
   ```bash
   # WRONG — cms describe-metric-data is NOT a valid substitute
   aliyun cms describe-metric-data --namespace acs_polardb ...
   ```

3. **Connecting to the database directly:**
   ```bash
   # WRONG — no direct database access allowed
   mysql -h pc-xxx.polardb.rds.aliyuncs.com -u user -p
   SELECT * FROM information_schema.tables;
   ```

4. **Manually listing instances then running one by one:**
   ```bash
   # WRONG — use --all instead of manual discovery + loop
   aliyun polardb describe-db-clusters --region cn-hangzhou
   # then looping over results...
   ```

## Local Utility Commands

### CORRECT (no --user-agent needed)
```bash
aliyun configure list
aliyun version
aliyun configure set --auto-plugin-install true
aliyun plugin update
```

### INCORRECT
```bash
# WRONG — using aliyun CLI directly to collect inspection data
aliyun polardb describe-db-cluster-attribute --db-cluster-id pc-xxx ...
aliyun das create-storage-analysis-task --instance-id pc-xxx ...
```
