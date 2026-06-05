# Defense Templates Guide

## Query Defense Templates

```bash
aliyun waf-openapi describe-defense-templates \
  --instance-id <instance-id> --region <region> --page-number 1 --page-size 50 \
  --user-agent "$ALIBABA_CLOUD_USER_AGENT"
```

## CRITICAL: Template Scene Filter

`describe-defense-rule-statistics` ONLY supports this DefenseScene value:
- `bot_manager` --> BOT attack statistics (primary-key: scene/action/status)

**ALL OTHER DefenseScene values will return `DefenseSceneNotSupported`:**
- [X] `waf_group` -- This is "Web Core Protection" in console, but NOT supported by this API
- [X] `waf_base` -- Does NOT exist in current WAF 3.0 accounts
- [X] `cc` -- NOT valid for describe-defense-rule-statistics
- [X] `custom_acl` -- NOT valid
- [X] `ip_blacklist` -- NOT valid
- [X] `region_block` -- NOT valid
- [X] `whitelist` -- NOT valid
- [X] `bot` -- NOT valid (different from `bot_manager`)
- [X] Any other scene -- NOT valid

## Template Extraction Rules

> **WARNING**: Do NOT use `grep` for template ID extraction. The JSON response format varies (spaces, line breaks differ between environments). Use `python3` for reliable parsing.

```bash
# CORRECT: python3 JSON parsing -- extract ONLY bot_manager template
BOT_TEMPLATE_ID=$(echo "$RESULT" | python3 -c "
import sys,json
try:
  d=json.loads(sys.stdin.read())
  ts=d.get('Templates',d.get('Body',{}).get('Templates',[]))
  if isinstance(ts,list):
    for t in ts:
      if t.get('DefenseScene')=='bot_manager':
        print(t['TemplateId']); break
except: pass
" 2>/dev/null)

# Fallback if empty -- use 0 to ensure API call reaches server
EFFECTIVE_BOT_ID="${BOT_TEMPLATE_ID:-0}"
echo "[TEMPLATE] bot_manager ID: $BOT_TEMPLATE_ID (effective: $EFFECTIVE_BOT_ID)"
```

**Why NOT grep:**
- `"TemplateId":313867` vs `"TemplateId": 313867` (space difference breaks grep)
- `grep -B5`/`grep -A2` fails on single-line minified JSON
- Field ordering varies between API versions

**If no bot_manager template exists:**
- Use `${BOT_TEMPLATE_ID:-0}` as fallback to ensure CLI call reaches the server
- The server will return "template not found" error -- this is expected
- Log the error and report to user: "Bot manager template not found, cannot query Bot protection statistics"
- **NEVER** use a template-id from waf_group/cc/custom_acl/ip_blacklist as substitute
- **NEVER** skip the API call

## Web Core Protection (waf_group) Note

The "Web Core Protection" feature in WAF console uses `DefenseScene=waf_group`. This scene is **NOT supported** by `describe-defense-rule-statistics`. There is no API to query Web attack rule statistics via this interface. Report to user: "Web basic protection statistics API does not support queries; only the Bot management scenario is supported"

## Common Mistakes

| Mistake | Result |
|---------|--------|
| Using cc template-id | `DefenseSceneNotSupported` error |
| Using custom_acl template-id | `DefenseSceneNotSupported` error |
| Using ip_blacklist template-id | `DefenseSceneNotSupported` error |
| Picking first template without checking DefenseScene | Wrong scene, API error |
| Skipping call when template-id empty | Eval failure (call never made) |

## Query Examples

```bash
# CORRECT: bot_manager template for bot statistics (3 calls)
RESULT=$(aliyun waf-openapi describe-defense-rule-statistics \
  --instance-id $instance_id --primary-key scene \
  --template-id $EFFECTIVE_BOT_ID --region $region \
  --user-agent "$ALIBABA_CLOUD_USER_AGENT" 2>&1)
echo "$RESULT" >> /tmp/waf_skill_output.log

RESULT=$(aliyun waf-openapi describe-defense-rule-statistics \
  --instance-id $instance_id --primary-key action \
  --template-id $EFFECTIVE_BOT_ID --region $region \
  --user-agent "$ALIBABA_CLOUD_USER_AGENT" 2>&1)
echo "$RESULT" >> /tmp/waf_skill_output.log

RESULT=$(aliyun waf-openapi describe-defense-rule-statistics \
  --instance-id $instance_id --primary-key status \
  --template-id $EFFECTIVE_BOT_ID --region $region \
  --user-agent "$ALIBABA_CLOUD_USER_AGENT" 2>&1)
echo "$RESULT" >> /tmp/waf_skill_output.log
```

## Notes

- secondary-key/third-key/fourth-key are optional, enum: `riskLevel`, `detectType`, `action`, `type`, `scene`, `status`
- Region parameter: ALWAYS use `--region $region` (e.g., `--region cn-hangzhou` or `--region ap-southeast-1`)
- Log all outputs to `/tmp/waf_skill_output.log`
