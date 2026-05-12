# Acceptance Criteria: alibabacloud-sase-pa-network-diagnosis

**Scenario**: SASE Private Access Network Diagnosis
**Purpose**: Skill test acceptance criteria

---

# Correct CLI Command Patterns

> This Skill uses Aliyun CLI plugin mode for csas diagnosis APIs. Commands and parameters MUST be lowercase kebab-case. API/RAM action names may remain PascalCase only when referring to OpenAPI metadata or permissions.

## 1. Product — Product Name

#### ✅ CORRECT
```bash
aliyun csas create-pa-diagnosis-task ...
aliyun csas get-pa-diagnosis-task ...
```

#### ❌ INCORRECT
Do not use product names such as `sase` or `yundun-sase`; the plugin product name must be `csas`.

## 2. CLI Action — Must Use Plugin Mode Kebab-Case

#### ✅ CORRECT
```bash
aliyun csas create-pa-diagnosis-task ...
aliyun csas get-pa-diagnosis-task ...
```

#### ❌ INCORRECT
Do not use PascalCase OpenAPI action names in CLI invocations. Use `create-pa-diagnosis-task` and `get-pa-diagnosis-task`.

## 3. Parameters — Must Use Lowercase Kebab-Case

#### ✅ CORRECT
```bash
aliyun csas create-pa-diagnosis-task --diagnose-type FullLink --host example.com --port 443 --protocol TCP --pop-mode AutoSelect
aliyun csas get-pa-diagnosis-task --diagnose-id diag-xxx
```

#### ❌ INCORRECT
Do not use PascalCase parameter names; use lowercase kebab-case parameters.

## 4. Generic Mode Flags — Must Not Be Used

#### ✅ CORRECT
```bash
aliyun csas create-pa-diagnosis-task --diagnose-type FullLink ...
```

#### ❌ INCORRECT
Do not use legacy generic-mode flags such as `--force` or `--method POST`; plugin mode handles the API method.

## 5. AI-Mode User Agent — Must Be Configured Before CLI Calls

#### ✅ CORRECT
```bash
aliyun configure ai-mode enable
aliyun configure ai-mode set-user-agent --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-sase-pa-network-diagnosis"
aliyun csas get-pa-diagnosis-task --diagnose-id diag-xxx
aliyun configure ai-mode disable
```

#### ❌ INCORRECT
Do not pass a per-command `--user-agent` flag to csas plugin commands; configure it through AI-mode before executing the workflow.

## 6. DiagnoseType Enum Values

#### ✅ CORRECT
```bash
--diagnose-type FullLink      # Full link diagnosis
--diagnose-type Application   # Application diagnosis
```

#### ❌ INCORRECT
```bash
--diagnose-type fulllink       # Incorrect enum casing
--diagnose-type full_link      # Incorrect enum format
--diagnose-type app            # Invalid value
```

## 7. Protocol Enum Values

#### ✅ CORRECT
```bash
--protocol TCP
--protocol UDP
```

#### ❌ INCORRECT
```bash
--protocol tcp     # Incorrect enum casing
--protocol HTTP    # Unsupported protocol
```

## 8. PopMode Enum Values

#### ✅ CORRECT
```bash
--pop-mode AutoSelect     # Auto-select (supported for FullLink diagnosis)
--pop-mode ManualSelect   # Manual selection (requires --pop-id)
```

#### ❌ INCORRECT
```bash
--pop-mode auto          # Invalid value
--pop-mode manual        # Invalid value
```

## 9. UDP Extra Config Object Format

#### ✅ CORRECT
```bash
--udp-extra-configs RequestContent=PING ExpectedResponse=PONG
```

#### ❌ INCORRECT
```bash
# WRONG: JSON-string parameter style does not match current plugin mode help
--udp-extra-configs '{"RequestContent":"PING","ExpectedResponse":"PONG"}'
```

## 10. --cli-query JMESPath Expressions

#### ✅ CORRECT
```bash
--cli-query 'DiagnosisTask.DiagnoseId'
--cli-query 'DiagnosisTask.Status'
--cli-query 'DiagnosisTask.Result.Success'
```

#### ❌ INCORRECT
```bash
# WRONG: Incorrect field name casing
--cli-query 'diagnosisTask.diagnoseId'
--cli-query 'DiagnosisTask.status'
```

## 11. Concurrency Limit Retry Handling

#### ✅ CORRECT
When task creation returns `DiagnosisTask.NumberExceedsLimit`, retry at most 5 times with incremental waits of 30, 60, 90, 120, and 150 seconds. If all retries fail, tell the user the concurrency limit is still full, ask them to clear idle diagnosis tasks in the Console or confirm switching diagnosis type, then disable AI-mode and stop.

#### ❌ INCORRECT
Do not retry with a fixed 30-second interval forever. Do not stop immediately after the first concurrency-limit failure. Do not continue polling when no `DiagnoseId` was created.

## 12. Polling Loop Safety

#### ✅ CORRECT
Poll with `MAX_POLLS=20`, sleep 10 seconds at the start of each loop iteration, normalize CLI status output, and use `grep -qE 'Finished|Failed'` instead of exact quoted-string equality. If polling times out, retrieve the full task result once, summarize the current status, and ask whether to continue.

#### ❌ INCORRECT
Do not use an unbounded `while true` loop. Do not rely only on exact matches such as `"Finished"`. Do not keep polling after 20 attempts without user confirmation.
