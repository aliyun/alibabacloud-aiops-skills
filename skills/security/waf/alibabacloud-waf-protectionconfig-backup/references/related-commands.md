# Related Commands

## WAF 3.0 Commands (API 2021-10-01)

| Command | Required Parameters | Pagination | Description |
|---------|-------------------|------------|-------------|
| `aliyun waf-openapi describe-instance` | `--region`, `--biz-region-id` | No | Query WAF 3.0 instance information |
| `aliyun waf-openapi describe-defense-resources` | `--region`, `--instance-id`, `--biz-region-id` | `--pager` | List all defense resources |
| `aliyun waf-openapi describe-defense-resource-groups` | `--region`, `--instance-id`, `--biz-region-id` | `--pager` | List all defense resource groups |
| `aliyun waf-openapi describe-defense-templates` | `--region`, `--instance-id`, `--biz-region-id`, `--defense-scene` | `--pager` | List defense templates by scene |
| `aliyun waf-openapi describe-defense-rules` | `--region`, `--instance-id`, `--biz-region-id`, `--defense-type`, `--query` (JSON with DefenseScene/TemplateId) | `--pager` | List defense rules for a template |
| `aliyun waf-openapi describe-template-resources` | `--region`, `--instance-id`, `--biz-region-id`, `--template-id`, `--resource-type` | `--pager` | List resources bound to a template |
| `aliyun waf-openapi describe-major-protection-black-ips` | `--region`, `--instance-id`, `--biz-region-id` | `--pager` | List major protection black IPs |
| `aliyun waf-openapi describe-addresses` | `--region`, `--instance-id`, `--biz-region-id` | `--pager` | List address book entries |

## WAF 2.0 Commands (API 2019-09-10)

**CRITICAL:** All WAF 2.0 commands MUST include `--api-version 2019-09-10` and `--region {region}`.

| Command | Required Parameters | Pagination | Description |
|---------|-------------------|------------|-------------|
| `aliyun waf-openapi describe-instance-info --api-version 2019-09-10` | `--region`, `--biz-region-id` | No | Query WAF 2.0 instance information |
| `aliyun waf-openapi describe-domain-names --api-version 2019-09-10` | `--region`, `--instance-id`, `--biz-region-id` | No | List all domains in WAF 2.0 |
| `aliyun waf-openapi describe-protection-module-rules --api-version 2019-09-10` | `--region`, `--instance-id`, `--biz-region-id`, `--domain`, `--defense-type` | `--pager` | List protection rules per domain per type |
| `aliyun waf-openapi describe-protection-module-status --api-version 2019-09-10` | `--region`, `--instance-id`, `--biz-region-id`, `--domain`, `--defense-type` | No | Query protection module on/off status |
| `aliyun waf-openapi describe-protection-module-mode --api-version 2019-09-10` | `--region`, `--instance-id`, `--biz-region-id`, `--domain`, `--defense-type` | No | Query protection module mode |
| `aliyun waf-openapi describe-domain-rule-group --api-version 2019-09-10` | `--region`, `--instance-id`, `--biz-region-id`, `--domain` | No | Query domain rule group ID |

## Common Parameters

| Parameter | Description | Example Values |
|-----------|-------------|---------------|
| `--region` | API endpoint region (MUST match `--biz-region-id`) | `cn-hangzhou` (China), `ap-southeast-1` (International) |
| `--biz-region-id` | WAF business region | `cn-hangzhou` (China), `ap-southeast-1` (International) |
| `--instance-id` | WAF instance ID | `waf-cn-xxx`, `waf_v2_xxx` |
| `--api-version` | API version (WAF 2.0 only) | `2019-09-10` |
| `--defense-scene` | Defense scene name (WAF 3.0) | See [defense-scene-values.md](defense-scene-values.md) |
| `--defense-type` | Defense type name (WAF 2.0) | See [defense-scene-values.md](defense-scene-values.md) |
| `--pager` | Enable automatic pagination | (no value needed) |
| `--user-agent` | Observability tracking | `AlibabaCloud-Agent-Skills/alibabacloud-waf-protectionconfig-backup/{session-id}` |
