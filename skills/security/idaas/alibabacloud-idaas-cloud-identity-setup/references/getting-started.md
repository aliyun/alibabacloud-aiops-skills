# First-use guidance

Before any cloud command, obtain the explicit target provider, account ID and
instance ID, or reuse a previously user-confirmed target. Read-only status
verification has the same requirement. Never discover or select a target from
default credentials or the only accessible instance.

Respond in the user's language. Ask only for missing fields: cloud provider,
cloud account ID, and IDaaS instance ID. Offer a short copyable example:

```text
Connect AWS international account 123456789012 to IDaaS instance idaas_example.
```

Explain that the skill checks environment and identities, prepares one concrete
change plan, asks for confirmation once, and configures/verifies the account.
Do not introduce profiles, IAM policies, or OIDC jargon before it is needed.
Do not ask the user to send keys, tokens, or callback codes.

Instance ID is found in the EIAM instance details or console URL. It identifies
an instance, not the target cloud account. Alibaba Cloud account ID comes from
account settings or STS AccountId. AWS account ID is the 12-digit STS Account.
Tencent Cloud account ID is the owner account UIN, not a subuser UIN.
Resolve “current Alibaba Cloud account” with verified EIAM STS identity and
show the resulting account in the plan. Ask about site only when existing
verified partition/account context cannot determine it.

Translate failures into one action: install the selected official CLI with
permission; log in to the requested account; request the specific missing
instance permission; or inspect the listed resource conflict. Resume after the
action without requiring the user to repeat supplied parameters.

If the account is managed by another instance, explain the ownership conflict
and stop without changing either instance. Cross-instance transfer is unsupported.
For timeout, report actual completed writes
and continue bounded readback rather than restarting authorization.
