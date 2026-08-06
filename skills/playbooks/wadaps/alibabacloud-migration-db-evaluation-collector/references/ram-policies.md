# RAM Permission Statement

## required_permissions

This Skill guides users through Alibaba Cloud CMH (Cloud Migration Hub) database evaluation via the APDS console (`https://apds.console.aliyun.com/<region>/db/db-evaluation/collect`). The console operations involved (download the Rainmeter collector, upload `data.zip`, create/view evaluation reports) require the following RAM permissions on the Alibaba Cloud account performing them:

| Permission (Action) | Description |
|---------------------|-------------|
| `apds:DescribeEvaluations` | View database evaluation task list and results in the APDS console |
| `apds:CreateEvaluation` | Create a database evaluation task after uploading collected data |
| `apds:UploadEvaluationData` | Upload the collector output package `data.zip` to APDS |
| `apds:DownloadCollector` | Download the Rainmeter collector package from the APDS console |

Recommended managed policy: `AliyunAPDSFullAccess` (or a custom policy scoped to the actions above for least privilege).

## Notes

- This Skill itself does NOT call any OpenAPI directly and does NOT read or store any AccessKey/SecretKey. All privileged operations are performed by the user in the Alibaba Cloud console with their own logged-in identity.
- The database collection accounts created by this Skill (e.g., `eoa_user`) are source-database local accounts with read-only privileges; they are unrelated to Alibaba Cloud RAM.
- No credentials are stored in this repository. All account-creation SQL in SKILL.md sets passwords at runtime through interactive, hidden input (SQL*Plus `ACCEPT ... HIDE`, psql `\password`, sqlcmd scripting variables, or MySQL server-generated random passwords).
