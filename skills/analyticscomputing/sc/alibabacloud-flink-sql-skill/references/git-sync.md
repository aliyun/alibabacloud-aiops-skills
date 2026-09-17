# Deployment Git Synchronization

Read when enabling or troubleshooting Git synchronization, synchronizing Deployments manually, or explaining the content and timing of automatic commits.

## Configuration

`config_init` saves Git settings with the resource scope. See [configuration.md](configuration.md) for question order, defaults, the configuration file, and overwrite rules. Synchronization is disabled when `git.repo_url` is absent. Repository authentication uses only the local Git/SSH environment; never embed credentials in an HTTP(S) URL.

## Automatic Triggers

After Git synchronization is enabled, these successful operations automatically write files, create a commit, and push it:

| Platform operation | Git action | Commit message |
|--------------------|------------|----------------|
| Create Deployment | Write the complete Deployment | `[create] {name}` |
| Update Deployment | Update Deployment artifacts from response fields | `[update] {name}` |
| Delete Deployment | Delete the corresponding Deployment directory | `[delete] {name}` |

Automatic synchronization is a fixed post-step after the platform operations above succeed; it does not mean the platform mutation itself is authorized. Deploying a Draft does not trigger Git automatically. To version its result, wait for the deployment ticket to succeed, read back the Deployment, and synchronize it manually by ID.

A Git synchronization failure does not roll back a successful cloud operation. Preserve the platform and Git results separately.

## Manual Synchronization

- `git_init`: clone or update the configured local repository.
- `git_sync --deployment_id <id>`: retrieve and synchronize the complete details of one Deployment.
- `git_sync`: page through every Deployment, retrieve complete details for each, and commit them together.

A single-resource synchronization uses `[sync] {name}`; a full synchronization uses `sync {count} deployments`. When there are no Deployments, it succeeds without creating a commit.

## Repository Artifacts

Each Deployment uses a directory named after the Deployment:

```text
flink-sql-repo/
└── deployments/
    └── order-aggregation/
        ├── job.sql
        ├── flink-conf.properties
        └── resource-config.json
```

- `job.sql`: written only when `artifact.kind=SQLSCRIPT` and SQL content is present; the content comes from `artifact.sqlArtifact.sqlScript`.
- `flink-conf.properties`: writes `flinkConf` as sorted `key=value` entries.
- `resource-config.json`: when resource settings exist, writes the BASIC/EXPERT streaming resource configuration or the batch resource configuration.

BASIC-mode example:

```json
{
  "mode": "BASIC",
  "parallelism": 4,
  "jobManager": {"cpu": 1.0, "memory": "1Gi"},
  "taskManager": {"cpu": 2.0, "memory": "4Gi"}
}
```

EXPERT mode preserves `jobManager` and the complete `resourcePlan`. Batch jobs use `mode: BATCH` and preserve `maxSlot` and the base resource configuration.

## Repository Protection

- Stop if the local path exists but is neither empty nor a Git repository; never overwrite existing files.
- Stop if the local repository's `origin` differs from the configured URL, preventing a push to the wrong repository.
- Stop when the local repository has uncommitted changes, preventing unrelated content from entering an automatic commit.
- Replace characters outside `[a-zA-Z0-9_.-]` in Deployment names with `_`. Restrict deletion strictly to `deployments/` within the repository, and reject symlinks for directories or artifact files.
- Disable local hooks for Git commands so automatic synchronization cannot unexpectedly execute scripts outside the repository.
- Use the machine's existing Git `user.name` and `user.email` as the commit author; the skill does not change identity settings.
- If a push fails after creating a Git commit, keep the local commit; a later synchronization will try to push it again.

## Verification and Reporting

Verify repository results according to [verification.md](verification.md), then report platform and Git states separately according to [output-schemas.md](output-schemas.md).
