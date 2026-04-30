# Acceptance Criteria: alibabacloud-ddoscoo-intercept-query

**Scenario**: DDoS Pro (Anti-DDoS Pro) Intercept Query
**Purpose**: Skill testing acceptance criteria

---

# Correct CLI Command Patterns

## 1. Product — verify product name exists

#### ✅ CORRECT
```bash
aliyun ddoscoo describe-instances ...
aliyun sls get-logs ...
```

#### ❌ INCORRECT
```
# Wrong product name (should be ddoscoo):
#   aliyun ddos describe-instances ...
# Wrong case:
#   aliyun DDosCoo describe-instances ...
# Traditional API format (PascalCase), not plugin mode:
#   Must use kebab-case like describe-instances, NOT PascalCase like DescribeInstances
```

## 2. Command — verify action exists under the product (plugin mode)

#### ✅ CORRECT
```bash
aliyun ddoscoo describe-instances --page-number 1 --page-size 50 --region cn-hangzhou
aliyun ddoscoo describe-web-access-log-status --domain 'example.com' --region cn-hangzhou
aliyun ddoscoo describe-web-cc-rules-v2 --domain 'example.com' --region cn-hangzhou
aliyun ddoscoo describe-web-precise-access-rule --domains 'example.com' --region cn-hangzhou
```

#### ❌ INCORRECT
```
# Traditional API format (PascalCase), not plugin mode:
#   Must use kebab-case like describe-instances, NOT PascalCase
#   Must use kebab-case like describe-web-access-log-status, NOT PascalCase
#   Must use kebab-case like describe-web-cc-rules-v2, NOT PascalCase
```

## 3. Parameters — verify each parameter name exists for the command

#### ✅ CORRECT
```bash
aliyun ddoscoo describe-instances --page-number 1 --page-size 50 --region cn-hangzhou
aliyun ddoscoo disable-web-cc-rule --domain 'example.com' --region cn-hangzhou
```

#### ❌ INCORRECT
```
# Wrong parameter format (PascalCase vs kebab-case):
#   Must use --page-number, NOT --PageNumber
#   Must use --domain, NOT --Domain
```

## 4. AI-Mode Lifecycle + User-Agent Header

#### ✅ CORRECT
```bash
# At skill start: enable AI-Mode and set User-Agent
aliyun configure ai-mode enable
aliyun configure ai-mode set-user-agent --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-intercept-query"

# Every aliyun command must also include --header with full skill name
aliyun ddoscoo describe-instances --page-number 1 --page-size 50 --region cn-hangzhou --header User-Agent=AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-intercept-query
aliyun sls get-logs --project <p> --logstore <l> --from <ts> --to <ts> --query <q> --region <r> --header User-Agent=AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-intercept-query

# At skill exit (every exit point): disable AI-Mode
aliyun configure ai-mode disable
```

#### ❌ INCORRECT
```bash
# Missing --header on any command
aliyun ddoscoo describe-instances --page-number 1 --page-size 50 --region cn-hangzhou

# Missing skill name suffix in User-Agent
aliyun ddoscoo describe-instances ... --header User-Agent=AlibabaCloud-Agent-Skills

# Not disabling AI-mode at exit
# (AI-mode must be disabled before final response)
```

## 5. Security — never expose credentials

#### ✅ CORRECT
```bash
aliyun configure list    # Only check status
```

#### ❌ INCORRECT
```bash
echo $ALIBABA_CLOUD_ACCESS_KEY_ID       # FORBIDDEN: printing AK
aliyun configure set --access-key-id xxx # FORBIDDEN: literal credential values
```

---

# Correct Script Patterns

## 1. SLS Log Query Script

#### ✅ CORRECT
```bash
python3 scripts/get_ddos_logs.py \
  --project ddoscoo-project-xxx \
  --logstore ddoscoo-logstore \
  --request-id 2f6fc15517769105850466500e008c \
  --region cn-hangzhou
```

#### ❌ INCORRECT
```bash
python3 get_ddos_logs.py ...                     # Script not in scripts/ directory
python3 scripts/get_ddos_logs.py --request_id    # Wrong parameter format (underscore vs hyphen)
```

---

# Workflow Patterns

## 1. Idempotent Check-Then-Act

#### ✅ CORRECT
```
1. Query current state (describe-web-cc-rules-v2 / describe-web-precise-access-rule)
2. If already in target state -> skip, inform user
3. If not -> confirm with user -> execute change
```

#### ❌ INCORRECT
```
1. Directly execute change without checking current state
2. Execute change without user confirmation
```

## 2. Full Log Enable Flow

#### ✅ CORRECT
```
1. Check SLS status (describe-sls-open-status)
2. Check log store exists (describe-log-store-exist-status)
3. Check domain log status (describe-web-access-log-status)
4. If enabled -> proceed to query
5. If not -> inform user -> get consent -> enable (enable-web-access-log-config)
```

#### ❌ INCORRECT
```
1. Skip status check, directly enable
2. Disable full log (disable-web-access-log-config) — FORBIDDEN via this skill
```
