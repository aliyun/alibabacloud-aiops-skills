## RAM Permission Requirements

### RAM Policy

If minimum required permissions principle is needed:
```yaml
metadata:
  required_permissions:
    - "pds:ListDomains" — List domains: list-domains
    - "pds:ListUser" — List users: list-user
    - "pds:GetDomain" — Get domain info: get-domain
    - "pds:ListFile" — List or search files: list-file
    - "pds:GetUser" — Get user info: get-user
    - "pds:DownloadFile" — Download file: download-file
    - "pds:AssumeUser" — Access via user identity token: user upload (upload-file) / download (get-download-url) / process file (file-process) / get user personal space list (list-my-drive) / get user team/enterprise space list (list-my-group-drive) / user mount (mountapp)
```

### API and Permission Reference Table (authentication_type: token, non-RAM authentication)

AssumeUser operation uses user identity access. In token scenario, except for domain management APIs and list user API, all other APIs operate after obtaining user token via AssumeUser, so the Required Permission for these operations is AssumeRole.

| API Action          | Required Permission | Resource                           |
|---------------------|---------------------|------------------------------------||
| list-domains        | `pds:ListDomains`   | "acs:pds:*:*:domain/*",            |
| get-domain          | `pds:GetDomain`     | "acs:pds:*:*:domain/<domain_id>"   |
| list-user           | `pds:ListUser`      | "acs:pds:*:*:domain/<domain_id>/*" |
| search-file         | `pds:AssumeUser`    | "acs:pds:*:*:domain/<domain_id>/*" |
| get-user            | `pds:AssumeUser`    | "acs:pds:*:*:domain/<domain_id>/*" |
| get-download-url    | `pds:AssumeUser`    | "acs:pds:*:*:domain/<domain_id>/*" |
| process             | `pds:AssumeUser`    | "acs:pds:*:*:domain/<domain_id>/*" |
| list-my-group-drive | `pds:AssumeUser`    | "acs:pds:*:*:domain/<domain_id>/*" |
| list-my-drives      | `pds:AssumeUser`    | "acs:pds:*:*:domain/<domain_id>/*" |
| upload-file         | `pds:AssumeUser`    | "acs:pds:*:*:domain/<domain_id>/*" |
| mountapp            | `pds:AssumeUser`    | "acs:pds:*:*:domain/<domain_id>/*" |

### API and Permission Reference Table (authentication_type: ak, RAM authentication)

Using ak authentication method without user identity, only the following APIs are supported:

| API Action          | Required Permission | Resource                           |
|---------------------|---------------------|------------------------------------||
| list-domains        | `pds:ListDomains`   | "acs:pds:*:*:domain/*",            |
| get-domain          | `pds:GetDomain`     | "acs:pds:*:*:domain/<domain_id>"   |
| search-file         | `pds:ListFile`      | "acs:pds:*:*:domain/<domain_id>/*" |
| get-user            | `pds:GetUser`       | "acs:pds:*:*:domain/<domain_id>/*" |
| list-user           | `pds:ListUser`      | "acs:pds:*:*:domain/<domain_id>/*" |
| get-download-url    | `pds:DownloadFile`  | "acs:pds:*:*:domain/<domain_id>/*" |

## Notes

1. In addition to RAM permissions, PDS also requires assigning corresponding Drive space access permissions to users in the **PDS Console**
2. When calling with AK/SK method, ensure the RAM user has the above permissions
3. When calling with Bearer Token (OAuth) method, permissions are determined by the user role within PDS
