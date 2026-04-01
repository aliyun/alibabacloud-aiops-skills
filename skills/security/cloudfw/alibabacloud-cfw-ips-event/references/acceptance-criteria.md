# Acceptance Criteria: alibabacloud-cfw-ips-event

Scenario: IPS Alert Event Analysis
Purpose: Skill testing acceptance criteria

## Correct CLI Invocation Patterns

### 1. Command Format

**CORRECT:**
```bash
aliyun cloudfw DescribeRiskEventGroup \
  --CurrentPage 1 \
  --PageSize 50 \
  --StartTime 1711324800 \
  --EndTime 1711411200 \
  --DataType 1 \
  --region cn-hangzhou \
  --user-agent AlibabaCloud-Agent-Skills
```

**INCORRECT - Wrong product name:**
```bash
# WRONG: Using "cloudfirewall" instead of "cloudfw"
aliyun cloudfirewall DescribeRiskEventGroup ...

# WRONG: Using "cfw" instead of "cloudfw"
aliyun cfw DescribeRiskEventGroup ...
```

**INCORRECT - Using kebab-case for API name:**
```bash
# WRONG: API names must be PascalCase, not kebab-case
aliyun cloudfw describe-risk-event-group ...
```

**INCORRECT - Missing --user-agent:**
```bash
# WRONG: All commands MUST include --user-agent
aliyun cloudfw DescribeRiskEventGroup \
  --CurrentPage 1 \
  --PageSize 50 \
  --region cn-hangzhou
```

**INCORRECT - Using old Python SDK pattern:**
```bash
# WRONG: Do not use Python SDK or other SDK patterns
from aliyunsdkcore.client import AcsClient
client = AcsClient(ak, sk, 'cn-hangzhou')
```

### 2. Parameter Format

**CORRECT - PascalCase parameters:**
```bash
aliyun cloudfw DescribeRiskEventGroup \
  --CurrentPage 1 \
  --PageSize 50 \
  --StartTime 1711324800 \
  --EndTime 1711411200 \
  --DataType 1 \
  --VulLevel 3 \
  --Direction in \
  --SrcIP 1.2.3.4 \
  --region cn-hangzhou \
  --user-agent AlibabaCloud-Agent-Skills
```

**INCORRECT - Wrong parameter casing:**
```bash
# WRONG: Using camelCase
aliyun cloudfw DescribeRiskEventGroup \
  --currentPage 1 \
  --pageSize 50 \
  --startTime 1711324800

# WRONG: Using snake_case
aliyun cloudfw DescribeRiskEventGroup \
  --current_page 1 \
  --page_size 50 \
  --start_time 1711324800

# WRONG: Using kebab-case
aliyun cloudfw DescribeRiskEventGroup \
  --current-page 1 \
  --page-size 50 \
  --start-time 1711324800
```

### 3. Authentication

**CORRECT - Let CLI handle credentials automatically:**
```bash
# Just call the API directly; CLI reads credentials from config
aliyun cloudfw DescribeDefaultIPSConfig \
  --region cn-hangzhou \
  --user-agent AlibabaCloud-Agent-Skills
```

**INCORRECT - Passing credentials in command:**
```bash
# WRONG: Never pass AK/SK directly in commands
aliyun cloudfw DescribeDefaultIPSConfig \
  --access-key-id LTAI5tXXXX \
  --access-key-secret 8dXXXX \
  --region cn-hangzhou

# WRONG: Never echo/print credentials
echo $ALIBABA_CLOUD_ACCESS_KEY_ID
cat ~/.aliyun/config.json
```

### 4. API Names

**CORRECT - All 7 API names (PascalCase):**
- `DescribeRiskEventStatistic`
- `DescribeRiskEventGroup`
- `DescribeRiskEventTopAttackAsset`
- `DescribeRiskEventTopAttackType`
- `DescribeRiskEventTopAttackApp`
- `DescribeDefaultIPSConfig`
- `DescribeSignatureLibVersion`

**INCORRECT - Wrong casing or naming:**
```
# WRONG casing examples:
describeriskeventstatistic
describeRiskEventStatistic
Describe_Risk_Event_Statistic
describe-risk-event-statistic
DESCRIBERRISKEVENTSTATISTIC

# WRONG names:
DescribeRiskEventStats          (wrong abbreviation)
DescribeRiskEventList           (wrong API name)
DescribeIPSConfig               (wrong - should be DescribeDefaultIPSConfig)
DescribeSignatureVersion        (wrong - should be DescribeSignatureLibVersion)
DescribeRiskEventTopAttack      (incomplete name)
```

### 5. Region Parameter

**CORRECT:**
```bash
# Mainland China (default)
--region cn-hangzhou

# Hong Kong / Overseas
--region ap-southeast-1
```

**INCORRECT:**
```bash
# WRONG: Other regions are not valid for Cloud Firewall
--region cn-shanghai
--region cn-beijing
--region us-east-1
```

### 6. Time Parameters

**CORRECT - Unix timestamp in seconds:**
```bash
--StartTime 1711324800 --EndTime 1711411200
```

**INCORRECT:**
```bash
# WRONG: Millisecond timestamps
--StartTime 1711324800000 --EndTime 1711411200000

# WRONG: Date strings
--StartTime "2024-03-25" --EndTime "2024-03-26"

# WRONG: ISO format
--StartTime "2024-03-25T00:00:00Z"
```
