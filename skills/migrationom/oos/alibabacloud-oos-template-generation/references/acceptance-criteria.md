# Acceptance Criteria: alibabacloud-oos-template-generation

**Scenario**: OOS Template Intelligent Generation
**Purpose**: Skill testing acceptance criteria

---

## Template Format Validation

### 1. FormatVersion — Must be `OOS-2019-06-01`

#### CORRECT
```yaml
FormatVersion: OOS-2019-06-01
```

#### INCORRECT
```yaml
FormatVersion: OOS-2020-01-01  # This version does not exist
```

### 2. Description — Must include both en and zh-cn bilingual content

#### CORRECT
```yaml
Description:
  en: 'Reboot an ECS instance'
  zh-cn: 'Reboot ECS instance'
```

#### INCORRECT
```yaml
Description: 'Reboot ECS instance'  # Missing bilingual structure
```

### 3. Task Name — Must use English naming, matching [a-zA-Z0-9-_]+ pattern

#### CORRECT
```yaml
Tasks:
  - Name: rebootInstance
  - Name: describe_instances
```

#### INCORRECT
```yaml
Tasks:
  - Name: reboot instance  # Cannot contain spaces
```

## Action Validation

### 4. Cloud Product Action Format

#### CORRECT
```yaml
Action: ACS::ECS::RebootInstance
Action: ACS::RDS::RestartInstance
```

#### INCORRECT
```yaml
Action: ACS::ExecuteScript  # Does not exist
Action: ACS::Flow::ForEach  # Does not exist
Action: ACS::RunCommand  # Does not exist, should use ACS::ECS::RunCommand
```

### 5. Parameter Reference Format

#### CORRECT
```yaml
Properties:
  regionId: '{{ regionId }}'
  instanceId: '{{ ACS::TaskLoopItem }}'
```

#### INCORRECT
```yaml
Properties:
  regionId: '{regionId}'  # Missing double curly braces and spaces
  regionId: '{{regionId}}'  # Missing spaces
```

## Loop Property Validation

### 6. Task Loop

#### CORRECT
```yaml
Tasks:
  - Name: stopInstances
    Action: ACS::ECS::StopInstance
    Properties:
      instanceId: '{{ ACS::TaskLoopItem }}'
    Loop:
      Items: '{{ describeInstances.instanceIds }}'
```

#### INCORRECT
```yaml
Tasks:
  - Name: stopInstances
    Action: ACS::Flow::ForEach  # This Action does not exist
    Properties:
      items: '{{ describeInstances.instanceIds }}'
```

## Output Reference Validation

### 7. Task Output Definition and Reference

#### CORRECT
```yaml
Tasks:
  - Name: listInstances
    Action: ACS::ExecuteAPI
    Outputs:
      instanceIds:
        Type: List
        ValueSelector: 'Instances.Instance[].InstanceId'
  - Name: stopInstances
    Action: ACS::ECS::StopInstance
    Properties:
      instanceId: '{{ ACS::TaskLoopItem }}'
    Loop:
      Items: '{{ listInstances.instanceIds }}'
```

#### INCORRECT
```yaml
Tasks:
  - Name: listInstances
    Action: ACS::ExecuteAPI
    # Missing Outputs definition
  - Name: stopInstances
    Action: ACS::ECS::StopInstance
    Loop:
      Items: '{{ listInstances.instanceIds }}'  # Referencing undefined output
```

## CLI Command Validation

### 8. OOS CLI Command Format — Must use plugin mode (kebab-case)

#### CORRECT
```bash
# OOS commands use plugin mode (kebab-case)
aliyun oos list-actions --biz-region-id cn-hangzhou --oos-action-name "ACS::ECS" --max-results 50
aliyun oos validate-template-content --biz-region-id cn-hangzhou --content "$(cat /tmp/oos_template.yaml)"
aliyun oos create-template --template-name "MyTemplate" --content '<yaml>'
aliyun oos start-execution --template-name "MyTemplate" --parameters '{"instanceId":"i-xxx"}'
```

#### INCORRECT
```bash
aliyun oos ListActions --RegionId cn-hangzhou  # Should use plugin mode (kebab-case)
aliyun oos ValidateTemplateContent --RegionId cn-hangzhou  # Should use validate-template-content
aliyun oos GetTemplate --TemplateName "MyTemplate"  # Should use get-template --template-name
```

### 9. OOS CLI Parameter Format

#### CORRECT
```bash
aliyun oos list-actions --biz-region-id cn-hangzhou --oos-action-name "ACS::ECS"
aliyun oos validate-template-content --biz-region-id cn-hangzhou --content "..."
```

#### INCORRECT
```bash
aliyun oos list-actions --RegionId cn-hangzhou  # Should use --biz-region-id
aliyun oos list-actions --OOSActionName "ACS::ECS"  # Should use --oos-action-name
```

## Security Validation

### 10. Do Not Fabricate Resource IDs

#### CORRECT
```yaml
Parameters:
  instanceId:
    Type: String
    Description: 'ECS Instance ID'
```

#### INCORRECT
```yaml
Parameters:
  instanceId:
    Type: String
    Default: 'i-bp1234567890abcdef'  # Should not fabricate resource IDs as default values
```

## Tool Usage Validation

### 11. Must Use CLI Commands, Not Abstract Tools

#### CORRECT
```bash
# Search Actions
aliyun oos list-actions --biz-region-id cn-hangzhou --oos-action-name "ACS::ECS::Reboot" --max-results 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-oos-template-generation

# Validate template
aliyun oos validate-template-content --biz-region-id cn-hangzhou --content "$(cat /tmp/oos_template.yaml)" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-oos-template-generation
```

#### INCORRECT
```
# Non-existent abstract tools
validate_oos_template(template_content="...")
list_oos_actions(action_name_filter="ACS::ECS")
get_oos_action_detail(action_name="ACS::ECS::RebootInstance")
```
