# Evaluation Deliverables Contract

Use this document for evaluator-facing tasks. It defines **required artifacts** and
auditable evidence patterns.

## 1) Required Artifact Matrix

| Eval scenario | Required artifact | Required filename |
|---|---|---|
| should-trigger batch | positive trigger jsonc | `outputs/should_trigger.jsonc` |
| should-not-trigger batch | negative trigger jsonc | `outputs/should_not_trigger.jsonc` |
| lifecycle minimal flow | command/output trace + closure summary | `ran_scripts/*.log` + `outputs/lifecycle_flow_summary.md` |

Hard rule: do not replace required `jsonc` artifacts with markdown-only summaries.

## 2) Generate Trigger Artifacts (Recommended)

Use the standard template copier:

```bash
python scripts/prepare_trigger_batch.py --type positive --output outputs/should_trigger.jsonc
python scripts/prepare_trigger_batch.py --type negative --output outputs/should_not_trigger.jsonc
```

If file exists and should be refreshed:

```bash
python scripts/prepare_trigger_batch.py --type positive --output outputs/should_trigger.jsonc --force
```

## 3) Safety Confirmation Evidence Requirements

For lifecycle checks involving `create` or `create_namespace`, evaluator evidence must
match `SafetyCheckRequired|--confirm`.

Use at least one of the following evidence paths:

1. **Negative probe**: run a create command without `--confirm` and capture
   `SafetyCheckRequired`.
2. **Positive execution evidence**: keep successful create JSON output that includes
   `confirmation_check.required_flag = "--confirm"`.

Do not claim confirmation enforcement without one of the above in logs/output.

## 4) Minimal Closure Checklist

Before finishing any evaluator task, verify:

- required output file names exist exactly (`should_trigger.jsonc` / `should_not_trigger.jsonc`)
- trigger files are valid JSONC with `triggering.type` and `triggering.test_cases`
- create steps include confirmation evidence (`SafetyCheckRequired` or `--confirm`)
- final summary references generated artifact paths
