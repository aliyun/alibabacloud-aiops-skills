# Related CLI Commands

All WAF business commands use the WAF OpenAPI product (`waf-openapi`), API version `2021-10-01`.
Account-identity discovery uses the STS product (`sts`).

## Account Topology (probed once at startup)

| Product | CLI Command | Description |
|---------|-------------|-------------|
| sts | `aliyun sts get-caller-identity` | Resolve the caller's AliUid (used as filename prefix and Summary attribution) |
| waf-openapi | `aliyun waf-openapi describe-account-delegated-status --region <r> --instance-id <id>` | Detect whether the executing account is the WAF delegated administrator |
| waf-openapi | `aliyun waf-openapi describe-member-accounts --region <r>` | Enumerate member accounts (delegated-administrator scenario only) |
| waf-openapi | `aliyun waf-openapi describe-defense-resource-owner-uid --region <r> --instance-id <id> --query-args '{"ResourceNames":["<name1>","<name2>"]}'` | Resolve `ResourceName → OwnerUid` (delegated-administrator scenario only; up to 100 names per call) |

## Instance Discovery

| Product | CLI Command | Description |
|---------|-------------|-------------|
| waf-openapi | `aliyun waf-openapi describe-instance --region cn-hangzhou` | Query WAF instance info (Chinese mainland) |
| waf-openapi | `aliyun waf-openapi describe-instance --region ap-southeast-1` | Query WAF instance info (International) |

## Onboarding Configuration

| Product | CLI Command | Description |
|---------|-------------|-------------|
| waf-openapi | `aliyun waf-openapi describe-domains --region <r> --instance-id <id> --page-size 50` | Paginated CNAME domain list |
| waf-openapi | `aliyun waf-openapi describe-domain-detail --region <r> --instance-id <id> --domain <d>` | Single CNAME domain detail |
| waf-openapi | `aliyun waf-openapi describe-cloud-resources --region <r> --instance-id <id>` | Cloud-product onboarding resources |
| waf-openapi | `aliyun waf-openapi describe-hybrid-cloud-resources --region <r> --instance-id <id>` | Hybrid-cloud onboarding resources |

## Protected Objects & Groups

| Product | CLI Command | Description |
|---------|-------------|-------------|
| waf-openapi | `aliyun waf-openapi describe-defense-resources --region <r> --instance-id <id> --page-size 50` | Full protected-object inventory (no template filter) |
| waf-openapi | `aliyun waf-openapi describe-defense-resource-groups --region <r> --instance-id <id> --page-size 50` | Protected-object groups |

## Defense Templates & Rules

| Product | CLI Command | Description |
|---------|-------------|-------------|
| waf-openapi | `aliyun waf-openapi describe-defense-templates --region <r> --instance-id <id> --defense-scene <scene> --page-size 50` | Defense template list |
| waf-openapi | `aliyun waf-openapi describe-defense-rules --region <r> --instance-id <id> --rule-type <defense\|whitelist> --query-args '{"DefenseScene":"<scene>","TemplateId":<id>}'` | Defense rule list |

## Bindings

| Product | CLI Command | Description |
|---------|-------------|-------------|
| waf-openapi | `aliyun waf-openapi describe-defense-resources --region <r> --instance-id <id> --query-args '{"TemplateId":<id>}'` | Template-to-resource bindings |

## 11 DefenseScene Types

| DefenseScene | Label | RuleType |
|-------------|-------|----------|
| waf_group | Basic Protection | defense |
| custom_acl | Custom Rules | defense |
| cc | CC Protection | defense |
| ip_blacklist | IP Blacklist | defense |
| whitelist | Whitelist | whitelist |
| region_block | Region Block | defense |
| antiscan | Anti-Scan | defense |
| bot_manager | Bot Management | defense |
| dlp | Data Leak Prevention | defense |
| tamperproof | Anti-Tampering | defense |
| custom_response | Custom Response | defense |

> RuleType has only two values: `defense` (10 types) and `whitelist` (1 type).

## Notes

- `--region` is a global flag that routes to the correct endpoint.
- WAF also accepts `--biz-region-id` as a request parameter (`cn-hangzhou` or `ap-southeast-1`).
- Field-name notes (verified from live API): load balancing is `Redirect.Loadbalance` (not `LoadBalanceType`); backend IPs are `Redirect.BackendList` (string array); cert id is `Listen.CertId`.

## Site and Instance Types

| Dimension | Chinese Mainland | Non-Chinese Mainland |
|-----------|------------------|----------------------|
| RegionId | `cn-hangzhou` | `ap-southeast-1` |
| Endpoint | `wafopenapi.cn-hangzhou.aliyuncs.com` | `wafopenapi.ap-southeast-1.aliyuncs.com` |
| InstanceId | Auto-discovered via DescribeInstance | Auto-discovered via DescribeInstance |

> Chinese mainland and International site APIs are identical (version 2021-10-01); only Endpoint and account system differ. AccessKeys are NOT interchangeable.
