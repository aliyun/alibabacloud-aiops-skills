# Verification Method — AgentLoop Evaluation

## 1. Verify CLI and plugin installation

```bash
python3 "$SKILL_DIR/scripts/agentloop_eval.py" doctor --agent-space <space>
```

**Expected**: Doctor checks pass, showing CLI version, plugin status, and AgentSpace access.

## 2. Verify evaluator discovery

```bash
python3 "$SKILL_DIR/scripts/agentloop_eval.py" discover --agent-space <space> --all-pages
```

**Expected**: JSON output listing saved evaluators, built-in evaluators, and evaluation tasks.

## 3. Verify one-shot evaluation preview

```bash
python3 "$SKILL_DIR/scripts/agentloop_eval.py" run --spec "$SKILL_DIR/references/examples/oneshot-example.json"
```

**Expected**: Dry-run preview renders the CLI commands without sending mutations. Output includes `+ aliyun agentloop create-evaluation-task ... --cli-dry-run`.

## 4. Verify one-shot evaluation execution

```bash
python3 "$SKILL_DIR/scripts/agentloop_eval.py" run \
  --spec "$SKILL_DIR/references/examples/oneshot-example.json" --execute --output /tmp/eval-result.json
```

**Expected**:
- `Created evaluation task: eval-temp-*` message
- `Evaluation status:` transitions to a terminal state (e.g., `Completed`)
- `Evaluation finished: taskId=..., runId=..., status=...` message
- `/tmp/eval-result.json` contains the full task and run responses

## 5. Verify result analysis preview

```bash
python3 "$SKILL_DIR/scripts/analyze_evaluation_results.py" \
  --agent-space <space> --region <region> \
  --from "2026-07-14T00:00:00+08:00" --to "2026-07-15T00:00:00+08:00" \
  --task-id <task-id> --preview
```

**Expected**: JSON preview showing the three SLS queries (overview, evaluatorBreakdown, lowScoreCases) without executing them.

## 6. Verify result analysis execution

```bash
python3 "$SKILL_DIR/scripts/analyze_evaluation_results.py" \
  --agent-space <space> --region <region> \
  --from "2026-07-14T00:00:00+08:00" --to "2026-07-15T00:00:00+08:00" \
  --task-id <task-id> --threshold 0.5 --max-cases 50 \
  --output /tmp/eval-analysis.json
```

**Expected**:
- JSON output with `overview`, `evaluatorBreakdown`, and `lowScoreCases` sections
- `overview.totalCount` > 0
- `/tmp/eval-analysis.json` contains the structured analysis

## 7. Verify task status polling

```bash
python3 "$SKILL_DIR/scripts/agentloop_eval.py" status \
  --agent-space <space> --task-id <task-id>
```

**Expected**: JSON output with `taskId`, `runId`, `status`, and nested `task`/`runs`/`run` responses.

## 8. Verify unit tests

```bash
cd "$SKILL_DIR" && python3 -m unittest tests.test_workflows -v
```

**Expected**: All 10 tests pass with `OK` status.
