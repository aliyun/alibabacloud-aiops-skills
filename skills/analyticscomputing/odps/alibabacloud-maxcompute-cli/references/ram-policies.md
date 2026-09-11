# RAM policy boundary

This Skill uses the Alibaba Cloud CLI as the caller. The surrounding account
or runtime must provide least-privilege RAM permissions for the requested
MaxCompute operation; the Skill does not grant, discover, or print credentials.

Use read-only permissions for context, project/schema/table/partition metadata,
SQL cost or explain, job inspection, and data reads. Add table- or project-
scoped write permissions only when the user explicitly authorizes an upload,
job submission, table mutation, or other write. Keep actions and resources
scoped to the named project/table and deny wildcard escalation. `auth whoami`
and local `agent context` report the effective identity but do not change RAM.

For MaxCompute RAM policies, map those boundaries to concrete actions rather
than granting a broad administrator policy. Typical read-only actions include
`odps:DescribeTable`, `odps:ListTables`, `odps:Select`, `odps:GetTable`, and
`odps:ReadData`; only the explicitly authorized write path may add narrowly
scoped actions such as `odps:CreateTable`, `odps:UploadData`,
`odps:UpdateTable`, or `odps:DeleteData`. Bind resources to the named project, schema, table, or
partition and review any action that can create, overwrite, or delete data.
