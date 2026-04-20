# Acceptance Criteria: alibabacloud-aes-sysom-os-diagnosis

**Scenario**: SysOM 深度诊断 — ECS 实例内核级性能诊断、纳管与告警配置
**Purpose**: Skill testing acceptance criteria

---

## Correct CLI Command Patterns

### 1. Product — verify product name exists

#### ✅ CORRECT
```bash
aliyun sysom invoke-diagnosis ...
aliyun ecs describe-cloud-assistant-status ...
```

#### ❌ INCORRECT
```bash
# 错误：产品名不存在
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
aliyun sysom install-agent
aliyun sysom install-agent-for-cluster
aliyun sysom list-instance-status
aliyun sysom list-clusters
aliyun sysom list-alert-items
aliyun sysom create-alert-strategy  # CLI 存在但不支持 destinations，需用 SDK 脚本
aliyun sysom uninstall-agent
```

#### ❌ INCORRECT
```bash
# 错误：使用传统 API 格式而非 plugin mode
aliyun sysom InvokeDiagnosis
aliyun sysom GetDiagnosisResult
aliyun sysom InstallAgent
```

### 3. Parameters — verify each parameter name exists

#### ✅ CORRECT
```bash
# invoke-diagnosis 参数（params key 使用 snake_case，必须包含 type）
aliyun sysom invoke-diagnosis --service-name ocd --channel ecs \
  --params '{"instance":"i-xxx","region":"cn-hangzhou","start_time":0,"end_time":0,"type":"ocd","ai_roadmap":true,"enable_sysom_link":false}'

# install-agent 参数
aliyun sysom install-agent --instances instance=i-xxx region=cn-hangzhou --install-type InstallAndUpgrade --agent-id xxx --agent-version 3.12.0-1

# describe-cloud-assistant-status 参数
aliyun ecs describe-cloud-assistant-status --biz-region-id cn-hangzhou --instance-id i-xxx

# list-instance-status 参数
aliyun sysom list-instance-status --instance i-xxx --biz-region cn-hangzhou

# list-clusters（不传 --cluster-id，获取全量后匹配）
aliyun sysom list-clusters

# create-alert-strategy（通过 SDK 脚本，CLI 不支持 destinations）
.sysom-sdk-venv/bin/python scripts/create-alert-strategy.py --name my-strategy --items "节点CPU使用率检测" --clusters "default" --destinations "1"
```

#### ❌ INCORRECT
```bash
# 错误：参数名不正确
aliyun sysom invoke-diagnosis --serviceName ocd  # 应为 --service-name
aliyun sysom install-agent --instanceId i-xxx    # 应为 --instances instance=i-xxx region=xxx
aliyun ecs describe-cloud-assistant-status --region-id cn-hangzhou  # 应为 --biz-region-id
aliyun sysom check-instance-support --region cn-hangzhou  # 应为 --biz-region

# 错误：invoke-diagnosis params 使用 camelCase 或缺少 type
aliyun sysom invoke-diagnosis --params '{"instanceId":"i-xxx","startTime":0}'  # key 应为 snake_case，且缺少 type

# 错误：list-clusters 传入 --cluster-id（应获取全量后匹配）
aliyun sysom list-clusters --cluster-id cxxx  # 应不传参数，获取全量列表后按 cluster_id 匹配
```

### 5. Alert Destination SDK Calls — verify SDK usage patterns

#### ✅ CORRECT
```bash
# SDK 环境初始化
bash scripts/setup-sdk.sh

# 创建告警联系人（通过脚本）
.sysom-sdk-venv/bin/python scripts/create-alert-destination.py 'https://oapi.dingtalk.com/robot/send?access_token=xxx'

# 创建告警联系人（指定名称）
.sysom-sdk-venv/bin/python scripts/create-alert-destination.py 'https://oapi.dingtalk.com/robot/send?access_token=xxx' '运维告警群'
```

#### ❌ INCORRECT
```bash
# 错误：尝试通过 CLI 调用告警联系人 API（不支持 CLI）
aliyun sysom create-alert-destination ...  # 此命令不存在

# 错误：未先运行 setup-sdk.sh 就直接调用脚本
python scripts/create-alert-destination.py '...'  # 应使用虚拟环境中的 python

# 错误：直接用 pip install 而非 setup-sdk.sh（不会创建虚拟环境）
pip install alibabacloud_sysom20231230
```

### 4. --user-agent flag present

#### ✅ CORRECT
```bash
aliyun sysom invoke-diagnosis --service-name ocd --channel ecs --params '...' --user-agent AlibabaCloud-Agent-Skills
```

#### ❌ INCORRECT
```bash
# 错误：缺少 --user-agent
aliyun sysom invoke-diagnosis --service-name ocd --channel ecs --params '...'
```

---

## Credential Verification Pattern

#### ✅ CORRECT
```bash
aliyun configure list --user-agent AlibabaCloud-Agent-Skills
```

#### ❌ INCORRECT
```bash
# 错误：打印 AK/SK 值
echo $ALIBABA_CLOUD_ACCESS_KEY_ID

# 错误：在命令行中传入明文凭据
aliyun configure set --access-key-id LTAI5tXXXXXX --access-key-secret 8dXXXXXXXX
```

---

## Parameter Handling

#### ✅ CORRECT
- 所有用户可定制参数（RegionId、instance_id 等）在执行前向用户确认
- `ocd_description` 使用纯英文关键词
- `--instances` 使用结构化格式 `instance=<id> region=<region>`

#### ❌ INCORRECT
- 假设 region 为 `cn-hangzhou` 而不询问用户
- 将中文直接传入 `ocd_description`
- `--instances` 使用 JSON 数组格式而非结构化格式

---

## CLI Plugin Mode Format

#### ✅ CORRECT
```bash
aliyun sysom invoke-diagnosis    # 小写 + 连字符
aliyun sysom get-diagnosis-result
aliyun sysom install-agent
```

#### ❌ INCORRECT
```bash
aliyun sysom InvokeDiagnosis     # 传统 API 格式
aliyun sysom GetDiagnosisResult
aliyun sysom InstallAgent
```
