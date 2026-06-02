# Acceptance Criteria: alibabacloud-waf-cname-config-export

**Scenario**: WAF 3.0 CNAME Domain Configuration Batch Export
**Purpose**: Skill testing acceptance criteria

---

## Correct CLI Command Patterns

### 1. Product — verify product name exists

✅ CORRECT
```bash
aliyun waf-openapi describe-instance --region cn-hangzhou
```

❌ INCORRECT
```bash
aliyun waf describe-instance --region cn-hangzhou
```
**Reason**: Product name is `waf-openapi`, not `waf`.

### 2. Command — verify action exists under the product

✅ CORRECT
```bash
aliyun waf-openapi describe-domains --region cn-hangzhou --instance-id <id>
```

❌ INCORRECT
```bash
aliyun waf-openapi list-domains --region cn-hangzhou --instance-id <id>
```
**Reason**: Action is `describe-domains`, not `list-domains`.

### 3. Parameters — verify each parameter name exists

✅ CORRECT
```bash
aliyun waf-openapi describe-domains --region cn-hangzhou --instance-id waf-instance-xxx --page-number 1 --page-size 50
```

❌ INCORRECT
```bash
aliyun waf-openapi describe-domains --region cn-hangzhou --InstanceId waf-instance-xxx --PageNumber 1 --PageSize 50
```
**Reason**: CLI plugin mode uses lowercase hyphenated parameters (`--instance-id`), not PascalCase (`--InstanceId`).

### 4. Region values — verify enum values are valid

✅ CORRECT
```bash
aliyun waf-openapi describe-instance --region cn-hangzhou
aliyun waf-openapi describe-instance --region ap-southeast-1
```

❌ INCORRECT
```bash
aliyun waf-openapi describe-instance --region cn-shanghai
```
**Reason**: WAF only supports `cn-hangzhou` and `ap-southeast-1`.

---

## Correct Python Wrapper Code Patterns

### 1. Excel Export Script

✅ CORRECT
```python
import json, subprocess, time
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

def run_cli(args, cli_profile=None):
    cmd = ["aliyun"] + args
    if cli_profile:
        cmd.extend(["--profile", cli_profile])
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return None
    return json.loads(result.stdout)
```

**Reason**: Uses subprocess to call CLI, handles errors gracefully.

### 2. Pagination Logic

✅ CORRECT
```python
def query_domains(instance_id, region, cli_profile=None):
    all_domains, page = [], 1
    while True:
        data = run_cli([
            "waf-openapi", "describe-domains",
            "--region", region, "--instance-id", instance_id,
            "--page-number", str(page), "--page-size", "50"
        ], cli_profile)
        if not data:
            break
        all_domains.extend(data.get("Domains", []))
        if len(all_domains) >= data.get("TotalCount", 0):
            break
        page += 1
    return all_domains
```

**Reason**: Properly handles pagination using TotalCount.

### 3. Rate Limiting

✅ CORRECT
```python
for i, dm in enumerate(domains):
    detail = query_domain_detail(inst["instance_id"], dn, inst["region"], CLI_PROFILE)
    time.sleep(0.2)  # 200ms delay
```

❌ INCORRECT
```python
for i, dm in enumerate(domains):
    detail = query_domain_detail(inst["instance_id"], dn, inst["region"], CLI_PROFILE)
    # No delay - will trigger throttling
```
**Reason**: Must add delay to prevent API throttling.

### 4. Field Name Mapping

✅ CORRECT
```python
row = [
    d.get("Domain", ""),
    d.get("Cname", ""),
    redirect.get("Loadbalance", ""),  # Note: lowercase 'b'
    ", ".join(str(x) for x in redirect.get("BackendList", [])),
    listen.get("CertId", ""),
]
```

❌ INCORRECT
```python
row = [
    redirect.get("LoadBalanceType", ""),  # Wrong field name
    redirect.get("Backends", []),  # Wrong field name
    listen.get("CertificateId", ""),  # Wrong field name
]
```
**Reason**: Actual API response uses `Loadbalance`, `BackendList`, `CertId`.

---

## Anti-Patterns

| Anti-Pattern | Why Wrong | Correct Approach |
|--------------|-----------|------------------|
| Hardcoding AK/SK | Security risk | Use `aliyun configure list` to verify |
| Using SDK when CLI is available | Unnecessary complexity | Prefer CLI first |
| Skipping both regions | Missing dual-instance data | Always query cn-hangzhou + ap-southeast-1 |
| No rate limiting | API throttling | Add `time.sleep(0.2)` between requests |
| Wrong field names | API response mismatch | Check actual API response structure |
| No pagination handling | Incomplete data | Loop until TotalCount reached |
