# Evaluation result analysis

Use this read-only workflow to measure evaluation quality and explain low-score cases after an evaluation run.

## Data source

- Resolve the SLS project from `get-agent-space` field `slsProject`, or accept an explicit `--project`.
- Query only the fixed `evaluation_detail` Logstore with `sls get-logs-v2`.
- Require a bounded `[from, to)` time window. Both endpoints become epoch seconds.
- Use the active Aliyun CLI profile. Never collect or store AccessKeys in an analysis file.

| Field | Analysis use |
|---|---|
| `task_id`, `run_id` | Scope the evaluation run |
| `evaluator_name`, `evaluator_display_name` | Compare evaluator performance |
| `status` | Separate success, unknown, and failed records |
| `score_value`, `score_range`, `normalized_score_value` | Rank and normalize results |
| `explanation`, `evaluation_process` | Identify the evaluator's stated failure reason; raw process is omitted by default |
| `eval_info` | Recover input, output, and expected output only with authorized `--include-content` |
| `data_link` | Link the case to its trace or dataset record |
| `eval_metrics`, `custom_outputs` | Inspect evaluator-specific evidence |
| `eval_latency` | Check latency outliers and possible timeouts |

## Score bands

Use the same normalized score bands as Evaluation Explorer:

| Band | Normalized score |
|---|---|
| Very poor | `< 0.3` |
| Poor | `>= 0.3` and `< 0.5` |
| Medium | `>= 0.5` and `< 0.7` |
| Good | `>= 0.7` and `< 0.9` |
| Excellent | `>= 0.9` |

The default low-score condition is `< 0.5`. Analyze `status=success` records by default because they contain completed evaluator judgments. Add `--include-unknown` only when unknown records carry useful scores.

## Run workflow

1. Preview with `analyze_evaluation_results.py --preview` and inspect all three queries.
2. Confirm `aliyun-cli-sls` is installed. If not, request approval before installation.
3. Run with the narrowest available `--task-id`, `--run-id`, or `--evaluator-name` filters.
4. Keep `--max-cases` at 50 unless more evidence is needed; the hard limit is 200.
5. Save structured JSON with `--output` when another report or automation will consume it.
6. Keep raw content omitted by default. Add `--include-content` only when exact input, output, evaluation process, or custom output values are necessary and explicitly authorized.

## Interpret the evidence

1. Check sample size, success rate, average score, low-score rate, and latency before drawing conclusions.
2. Rank evaluators by low-score count and rate. Do not combine metrics with different meanings into one quality claim.
3. Read the lowest-score cases first. Start with scores, explanation, latency, metrics, and available field names. When exact content is authorized, rerun with `--include-content` and compare input, actual output, and expected output.
4. Cluster repeated failures such as missing facts, instruction violations, tool errors, malformed output, or evaluator ambiguity.
5. Cite task ID, run ID, evaluator, eval ID, score, and timestamp for each representative case.
6. Separate observed evidence from hypotheses. Recommend changes only after a repeated pattern is visible.
7. Redact or summarize customer content unless exact text is necessary and authorized.
