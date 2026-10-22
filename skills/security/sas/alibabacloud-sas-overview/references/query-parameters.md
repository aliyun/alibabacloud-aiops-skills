# Query parameters and dependencies

Before API examples, initialize and reuse the manifest-derived `USER_AGENT` as
described in [SKILL.md](../SKILL.md#observability).

Use already-confirmed values; clarify only missing inputs for the selected scope.
Parameter validation checks format and dependencies, not user approval or entitlement.
Run helpers from the Skill directory; they make no cloud calls.

| Query | Required by API / workflow | Source and dependency |
|---|---|---|
| Score / governance / response | --cal-type home_security_score for the overview contract | Fixed selector; validate only the requested result fields |
| Regional SAS queries | --region | Confirmed SAS service region, not arbitrary ECS asset region |
| Full host inventory | --current-page, --page-size 20, --machine-types ecs | Page-number loop; do not enable NextToken mode because TotalCount is needed |
| WAF discovery | --region | Confirmed WAF service region; plugin default API must be 2021-10-01 |
| WAF flow chart | --instance-id, --start-timestamp, --interval | InstanceId from successful same-account, same-region discovery; seconds; interval must be a multiple of 60 (example 3600) |
| SAS trend | --chart-id, --report-id, --time-start, --time-end | Existing overview chart CID_ASSET_RISK_TREND / report -1; milliseconds; start before end. Conditional chart-id requirement is documented for report v2 |
| Bills | --billing-cycle, --product-code sas, --region | Confirmed YYYY-MM and endpoint/account site; account-level billing is not an asset-region partition |
| All cloud queries | --user-agent | Same runtime session UA including skill-version from manifest.json; no unresolved placeholders |

## WAF chain

1. Confirm account and WAF service region. Run DescribeInstance for that region.
2. Save the complete successful discovery response; retain its region/account context.
3. Validate its InstanceId before using it. For a selected region in `WAF_REGION`:

```bash
WAF_INSTANCE_ID=$(python3 scripts/query_parameters.py waf-instance --region "$WAF_REGION" --discovery-region "$DISCOVERY_REGION" < waf-instance.json) || exit 2
START_SEC=$(python3 scripts/query_parameters.py window --days "$TIME_RANGE_DAYS" --unit seconds) || exit 2
aliyun waf-openapi describe-flow-chart --region "$WAF_REGION" --instance-id "$WAF_INSTANCE_ID" --start-timestamp "$START_SEC" --interval 3600 --user-agent "$USER_AGENT"
```

`DISCOVERY_REGION` records where the response was fetched; never relabel a response
from another region. Repeat discovery per selected region. An absent/invalid ID
blocks flow-chart calls; confirmed absence and failed discovery are different states.

## Time and billing

Assign `TIME_RANGE_DAYS` from the confirmed request. The helper returns validated
start timestamps in the requested unit; use a common end time when comparing
regions. Do not silently replace an explicit month with the current month.

```bash
BILLING_CYCLE=$(python3 scripts/query_parameters.py billing --cycle "$BILLING_CYCLE") || exit 2
START_MS=$(python3 scripts/query_parameters.py window --days "$TIME_RANGE_DAYS" --unit ms) || exit 2
```

QueryBill supports page-num/page-size (default 20; maximum 300). Complete bill
reports require all pages and matching currency/account/month, with duplicate bill
identities removed before aggregation. Different endpoint regions do not prove
independent bills. If coverage cannot be established, report partial details without
a combined spend total. CLI help checks cannot validate account-specific endpoints.
