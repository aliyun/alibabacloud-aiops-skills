# HTTPDNS OpenAPI Reference

Public product page: https://api.aliyun.com/product/Httpdns

Additional public references used by this Skill:

- API list: https://help.aliyun.com/document_detail/2868021.html
- `ListDomains`: https://www.alibabacloud.com/help/zh/doc-detail/56800.html
- `AddDomain`: https://www.alibabacloud.com/help/zh/doc-detail/30130.html
- `GetResolveStatistics`: https://api.aliyun.com/document/Httpdns/2016-02-01/GetResolveStatistics
- RAM domain authorization: https://help.aliyun.com/document_detail/435245.html

CLI product:

```bash
aliyun httpdns --help
```

Observed locally with `aliyun` 3.3.13:

- Product: `Httpdns`
- Version: `2016-02-01`
- CLI form: `aliyun httpdns <kebab-case-action> --kebab-case-flag value`
- API docs use canonical OpenAPI action names, but CLI commands must use
  plugin-mode kebab-case action names and flags.

## Capability map

| Scenario | OpenAPI | CLI action | Required CLI flags | Optional CLI flags | Notes |
| --- | --- | --- | --- | --- | --- |
| Account/key lookup | `GetAccountInfo` | `get-account-info` | none | none | May return secret-like fields; mask by default. |
| Add domain | `AddDomain` | `add-domain` | `--domain-name` | `--account-id` | Mutating operation; confirm before execution. |
| Delete domain | `DeleteDomain` | `delete-domain` | `--domain-name` | `--account-id` | Mutating operation; confirm before execution. |
| Describe domains | `DescribeDomains` | `describe-domains` | none | `--account-id`, `--page-number`, `--page-size` | Use for account-scoped domain inventory. |
| List domains and counters | `ListDomains` | `list-domains` | none | `--page-number`, `--page-size`, `--search`, `--without-metering-data` | Returns domain list and metering-related fields. |
| Domain usage trend | `GetResolveStatistics` | `get-resolve-statistics` | `--domain-name`, `--granularity`, `--time-span` | `--protocol-name` | Use for one domain over a recent time span. |
| Account resolve summary | `GetResolveCountSummary` | `get-resolve-count-summary` | `--granularity`, `--time-span` | none | Use for account-level usage totals. |
| Refresh cache | `RefreshResolveCache` | `refresh-resolve-cache` | none | `--domains` list values | Mutating/operational action; confirm domain list. |

## Parameter notes

- `--domain-name`: single HTTPDNS domain, for example `www.example.com`.
- `--domains`: one or more list values for `refresh-resolve-cache`, for example `--domains www.example.com` or `--domains www.example.com api.example.com`. Do not pass a JSON array string; the plugin help documents this parameter as `format: --domains value1 value2 value3`.
- `--granularity`: pass the value requested by the user; common values are `day` or `hour`, but verify with `--help` or OpenAPI docs when uncertain.
- `--time-span`: integer time span required by statistics APIs.
- `--protocol-name`: optional protocol filter accepted by `get-resolve-statistics`.
- `--page-number`: starts from `1`.
- `--page-size`: keep small by default; only increase when the user asks for broad inventory.

## Sensitive data handling

`get-account-info` is part of the requested key-retrieval scenario. Treat all
secret-like fields as sensitive:

1. Call the API directly when the user asks for account/key information.
2. Return masked values by default; do not ask a follow-up confirmation just to show masked output.
3. Do not print AK/SK files or `~/.aliyun/config.json`.
4. Mask values named like `Secret`, `Key`, `Token`, or `Password` in command output and summaries.
5. Include `RequestId` for traceability.
6. Show unmasked values only when the user explicitly asks for raw/full secret output.
