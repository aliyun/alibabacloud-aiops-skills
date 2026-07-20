# Acceptance Criteria: alibabacloud-agentloop-evaluation

**Scenario**: AgentLoop evaluation workflow orchestration
**Purpose**: Skill testing acceptance criteria

---

# Correct CLI Command Patterns

## 1. Product — verify product name exists

#### ✅ CORRECT
```bash
aliyun agentloop list-evaluators --agent-space <space>
```

#### ❌ INCORRECT
```bash
aliyun AgentLoop ListEvaluators --agent-space <space>   # Wrong: API mode, not plugin mode
aliyun agentloop listevaluators --agent-space <space>   # Wrong: missing hyphen
```

## 2. Command — verify action exists under the product

#### ✅ CORRECT
```bash
aliyun agentloop create-evaluation-task --agent-space <space> --task-name <name> --task-mode batch --data-type trace --data-filter '{}' --evaluators '[]'
```

#### ❌ INCORRECT
```bash
aliyun agentloop CreateEvaluationTask ...   # Wrong: PascalCase, not plugin mode
aliyun agentloop create-evaluation-task ...  # Correct format (for reference)
```

## 3. Parameters — verify each parameter name exists

#### ✅ CORRECT
```bash
aliyun agentloop get-evaluator --agent-space <space> --name <evaluator-name> --biz-version v1
```

#### ❌ INCORRECT
```bash
aliyun agentloop get-evaluator --agentspace <space> ...      # Wrong: missing hyphen
aliyun agentloop get-evaluator --agent-space <space> --version v1  # Wrong: should be --biz-version
```

## 4. JSON parameters — use compact JSON for complex flags

#### ✅ CORRECT
```bash
aliyun agentloop create-evaluation-task \
  --data-filter '{"maxRecords":100}' \
  --evaluators '[{"evaluatorRef":"Builtin.agent_correctness"}]'
```

#### ❌ INCORRECT
```bash
aliyun agentloop create-evaluation-task \
  --data-filter maxRecords=100 \          # Wrong: must be JSON
  --evaluators Builtin.agent_correctness   # Wrong: must be JSON array
```

# Correct Python Wrapper Patterns

## 1. Spec file loading — must be a JSON object

#### ✅ CORRECT
```python
spec = {
    "agent_space": "my-space",
    "region": "cn-hangzhou",
    "task": {
        "mode": "oneshot",
        "data_filter": {"provided": {"input": "hello"}},
        "evaluator_refs": [{"ref": "Builtin.agent_correctness"}]
    }
}
```

#### ❌ INCORRECT
```python
spec = {
    "agentSpace": "my-space",  # Wrong: use snake_case in spec, wrapper converts
    "task": "oneshot"          # Wrong: task must be an object
}
```

## 2. Evaluator type — must be exactly AGENT, LLM, or CODE

#### ✅ CORRECT
```python
{"action": "create", "name": "my-eval", "type": "AGENT", "metric_name": "quality", "biz_version": "v1"}
{"action": "create", "name": "my-eval", "type": "LLM", "metric_name": "quality", "biz_version": "v1"}
{"action": "create", "name": "my-eval", "type": "CODE", "metric_name": "quality", "biz_version": "v1"}
```

#### ❌ INCORRECT
```python
{"action": "create", "type": "agent", ...}    # Wrong: must be uppercase
{"action": "create", "type": "CUSTOM", ...}   # Wrong: not a supported type
```

## 3. Dataset config — must use exact camelCase keys

#### ✅ CORRECT
```python
{"data_type": "dataset", "config": {"datasetName": "my-dataset"}}
```

#### ❌ INCORRECT
```python
{"data_type": "dataset", "config": {"dataset_name": "my-dataset"}}  # Wrong: snake_case not converted in config
```

## 4. Time window — must include timezone

#### ✅ CORRECT
```python
{"window": {"start": "2026-07-14T09:00:00+08:00", "end": "2026-07-14T10:00:00+08:00"}}
```

#### ❌ INCORRECT
```python
{"window": {"start": "2026-07-14T09:00:00", "end": "2026-07-14T10:00:00"}}  # Wrong: no timezone
```

## 5. Continuous evaluation — requires explicit flag

#### ✅ CORRECT
```bash
python3 scripts/agentloop_eval.py run --spec continuous.json --allow-continuous --execute
```

#### ❌ INCORRECT
```bash
python3 scripts/agentloop_eval.py run --spec continuous.json --execute
# Error: continuous evaluation requires --allow-continuous after explicit cost approval
```
