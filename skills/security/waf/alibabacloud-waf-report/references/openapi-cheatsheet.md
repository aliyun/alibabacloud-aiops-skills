# Aliyun WAF and SLS Plugin-Mode Command Reference

## Command rules

All aliyun CLI calls in this skill use plugin mode:

- Operation names are lowercase and hyphenated.
- Parameter names are lowercase and hyphenated.
- Do not fall back to PascalCase RPC-style operations.
- Use only the default credential chain or an already configured profile.
- Reuse the assessment-wide `SESSION_ID` in `--user-agent` whenever supported.

Common tracing option:

```bash
--user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-report/${SESSION_ID}"
```

## Authentication check

Never request or pass AccessKey credentials. Verify the existing authenticated context:

```bash
aliyun waf-openapi describe-instance \
  --region-id <region-id> \
  --profile <profile> \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-report/${SESSION_ID}"
```

## WAF instance, domains, and templates

```bash
aliyun waf-openapi describe-instance \
  --region-id <region-id> \
  --profile <profile> \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-report/${SESSION_ID}"

aliyun waf-openapi describe-domains \
  --region-id <region-id> \
  --instance-id <instance-id> \
  --profile <profile> \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-report/${SESSION_ID}"

aliyun waf-openapi describe-defense-templates \
  --region-id <region-id> \
  --instance-id <instance-id> \
  --profile <profile> \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-report/${SESSION_ID}"
```

## WAF defense rules

Query every required defense type and follow the response pagination fields until completion.

```bash
for dtype in waf_base custom_acl whitelist antiscan cc threat_intelligence bot_manager bot_custom_acl; do
  aliyun waf-openapi describe-defense-rules \
    --instance-id <instance-id> \
    --region-id <region-id> \
    --defense-type "$dtype" \
    --page-size 50 \
    --profile <profile> \
    --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-report/${SESSION_ID}"
done
```

```bash
aliyun waf-openapi describe-defense-rule \
  --instance-id <instance-id> \
  --region-id <region-id> \
  --rule-id <rule-id> \
  --profile <profile> \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-report/${SESSION_ID}"
```

## WAF API Security

The API Security plugin operations use `--region`. Confirm current flags with plugin help before execution.

```bash
aliyun waf-openapi describe-apisec-events \
  --instance-id <instance-id> \
  --region <region-id> \
  --page-number 1 \
  --profile <profile> \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-report/${SESSION_ID}"

aliyun waf-openapi describe-apisec-abnormals \
  --instance-id <instance-id> \
  --region <region-id> \
  --page-number <page-number> \
  --profile <profile> \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-report/${SESSION_ID}"

aliyun waf-openapi describe-apisec-matched-hosts \
  --instance-id <instance-id> \
  --region <region-id> \
  --profile <profile> \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-report/${SESSION_ID}"

aliyun waf-openapi describe-apisec-rules \
  --instance-id <instance-id> \
  --region <region-id> \
  --profile <profile> \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-report/${SESSION_ID}"

aliyun waf-openapi describe-apisec-abnormal-domain-statistic \
  --instance-id <instance-id> \
  --region <region-id> \
  --profile <profile> \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-report/${SESSION_ID}"

aliyun waf-openapi describe-apisec-event-detail \
  --instance-id <instance-id> \
  --region <region-id> \
  --event-id <event-id> \
  --profile <profile> \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-report/${SESSION_ID}"
```

Do not hard-code a maximum API Security page. Continue until the returned count, total, or next-page fields show completion, and record the page count.

## SLS log queries

```bash
aliyun sls get-logs \
  --project <project> \
  --logstore <logstore> \
  --from <start-unix-seconds> \
  --to <end-unix-seconds> \
  --query "* | select count(1) as cnt" \
  --line 1 \
  --profile <profile> \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-report/${SESSION_ID}"

aliyun sls list-project \
  --profile <profile> \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-report/${SESSION_ID}"

aliyun sls list-log-stores \
  --project <project> \
  --profile <profile> \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-report/${SESSION_ID}"
```

Use Unix timestamps in seconds. Generate exact start and end values outside the command so the evidence record contains stable values rather than moving shell expressions.

## Important SLS fields

- `real_client_ip`: client IP derived by the WAF logging pipeline
- `remote_addr`: direct peer connected to WAF, which may be a proxy
- `host`, `request_path`, `querystring`, `request_method`, `request_body`
- `http_user_agent`, `http_referer`, `http_x_forwarded_for`
- `upstream_status`, `body_bytes_sent`
- `final_action`, `final_plugin`, `final_rule_id`, `final_rule_type`
- `acl_action`, `acl_rule_id`, `acl_rule_type`
- `scene_action`, `scene_rule_id`, `scene_rule_type`, `scene_test`
- `wxbb_info_tbl`, `wxbb_invalid_wua`, `antibot_scene_id`, `antibot_scene_tag`

Confirm which fields are indexed before using them in a query. Treat missing fields as an evidence gap.

## External network ownership lookup

```bash
curl -sS --connect-timeout 5 --max-time 10 \
  -A "AlibabaCloud-Agent-Skills/alibabacloud-waf-report/${SESSION_ID}" \
  "https://ipinfo.io/<ip>/json"
```

Record lookup time and confirm business ownership with the customer. ASN and geography are contextual signals, not attack classification.

## Common errors

1. `describe-instance` does not take an instance ID; it returns the regional instance.
2. `describe-defense-rule` requires a rule ID.
3. All operation and parameter names must remain lowercase and hyphenated.
4. `get-logs` uses SLS search plus SQL syntax; `--line` limits returned rows.
5. Timestamp parameters use Unix seconds.
6. If a plugin operation or flag is unavailable, stop and ask the user to install or update the plugin. Do not fall back to PascalCase RPC-style commands.
