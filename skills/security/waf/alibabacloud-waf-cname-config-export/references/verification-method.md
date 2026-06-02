# Success Verification Method

## Verification Steps

### Step 1: File Existence Check

```bash
ls -lh waf_cname_config_export_*.xlsx
```

Expected: At least one Excel file with timestamp in the name.

### Step 2: Sheet Structure Check

Open the Excel file and verify:

- Sheet names: "Chinese Mainland" and/or "Non-Chinese Mainland"
- Missing sheet means no instance was found in that region
- Each sheet has exactly 18 column headers:

| # | Column Name |
|---|-------------|
| 1 | Domain |
| 2 | CNAME |
| 3 | Status |
| 4 | HTTP Ports |
| 5 | HTTPS Ports |
| 6 | Backends |
| 7 | Backup Backends |
| 8 | Load Balancing |
| 9 | TLS Version |
| 10 | HTTP/2 |
| 11 | Cert ID |
| 12 | SNI |
| 13 | SNI Host |
| 14 | Connect Timeout(s) |
| 15 | Read Timeout(s) |
| 16 | Write Timeout(s) |
| 17 | Force HTTP Backend |
| 18 | Resource Group |

### Step 3: Domain Count Verification

Compare domain count in Excel with WAF console:

1. Open WAF console: https://waf.console.aliyun.com/
2. Navigate to "Domain Management" → "CNAME Access"
3. Count domains for each region
4. Compare with Excel row count (excluding header)

### Step 4: Spot-Check Domain Config

Select 2-3 domains and verify:

- **CNAME value** matches console display
- **Backend list** matches origin server configuration
- **HTTP/HTTPS ports** match listener configuration
- **TLS version** and **HTTP/2** settings match console
- **SNI configuration** matches console

### Step 5: Data Integrity Check

Verify:

- No unexpected empty cells in critical columns (Domain, CNAME)
- Status values are valid: "Normal", "Abnormal", "Configuring"
- Boolean fields (HTTP/2, SNI, Force HTTP Backend) show "Yes" or "No"
- Timeout values are numeric

## Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Empty Excel file | No WAF instances found | Verify account has WAF 3.0 instances |
| Missing domains | Pagination error | Check PageSize and loop logic |
| Empty CNAME fields | Non-CNAME onboarding type | Label as "Cloud Product Onboarding" or "Transparent Proxy" |
| Permission denied | Insufficient RAM permissions | Attach `AliyunYundunWAFReadOnlyAccess` policy |
