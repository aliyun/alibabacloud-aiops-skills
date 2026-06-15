# STAROps RAM Policy Notes

This skill does not use STAROps-specific AccessKey environment variables. It relies on Alibaba Cloud Credentials default-chain behavior, so credentials should be configured through standard Alibaba Cloud mechanisms.

## Required Access

The STAROps OpenAPI actions are registered under the **`cms`** service code. Grant the caller the following actions:

| Action | Description |
|--------|-------------|
| `cms:CreateThread` | Create an investigation thread |
| `cms:CreateChat` | Send a message and stream the agent response |

Resource ARN format:

```
acs:cms::{uid}:digitalemployee/{employee_name}
```

### Example Custom Policy

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cms:CreateThread",
        "cms:CreateChat"
      ],
      "Resource": "acs:cms::*:digitalemployee/*"
    }
  ]
}
```

To restrict access to a specific account and digital employee, replace `*` with concrete values, e.g. `acs:cms::<your-uid>:digitalemployee/<employee-name>`.

## Recommended Credential Sources

Use one of the Alibaba Cloud Credentials default-chain sources:

- Standard Alibaba Cloud AccessKey environment credentials.
- Alibaba Cloud CLI profile or shared credentials profile.
- STS credentials.
- RAM role credentials.
- ECS instance metadata credentials, when available.

For local development environments where metadata lookup causes delays, set:

```bash
export ALIBABA_CLOUD_ECS_METADATA_DISABLED=true
```

## Security Boundaries

This skill creates STAROps investigation threads and streams STAROps Agent answers. It does not directly mutate ECS, OSS, RDS, SLS, or other cloud resources. Any operational action proposed by STAROps should still be reviewed according to the user's normal change-management process.

## Permission Failure Handling

When the script returns an HTTP 401 or 403 error indicating an authorization failure:

1. Stop immediately. Do **not** retry with different credentials or fabricate diagnostic results.
2. Report the exact error message to the user, including the `Action` and `Resource` from the error response.
3. Direct the user to check that their identity has the required STAROps permissions listed in the **Required Access** section above.
4. If using STS credentials, verify that the STS token has not expired and that the assumed role's policy includes `cms:CreateThread` and `cms:CreateChat`.
5. Wait for the user to confirm that permissions have been granted before retrying.