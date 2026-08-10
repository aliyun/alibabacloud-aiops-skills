# PDS Aliyun CLI Configuration Guide (Important)

**Scenario**: Required configuration when using aliyun pds cli for the first time
**Purpose**: Verify existing PDS configuration and initialize it with the authentication method selected by the user

---

**Before executing any PDS operations, first verify whether PDS configuration already exists:**

## Configuration Check

```bash
aliyun pds get-user --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pds-intelligent-workspace
```
If already configured successfully, it will return the current logged-in user information. Reuse that configuration, skip initialization, and continue with the requested PDS operation.

If the initial check returns any other command, network, permission, or authentication error—not a clear indication that PDS configuration is missing or incomplete—report the error, do not begin initialization, and wait for corrected input or user direction.

If the response clearly indicates that PDS configuration is missing or incomplete, ask the user to choose exactly one initialization method before running any branch-specific command:

1. **AK authentication** — use the existing Alibaba Cloud CLI credential to select a domain and a user.
2. **API Key authentication** — use a PDS domain ID and a user API Key supplied by the user.

Follow only the selected branch. Do not silently fall back to the other authentication method.

## AK Authentication

### Query the domain list

Query the domain list using `aliyun pds list-domains` (skip this step if you already have the `domain_id` to configure):

```bash
aliyun pds list-domains --service-code edm --limit 100 --region cn-beijing --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pds-intelligent-workspace
```

The returned JSON structure is as follows. Extract the domain list from the response and display it to the user in a table format with columns `domain_id` and `domain_name`, prompting the user to select one domain. (If there is only one domain, use it directly without asking)
```json
{
	"items": [{
      "domain_id": "bj322",
      "domain_name": "beijing-31216",
      "region_id": "cn-beijing",
      "service_code": "edm"
    }],
	"next_marker": ""
}
```
This step requires obtaining the selected domain_id before proceeding to the next step.

### Query the user list

Query the user list under the domain using `aliyun pds list-user` (skip this step if you already have the `user_id` to configure):

```bash
# First configure domain_id with ak authentication type
aliyun pds config --domain-id <domain_id> --authentication-type ak --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pds-intelligent-workspace
# Then list users under this domain
aliyun pds list-user --limit 100 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pds-intelligent-workspace
```

The returned JSON structure is as follows. Extract the user list from the response and display it to the user in a table format with columns `user_id`, `nick_name`, `phone`, `email`, and `role`, prompting the user to select one user. (If there is only one user, use it directly without asking)
```json
{
	"items": [
		{
			"nick_name": "SuperAdmin",
			"role": "superadmin",
			"status": "enabled",
			"updated_at": 1774159173066,
			"phone": "123",
            "email": "test@example.com",
			"user_id": "a34527bd247e48b6b7e48d5c381b23f3"
		}
	],
	"next_marker": ""
}
```
This step requires obtaining the selected user_id before proceeding to the next step.

### Configure the selected domain and user

Configure `domain_id`, `user_id`, and authentication type for the Aliyun PDS CLI using `aliyun pds config`:

```bash
aliyun pds config \
  --domain-id <domain_id> \
  --user-id <user_id> \
  --authentication-type token \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pds-intelligent-workspace
```

**Parameter Description**:
- `--domain-id`: PDS domain ID (e.g., `bj31216`), provided by PDS user, check if included in the prompt
- `--user-id`: PDS user ID (e.g., `a34527bd247e48b6b7e48d5c381b23f3`), provided by PDS user, check if included in the prompt
- `--authentication-type`: **Must be set to `token` if user_id parameter is provided**, indicating access with user identity

**Effect After Configuration**:
- No need to pass `--domain-id` parameter for subsequent PDS API calls
- CLI will automatically use the configured domain_id and user_id

**Notes**:
- Domain_id and user_id will be preset in CLI configuration
- User's token will be preset in Aliyun CLI configuration file
- After configuring once, no need to repeat configuration for subsequent operations

## API Key Authentication

Ask the user for both values if they were not already provided:

- PDS domain ID (`domainID`)
- User API Key

Do not execute the configuration command until both values are available. Treat the API Key as sensitive: never repeat it in conversational output, status messages, or the final response.

```bash
aliyun pds config \
  --domain-id <domain_id> \
  --authentication-type api_key \
  --api-key <api_key_value> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pds-intelligent-workspace
```

Do not list domains or users, and do not ask for a user ID in this branch.

## Verify Configuration

After completing the selected initialization branch, verify the configuration:

```bash
aliyun pds get-user --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pds-intelligent-workspace
```

Report `domain_id`, `nick_name`, and `user_id` when returned.

If configuration or verification fails, report the error without exposing the API Key and wait for corrected input or user direction.
