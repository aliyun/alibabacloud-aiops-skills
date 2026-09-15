# Storage Routing and Artifact Upload

## Discover the workspace storage

```bash
SKILL_SESSION_ID={session-id} python3 scripts/flink_python_submit.py get-storage-mode \
  --region <region> --workspace <workspace-id> --namespace <namespace>
```

The script matches the supplied workspace/cluster or sales instance ID in
DescribeInstances. Storage belongs to the workspace, so namespace is not an API
filter. Require one match, a non-empty `consoleUrl`, and an explicit storage mode:

- `FULLY_MANAGED`: upload through authenticated VVP File Management.
- `USER_MANAGED_OSS`: upload through `aliyun ossutil` to the returned `ossBucket`.

`DescribeInstances.ClusterState.Url` supplies the console origin;
`Storage.FullyManaged` and `Storage.Oss.Bucket` determine storage routing.
A missing or ambiguous result requires resolving the metadata error; bucket
names and artifact URIs do not prove the storage mode.

## Fully managed storage

Use an authenticated browser-control capability with local-file upload support.
If unavailable, ask the user to enable one. Open:

```text
<consoleUrl>/web/<workspace>/zh/#/workspaces/<workspace>/namespaces/<namespace>/artifacts-managed/artifact
```

Verify the target namespace, check for the exact filename, upload the local
file, and verify the resulting table row and file size. Repeat for dependencies.
A file chooser interaction alone does not prove upload completion.

Use the canonical artifact URI after verification:

```text
oss://flink-fullymanaged-<workspace>/artifacts/namespaces/<namespace>/<filename>
```

This URI is a VVP artifact address, not access to a customer OSS bucket.
Perform fully managed artifact operations through File Management.

## User-managed OSS

Use the returned bound bucket and the confirmed namespace. Pass the bucket's
region and endpoint explicitly; the CLI profile may default to another region:

```bash
aliyun ossutil stat oss://<ossBucket>/artifacts/namespaces/<namespace>/<filename> \
  --region <bucket-region> --endpoint oss-<bucket-region>.aliyuncs.com
aliyun ossutil cp <local-file> oss://<ossBucket>/artifacts/namespaces/<namespace>/<filename> \
  --region <bucket-region> --endpoint oss-<bucket-region>.aliyuncs.com
aliyun ossutil stat oss://<ossBucket>/artifacts/namespaces/<namespace>/<filename> \
  --region <bucket-region> --endpoint oss-<bucket-region>.aliyuncs.com
```

The first stat checks conflicts; distinguish object-not-found from permission
or network errors. The final stat verifies the exact object and expected size.
OSS commands use the ossutil backend and omit `--user-agent`.

## Filename conflicts

When an exact name exists, ask whether to reuse, replace in place, or rename.
Preserve filenames referenced by the code. Require approval for replacement;
offer it in VVP only when an in-place action is available without deletion.
Otherwise offer reuse or a new filename. Apply this to every artifact and verify
the result on the same storage surface before using its URI.
