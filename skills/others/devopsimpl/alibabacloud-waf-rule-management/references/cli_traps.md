# WAF CLI Traps Checklist

> This file documents common traps and error patterns in Alibaba Cloud WAF CLI calls. MUST be consulted before execution.

---

## 1. DescribeDefenseRules Whitelist Scenario MUST Specify RuleType

**API**: `DescribeDefenseRules`

### Error Pattern

```bash
# ❌ WRONG: Query whitelist rules without specifying RuleType
aliyun waf-openapi describe-defense-rules \
  --InstanceId '<instance_id>' \
  --Query '{"templateId":<template_id>}'
# Result: Returns 0 records
```

### Correct Usage

```bash
# ✅ CORRECT: MUST add --RuleType whitelist for whitelist scenarios
aliyun waf-openapi describe-defense-rules \
  --InstanceId '<instance_id>' \
  --Query '{"templateId":<template_id>}' \
  --RuleType 'whitelist'
```

### Root Cause

WAF API has special handling for whitelist DefenseScene. If `--RuleType whitelist` is not explicitly specified, the API filters out whitelist rules.

### Checklist

Before querying rules, confirm:
- [ ] If querying whitelist rules, MUST add `--RuleType whitelist`
- [ ] Other DefenseScenes also need corresponding RuleType specified

---

## 2. SLS Query Field Truncation Issue

**API**: `aliyunlog log get_log`

### Error Pattern

```bash
# ❌ WRONG: Without specifying select, log fields may be truncated
aliyunlog log get_log \
  --project=<project> --logstore=wafnew-logstore \
  --from=<timestamp> --to=<timestamp> \
  --query="request_traceid: '<traceid>'"
# Result: Key fields like matched_host, real_client_ip may be missing
```

### Correct Usage

```bash
# ✅ CORRECT: Use select to explicitly specify required fields
aliyunlog log get_log \
  --project=<project> --logstore=wafnew-logstore \
  --from=<timestamp> --to=<timestamp> \
  --query="* | select request_traceid, matched_host, host, real_client_ip, request_path, request_method, status, final_plugin, final_rule_id, waf_rule_type, waf_action"
```

---

## 3. WAF 3.0 Console Path Errors

**CRITICAL**: WAF 3.0 and WAF 2.0 console paths are COMPLETELY different.

### Error Pattern

```
❌ WRONG (WAF 2.0 path):
- Security Operations → Website Configuration
- Protection Configuration → CC Security Protection
```

### Correct Usage

```
✅ CORRECT (WAF 3.0 path):
- CC Protection: Protection Configuration → Web Core Protection → CC Protection
- Whitelist: Protection Configuration → Custom Protection → Whitelist
- Custom Rules: Protection Configuration → Custom Protection → Custom Rules
- IP Blacklist: Protection Configuration → Custom Protection → IP Blacklist
```

### Important Notes

- WAF 3.0 uses "Web Core Protection" submenu (not top-level menu)
- CC Protection requires creating protection templates first
- CC Protection strict mode is NOT suitable for API interfaces
- If user does not specify version, ALWAYS default to WAF 3.0

---

## 4. CC Protection Mode Selection

**Common Mistake**: Using strict mode for API interfaces

### Error Pattern

Using CC Protection strict mode for API rate limiting:
- Causes high false positive rate
- Intercepts legitimate API requests
- Only suitable for web pages (including H5)

### Correct Usage

**For API rate limiting**:
- Use Custom Rules instead: `Protection Configuration` → `Custom Protection` → `Custom Rules`
- Configure frequency-based rules with IP dimension
- Set appropriate thresholds (1.5-2x normal peak)

**CC Protection mode selection**:
- **Normal Mode**: Daily use, low false positive rate
- **Strict Mode**: Only for web pages under CC attack, NEVER for APIs

---

## 5. Rule Naming Convention Violations

### Error Pattern

```
❌ WRONG (contains spaces):
- "rate limit api login"
- "whitelist scan test"
```

### Correct Usage

```
✅ CORRECT (use underscores or hyphens):
- rate_limit_api_login
- whitelist-scan-test
- cc_protection_api
```

### Rule

All rule names and protection template names MUST NOT contain spaces.

---

## 6. SLS CLI Missing User-Agent

### Error Pattern

```bash
# ❌ WRONG: Missing User-Agent parameter
aliyunlog log get_log \
  --project=<project> --logstore=wafnew-logstore \
  --from=<timestamp> --to=<timestamp> \
  --query="*"
```

### Correct Usage

```bash
# ✅ CORRECT: ALL Alibaba Cloud CLI commands MUST include User-Agent
aliyun waf-openapi describe-instance \
  --version 2021-10-01 --force --region cn-hangzhou \
  --user-agent AlibabaCloud-Agent-Skills
```

---

## 7. SLS CLI 命令格式陷阱 (aliyunlog)

**重要**: `aliyunlog` 命令有多个常见陷阱,必须严格遵守正确格式。

### 7.1 子命令缺失

```bash
# ❌ 错误: 缺少 log 子命令
aliyunlog get_log --project=... --logstore=...

# ✅ 正确: 必须包含 log 子命令
aliyunlog log get_log --project=... --logstore=...
```

### 7.2 时间参数名称错误

```bash
# ❌ 错误: 使用 --from 和 --to
aliyunlog log get_log ... --from="$(date +%s)" --to="$(date +%s)"

# ✅ 正确: 必须使用 --from_time 和 --to_time
aliyunlog log get_log ... --from_time="$(date +%s)" --to_time="$(date +%s)"
```

### 7.3 凭证参数错误

```bash
# ❌ 错误: aliyunlog 不支持 --profile 参数
aliyunlog log get_log ... --profile default --endpoint cn-hangzhou.log.aliyuncs.com

# ✅ 正确: 使用 --region-endpoint 参数,凭证通过 ~/.aliyunlog/config 配置
aliyunlog log get_log --region-endpoint="cn-hangzhou.log.aliyuncs.com" --project=... --logstore=...
```

**重要说明**:
- `aliyunlog` **不支持** `--profile` 参数
- 凭证必须提前通过 `aliyunlog configure` 配置,存储在 `~/.aliyunlog/config`
- 如果用户未配置,需要指导用户先运行: `aliyunlog configure`

### 7.4 查询语法格式

```bash
# ❌ 错误: 使用纯 SQL 格式
--query="* | select field1, field2 where request_traceid = 'xxx'"

# ✅ 正确: 使用 SLS 查询语法 (先过滤后处理)
--query="request_traceid:xxx | select field1, field2 limit 1"
```

### 7.5 完整正确示例

```bash
# ✅ 完整的正确命令格式
aliyunlog log get_log \
  --region-endpoint="cn-hangzhou.log.aliyuncs.com" \
  --project="wafnew-project-1882089769163987-cn-hangzhou" \
  --logstore="wafnew-logstore" \
  --from_time="$(( $(date +%s) - 604800 ))" \
  --to_time="$(date +%s)" \
  --query="request_traceid:2f6f0cbc17759652456034145eef13 | select matched_host, host, real_client_ip, request_path, request_method, status, final_plugin, final_rule_id, waf_rule_type, waf_action limit 1" \
  --format=json
```

### 7.6 常见错误排查

| 错误信息 | 原因 | 解决方案 |
|---------|------|---------|
| `Unknown command: 'get_log'` | 缺少 `log` 子命令 | 使用 `aliyunlog log get_log` |
| `Missing required parameter 'from_time'` | 使用了 `--from` 而非 `--from_time` | 改用 `--from_time` 和 `--to_time` |
| `Missing required parameter 'logstore'` | 参数格式错误或使用了不支持的参数 | 检查参数名称,移除 `--profile` |
| `Invalid parameters` | 多个参数格式问题 | 参考 7.5 完整示例重新构造命令 |

---

## Quick Reference Checklist

在执行任何 WAF CLI 命令之前:

- [ ] 使用 WAF 3.0 API 版本 (`2021-10-01`)
- [ ] 使用正确的 WAF 3.0 控制台路径 (非 WAF 2.0)
- [ ] 添加了 `--user-agent AlibabaCloud-Agent-Skills` 参数 (仅限 aliyun 命令)
- [ ] **未使用 `--profile` 参数** (依赖默认配置)
- [ ] **未运行 `aliyun configure get`** (会暴露AK/SK)
- [ ] aliyunlog 命令使用 `--region-endpoint` 而非 `--profile`
- [ ] aliyunlog 命令包含 `log` 子命令
- [ ] aliyunlog 时间参数使用 `--from_time` 和 `--to_time`
- [ ] 规则名称不包含空格
- [ ] 白名单查询包含 `--RuleType whitelist`
- [ ] SLS 查询使用显式 `select` 指定关键字段
- [ ] CC 防护严格模式不用于 API 接口
- [ ] 输出简洁 (尽可能控制在 20 行以内)
