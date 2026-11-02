# RAM permissions

Use a RAM identity with only the permissions required to inspect IDaaS instances and manage inbound identity providers. Avoid using an Alibaba Cloud account AccessKey for routine operations.

The skill invokes EIAM OpenAPI operations for these capabilities:

- List accessible EIAM instances.
- List and inspect identity providers.
- resolve SAML metadata URLs.
- Create or update a SAML identity provider.
- Start and read identity-provider status checks.
- Enable identity-provider authentication when explicitly requested.

Grant these permissions through an administrator-approved custom RAM policy or the applicable IDaaS service role. Scope access to the intended account and instances whenever the authorization model supports resource-level restrictions.

Example action set for a custom policy:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "eiam:ListEiamInstances",
        "eiam:ListIdentityProviders",
        "eiam:GetIdentityProvider",
        "eiam:ExecIdentityProviderMetadataUrlResolution",
        "eiam:CreateIdentityProvider",
        "eiam:UpdateIdentityProvider",
        "eiam:CreateIdentityProviderStatusCheckJob",
        "eiam:GetIdentityProviderStatusCheckJob",
        "eiam:EnableIdentityProviderAuthn"
      ],
      "Resource": "*"
    }
  ]
}
```

Review the policy with the account administrator before use. Remove update or enable actions when those operations are outside the user's task.

Do not place AccessKey IDs or AccessKey secrets in prompts, source files, shell history, or skill configuration. Configure credentials through Alibaba Cloud CLI profiles or another supported Alibaba Cloud credential provider.
