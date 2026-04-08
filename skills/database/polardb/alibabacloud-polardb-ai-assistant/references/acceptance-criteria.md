# Acceptance Criteria: alibabacloud-polardb-ai-assistant

**Scenario**: PolarDB Database AI Assistant
**Purpose**: Skill testing acceptance criteria

---

# Correct CLI Command Patterns

## 1. Product — DAS (Database Autonomy Service)

#### CORRECT
```bash
aliyun das GetYaoChiAgent --Query "List clusters" --Source "polardb-console" --endpoint das.cn-shanghai.aliyuncs.com --user-agent AlibabaCloud-Agent-Skills
```

#### INCORRECT
```bash
# Error: Product name spelling error
aliyun DAS GetYaoChiAgent --Query "List clusters"

# Error: Using non-existent plugin mode command
aliyun das get-yao-chi-agent --query "List clusters"
```

**Note**: DAS product uses traditional API format (PascalCase), not plugin mode (kebab-case).

## 2. Command — GetYaoChiAgent

#### CORRECT
```bash
aliyun das GetYaoChiAgent --Query "Hello" --endpoint das.cn-shanghai.aliyuncs.com --user-agent AlibabaCloud-Agent-Skills
```

#### INCORRECT
```bash
# Error: API name spelling error
aliyun das GetYaochiAgent --Query "Hello"

# Error: Using non-existent API
aliyun das YaoChiAgent --Query "Hello"
```

## 3. Parameters — Parameter Validation

### GetYaoChiAgent Parameters

#### CORRECT
```bash
# Required parameter --Query
aliyun das GetYaoChiAgent --Query "List PolarDB clusters in Hangzhou region" --endpoint das.cn-shanghai.aliyuncs.com --user-agent AlibabaCloud-Agent-Skills

# Optional parameter --Source
aliyun das GetYaoChiAgent --Query "List clusters" --Source "polardb-console" --endpoint das.cn-shanghai.aliyuncs.com --user-agent AlibabaCloud-Agent-Skills

# Optional parameter --SessionId (multi-turn conversation)
aliyun das GetYaoChiAgent --Query "Continue analysis" --SessionId "sess-xxx" --Source "polardb-console" --endpoint das.cn-shanghai.aliyuncs.com --user-agent AlibabaCloud-Agent-Skills

# Optional parameter --ExtraInfo
aliyun das GetYaoChiAgent --Query "Show cluster" --ExtraInfo "{}" --endpoint das.cn-shanghai.aliyuncs.com --user-agent AlibabaCloud-Agent-Skills
```

#### INCORRECT
```bash
# Error: Missing required parameter --Query
aliyun das GetYaoChiAgent --Source "polardb-console"

# Error: Parameter name in lowercase (CLI parameter names are case-sensitive)
aliyun das GetYaoChiAgent --query "List clusters"

# Error: Parameter name spelling error
aliyun das GetYaoChiAgent --Query "List clusters" --Session-Id "sess-xxx"

# Error: Using non-existent parameter
aliyun das GetYaoChiAgent --Query "List clusters" --RegionId "cn-hangzhou"
```

## 4. Endpoint — Endpoint Validation

#### CORRECT
```bash
# GetYaoChiAgent uses cn-shanghai endpoint uniformly
aliyun das GetYaoChiAgent --Query "List clusters" --endpoint das.cn-shanghai.aliyuncs.com --user-agent AlibabaCloud-Agent-Skills
```

#### INCORRECT
```bash
# Error: Using wrong endpoint
aliyun das GetYaoChiAgent --Query "List clusters" --endpoint das.cn-beijing.aliyuncs.com

# Error: Endpoint not specified, may use wrong default endpoint
aliyun das GetYaoChiAgent --Query "List clusters"
```

## 5. --user-agent Flag — Must Include

#### CORRECT
```bash
aliyun das GetYaoChiAgent --Query "List clusters" --endpoint das.cn-shanghai.aliyuncs.com --user-agent AlibabaCloud-Agent-Skills
```

#### INCORRECT
```bash
# Error: Missing --user-agent flag
aliyun das GetYaoChiAgent --Query "List clusters" --endpoint das.cn-shanghai.aliyuncs.com
```

## 6. Timeout — Timeout Settings

#### CORRECT
```bash
# SSE streaming API requires longer read timeout (180 seconds)
aliyun das GetYaoChiAgent --Query "List clusters" --endpoint das.cn-shanghai.aliyuncs.com --read-timeout 180 --connect-timeout 30 --user-agent AlibabaCloud-Agent-Skills
```

#### INCORRECT
```bash
# Error: Read timeout too short, streaming API may timeout
aliyun das GetYaoChiAgent --Query "List clusters" --endpoint das.cn-shanghai.aliyuncs.com --read-timeout 10 --user-agent AlibabaCloud-Agent-Skills
```

---

# Correct Bash Script Patterns

## 1. Script Invocation

#### CORRECT
```bash
bash $SKILL_DIR/scripts/call_yaochi_agent.sh "List PolarDB clusters in Hangzhou region"
bash $SKILL_DIR/scripts/call_yaochi_agent.sh "Analyze cluster pc-xxx performance" --session-id "sess-xxx"
bash $SKILL_DIR/scripts/call_yaochi_agent.sh "List clusters" --profile myprofile
echo "List clusters" | bash $SKILL_DIR/scripts/call_yaochi_agent.sh -
```

#### INCORRECT
```bash
# Error: Using old Python script
uv run $SKILL_DIR/scripts/call_yaochi_agent.py "List clusters"

# Error: Using Python interpreter to run bash script
python $SKILL_DIR/scripts/call_yaochi_agent.sh "List clusters"

# Error: Parameter name using old format
bash $SKILL_DIR/scripts/call_yaochi_agent.sh "List clusters" --role-arn acs:ram::xxx:role/xxx
```

## 2. SSE Response Parsing

#### CORRECT — Script automatically parses SSE response
```
# Input: SSE format response body
data: {"Content":"PolarDB cluster list:","SessionId":"sess-abc123","ReasoningContent":""}
data: {"Content":"\n1. pc-xxx (cn-hangzhou)","SessionId":"sess-abc123","ReasoningContent":""}
data: [DONE]

# Output: Concatenated Content
PolarDB cluster list:
1. pc-xxx (cn-hangzhou)
```

## 3. Credential Management

#### CORRECT
```bash
# Use existing aliyun CLI configuration
aliyun configure --mode OAuth
bash $SKILL_DIR/scripts/call_yaochi_agent.sh "List clusters"

# Use specified profile
bash $SKILL_DIR/scripts/call_yaochi_agent.sh "List clusters" --profile myprofile
```

#### INCORRECT
```bash
# Error: Hardcoding AK/SK in script
export ALIBABA_CLOUD_ACCESS_KEY_ID="LTAI5tXXXXXXXX"
export ALIBABA_CLOUD_ACCESS_KEY_SECRET="8dXXXXXXXXXXXX"

# Error: Using custom credential variables from old script
export YAOCHI_ACCESS_KEY_ID="xxx"
export YAOCHI_ACCESS_KEY_SECRET="xxx"
```

---

# Authentication Patterns

#### CORRECT — Use aliyun CLI configuration
```bash
# OAuth mode (Recommended)
aliyun configure --mode OAuth

# AK mode
aliyun configure set --mode AK --access-key-id <AK> --access-key-secret <SK> --region cn-hangzhou

# Cross-account RamRoleArn mode
aliyun configure set --mode RamRoleArn --access-key-id <AK> --access-key-secret <SK> --ram-role-arn <ARN> --role-session-name yaochi-session --region cn-hangzhou
```

#### INCORRECT — Managing credentials in script
```python
# Error: Using Python SDK to manage credentials
from alibabacloud_das20200116.client import Client as DAS20200116Client

# Error: Parsing credentials from .env file
# Error: Parsing credentials from ~/.alibabacloud/credentials
```
