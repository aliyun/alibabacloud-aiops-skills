# Related CLI Commands

All CLI commands used in this skill. Commands use plugin mode format (lowercase + hyphens). Every command includes `--header User-Agent=AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-intercept-query`.

## DDoS Pro (ddoscoo) Commands

| Command | Description | Used In |
|---------|-------------|---------|
| `aliyun ddoscoo describe-instances --page-number 1 --page-size 50 --region <r> --header User-Agent=AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-intercept-query` | Query DDoS Pro instance list | Step 2a |
| `aliyun ddoscoo describe-sls-open-status --region <r> --header User-Agent=AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-intercept-query` | Check SLS open status | Step 2b |
| `aliyun ddoscoo describe-log-store-exist-status --region <r> --header User-Agent=AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-intercept-query` | Check if log store exists | Step 2b |
| `aliyun ddoscoo describe-sls-logstore-info --region <r> --header User-Agent=AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-intercept-query` | Get SLS logstore info (project, logstore, capacity, TTL) | Step 2b |
| `aliyun ddoscoo describe-web-access-log-status --domain <d> --region <r> --header User-Agent=AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-intercept-query` | Check domain full log status | Step 2b / 2c |
| `aliyun ddoscoo describe-web-access-log-dispatch-status --page-number 1 --page-size 10 --region <r> --header User-Agent=AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-intercept-query` | Check all domains full log dispatch status | Step 2c |
| `aliyun ddoscoo enable-web-access-log-config --domain <d> --region <r> --header User-Agent=AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-intercept-query` | Enable full log for a domain (enable only) | Step 2c |
| `aliyun ddoscoo describe-web-cc-protect-switch --domains.1 <d> --region <r> --header User-Agent=AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-intercept-query` | Query all protection switch states | Step 4b |
| `aliyun ddoscoo describe-web-cc-rules-v2 --domain <d> --region <r> --header User-Agent=AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-intercept-query` | Query CC protection rules | Step 4c |
| `aliyun ddoscoo describe-web-precise-access-rule --domains.1 <d> --region <r> --header User-Agent=AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-intercept-query` | Query precise access control rules | Step 4c |
| `aliyun ddoscoo describe-web-area-block-configs --domains.1 <d> --region <r> --header User-Agent=AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-intercept-query` | Query region blocking configs | Step 4c |
| `aliyun ddoscoo describe-l7-global-rule --domain <d> --region <r> --header User-Agent=AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-intercept-query` | Query global defense policy | Step 4c |
| `aliyun ddoscoo describe-web-rules --domain <d> --region <r> --header User-Agent=AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-intercept-query` | Query website forwarding rules (IP blacklist/whitelist) | Step 4c |
| `aliyun ddoscoo disable-web-cc-rule --domain <d> --region <r> --header User-Agent=AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-intercept-query` | Disable CC custom rule | Rule Operations |
| `aliyun ddoscoo enable-web-cc-rule --domain <d> --region <r> --header User-Agent=AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-intercept-query` | Enable CC custom rule | Rule Operations |
| `aliyun ddoscoo modify-web-precise-access-switch --domain <d> --config <json> --region <r> --header User-Agent=AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-intercept-query` | Toggle precise access control switch | Rule Operations |

## SLS Commands

| Command | Description | Used In |
|---------|-------------|---------|
| `aliyun sls get-logs --project <p> --logstore <l> --from <ts> --to <ts> --query <q> --lines 100 --region <r> --header User-Agent=AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-intercept-query` | Query SLS logs by keyword (plugin-mode) | Step 3 |
| `aliyun sls list-project --region <r> --header User-Agent=AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-intercept-query` | List all SLS projects (fallback to discover ddoscoo project) | Step 2b |

## Utility Commands

| Command | Description | Used In |
|---------|-------------|---------|
| `aliyun version` | Check CLI version (>= 3.3.3 required) | Pre-check |
| `aliyun configure list` | Check credential configuration | Authentication |
| `aliyun configure set --auto-plugin-install true` | Enable auto plugin install | Pre-check |
| `aliyun plugin update` | Update CLI plugins | Pre-check |
