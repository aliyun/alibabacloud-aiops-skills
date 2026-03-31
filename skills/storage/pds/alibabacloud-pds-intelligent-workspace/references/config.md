# PDS Aliyun CLI Configuration Guide (Important)

**Scenario**: Required configuration when using aliyun pds cli for the first time
**Purpose**: Configure domain_id, user_id, and authentication type for aliyun pds cli

---

**Before executing any PDS operations, you must first configure domain_id, user_id, and authentication type:**

## Step 1: Verify if configuration already exists (only needs to be configured once during initialization)
```bash
aliyun pds get-user --user-agent AlibabaCloud-Agent-Skills
```
If already configured successfully, it will return the current logged-in user information, and you can skip the subsequent steps.

## Step 2: Query domain list using aliyun pds list-domains (skip this step if you already have the domain_id to configure)
```bash
aliyun pds list-domains --service-code edm --limit 100 --region cn-beijing --user-agent AlibabaCloud-Agent-Skills
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

## Step 3: Query user list under the domain using aliyun pds list-user (skip this step if you already have the user_id to configure)
```bash
# First configure domain_id with ak authentication type
aliyun pds config --domain-id <domain_id> --authentication-type ak --user-agent AlibabaCloud-Agent-Skills
# Then list users under this domain
aliyun pds list-user --limit 100 --user-agent AlibabaCloud-Agent-Skills
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

## Step 4: Configure domain_id, user_id, and authentication type to aliyun pds cli using aliyun pds config
```bash
aliyun pds config \
  --domain-id <domain_id> \
  --user-id <user_id> \
  --authentication-type token \
  --user-agent AlibabaCloud-Agent-Skills
```

**Parameter Description**:
- `--domain-id`: PDS domain ID (e.g., `bj31216`), provided by PDS user, check if included in the prompt
- `--user-id`: PDS user ID (e.g., `a34527bd247e48b6b7e48d5c381b23f3`), provided by PDS user, check if included in the prompt
- `--authentication-type`: **Must be set to `token` if user_id parameter is provided**, indicating access with user identity

**Effect After Configuration**:
- No need to pass `--domain-id` parameter for subsequent PDS API calls
- CLI will automatically use the configured domain_id and user_id

**Verify Configuration**:
```bash

# Test if configuration is effective, get-user API without parameters returns current logged-in user information in token scenario
aliyun pds get-user --user-agent AlibabaCloud-Agent-Skills
```
Extract the current logged-in user information from the returned JSON: domain_id: `domain_id`, user_id: `user_id`, nick_name: `nick_name`.

After successful configuration, notify the user: Current PDS DomainID: <domain_id>, logged-in user: <nick_name>(<user_id>)


**Notes**:
- Domain_id and user_id will be preset in CLI configuration
- User's token will be preset in Aliyun CLI configuration file
- After configuring once, no need to repeat configuration for subsequent operations

---