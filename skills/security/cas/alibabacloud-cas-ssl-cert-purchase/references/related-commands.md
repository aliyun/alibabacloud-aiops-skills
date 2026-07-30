# Related CLI Commands

Complete CLI command reference for the alibabacloud-cas-ssl-cert-purchase skill.

## CAS (Certificate Authority Service)

| Product | CLI Command | Description |
|---------|------------|-------------|
| CAS | `aliyun cas list-instances` | List certificate instances (supports `--status`, `--keyword`, `--instance-type`, `--brand`, `--certificate-type` filters) |
| CAS | `aliyun cas get-instance-detail` | Get details for a specific certificate instance by `--instance-id` |
| CAS | `aliyun cas update-instance` | Fill in certificate application info (domain, algorithm, validation, CSR, contact, company) |
| CAS | `aliyun cas apply-certificate` | Submit certificate application (async operation) |
| CAS | `aliyun cas get-task-attribute` | Poll async task result by `--task-id` and `--task-type` |
| CAS | `aliyun cas list-contact` | List contacts for certificate application (supports `--keyword` filter) |

## BSS (Business Support System)

BSS commands are executed via the wrapper script `scripts/bss-purchase.sh` because the `bssopenapi` plugin does not support plugin mode format. The script handles BSS API calls internally.

| Script Action | Description |
|--------------|-------------|
| `bash scripts/bss-purchase.sh check-plugin` | Verify BSS plugin availability |
| `bash scripts/bss-purchase.sh create-instance` | Purchase certificate instance (paid, requires confirmation gate) |
| `bash scripts/bss-purchase.sh get-order-detail` | Query order detail after purchase |

## CLI Utility Commands (no `--user-agent` needed)

| Command | Description |
|---------|-------------|
| `aliyun version` | Check CLI version (must be >= 3.3.3) |
| `aliyun upgrade` | Self-update CLI (available >= 3.3.5) |
| `aliyun configure list` | List configured profiles and credentials |
| `aliyun configure set` | Configure CLI profile settings |
| `aliyun plugin update` | Update installed plugins |
| `aliyun plugin install` | Install specific plugins |

## Command Format Notes

- **CAS commands** use plugin mode format: `aliyun cas action-name` (lowercase-hyphenated)
- **BSS commands** are wrapped in `scripts/bss-purchase.sh` — the `bssopenapi` plugin only supports PascalCase API names, so BSS calls go through the script to maintain consistency
- **All CAS API commands** must include `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-cas-ssl-cert-purchase/{session-id}`
- **Utility commands** (`version`, `configure`, `plugin`) do NOT support `--user-agent`
