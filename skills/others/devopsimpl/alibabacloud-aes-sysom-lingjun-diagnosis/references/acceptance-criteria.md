# Acceptance Criteria: alibabacloud-aes-sysom-lingjun-diagnosis

**Scenario**: SysOM deep diagnosis — kernel-level performance diagnosis and DingTalk alert configuration for lingjun nodes
**Purpose**: Skill testing acceptance criteria

> Node enrollment / Agent installation is **not** part of this skill: `install-agent`, `list-instance-status` and `uninstall-agent` must never appear in a correct run.

---

## Correct CLI Command Patterns

### 1. Product — verify product name exists

#### ✅ CORRECT
```bash
aliyun sysom invoke-diagnosis ...
aliyun ecs describe-cloud-assistant-status ...   # Cloud Assistant status check, pass the lingjun node ID
```

#### ❌ INCORRECT
```bash
# Wrong: product name does not exist
aliyun SysOM invoke-diagnosis ...
aliyun sysom InvokeDiagnosis ...
```

### 2. Command — verify action exists under the product

#### ✅ CORRECT
```bash
aliyun sysom invoke-diagnosis
aliyun sysom get-diagnosis-result
aliyun sysom initial-sysom --check-only false --source aes-skills
aliyun sysom check-instance-support
aliyun sysom list-alert-items
aliyun sysom create-alert-strategy  # Exists in the CLI but does NOT support destinations; use the SDK script
```

#### ❌ INCORRECT
```bash
# Wrong: using the legacy API format instead of plugin mode
aliyun sysom InvokeDiagnosis
aliyun sysom GetDiagnosisResult

# Wrong: enrollment commands are out of this skill's scope
aliyun sysom install-agent ...
aliyun sysom list-instance-status ...
aliyun sysom uninstall-agent ...
```

### 3. Parameters — verify each parameter name exists

#### ✅ CORRECT
```bash
# invoke-diagnosis parameters (lingjun node: --channel is fixed to eflo, params keys use snake_case, and type plus product are mandatory)
aliyun sysom invoke-diagnosis --service-name ocd --channel eflo \
  --params '{"instance":"e01-cn-xxx","region":"cn-hangzhou","start_time":0,"end_time":0,"type":"ocd","ai_roadmap":true,"enable_sysom_link":false,"product":"LINGJUN"}'

# describe-cloud-assistant-status parameters
aliyun ecs describe-cloud-assistant-status --biz-region-id cn-hangzhou --instance-id e01-cn-xxx

# create-alert-strategy (via the SDK script, since the CLI does not support destinations)
SKILL_SESSION_ID=<session-id> .sysom-sdk-venv/bin/python scripts/create-alert-strategy.py --name my-strategy --items "Node CPU Usage Detection" --clusters "default" --destinations "1"
```

#### ❌ INCORRECT
```bash
# Wrong: incorrect parameter names
aliyun sysom invoke-diagnosis --serviceName ocd  # should be --service-name
aliyun ecs describe-cloud-assistant-status --region-id cn-hangzhou  # should be --biz-region-id
aliyun sysom check-instance-support --region cn-hangzhou  # should be --biz-region

# Wrong: invoke-diagnosis params use camelCase or omit type
aliyun sysom invoke-diagnosis --params '{"instanceId":"e01-cn-xxx","startTime":0}'  # keys should be snake_case, and type is missing

# Wrong: lingjun node diagnosis uses the ecs channel or omits product
aliyun sysom invoke-diagnosis --service-name ocd --channel ecs --params '{"instance":"e01-cn-xxx",...}'  # should be --channel eflo
aliyun sysom invoke-diagnosis --service-name ocd --channel eflo --params '{"instance":"e01-cn-xxx","type":"ocd"}'  # missing "product":"LINGJUN"
```

### 5. Alert Destination SDK Calls — verify SDK usage patterns

#### ✅ CORRECT
```bash
# SDK environment setup
bash scripts/setup-sdk.sh

# Create an alert destination (via the script)
SKILL_SESSION_ID=<session-id> .sysom-sdk-venv/bin/python scripts/create-alert-destination.py 'https://oapi.dingtalk.com/robot/send?access_token=xxx'

# Create an alert destination (with an explicit name)
SKILL_SESSION_ID=<session-id> .sysom-sdk-venv/bin/python scripts/create-alert-destination.py 'https://oapi.dingtalk.com/robot/send?access_token=xxx' 'ops-alert-group'
```

#### ❌ INCORRECT
```bash
# Wrong: calling the alert destination API through the CLI (not supported by the CLI)
aliyun sysom create-alert-destination ...  # this command does not exist

# Wrong: calling the script without running setup-sdk.sh first
python scripts/create-alert-destination.py '...'  # use the python from the virtual environment

# Wrong: running pip install directly instead of setup-sdk.sh (no virtual environment is created)
pip install alibabacloud_sysom20231230

# Wrong: omitting SKILL_SESSION_ID, so the SDK User-Agent carries no session-id
.sysom-sdk-venv/bin/python scripts/create-alert-destination.py '...'
```

### 4. User-Agent and session-id

#### ✅ CORRECT
```bash
# OpenAPI commands carry the full UA template, with the same session-id reused across the session
aliyun sysom invoke-diagnosis --service-name ocd --channel eflo --params '...' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-aes-sysom-lingjun-diagnosis/3f9a1c2b4d5e6f708192a3b4c5d6e7f8

# SDK scripts receive the same session-id through SKILL_SESSION_ID
SKILL_SESSION_ID=3f9a1c2b4d5e6f708192a3b4c5d6e7f8 .sysom-sdk-venv/bin/python scripts/create-alert-strategy.py --name my-strategy --items "Node CPU Usage Detection" --clusters "default" --destinations "1"

# Local/system commands carry NO --user-agent
aliyun version
aliyun configure list
aliyun configure set --auto-plugin-install true
aliyun plugin update
```

#### ❌ INCORRECT
```bash
# Wrong: missing --user-agent on an OpenAPI command
aliyun sysom invoke-diagnosis --service-name ocd --channel eflo --params '...'

# Wrong: UA missing the skill name and/or the session-id segment
aliyun sysom invoke-diagnosis --service-name ocd --channel eflo --params '...' --user-agent AlibabaCloud-Agent-Skills

# Wrong: a different session-id per command instead of one reused value
aliyun sysom get-diagnosis-result --task-id xxx --user-agent AlibabaCloud-Agent-Skills/alibabacloud-aes-sysom-lingjun-diagnosis/<newly-generated-id>

# Wrong: --user-agent added to local/system commands
aliyun version --user-agent AlibabaCloud-Agent-Skills
aliyun configure list --user-agent AlibabaCloud-Agent-Skills

# Wrong: deprecated ai-mode mechanism used to set the User-Agent
aliyun configure ai-mode enable
aliyun configure ai-mode set-user-agent --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-aes-sysom-lingjun-diagnosis"
aliyun configure ai-mode disable
```

---

## Credential Verification Pattern

#### ✅ CORRECT
```bash
aliyun configure list
```

#### ❌ INCORRECT
```bash
# Wrong: printing AK/SK values
echo $ALIBABA_CLOUD_ACCESS_KEY_ID

# Wrong: passing plaintext credentials on the command line
aliyun configure set --access-key-id LTAI5tXXXXXX --access-key-secret 8dXXXXXXXX
```

---

## Parameter Handling

#### ✅ CORRECT
- Start the diagnosis as soon as `region` and `instance_id` are known — no parameter-confirmation round
- Ask only for a missing `region` / `instance_id`, or for a Webhook URL when alerts were requested without one
- `ocd_description` uses English-only keywords

#### ❌ INCORRECT
- Assuming the region is `cn-hangzhou` without asking the user
- Asking the user to confirm parameters or to approve starting the diagnosis when both required parameters are already known
- Asking for an exact timestamp instead of inferring the time window from a temporal reference
- Passing non-English text directly into `ocd_description`
- Passing an ECS instance ID (`i-xxx`) — this Skill only supports lingjun nodes (prefixed with `e01-`)

---

## CLI Plugin Mode Format

#### ✅ CORRECT
```bash
aliyun sysom invoke-diagnosis    # lowercase + hyphens
aliyun sysom get-diagnosis-result
aliyun sysom list-alert-items
```

#### ❌ INCORRECT
```bash
aliyun sysom InvokeDiagnosis     # legacy API format
aliyun sysom GetDiagnosisResult
aliyun sysom ListAlertItems
```
