# RAM Authorization Behavior

No RAM policy is required by default for the ramoauth `GenerateAccessToken` API. This API uses deny-only authorization: a request is rejected only when an applicable RAM policy explicitly denies `ram:GenerateAccessToken`. The absence of an explicit `Allow` does not block the request and does not require remediation.

For example, the following policy statement would block the token exchange. It is an example to inspect for, remove, or narrow—not a policy to add:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Deny",
      "Action": "ram:GenerateAccessToken",
      "Resource": "*"
    }
  ]
}
```

Do not tell the user to create or attach an `Allow` policy for this API. If the service returns `NoPermission` or an authorization error, ask the account administrator to inspect the policies applicable to the selected aliyun CLI profile or AgentHub OAuth identity, then remove or narrow any explicit `Deny` that covers `ram:GenerateAccessToken`.

This authorization behavior concerns only the local AgentHub token exchange. It does not change the Alibaba Cloud resource permissions used by a remote Agent.
