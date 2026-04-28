# Acceptance Criteria: alibabacloud-cfw-exposure-detection

**Scenario**: Public Network Exposure Detection & Analysis
**Purpose**: Skill testing acceptance criteria

---

## Correct CLI Invocation Patterns

### 1. Command Format — verify product and API name (plugin mode)

#### CORRECT — Plugin mode (lowercase-hyphenated)
```bash
aliyun cloudfw describe-internet-open-ip \
  --CurrentPage 1 \
  --PageSize 50 \
  --StartTime 1710000000 \
  --EndTime 1711000000 \
  --region cn-hangzhou \
  --user-agent AlibabaCloud-Agent-Skills
```

#### INCORRECT — Wrong product name
```bash
aliyun cloudfirewall describe-internet-open-ip --region cn-hangzhou
```
**Why**: Product name is `cloudfw`, not `cloudfirewall` or `cfw`.

#### INCORRECT — PascalCase API name (legacy format)
```bash
aliyun cloudfw DescribeInternetOpenIp --region cn-hangzhou
```
**Why**: Cloud Firewall CLI uses plugin mode with lowercase-hyphenated API names (e.g., `describe-internet-open-ip`).

#### INCORRECT — Missing --user-agent
```bash
aliyun cloudfw describe-internet-open-ip --CurrentPage 1 --PageSize 50 --region cn-hangzhou
```
**Why**: All commands must include `--user-agent AlibabaCloud-Agent-Skills`.

#### INCORRECT — Using old Python SDK pattern
```bash
python3 scripts/call_api.py \
  --api-name DescribeInternetOpenIp \
  --api-version 2017-12-07 \
  --endpoint cloudfw.cn-hangzhou.aliyuncs.com
```
**Why**: The skill uses Aliyun CLI directly, not a Python SDK wrapper script.

### 2. Parameter Format

#### CORRECT — PascalCase CLI flags with plugin mode command
```bash
aliyun cloudfw describe-internet-open-ip \
  --CurrentPage 1 \
  --PageSize 50 \
  --StartTime 1710000000 \
  --EndTime 1711000000 \
  --region cn-hangzhou \
  --user-agent AlibabaCloud-Agent-Skills
```

#### INCORRECT — Kebab-case parameter names
```bash
aliyun cloudfw describe-internet-open-ip --current-page 1 --page-size 50
```
**Why**: Parameters use PascalCase (e.g., `--CurrentPage`, `--PageSize`), only the API action name uses lowercase-hyphenated format.

#### INCORRECT — Using --region-id instead of --region
```bash
aliyun cloudfw DescribeInternetOpenIp --region-id cn-hangzhou
```
**Why**: The CLI global flag is `--region`, not `--region-id`.

#### INCORRECT — JSON params format (old SDK pattern)
```bash
--params '{"CurrentPage": "1", "PageSize": "50"}'
```
**Why**: CLI uses individual flags, not a JSON params string.

### 3. Authentication — never expose credentials

#### CORRECT — Verify credential profile via default credential chain
```bash
aliyun configure list
```

#### INCORRECT — Reading or printing raw credentials
```bash
aliyun configure get           # FORBIDDEN: may expose credential details
cat ~/.aliyun/config.json      # FORBIDDEN: may expose credential details
```

#### INCORRECT — Any command that prints environment credentials
```bash
echo $CLOUD_ACCESS_KEY                # FORBIDDEN: example of secret output
printenv | grep -i credential         # FORBIDDEN: may reveal secrets
env | grep -i access_key              # FORBIDDEN: may reveal secrets
```

### 4. API Names — verify plugin mode (lowercase-hyphenated)

#### CORRECT
```
describe-internet-open-statistic
describe-internet-open-ip
describe-internet-open-port
describe-asset-list
describe-asset-risk-list
describe-vulnerability-protected-list
describe-risk-event-group
describe-control-policy
```

#### INCORRECT
```
DescribeInternetOpenIp         # PascalCase (legacy, not plugin mode)
describeInternetOpenIp         # Wrong casing
Describe_Internet_Open_Ip      # Wrong format
DescribeInternetOpenIP         # Wrong casing (Ip not IP)
DescribeOpenIp                 # Wrong API name
```
