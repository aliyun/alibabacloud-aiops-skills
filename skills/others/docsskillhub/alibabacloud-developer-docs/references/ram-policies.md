# RAM permission summary (`ram-policies`)

Single audit view of every RAM permission this Skill's flows can involve. This Skill is documentation consultation: it calls no resource-type OpenAPI directly and has no resource-changing capability. Every credentialed call is delegated to the **user's local aliyun CLI**, is read-only, whitelisted in code, and runs only after the user authorizes that execution. All other commands are anonymous and need no RAM permissions at all.

## Per-API permissions (credentialed exceptions only)

| Skill command path | API (version) | Access | RAM action | Resource |
| --- | --- | --- | --- | --- |
| `diagnose` (own log, default) | OpenAPIExplorer `GetOwnRequestLog` (`2024-11-30`) | valid credentials only | none published (metadata `ramActions` is empty) | — |
| `diagnose --scope account` (or `auto` fallback on `NotFound.RequestLog`) | OpenAPIExplorer `GetRequestLog` (`2024-11-30`) | RAM authorization | `openapiexplorer:GetRequestLog` | `*` (all resources; no finer granularity published) |
| `diagnose` (official solutions) | OpenAPIExplorer `GetErrorCodeSolutions` (`2024-11-30`) | valid credentials only | none published (metadata `ramActions` is empty) | — |
| `iac-doc <resource> --via-api` | IaCService `GetProviderDocument` (`2021-08-06`) | valid credentials only (no anonymous access) | none published (metadata `ramActions` is empty) | — |

Permission points are verified live, not from memory: `api-info OpenAPIExplorer <ApiName> -V 2024-11-30 --json` and `api-info IaCService GetProviderDocument -V 2021-08-06 --json` (`ramActions` field). "Valid credentials only" means the CLI's current profile (or `--profile`) must be configured and able to sign; the API declares no separate RAM action to grant.

## Least-privilege grant

Only one RAM action is ever needed beyond valid credentials. Grant the RAM action `openapiexplorer:GetRequestLog` to the calling RAM user/role when account-level log lookup is wanted; without it, keep `--scope own` (the default `auto` falls back to account scope only on `NotFound.RequestLog` and stops on permission errors). Minimal custom policy:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "openapiexplorer:GetRequestLog",
      "Resource": "*"
    }
  ]
}
```

The grant is performed by the user in the RAM console; the Skill never creates, attaches, or modifies policies.

## User-side-only permissions (never called by this Skill)

- `ram:DecodeDiagnosticMessage` — mentioned in error-diagnosis rules only as guidance when the **user** chooses to decode an `encodedDiagnosticMessage` from an authorization error. The Skill verifies the permission point and gives the CLI for the user to run; it never invokes this API itself.

## Boundaries

- No other RAM permissions are required or requested; doc retrieval, OpenAPI metadata, SDK guides, announcements, trial cards, and Terraform catalog/doc paths are anonymous.
- Credentials stay inside the local CLI: no reading `~/.aliyun/config.json`, no AccessKey/STS Token handling, no `aliyun configure`, no plugin installation on the user's behalf.
- Credential and permission failures stop only the corresponding credentialed path (exit `2` with self-service commands); anonymous doc retrieval proceeds independently.