# Acceptance Criteria: alibabacloud-polardbx-ai-assistant

**Scenario**: PolarDB-X Distributed Database AI Assistant
**Purpose**: Skill testing acceptance criteria

---

# Correct CLI Command Patterns

## 1. Product - DAS (Database Autonomy Service)

#### CORRECT
```bash
# Plugin kebab-case command (Signature V3, recommended)
aliyun das get-yao-chi-agent --query "List instances" --source "polardbx-console" --endpoint das.cn-shanghai.aliyuncs.com --user-agent AlibabaCloud-Agent-Skills
```

#### INCORRECT
```bash
# Error: product name wrong case
aliyun DAS get-yao-chi-agent --query "List instances"

# Error: missing --user-agent flag
aliyun das get-yao-chi-agent --query "List instances" --source "polardbx-console" --endpoint das.cn-shanghai.aliyuncs.com
```

## 2. Command - get-yao-chi-agent

#### CORRECT
```bash
aliyun das get-yao-chi-agent --query "Hello" --endpoint das.cn-shanghai.aliyuncs.com --user-agent AlibabaCloud-Agent-Skills
```

#### INCORRECT
```bash
# Error: API name typo
aliyun das get-yao-chi --query "Hello"

# Error: using non-existent API
aliyun das yaochi-agent --query "Hello"
```

## 3. Parameters

### get-yao-chi-agent Parameters

#### CORRECT
```bash
# Required parameter --query
aliyun das get-yao-chi-agent --query "List PolarDB-X instances in Hangzhou region" --endpoint das.cn-shanghai.aliyuncs.com --user-agent AlibabaCloud-Agent-Skills

# Optional parameter --source
aliyun das get-yao-chi-agent --query "List instances" --source "polardbx-console" --endpoint das.cn-shanghai.aliyuncs.com --user-agent AlibabaCloud-Agent-Skills

# Optional parameter --session-id (multi-turn)
aliyun das get-yao-chi-agent --query "Continue analysis" --session-id "sess-xxx" --source "polardbx-console" --endpoint das.cn-shanghai.aliyuncs.com --user-agent AlibabaCloud-Agent-Skills
```

#### INCORRECT
```bash
# Error: missing required parameter --query
aliyun das get-yao-chi-agent --source "polardbx-console"

# Error: using non-existent parameter
aliyun das get-yao-chi-agent --query "List instances" --region-id "cn-hangzhou"
```

## 4. Endpoint

#### CORRECT
```bash
# get-yao-chi-agent always uses cn-shanghai endpoint
aliyun das get-yao-chi-agent --query "List instances" --endpoint das.cn-shanghai.aliyuncs.com --user-agent AlibabaCloud-Agent-Skills
```

#### INCORRECT
```bash
# Error: wrong endpoint
aliyun das get-yao-chi-agent --query "List instances" --endpoint das.cn-beijing.aliyuncs.com

# Error: missing endpoint, may use wrong default
aliyun das get-yao-chi-agent --query "List instances"
```

## 5. --user-agent Flag - Required

#### CORRECT
```bash
aliyun das get-yao-chi-agent --query "List instances" --endpoint das.cn-shanghai.aliyuncs.com --user-agent AlibabaCloud-Agent-Skills
```

#### INCORRECT
```bash
# Error: missing --user-agent flag
aliyun das get-yao-chi-agent --query "List instances" --endpoint das.cn-shanghai.aliyuncs.com
```

## 6. Timeout Settings

#### CORRECT
```bash
# SSE streaming API needs longer read timeout (180s)
aliyun das get-yao-chi-agent --query "List instances" --endpoint das.cn-shanghai.aliyuncs.com --read-timeout 180 --connect-timeout 30 --user-agent AlibabaCloud-Agent-Skills
```

#### INCORRECT
```bash
# Error: read timeout too short, streaming API may timeout
aliyun das get-yao-chi-agent --query "List instances" --endpoint das.cn-shanghai.aliyuncs.com --read-timeout 10 --user-agent AlibabaCloud-Agent-Skills
```

---

# Correct Bash Script Patterns

## 1. Script Invocation

#### CORRECT
```bash
bash $SKILL_DIR/scripts/call_yaochi_agent.sh "List PolarDB-X instances in Hangzhou region"
bash $SKILL_DIR/scripts/call_yaochi_agent.sh "Analyze performance of instance pxc-xxx" --session-id "sess-xxx"
bash $SKILL_DIR/scripts/call_yaochi_agent.sh "List instances" --profile myprofile
echo "List instances" | bash $SKILL_DIR/scripts/call_yaochi_agent.sh -
```

#### INCORRECT
```bash
# Error: using Python script (does not exist)
uv run $SKILL_DIR/scripts/call_yaochi_agent.py "List instances"

# Error: using Python interpreter on bash script
python $SKILL_DIR/scripts/call_yaochi_agent.sh "List instances"

# Error: using old parameter format
bash $SKILL_DIR/scripts/call_yaochi_agent.sh "List instances" --role-arn acs:ram::xxx:role/xxx
```

## 2. SSE Response Parsing

#### CORRECT - script auto-parses SSE response
```
# Input: SSE format response body
data: {"Content":"PolarDB-X instance list:","SessionId":"sess-abc123","ReasoningContent":""}
data: {"Content":"\n1. pxc-xxx (cn-hangzhou)","SessionId":"sess-abc123","ReasoningContent":""}
data: [DONE]

# Output: concatenated Content
PolarDB-X instance list:
1. pxc-xxx (cn-hangzhou)
```

## 3. Credential Management

#### CORRECT
```bash
# Use existing aliyun CLI configuration
aliyun configure --mode OAuth
bash $SKILL_DIR/scripts/call_yaochi_agent.sh "List instances"

# Use specific profile
bash $SKILL_DIR/scripts/call_yaochi_agent.sh "List instances" --profile myprofile
```

#### INCORRECT
```bash
# Error: hardcoding AK/SK in script
export ALIBABA_CLOUD_ACCESS_KEY_ID="LTAI5tXXXXXXXX"
export ALIBABA_CLOUD_ACCESS_KEY_SECRET="8dXXXXXXXXXXXX"

# Error: using custom credential variables
export YAOCHI_ACCESS_KEY_ID="xxx"
export YAOCHI_ACCESS_KEY_SECRET="xxx"
```

---

# Authentication Patterns

#### CORRECT - use aliyun CLI configuration
```bash
# OAuth mode (recommended)
aliyun configure --mode OAuth

# AK mode
aliyun configure set --mode AK --access-key-id <AK> --access-key-secret <SK> --region cn-hangzhou

# Cross-account RamRoleArn mode
aliyun configure set --mode RamRoleArn --access-key-id <AK> --access-key-secret <SK> --ram-role-arn <ARN> --role-session-name yaochi-session --region cn-hangzhou
```

#### INCORRECT - managing credentials in script
```python
# Error: using Python SDK for credentials
from alibabacloud_das20200116.client import Client as DAS20200116Client

# Error: parsing credentials from .env file
# Error: parsing credentials from ~/.alibabacloud/credentials
```
