# Acceptance Criteria — Domain Query

**Scenario**: Domain information query operations (read-only)
**Purpose**: Skill testing acceptance criteria

---

## Negative Examples

| ❌ WRONG | ✅ CORRECT | Rule |
|----------|------------|------|
| `aliyun domain QueryDomainList` | `aliyun domain query-domain-list` | kebab-case actions |
| `aliyun Domain query-domain-list` | `aliyun domain query-domain-list` | lowercase product code |
| `--DomainName "example.com"` | `--domain-name "example.com"` | kebab-case parameters |
| `--PageNum 1` | `--page-num 1` | kebab-case parameters |
| `--InstanceId "S2024..."` | `--instance-id "S2024..."` | kebab-case parameters |
| `--region-id cn-hangzhou` | No `--region-id` | global service |
| Missing `--user-agent` | `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-domain-manage` | mandatory user-agent |
| `echo $ALIBABA_CLOUD_ACCESS_KEY_ID` | `aliyun configure list` | never expose credentials |
| Fabricated domain data in output | Only display actual API response data | no fabrication |

---

## Pre-flight Validation Checklist

Before executing CLI commands, verify:

- [ ] CLI version >= 3.3.3 (`aliyun version`)
- [ ] Credentials valid (`aliyun configure list`)
- [ ] Auto plugin install enabled (`aliyun configure set --auto-plugin-install true`)
- [ ] Plugins up-to-date (`aliyun plugin update`)
- [ ] AI-mode enabled (`aliyun configure ai-mode enable`)
- [ ] All required parameters are provided
- [ ] `--page-num` >= 1, `--page-size` between 1 and 200
- [ ] Domain name format is valid (for domain detail queries)
- [ ] Timestamp values are in milliseconds (for advanced query date filters)

---

## CLI Command Correctness

- [ ] All commands use kebab-case actions and parameters
- [ ] All commands include `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-domain-manage`
- [ ] No `--region-id` is passed (domain is a global service)
- [ ] Product code is `domain` (lowercase)

## Security

- [ ] Query operations do not require user confirmation
- [ ] No AK/SK values are printed or echoed
- [ ] Credential check uses only `aliyun configure list`

## Output Validation Checklist

> **[MUST] Verify after every API call before displaying results:**

- [ ] All displayed information comes from actual API results (no fabrication)
- [ ] Displayed count matches `TotalItemNum` from API response
- [ ] Pagination info is shown when `TotalPageNum > CurrentPageNum`
- [ ] Dates are displayed in user-friendly format (e.g., `2025-01-01`)
- [ ] No truncated or incomplete data is presented without re-querying

---

## Functional Requirements — Domain Query

- [ ] Can query domain list with `query-domain-list`
- [ ] Supports pagination with `--page-num` and `--page-size`
- [ ] Supports fuzzy search with `--domain-name` parameter
- [ ] Can query domain details with `query-domain-by-domain-name`
- [ ] Can query by instance ID with `query-domain-by-instance-id`
- [ ] Can use advanced search with `query-advanced-domain-list`
- [ ] Supports domain status filter (`--domain-status`)
- [ ] Supports expiration date range filter

## AI-Mode Lifecycle

- [ ] AI-mode enabled before first CLI invocation
- [ ] AI-mode user-agent set correctly
- [ ] AI-mode disabled at every exit point (success, failure, cancellation)

---

## Testing Checklist

| # | Test Case | Expected Flow |
|---|-----------|--------------|
| 1 | "查看 example.com 的详细信息" | `query-domain-by-domain-name` |
| 2 | "查看我所有的域名" | `query-domain-list --page-num 1 --page-size 20` |
| 3 | "查看即将过期的域名" | `query-advanced-domain-list` with expiration date filters |
| 4 | "查看所有 .com 域名" | `query-advanced-domain-list --suffix-name ".com"` |
| 5 | "查一下实例 S20241234567890" | `query-domain-by-instance-id --instance-id "S20241234567890"` |
| 6 | "查看所有正常状态的域名" | `query-advanced-domain-list --domain-status 1` |
| 7 | "查看已过期的域名" | `query-advanced-domain-list --domain-status 2` |
| 8 | "搜索包含 test 的域名" | `query-domain-list --domain-name "test"` |
