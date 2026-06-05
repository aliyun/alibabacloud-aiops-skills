# Acceptance Criteria: alibabacloud-waf-security-monitor

## Evaluation Philosophy

Assertions are split into 3 layers:
- **Layer 1 (Execution Evidence)**: API command appears in log -- PASS. Not present -- FAIL.
- **Layer 2 (Parameter Correctness)**: Required params (--start-timestamp, --instance-id, etc.) are present and non-empty.
- **Layer 3 (Result Handling)**: Response correctly classified as data/empty/error and report reflects that.

> **Key Principle**: "API was called with correct params" != "API returned non-empty data". An API returning empty `[]` (HTTP 200) or failing due to missing template is NOT a test failure -- it is expected product behavior when the WAF instance has no traffic or no waf_base template configured.

---

## 1. Command Format (kebab-case, plugin mode)

CORRECT: `aliyun waf-openapi describe-instance --region cn-hangzhou --user-agent "$ALIBABA_CLOUD_USER_AGENT"`
INCORRECT: `aliyun waf-openapi DescribeInstance --RegionId cn-hangzhou` (PascalCase, missing --user-agent)

## 2. Region Parameter

CORRECT: Use `--region` (CLI global flag) for all commands. Same flag for both cn-hangzhou and ap-southeast-1.
INCORRECT: Using `--region-id` (unknown flag error). Using `--biz-region-id` (doesn't route to ap-southeast-1). Storing param in a variable.

## 3. Business Region Coverage (2 regions only)

CORRECT: `for region in cn-hangzhou ap-southeast-1; do ... done` with `--region $region` in every command
INCORRECT: Traversing 12 regions (WAF 3.0 only supports 2). Only querying one region. Missing `--region` flag.

## 4. Region-Instance Isolation

CORRECT: `declare -A REGION_INSTANCES` --> call `describe-instance --region $region` per region --> each region gets its own InstanceId
INCORRECT: Reusing cn-hangzhou instance-id for ap-southeast-1 queries. Not using `--region ap-southeast-1`. Single `$INSTANCE_ID` across regions.

## 5. describe-domains (MUST execute per instance)

CORRECT: Called for every discovered instance with correct region and instance-id. Uses `--page-size 10`.
INCORRECT: Skipping after getting instance list. Missing any instance. Using --page-size 100 (InvalidPageSize).

## 6. Defense Template Selection (CRITICAL)

CORRECT: Filter for EXACTLY `DefenseScene=bot_manager` from describe-defense-templates using python3 JSON parsing
CORRECT: Use `${BOT_TEMPLATE_ID:-0}` fallback when template not found (ensures call reaches server)
INCORRECT: Using template-id from `waf_group` scene (this is "Web Core Protection" but NOT supported by the API)
INCORRECT: Using template-id from `cc` / `custom_acl` / `ip_blacklist` scenes
INCORRECT: Picking first template without checking DefenseScene field
INCORRECT: Using grep to extract template-id (breaks on different JSON formatting)

## 7. describe-defense-rule-statistics (UNCONDITIONAL, bot_manager ONLY)

CORRECT: Called 3 times (scene/action/status with bot_manager template-id). Uses ONLY bot_manager template-id.
CORRECT: If template not found: uses fallback ID=0, call reaches server, error logged and reported to user.
INCORRECT: Skipping because template-id empty. Using `if [ -n ]` to conditionally skip.
INCORRECT: Using waf_group/cc/custom_acl template-ids (returns DefenseSceneNotSupported).
INCORRECT: Calling with `--template-id ""` (empty string causes CLI local parse failure, call never reaches server).
INCORRECT: Attempting to query web attack stats via waf_group template (not supported by this API).

**Note**: `waf_group` (Web Core Protection) does NOT support this API. Only `bot_manager` works.

## 8. describe-response-code-trend-graph (UNCONDITIONAL)

CORRECT: Called 2 times: `--type waf` AND `--type upstream`. Both calls include `--start-timestamp` and `--end-timestamp`.
INCORRECT: Only calling one type. Skipping because 4.2/4.3 had errors. Missing --start-timestamp parameter.

## 9. Timestamp Parameter Correctness

CORRECT: Log contains `[TIMESTAMP CHECK] BASE_START=` with a 10-digit Unix timestamp before any Phase 4 time-based API call.
CORRECT: All time-based APIs (describe-flow-chart, describe-peak-trend, describe-response-code-trend-graph) include `--start-timestamp` and `--end-timestamp` with valid values.
INCORRECT: Calling time-based APIs without timestamps --> `--start-timestamp is required` error.
INCORRECT: Skipping Phase 3 timestamp initialization.

## 10. Error vs Empty in Report

CORRECT: API 200 + empty `[]` --> `0 (API returned empty)` | API 400 --> `[QUERY FAILED (ErrorCode: XXX)]`
INCORRECT: Writing `0` when API returned error. Writing "normal" when API failed.

**Distinction**: Empty data (no traffic) is NOT a failure. It should be reported as `0 (API returned empty)`, not `[QUERY FAILED]`.

## 11. Verification (file-based, anti-fabrication)

CORRECT: `WAF_CALLS=$(grep -c 'waf-openapi' /tmp/waf_skill_output.log)` -- parsed from log
INCORRECT: `echo "81"` -- hardcoded number. Mental math for certificate days. Manual event sums.

## 12. AI-Mode Lifecycle

CORRECT: Enable at start. Disable at EVERY exit (success, failure, timeout). Verify after disable.
INCORRECT: Only disabling on success path. Not verifying.

## 13. Forced Heartbeat

CORRECT: First CLI command is `aliyun waf-openapi describe-instance --user-agent "$ALIBABA_CLOUD_USER_AGENT"`. No planning before it.
INCORRECT: Performing analysis before any CLI call. Exiting with zero tool calls.

## 14. Conclusion Generation (Red-Line)

CORRECT: When `FAILED_COUNT > 50%` of core items: conclusion states data retrieval was partial, cannot provide full assessment.
CORRECT: When ALL core items failed: conclusion is "unable to perform security assessment".
CORRECT: Every data point cites its source API name.
INCORRECT: Writing "status normal" / "no risk" when ANY `[QUERY FAILED]` exists.
INCORRECT: Cross-API data substitution (using cert data to fill domain fields).
INCORRECT: Generating positive conclusion when majority of APIs failed.

## 15. Unified Error Interception

CORRECT: After every Phase 4 API call, checks for `HttpCode:400` or `ErrorCode`, logs `[API ERROR]`, and continues.
INCORRECT: Silently breaking the loop on first error. Skipping subsequent steps after one failure.
INCORRECT: Retrying parameter/template errors (these won't self-heal).
