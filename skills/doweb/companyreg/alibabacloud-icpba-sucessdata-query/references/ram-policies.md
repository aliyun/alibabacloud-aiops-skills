# RAM Policies for ICP Filing Success Query

## Required Permissions

This skill requires the following RAM permissions to function properly:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "beian:QuerySuccessIcpData"
      ],
      "Resource": "*"
    }
  ]
}
```

## Permission Details

### beian:QuerySuccessIcpData

**Action**: `beian:QuerySuccessIcpData`

**Description**: Query ICP filing success data including entity information, website information, APP information, and risk information.

**Resource**: `*` (applies to all resources under the account)

**Usage Scenario**:
- Query filing success information after successful filing
- Retrieve entity, website, and APP details
- Check filing risks and rectification requirements

## How to Grant Permissions

### Option 1: Through RAM Console

1. Login to [RAM Console](https://ram.console.aliyun.com/)
2. Navigate to **Identities** > **Users** or **Roles**
3. Select the target user or role
4. Click **Add Permissions**
5. Select **Custom Policy** and create a new policy with the JSON above
6. Or select **System Policy** if available (search for "Beian")
7. Click **OK** to grant permissions

### Option 2: Using CLI

Create a custom policy file `icp-filing-query-policy.json`:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "beian:QuerySuccessIcpData"
      ],
      "Resource": "*"
    }
  ]
}
```

Create the policy:

```bash
aliyun ram create-policy \
  --policy-name IcpFilingQueryPolicy \
  --policy-document "$(cat icp-filing-query-policy.json)"
```

Attach the policy to a user:

```bash
aliyun ram attach-policy-to-user \
  --policy-type Custom \
  --policy-name IcpFilingQueryPolicy \
  --user-name <your-username>
```

### Option 3: Using Python SDK

```python
from alibabacloud_credentials.client import Client as CredentialClient
from alibabacloud_tea_openapi.client import Client as OpenApiClient
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_tea_util import models as util_models
import json

def create_ram_client() -> OpenApiClient:
    credential = CredentialClient()
    config = open_api_models.Config(
        credential=credential,
        endpoint='ram.aliyuncs.com'
    )
    return OpenApiClient(config)

def create_policy():
    client = create_ram_client()

    policy_document = {
        "Version": "1",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": ["beian:QuerySuccessIcpData"],
                "Resource": "*"
            }
        ]
    }

    params = open_api_models.Params(
        action='CreatePolicy',
        version='2015-05-01',
        protocol='HTTPS',
        method='POST',
        auth_type='AK',
        style='RPC',
        pathname='/',
        req_body_type='formData',
        body_type='json'
    )

    request = open_api_models.OpenApiRequest(
        query={
            'PolicyName': 'IcpFilingQueryPolicy',
            'PolicyDocument': json.dumps(policy_document)
        }
    )

    runtime = util_models.RuntimeOptions()
    response = client.call_api(params, request, runtime)
    return response

# Create policy
result = create_policy()
print(json.dumps(result, indent=2))
```

## Permission Verification

To verify that permissions are correctly configured:

1. **Check User Policies**:
   ```bash
   aliyun ram list-policies-for-user --user-name <your-username>
   ```

2. **Test API Call**:
   Try running the query operation. If you receive a permission error, the permissions are not correctly configured.

   Common permission error messages:
   - `You are not authorized to do this action.`
   - `User not authorized to operate on the specified resource.`
   - `Forbidden.RAM`

## Minimum Privilege Principle

This skill follows the principle of least privilege by only requesting:
- Read-only access to ICP filing data
- No write or delete permissions
- No access to other Alibaba Cloud services

## Security Recommendations

1. **Use RAM Roles**: When possible, use RAM roles instead of RAM users for better security
2. **Regular Audits**: Regularly review and audit permissions granted to users
3. **Temporary Credentials**: Use STS temporary credentials for short-term access
4. **Avoid Root Account**: Never use the root account for daily operations
5. **Enable MFA**: Enable multi-factor authentication for sensitive operations

## Troubleshooting Permission Issues

If you encounter permission errors:

1. **Verify the policy is attached**: Check that the policy is actually attached to your user/role
2. **Check policy content**: Ensure the policy JSON is correctly formatted
3. **Verify resource scope**: Confirm that `Resource: "*"` is set correctly
4. **Check API action name**: Ensure the action name is exactly `beian:QuerySuccessIcpData`
5. **Review account status**: Verify your account is in good standing and not suspended
6. **Use RAM permission diagnosis**: Use the `ram-permission-diagnose` skill for detailed analysis

## Related Documentation

- [RAM Policy Language](https://www.alibabacloud.com/help/ram/developer-reference/ram-policy-language)
- [RAM Policy Best Practices](https://www.alibabacloud.com/help/ram/user-guide/best-practices-for-ram-policies)
- [Beian Service Documentation](https://www.alibabacloud.com/help/beian)
