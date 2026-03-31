# Acceptance Criteria: PTS Stress Testing Scenario Skill

**Scenario**: PTS Performance Testing Service - Create and Manage Stress Testing Scenarios  
**Purpose**: Skill testing acceptance criteria

---

## Correct CLI Command Patterns

### 1. Product — verify product name exists

#### ✅ CORRECT
```bash
aliyun pts <action>
```
The product name `pts` is correct for PTS (Performance Testing Service).

#### ❌ INCORRECT
```bash
aliyun PTS <action>     # Wrong: uppercase
aliyun performance <action>  # Wrong: not the product code
```

### 2. Command — verify action exists under the product

#### ✅ CORRECT PTS Native Commands
```bash
aliyun pts create-pts-scene
aliyun pts get-pts-scene
aliyun pts list-pts-scene
aliyun pts start-pts-scene
aliyun pts stop-pts-scene
aliyun pts delete-pts-scene
aliyun pts start-debug-pts-scene
aliyun pts get-pts-report-details
```

#### ✅ CORRECT JMeter Commands
```bash
aliyun pts save-open-jmeter-scene
aliyun pts get-open-jmeter-scene
aliyun pts list-open-jmeter-scenes
aliyun pts start-testing-jmeter-scene
aliyun pts stop-testing-jmeter-scene
aliyun pts remove-open-jmeter-scene
aliyun pts get-jmeter-report-details
```

#### ❌ INCORRECT
```bash
aliyun pts CreatePtsScene        # Wrong: PascalCase API style
aliyun pts create-scene          # Wrong: missing 'pts' prefix
aliyun pts createPtsScene        # Wrong: camelCase
```

### 3. Parameters — verify each parameter name exists for the command

#### ✅ CORRECT Parameter Names
```bash
# For create-pts-scene
aliyun pts create-pts-scene --scene '...'

# For get-pts-scene
aliyun pts get-pts-scene --scene-id <id>

# For list-pts-scene
aliyun pts list-pts-scene --page-number 1 --page-size 10

# For start-pts-scene
aliyun pts start-pts-scene --scene-id <id>

# For save-open-jmeter-scene
aliyun pts save-open-jmeter-scene --open-jmeter-scene '...'

# For get-jmeter-report-details
aliyun pts get-jmeter-report-details --report-id <id>
```

#### ❌ INCORRECT Parameter Names
```bash
aliyun pts get-pts-scene --sceneId <id>     # Wrong: camelCase
aliyun pts get-pts-scene --SceneId <id>     # Wrong: PascalCase
aliyun pts list-pts-scene --pageNumber 1    # Wrong: camelCase
```

### 4. User-Agent Flag — must be present in every command

#### ✅ CORRECT
```bash
aliyun pts list-pts-scene \
  --page-number 1 \
  --page-size 10 \
  --user-agent AlibabaCloud-Agent-Skills
```

#### ❌ INCORRECT
```bash
# Missing --user-agent flag
aliyun pts list-pts-scene --page-number 1 --page-size 10
```

### 5. JSON Parameter Format — verify complex parameters use proper JSON

#### ✅ CORRECT JSON Format for PTS Scene
```bash
aliyun pts create-pts-scene \
  --scene '{"name":"test-scene","type":"HTTP","requests":[{"url":"https://example.com","method":"GET"}]}' \
  --user-agent AlibabaCloud-Agent-Skills
```

#### ✅ CORRECT JSON Format for JMeter Scene
```bash
aliyun pts save-open-jmeter-scene \
  --open-jmeter-scene '{"scene_name":"MyJMeterTest","test_file":"example.jmx","duration":300,"concurrency":100,"mode":"CONCURRENCY"}' \
  --user-agent AlibabaCloud-Agent-Skills
```

#### ❌ INCORRECT JSON Format
```bash
# Wrong: unquoted strings
aliyun pts create-pts-scene --scene {name:test-scene}

# Wrong: double quotes not properly escaped
aliyun pts create-pts-scene --scene "{"name":"test"}"
```

---

## Parameter Confirmation Requirements

### Required User Confirmation Parameters

The following parameters MUST be confirmed with the user before execution:

| Parameter | Type | Example | Confirmation Required |
|-----------|------|---------|----------------------|
| Scene Name | String | "my-stress-test" | Yes |
| Target URL | String | "https://api.example.com" | Yes |
| Concurrency | Integer | 100 | Yes |
| Duration | Integer (seconds) | 300 | Yes |
| Request Method | String | "GET", "POST" | Yes |
| JMX File Path | String | "test.jmx" | Yes |

### ✅ CORRECT: Parameter Confirmation Flow

1. List all required parameters
2. Ask user to confirm or provide values
3. Show preview of command before execution
4. Execute only after user approval

### ❌ INCORRECT: Hardcoding Values

```bash
# Wrong: hardcoded URL without user confirmation
aliyun pts create-pts-scene \
  --scene '{"name":"test","requests":[{"url":"https://example.com"}]}' \
  --user-agent AlibabaCloud-Agent-Skills
```

---

## Success Verification Patterns

### ✅ CORRECT Verification Pattern

After each operation, verify success by checking the result:

```bash
# 1. Create scenario
SCENE_RESULT=$(aliyun pts create-pts-scene --scene '...' --user-agent AlibabaCloud-Agent-Skills)

# 2. Extract scene ID
SCENE_ID=$(echo $SCENE_RESULT | jq -r '.SceneId')

# 3. Verify creation
aliyun pts get-pts-scene --scene-id $SCENE_ID --user-agent AlibabaCloud-Agent-Skills
```

### ❌ INCORRECT: No Verification

```bash
# Wrong: no verification after creation
aliyun pts create-pts-scene --scene '...' --user-agent AlibabaCloud-Agent-Skills
# Immediately proceeding without checking if creation succeeded
```

---

## Error Handling Patterns

### ✅ CORRECT Error Handling

Check command exit status and handle errors:

```bash
if ! aliyun pts get-pts-scene --scene-id $SCENE_ID --user-agent AlibabaCloud-Agent-Skills; then
  echo "Error: Failed to get scene details"
  exit 1
fi
```

### ❌ INCORRECT: Ignoring Errors

```bash
# Wrong: ignoring potential errors
aliyun pts start-pts-scene --scene-id $SCENE_ID --user-agent AlibabaCloud-Agent-Skills
aliyun pts get-pts-report-details --scene-id $SCENE_ID --plan-id $PLAN_ID --user-agent AlibabaCloud-Agent-Skills
```

---

## Cleanup Patterns

### ✅ CORRECT Cleanup

Always provide cleanup commands after examples:

```bash
# Cleanup: Delete the test scenario
aliyun pts delete-pts-scene \
  --scene-id $SCENE_ID \
  --user-agent AlibabaCloud-Agent-Skills

# For JMeter scenarios
aliyun pts remove-open-jmeter-scene \
  --scene-id $JMETER_SCENE_ID \
  --user-agent AlibabaCloud-Agent-Skills
```

### ❌ INCORRECT: No Cleanup

Examples without cleanup commands may leave orphaned resources.

---

## Version Requirements

### ✅ CORRECT Version Check

```bash
# Must check CLI version >= 3.3.1
CLI_VERSION=$(aliyun version | head -1)
if [[ "$CLI_VERSION" < "3.3.1" ]]; then
  echo "Please upgrade aliyun CLI to version 3.3.1 or later"
  exit 1
fi
```

### ❌ INCORRECT: No Version Check

Running commands without verifying CLI version may lead to compatibility issues.
