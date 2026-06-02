# Related CLI Commands

## WAF OpenAPI Commands

| Product | CLI Command | Description | Parameters |
|---------|-------------|-------------|------------|
| waf-openapi | `aliyun waf-openapi describe-instance` | Query WAF instance info | `--region`, `--profile` |
| waf-openapi | `aliyun waf-openapi describe-domains` | Paginated domain list query | `--region`, `--instance-id`, `--page-number`, `--page-size` |
| waf-openapi | `aliyun waf-openapi describe-domain-detail` | Query single domain detailed config | `--region`, `--instance-id`, `--domain` |

## Command Examples

### 1. Discover WAF Instance

```bash
# Chinese mainland instance
aliyun waf-openapi describe-instance --region cn-hangzhou

# Non-Chinese mainland instance
aliyun waf-openapi describe-instance --region ap-southeast-1
```

### 2. Query Domain List (Paginated)

```bash
aliyun waf-openapi describe-domains \
  --region cn-hangzhou \
  --instance-id <InstanceId> \
  --page-number 1 \
  --page-size 50
```

### 3. Query Domain Detail

```bash
aliyun waf-openapi describe-domain-detail \
  --region cn-hangzhou \
  --instance-id <InstanceId> \
  --domain <DomainName>
```

## Notes

- `--region` is a global flag that routes to the correct endpoint
- WAF also accepts `--biz-region-id` as a request parameter (values: `cn-hangzhou` or `ap-southeast-1`)
- International site users add `--profile intl` to commands
- PageSize maximum is 50
