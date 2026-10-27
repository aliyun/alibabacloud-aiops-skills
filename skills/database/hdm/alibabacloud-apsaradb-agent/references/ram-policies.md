# RAM Policy for ApsaraDB Agent

## Least-Privilege Permission

GetYaoChiAgent does not support resource-level authorization. The minimum API permission is:

| Product | RAM action | Access | Resource |
|---|---|---|---|
| DAS | `hdm:GetYaoChiAgent` | Get | `*` |

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "hdm:GetYaoChiAgent",
      "Resource": "*"
    }
  ]
}
```

Grant this policy to the RAM user or role represented by the selected aliyun CLI profile. Do not add AccessKey values to a policy, script, query, or troubleshooting message.

## Downstream Product Permissions

`hdm:GetYaoChiAgent` permits calling the Agent endpoint. Agent requests are readonly, but a diagnosis may still need product-specific read permissions to inspect the user's resources. Grant only the read actions required for the intended product and scope them to resources where the product supports resource-level authorization.

## Permission Failure

Follow the mandatory permission-failure workflow in [SKILL.md](../SKILL.md#ram-policy).

Report the returned action and request ID when available. Never ask the user to paste an AccessKey, secret, or STS token.

For `Forbidden.RAM` without an action, verify `hdm:GetYaoChiAgent` first, then check read permissions for the target database product.

## References

- [GetYaoChiAgent authorization](https://help.aliyun.com/zh/das/developer-reference/api-das-2020-01-16-getyaochiagent)
- [Alibaba Cloud RAM policy elements](https://help.aliyun.com/zh/ram/user-guide/policy-elements)
