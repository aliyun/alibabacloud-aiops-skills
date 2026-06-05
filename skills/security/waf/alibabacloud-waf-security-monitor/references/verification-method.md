# Verification Method

## Evaluation Layers

| Layer | What it checks | PASS condition | FAIL condition |
|-------|---------------|----------------|----------------|
| 1 - Execution | API command appears in log | `grep -c '<api-name>' log >= expected` | Command absent from log |
| 2 - Parameters | Required params present | `--start-timestamp`, `--instance-id` etc. in command | `is required` error in response |
| 3 - Result Handling | Response correctly processed | empty-->"0 (API returned empty)", error-->"[QUERY FAILED]" | "0" written when error occurred |

> **Critical**: Layer 3 does NOT require non-empty data. An API returning `[]` with HTTP 200 is a PASS at all layers.

## Phase 1: Connectivity

| Check | Method | Expected |
|-------|--------|----------|
| Heartbeat | First CLI command executed -- both regions tried | Non-empty response for at least one region |
| Region param | Verify `--region` appears in commands | Literal `--region cn-hangzhou` and `--region ap-southeast-1` (NOT `--region-id`, NOT `--biz-region-id`) |
| Log file | `ls /tmp/waf_skill_output.log` | Exists, non-zero |

## Phase 2: Asset Completeness

| Check | Method | Expected |
|-------|--------|----------|
| Both regions | Count region queries in log | 2 (cn-hangzhou + ap-southeast-1) |
| Region isolation | `REGION_INSTANCES` mapping | Different IDs per region (or empty for one region) |
| describe-domains | `grep -c 'describe-domains' /tmp/waf_skill_output.log` | >= 1 per instance |
| describe-certs | `grep -c 'describe-certs' /tmp/waf_skill_output.log` | >= 1 per instance |
| page-size | Check command params | Uses --page-size 10, NOT 100 |

## Phase 3: Timestamp Validation

| Check | Method | Expected |
|-------|--------|----------|
| Timestamp init | `grep 'TIMESTAMP CHECK' /tmp/waf_skill_output.log` | Contains `BASE_START=` with 10-digit number |
| Before Phase 4 | Timestamp check appears BEFORE first Phase 4 API call | Correct ordering in log |

## Phase 4: API Call Verification

| Check | Method | PASS | Acceptable (not FAIL) |
|-------|--------|------|----------------------|
| describe-defense-rule-statistics | `grep -c 'defense-rule-statistics' log` | >= 3 calls (bot_manager only) | API error due to fallback template-id=0 is OK |
| describe-response-code-trend-graph | `grep -c 'response-code-trend' log` | >= 4 (2 types x 2 periods) | Empty response is OK (no traffic) |
| describe-flow-chart | `grep -c 'flow-chart' log` | >= 2 (base + compare) | Empty FlowChart=[] is OK |
| Template scene | Bot calls use bot_manager ID only | No DefenseSceneNotSupported | "template not found" from fallback ID=0 is acceptable |
| Error interception | `grep -c 'API ERROR' log` after failures | Errors logged, execution continues | -- |

## Timestamp Parameter Verification

| Check | Method | Expected |
|-------|--------|----------|
| describe-flow-chart params | Inspect command in log | Contains `--start-timestamp <10-digit>` |
| describe-peak-trend params | Inspect command in log | Contains `--start-timestamp <10-digit>` |
| describe-response-code-trend-graph params | Inspect command in log | Contains `--start-timestamp <10-digit>` |
| No "is required" errors | `grep -c 'is required' log` | 0 for time-based APIs |

## Business Metric Verification

| Check | Method | Expected |
|-------|--------|----------|
| Event totals | `grep -o '"Count":[0-9]*' log \| awk sum` | Matches report (or "0 (API returned empty)") |
| Certificate days | `date +%s` math / 86400 | Exact days, not estimate |
| Percentages | `awk` formula | Within 0.1% of report |
| Error vs empty | API 400 --> [QUERY FAILED], NOT "0" | Correct annotation |
| Data source citation | Each number in report cites API name | Present for all data points |

## Conclusion Generation Verification

| Check | Method | Expected |
|-------|--------|----------|
| FAILED_COUNT | `grep -c 'QUERY FAILED' log` | Computed before conclusion |
| >50% failed | Conclusion text | MUST contain "partial data retrieval failure" caveat |
| 100% failed | Conclusion text | MUST be "unable to perform security assessment" |
| Positive assertion | Conclusion text when QUERY FAILED exists | FORBIDDEN: "status normal", "no risk" |
| Cross-API mixing | Data attribution | Each point traces to one specific API |

## Anti-Fabrication Rules

- ALL verification numbers MUST come from `grep`/`jq`/`awk` on `/tmp/waf_skill_output.log`
- Hardcoded `echo "81"` without pipe from file = FABRICATION = ABORT
- If verification != report draft --> ABORT, re-parse, correct
- Template-id must be from bot_manager scene ONLY (waf_group/waf_base are NOT supported)

## Success Criteria

1. Heartbeat executed (non-zero calls)
2. Both regions queried, REGION_INSTANCES mapping correct
3. describe-domains called per instance (data retrieved or error logged) with --page-size 10
4. Timestamps validated (log contains [TIMESTAMP CHECK] with 10-digit values)
5. describe-defense-rule-statistics called >= 3 times with bot_manager template-id (server errors from fallback ID=0 are acceptable, NOT failures)
6. describe-response-code-trend-graph called >= 2 times (waf + upstream) with --start-timestamp present
7. describe-flow-chart called with --start-timestamp present (empty response is NOT a failure)
8. No cross-region instance-id reuse
9. Report numbers match verification script output
10. API errors reported as [QUERY FAILED], empty responses reported as "0 (API returned empty)"
11. Conclusion respects red-line: no positive assertion when QUERY FAILED exists
12. AI-Mode disabled at exit
13. Error interception active: [API ERROR] logged for each failed call, execution not interrupted
