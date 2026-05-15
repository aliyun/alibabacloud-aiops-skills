# RAM Policies

The exact authorization model can change with the CMS API release. Use this file as the required permission inventory for this skill, and verify action names against the current Alibaba Cloud RAM console or API metadata when creating production policies.

## Required CMS Actions

| API | RAM Action |
| --- | --- |
| CreateContextStore | `cms:CreateContextStore` |
| GetContextStore | `cms:GetContextStore` |
| ListContextStores | `cms:ListContextStores` |
| UpdateContextStore | `cms:UpdateContextStore` |
| DeleteContextStore | `cms:DeleteContextStore` |
| AddContexts | `cms:AddContexts` |
| GetContext | `cms:GetContext` |
| SearchContext | `cms:SearchContext` |
| UpdateContext | `cms:UpdateContext` |
| DeleteContext | `cms:DeleteContext` |
| DeleteContexts | `cms:DeleteContexts` |
| CreateContextStoreApiKey | `cms:CreateContextStoreApiKey` |
| ListContextStoreApiKeys | `cms:ListContextStoreApiKeys` |
| DeleteContextStoreApiKey | `cms:DeleteContextStoreApiKey` |

## Policy Template

Scope resources more narrowly when resource-level authorization is documented for the account and region. Use `Resource: "*"` only when the service does not support narrower resource ARNs for these actions.

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cms:CreateContextStore",
        "cms:GetContextStore",
        "cms:ListContextStores",
        "cms:UpdateContextStore",
        "cms:DeleteContextStore",
        "cms:AddContexts",
        "cms:GetContext",
        "cms:SearchContext",
        "cms:UpdateContext",
        "cms:DeleteContext",
        "cms:DeleteContexts",
        "cms:CreateContextStoreApiKey",
        "cms:ListContextStoreApiKeys",
        "cms:DeleteContextStoreApiKey"
      ],
      "Resource": "*"
    }
  ]
}
```

## Optional Source Logstore Access

When creating a memory store from an existing logstore or an experience store from a trace logstore, the caller or service-linked role may also need read access to the source Log Service project/logstore. Confirm the current SLS permission requirements before issuing a policy. Typical read permissions include project/logstore describe and log read actions.

## Permission Failure Handling

When a command fails with authorization errors:

1. Capture the API name, request ID, and denied action from the CLI error.
2. Compare the denied action with the tables above to identify the missing permission.
3. If the `ram-permission-diagnose` skill is installed in the current environment, invoke it to guide the user through requesting the missing permissions. Otherwise, present the missing RAM action(s) to the user along with the policy template above and instruct them to attach the policy to the current RAM identity in the [Alibaba Cloud RAM Console](https://ram.console.aliyun.com/).
4. Pause until the user confirms that permissions have been granted before retrying the failed command.
