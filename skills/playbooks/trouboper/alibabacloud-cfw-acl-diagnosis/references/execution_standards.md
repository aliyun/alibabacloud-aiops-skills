# Execution Standards for Cloud Firewall ACL Diagnosis

This document defines mandatory execution standards for all diagnosis operations.

## 🔒 MANDATORY EXECUTION PRINCIPLES (APPLIES TO ALL AGENT FRAMEWORKS)

1. **ALL operations MUST be executed via actual CLI tool calls** - NEVER describe operations in text without executing them
2. **Each diagnosis step MUST include**:
   a. Actual CLI command executed
   b. Real command output from the CLI
   c. Analysis conclusion based on actual output
3. **If any command fails**, record the error and try alternatives - NEVER skip the step
4. **NEVER give diagnosis conclusions without actually executing commands first**
5. **NEVER fabricate or simulate CLI output data** - use only real API responses
6. **Output conclusions DIRECTLY in conversation** - NO file output required

## 🔒 CLI COMMAND EXECUTION STANDARDS

### Standard Command Format

**⚠️ CRITICAL**: aliyun CLI does NOT support `--output json` parameter. Output defaults to JSON format. DO NOT add `--output` flag.

```bash
# CORRECT format
aliyun cloudfw describe-control-policy --direction in --page-size 50 --current-page 1 --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-cfw-acl-diagnosis/{{SESSION_ID}}"

# WRONG format (will cause 'bad flag format' error)
aliyun cloudfw describe-control-policy --direction in --page-size 50 --current-page 1 --output json
```

### Error Handling Priority

When CLI command fails, troubleshoot in this order:
1. **First**: Check command syntax (parameter format, flag names)
2. **Second**: Check API version and endpoint
3. **Last**: Consider authentication issues (verify `ALIBABA_CLOUD_ACCESS_KEY_ID` / `ALIBABA_CLOUD_ACCESS_KEY_SECRET` env vars are set — do NOT run `aliyun configure list` or `aliyun configure get`)

**DO NOT mistake syntax errors for authentication failures.**

### Timeout Policy

- **aliyun CLI default timeout**: 30 seconds per command (built-in, no explicit flag needed)
- **Paginated queries**: Each page call ≤ 30s; total pages × 30s should not exceed 3 minutes — stop and report partial results if exceeded
- **Traffic log queries**: Limit time window to ≤ 24 hours per call to avoid timeout; narrow with `--StartTime` / `--EndTime` if needed

## 🔒 SECURITY REQUIREMENTS (MANDATORY)

1. **NEVER include the following sensitive information in plaintext in any output files, scripts, or logs:**
   - AccessKeyId, AccessKeySecret, SecurityToken
   - Any passwords, keys, or tokens

2. **When referencing credentials in scripts, MUST use environment variables:**
   ```python
   # CORRECT way
   access_key_id = os.environ.get('ALIBABA_CLOUD_ACCESS_KEY_ID')
   access_key_secret = os.environ.get('ALIBABA_CLOUD_ACCESS_KEY_SECRET')
   
   # FORBIDDEN (NEVER do this)
   access_key_secret = '<YOUR_SECRET_KEY>'  # NEVER hardcode real credentials
   ```

3. **PREFER using `aliyun` CLI tool** (automatically reads configured credentials) instead of manually constructing signed curl requests

4. **If credentials appear in outputs, MUST mask them** (e.g., show first 4 chars + ***)
