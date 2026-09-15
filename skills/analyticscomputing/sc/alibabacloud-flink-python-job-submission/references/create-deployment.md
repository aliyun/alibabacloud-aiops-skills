# Python Deployment Configuration

Use `create-deployment --help` for supported arguments and defaults. Resolve the
following choices before sending the approved CreateDeployment request.

## Engine and resources

Use the user's explicit engine version. Otherwise run `list-engine-versions`
with the target workspace and region, then propose its `defaultEngineVersion`.
Treat engine IDs as opaque; do not rank or filter them by naming prefix.

Suggest `default-queue` when no resource queue is specified. Propose STREAMING
when execution mode is omitted, including for bounded input. Preserve an
explicit BATCH choice. Include parallelism and JM/TM CPU and memory in the
creation proposal; use compact API memory units such as `4g` or `4096m`.

## Python artifacts

All URIs must refer to artifacts verified through the selected storage surface.

| Input | Deployment argument |
|---|---|
| Main `.py` file | `--artifact-uri`; leave `--entry-module` empty |
| Main `.zip` project | `--artifact-uri`; require `--entry-module module.path` without `.py` |
| Python wheel dependencies | `--libraries` with comma-separated URIs |
| Python archives or custom environment | `--archives` with comma-separated URIs |
| Other dependencies, including data files | `--additional-deps` with comma-separated URIs |
| Program arguments | `--main-args` |

A custom Python environment must match the cluster's Linux OS and architecture.
Inspect the archive layout to choose its executable path. For an archive
containing `venv/bin/python`, for example:

```json
{
  "python.executable": "venv.zip/venv/bin/python",
  "python.client.executable": "venv.zip/venv/bin/python"
}
```

## Other Configuration

Pass a single `--flink-conf` JSON object or `@/path/to/config.json`. Its keys are
non-empty strings and its values are strings; duplicate keys are rejected.
It is sent with CreateDeployment, without a follow-up update.

For a supported pre-installed Python interpreter, select its executable in both
`python.executable` and `python.client.executable`. For example, VVR 11.7+ can
use `python3.11`.

DataFrame API jobs leave `pipeline.used-builtin-*` absent. For other APIs, include
those settings only when required by the job, using confirmed connector and
format names separated by semicolons.

## Create result

Read the returned ID from `data.deploymentId`.
A timeout or unrecognized response does not prove that creation failed. Inspect
the redacted response and use **alibabacloud-flink-workspace-ops** to check for
an existing deployment at the confirmed location before retrying. An existing
deployment should be verified, not created again.
