# Related Commands

## Pre-checks

```bash
aliyun version
aliyun configure list
aliyun httpdns --help
```

## AI mode

```bash
aliyun configure ai-mode enable
aliyun configure ai-mode set-user-agent --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-httpdns"
aliyun configure ai-mode disable
```

## Account/key lookup

```bash
scripts/httpdns-openapi.sh account-info
```

With a named profile:

```bash
scripts/httpdns-openapi.sh account-info --profile production
```

The helper masks secret-like fields by default. Do not run raw
`aliyun httpdns get-account-info` for diagnostics because it can print
`SignSecret` and other secret-like fields.

Do not ask a follow-up confirmation before returning masked account info. Only
use raw output when the user explicitly asks for unmasked/raw/full secret
values:

```bash
scripts/httpdns-openapi.sh account-info --raw
```

## Domain settings

Add a domain:

```bash
scripts/httpdns-openapi.sh add-domain --domain www.example.com --yes
aliyun httpdns list-domains --search www.example.com --page-number 1 --page-size 100
```

For add-and-confirm requests, always verify with `list-domains` after
`add-domain`. If `add-domain` fails, still run `list-domains` when possible to
check whether the domain already exists.

Idempotent replacement for placeholder/evaluation domains only:

```bash
scripts/httpdns-openapi.sh add-domain --domain www.example.com --yes
aliyun httpdns list-domains --search www.example.com --page-number 1 --page-size 100
scripts/httpdns-openapi.sh delete-domain --domain www.example.com --yes
scripts/httpdns-openapi.sh add-domain --domain www.example.com --yes
aliyun httpdns list-domains --search www.example.com --page-number 1 --page-size 100
```

Use this replacement flow only when `add-domain` returns `DomainAlreadyExists`
for `www.example.com` or another `example.com` placeholder domain, or when a
real user explicitly approves replacement.

Delete a domain:

```bash
scripts/httpdns-openapi.sh delete-domain --domain www.example.com --yes
```

Describe account domains:

```bash
aliyun httpdns describe-domains --page-number 1 --page-size 20
```

List domains and metering counters:

```bash
aliyun httpdns list-domains --page-number 1 --page-size 20
```

Search domains:

```bash
aliyun httpdns list-domains --search example --page-number 1 --page-size 20
```

Refresh cache:

```bash
scripts/httpdns-openapi.sh refresh-cache --domains www.example.com --yes
```

## Usage pull

Domain statistics:

```bash
aliyun httpdns get-resolve-statistics --domain-name www.example.com --granularity day --time-span 7
```

Domain statistics with protocol filter:

```bash
aliyun httpdns get-resolve-statistics --domain-name www.example.com --granularity day --time-span 7 --protocol-name https
```

Account count summary:

```bash
aliyun httpdns get-resolve-count-summary --granularity day --time-span 7
```

## Helper script

```bash
scripts/httpdns-openapi.sh account-info
scripts/httpdns-openapi.sh add-domain --domain www.example.com --yes
scripts/httpdns-openapi.sh delete-domain --domain www.example.com --yes
scripts/httpdns-openapi.sh describe-domains --page-number 1 --page-size 20
scripts/httpdns-openapi.sh list-domains --search example --page-number 1 --page-size 20
scripts/httpdns-openapi.sh resolve-statistics --domain www.example.com --granularity day --time-span 7
scripts/httpdns-openapi.sh resolve-count-summary --granularity day --time-span 7
scripts/httpdns-openapi.sh refresh-cache --domains www.example.com --yes
```
