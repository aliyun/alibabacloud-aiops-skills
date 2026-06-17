# Troubleshooting Guide

This guide provides solutions to common issues encountered when using the PAI-Rec Engine Diagnosis and Configuration Validation skill.

---

## [MUST READ] Reporting Principle — Evidence-Only Conclusions

When delivering a diagnosis conclusion to the user, strictly follow the evidence-only rule defined in `SKILL.md` (Step 6 → `[MUST] Evidence-only reporting rule`).

**Allowed in a conclusion:**
- Exact log lines actually retrieved from EAS (with `file:line`, level, message)
- Exact config fragments actually retrieved from the engine configuration
- The direct causal chain that connects the above evidence to the observed API response
- An explicit statement of what evidence is still missing, if any

**NOT allowed (unless the user explicitly asks for it in a follow-up):**
- Speculative root causes that are not directly visible in the logs or config
- Guesses about client-side behavior, upstream systems, or data sources
- Fix recommendations or remediation steps
- Conditional "if X then Y" scenarios
- Tangential best-practice advice (security, fallback design, naming, etc.)

This principle applies to every troubleshooting item in this guide: the workarounds below describe *how to gather evidence*; they do NOT authorize adding speculation on top of that evidence when reporting to the user.

---

## Table of Contents

1. [CLI and Authentication Issues](#cli-and-authentication-issues)
2. [Service Access Issues](#service-access-issues)
3. [Log Query Issues](#log-query-issues)
4. [Configuration Retrieval Issues](#configuration-retrieval-issues)
5. [Engine API Issues](#engine-api-issues)
6. [Configuration Validation Issues](#configuration-validation-issues)
7. [Performance Issues](#performance-issues)

---

## CLI and Authentication Issues

### Issue: Aliyun CLI Not Found

**Symptoms:**
```bash
bash: aliyun: command not found
```

**Solution:**
1. Install Aliyun CLI:
   ```bash
   curl -fsSL https://aliyuncli.alicdn.com/setup.sh | bash
   ```

2. Reload shell configuration:
   ```bash
   source ~/.bashrc  # or ~/.zshrc
   ```

3. Verify installation:
   ```bash
   aliyun version
   ```

**Related Documentation:** [CLI Installation Guide](cli-installation-guide.md)

---

### Issue: Aliyun CLI Version Too Old

**Symptoms:**
```bash
aliyun version
# Output: 3.0.x (needs >= 3.3.3)
```

**Solution:**
1. Update Aliyun CLI:
   ```bash
   curl -fsSL https://aliyuncli.alicdn.com/setup.sh | bash
   ```

2. Verify update:
   ```bash
   aliyun version  # Should show >= 3.3.3
   ```

---

### Issue: No Credentials Configured

**Symptoms:**
```
Error: No credential configured
```

**Solution:**
1. Check current configuration:
   ```bash
   aliyun configure list
   ```

2. If empty, configure credentials **outside this session**:
   ```bash
   # In a separate terminal
   aliyun configure
   ```

3. Provide credentials when prompted:
   - Access Key ID
   - Access Key Secret
   - Region (e.g., cn-hangzhou)

**Security Note:** NEVER type credentials in chat or skill execution context.

---

### Issue: Forbidden.RAM - Insufficient Permissions

**Symptoms:**
```json
{
  "Code": "Forbidden.RAM",
  "Message": "User not authorized to perform this operation"
}
```

**Solution:**
1. Check required permissions in [RAM Policies](ram-policies.md)

2. Request permissions from account administrator

3. Verify permissions granted:
   ```bash
   aliyun ram get-user-policy \
     --user-name <your-username> \
     --policy-name <policy-name>
   ```

4. Test access after permissions granted:
   ```bash
   aliyun eas describe-service \
     --cluster-id <cluster-id> \
     --service-name <service-name>
   ```

**Common Missing Permissions:**
- `eas:DescribeService`
- `eas:DescribeServiceLog`
- `pairecservice:ListEngineConfigs`
- `pairecservice:GetEngineConfig`

---

### Issue: Missing --user-agent Flag

**Symptoms:**
CLI calls succeed but cannot be traced back to this skill session.

**Solution:**
Ensure a session-id (32-char lowercase hex string) was generated at session start and every `aliyun` API command includes:
```bash
--user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-rec-diagnosis/{session-id}
```

**Prevention:**
Generate the session-id once at the very start of the workflow. Local utility commands (`configure`, `plugin`, `version`) do not support `--user-agent` and should be excluded.

---

## Service Access Issues

### Issue: Service Not Found

**Symptoms:**
```json
{
  "Code": "InvalidService.NotFound",
  "Message": "The specified service does not exist"
}
```

**Diagnostic Steps:**
1. Verify service name spelling:
   ```bash
   # List all services in cluster
   aliyun eas list-services --cluster-id <cluster-id>
   ```

2. Check if service exists in different cluster/region

3. Verify cluster ID is correct

**Solution:**
- Use exact service name from service list
- Specify correct cluster ID
- Check if service has been deleted

---

### Issue: Cluster ID Unknown

**Symptoms:**
Need cluster ID but don't know it

**Solution:**
1. Cluster ID is typically the region ID:
   - `cn-hangzhou`
   - `cn-shanghai`
   - `cn-beijing`
   - etc.

2. Or list services to find cluster:
   ```bash
   aliyun eas list-services --region <region-id>
   ```

3. Check EAS console for cluster information:
   [EAS Console](https://eas.console.aliyun.com/)

---

### Issue: Service Configuration Missing Environment Variables

**Symptoms:**
Service info retrieved but environment variables not found

**Diagnostic Steps:**
1. Check ServiceConfig structure:
   ```bash
   aliyun eas describe-service \
     --cluster-id <cluster-id> \
     --service-name <service-name> \
     --cli-query 'ServiceConfig'
   ```

2. Look for environment variables in different locations:
   - `ServiceConfig.envs`
   - `ServiceConfig.metadata`
   - `ServiceConfig.configs`

**Solution:**
- If env vars missing, service may not be PAI-Rec service
- Check service deployment configuration
- Consult service owner for configuration details

---

## Log Query Issues

### Issue: No Logs Found for Request ID

**Symptoms:**
```json
{
  "Logs": [],
  "TotalCount": 0
}
```

**#1 root cause — combining `--keyword` with a time range:**

`aliyun eas describe-service-log` has a well-known quirk: when `--keyword` is supplied together with `--start-time` / `--end-time`, PAI-Rec application (business) logs are silently dropped even if the window covers the real log time; only `/bin/sh` wrapper heartbeats and `502 Bad Gateway` noise remain. The correct pattern is to use `--keyword` **without** any time parameters:

```bash
# [CORRECT] Keyword-only lookup returns the full business trace
aliyun eas describe-service-log \
  --cluster-id <cluster-id> \
  --service-name <service-name> \
  --keyword <request-id> \
  --page-size 500
```

```bash
# [WRONG] Adding a time range drops all controller.go/feed.go/recall.go lines
aliyun eas describe-service-log \
  --cluster-id <cluster-id> \
  --service-name <service-name> \
  --keyword <request-id> \
  --start-time "2025-04-28 06:00:00" \
  --end-time   "2025-04-28 10:00:00"
```

**Other diagnostic steps (only if keyword-only lookup is already zero):**

1. **Verify request ID format:**
   - Exact match, case-sensitive
   - No truncation, full UUID
   - Copy directly from the API response `request_id` field

2. **Verify log retention:**
   - EAS log retention is limited; old requests may no longer be queryable
   - Diagnose promptly after the issue occurs

3. **Cross-check the service actually received the request:**
   - Confirm the service name and cluster/region match the endpoint that was called
   - Consider traffic mirroring rules (`ExtraData.mirror`) which may redirect traffic to another service

4. **Sanity check with a broader time-window scan (no keyword):**
   ```bash
   # Dumps raw /bin/sh wrapper output only (good for confirming the service is producing logs)
   aliyun eas describe-service-log \
     --cluster-id <cluster-id> \
     --service-name <service-name> \
     --start-time "2025-04-28 01:30:00" \
     --end-time   "2025-04-28 02:10:00" \
     --page-size 500
   ```

**Solutions:**
- Prefer keyword-only lookup for request-level diagnosis
- Verify request ID exactly matches API response
- Diagnose promptly before log retention expires

---

### Issue: Too Many Logs Returned

**Symptoms:**
Thousands of log entries, hard to analyze

**Solution:**
1. **Use the full `request_id` as keyword (do NOT add a time range):**
   ```bash
   aliyun eas describe-service-log \
     --cluster-id <cluster-id> \
     --service-name <service-name> \
     --keyword "941b4e14-d1c5-489f-a184-b2b17f8b4fdb" \
     --page-size 500
   ```
   A single request's full trace is usually < 30 entries.

2. **For broad time-window scans without keyword, use pagination:**
   ```bash
   aliyun eas describe-service-log \
     --cluster-id <cluster-id> \
     --service-name <service-name> \
     --start-time "2025-04-28 08:10:00" \
     --end-time   "2025-04-28 08:20:00" \
     --page-num 1 \
     --page-size 100
   ```
   Time format must be `yyyy-MM-dd HH:mm:ss` UTC (space separator, no `T` / no `Z`).

---

### Issue: Log Timestamps Don't Match

**Symptoms:**
Log timestamps in different timezone than expected; `--start-time` / `--end-time` rejected with `InvalidParameter`

**Solution:**
1. **Use the exact format `yyyy-MM-dd HH:mm:ss` in UTC:**
   - Correct: `2025-04-28 08:15:23`
   - Wrong:   `2025-04-28T08:15:23Z` (ISO-8601 is rejected)

2. **Convert local time to UTC (example for CST / UTC+8):**
   ```text
   Local (Beijing): 2025-04-28 16:15:23
   UTC:             2025-04-28 08:15:23
   ```

3. **Note:** Log lines shown in the EAS console appear in Beijing time (`[YYYY-MM-DD HH:MM:SS]` prefix), but CLI parameters require UTC. Subtract 8 hours when translating a console timestamp into CLI `--start-time` / `--end-time`.

4. **Prefer `--keyword <request_id>` only (no time parameters) for request-level diagnosis** — this sidesteps timezone confusion entirely.

---

## Configuration Retrieval Issues

### Issue: No Released Configurations Found

**Symptoms:**
```json
{
  "EngineConfigs": [],
  "TotalCount": 0
}
```

**Diagnostic Steps:**

1. **Check all statuses:**
   ```bash
   # Remove status filter
   aliyun pairecservice list-engine-configs \
     --instance-id <instance-id> \
     --environment <Prod|Pre>
   ```

2. **Check environment mapping:**
   - Service env `product` → CLI param `Prod`
   - Service env `prepub` → CLI param `Pre`
   - Verify correct mapping used

3. **List all configs:**
   ```bash
   # Remove all filters
   aliyun pairecservice list-engine-configs \
     --instance-id <instance-id>
   ```

**Solutions:**
- Use correct environment parameter
- Check if configurations exist in different environment
- Verify instance ID is correct
- Check if configurations have been archived

---

### Issue: Wrong Environment Configurations Returned

**Symptoms:**
Got Pre environment config when expecting Prod

**Root Cause:**
Environment variable `PAIREC_ENVIRONMENT` mapping incorrect

**Solution:**
1. **Verify environment mapping:**
   - `product` → `Prod`
   - `prepub` → `Pre`
   - Case-sensitive

2. **Double-check service environment:**
   ```bash
   aliyun eas describe-service \
     --cluster-id <cluster-id> \
     --service-name <service-name> \
     --cli-query 'ServiceConfig.envs.PAIREC_ENVIRONMENT'
   ```

---

### Issue: Multiple Versions Returned

**Symptoms:**
List returns many configuration versions, unclear which to use

**Solution:**
1. **Filter by Released status:**
   ```bash
   aliyun pairecservice list-engine-configs \
     --instance-id <instance-id> \
     --environment Prod \
     --status Released
   ```

2. **Select most recent:**
   - Sort by `GmtCreateTime`
   - Use latest unless specified otherwise

3. **Ask user to confirm:**
   - Display version list with metadata
   - Let user select specific version

---

### Issue: ConfigValue is Empty

**Symptoms:**
```json
{
  "EngineConfig": {
    "ConfigValue": ""
  }
}
```

**Diagnostic Steps:**
1. Check if configuration was properly saved
2. Verify configuration is not in Draft state
3. Check permissions to view configuration

**Solution:**
- Use Released configuration
- Verify configuration was deployed successfully
- Contact configuration owner

---

## Engine API Issues

### Issue: Code 299 - Items Size Not Enough

**Error Response:**
```json
{
  "code": 299,
  "msg": "items size not enough",
  "size": 0,
  "items": []
}
```

**Common Causes:**

1. **Recall topk too low:**
   ```json
   // Fix: Increase topk
   "recall": {
     "modules": [{
       "params": {
         "topk": 500  // Increased from 100
       }
     }]
   }
   ```

2. **Filters too aggressive:**
   ```json
   // Fix: Relax filter thresholds
   "filter": {
     "rules": [{
       "params": {
         "min_score": 0.05  // Lowered from 0.2
       }
     }]
   }
   ```

3. **No data for user:**
   - Check if user exists in system
   - Verify user has historical behavior
   - Check data freshness

4. **Table access issues:**
   - Verify recall tables have data
   - Check table permissions
   - Validate table names in config

**Diagnosis Workflow:**
1. Check service logs for detailed error
2. Review recall configuration
3. Verify data availability
4. Test with known good user

---

### Issue: Request Timeout

**Error Response:**
```json
{
  "code": 500,
  "msg": "request timeout"
}
```

**Common Causes:**

1. **Recall timeout too low:**
   ```json
   "params": {
     "timeout_ms": 500  // Increased from 200
   }
   ```

2. **Too many recall modules:**
   - Reduce number of parallel recalls
   - Optimize recall order
   - Use async where possible

3. **Large batch in ranking:**
   ```json
   "params": {
     "batch_size": 30  // Reduced from 100
   }
   ```

4. **Slow model endpoint:**
   - Check model service status
   - Optimize model inference
   - Increase timeout

**Diagnosis:**
1. Check logs for which stage timed out
2. Review timeout configurations
3. Test individual modules separately

---

### Issue: Invalid Request Parameters

**Error Response:**
```json
{
  "code": 400,
  "msg": "invalid parameter: user_id"
}
```

**Solution:**
1. Check API documentation for required parameters
2. Validate parameter formats
3. Review request payload in logs
4. Test with known good request

---

## Configuration Validation Issues

### Issue: JSON Parsing Error

**Symptoms:**
Cannot parse ConfigValue as JSON

**Solutions:**

1. **Check for escape characters:**
   ```bash
   # ConfigValue may be escaped string
   echo "$CONFIG_VALUE" | jq -r . | jq .
   ```

2. **Validate JSON syntax:**
   ```bash
   echo "$CONFIG_VALUE" | jq .
   ```

3. **Check encoding:**
   - Ensure UTF-8 encoding
   - Remove BOM if present

4. **Handle YAML:**
   - Some configs may be YAML format
   - Use YAML parser if needed

---

### Issue: Reference Validation Failures

**Symptoms:**
Configuration references tables/models that don't exist

**Diagnostic Steps:**

1. **For table references:**
   - Check if table exists in MaxCompute/OSS
   - Verify table name spelling
   - Check environment (Prod vs Pre tables)

2. **For model endpoints:**
   - Verify endpoint URL is reachable
   - Check model service status
   - Test endpoint separately

3. **For feature names:**
   - Check feature table schema
   - Verify feature names match exactly
   - Check if features are computed

**Solution:**
- Update config with correct references
- Ensure resources exist in target environment
- Use environment-specific resource names

---

### Issue: Validation Warnings vs Errors

**Question:**
Should warnings block deployment?

**Guideline:**

**Errors (❌):** Must be fixed before deployment
- Invalid syntax
- Missing required fields
- Inaccessible resources
- Type mismatches

**Warnings (⚠️):** Should review but may proceed
- Suboptimal settings
- Performance concerns
- Deprecated parameters
- Style violations

**Best Practice:**
- Fix all errors
- Review warnings with domain expert
- Document accepted warnings
- Monitor metrics post-deployment

---

## Performance Issues

### Issue: Slow Diagnosis Workflow

**Symptoms:**
Diagnosis takes >5 minutes

**Optimization:**

1. **Parallel API calls:**
   ```bash
   # Run independent queries in parallel
   aliyun eas describe-service ... &
   aliyun pairecservice list-engine-configs ... &
   wait
   ```

2. **Narrow log search:**
   - For request-level diagnosis, use `--keyword <request_id>` only (do NOT add `--start-time` / `--end-time`, which filters out business logs)
   - For broad scans, use time windows in `yyyy-MM-dd HH:mm:ss` UTC format
   - Limit page size

3. **Cache service info:**
   - Service config rarely changes
   - Can reuse for multiple diagnoses

---

### Issue: Configuration Validation Takes Too Long

**Symptoms:**
Validation >1 minute for single config

**Optimization:**

1. **Prioritize checks:**
   - Syntax validation first (fast)
   - Structure validation second
   - Resource validation last (slow)

2. **Parallel resource checks:**
   - Check tables in parallel
   - Batch model endpoint tests

3. **Cache validation results:**
   - Table existence checks
   - Model availability

---

## General Troubleshooting Tips

### 1. Enable Debug Logging

```bash
aliyun eas describe-service \
  --cluster-id <cluster-id> \
  --service-name <service-name> \
  --log-level DEBUG
```

### 2. Use Dry-Run Mode

```bash
aliyun eas describe-service \
  --cluster-id <cluster-id> \
  --service-name <service-name> \
  --cli-dry-run
```

### 3. Check API Quotas

Some APIs have rate limits:
- Pace requests if hitting limits
- Use pagination appropriately
- Cache results when possible

### 4. Verify Region Consistency

Ensure all resources in same region:
- EAS service region
- PAI-Rec instance region
- Data tables region

### 5. Consult Official Documentation

- [PAI-Rec Documentation](https://www.alibabacloud.com/help/pai/)
- [EAS Documentation](https://www.alibabacloud.com/help/eas/)
- [Aliyun CLI Documentation](https://www.alibabacloud.com/help/cli/)

---

## Getting Help

If issues persist:

1. **Collect diagnostic information:**
   - Error messages
   - Command outputs
   - Service/instance IDs
   - Timestamps

2. **Check service status:**
   - EAS console
   - PAI-Rec console
   - Service health metrics

3. **Contact support:**
   - Alibaba Cloud support ticket
   - PAI-Rec support channels
   - Include diagnostic information

---

## Related Documentation

- [RAM Policies](ram-policies.md) - Permission requirements
- [Related Commands](related-commands.md) - CLI command reference
- [Verification Method](verification-method.md) - How to verify success
- [Configuration Examples](configuration-examples.md) - Sample configurations
