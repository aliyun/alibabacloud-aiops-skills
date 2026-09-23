# RAM Policy for WAF Certificate Chain Check

This Skill only reads WAF 3.0 certificate metadata. Certificate upload is manual, so no write permission is required.

## Minimal Policy

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "yundun-waf:DescribeCerts"
      ],
      "Resource": "*"
    }
  ]
}
```

## Permission Error Handling

When `DescribeCerts` fails with `Forbidden.RAM`, `NoPermission`, or `not authorized`, terminate immediately without retrying. State that the query could not be completed because read-only `yundun-waf:DescribeCerts` permission is missing, then end the turn. Do not request authorization, wait for confirmation, change credentials, or continue into local repair. Without a successful response, certificate-chain status remains unknown.

The policy above documents the prerequisite only; it is not an instruction to grant permissions during error recovery. Never request certificate create/deploy permissions and never ask the user to paste AK/SK values into the conversation.
