# Verification Method: alibabacloud-oss-manage-network-probe

## Goal

Verify that the `aliyun ossutil probe` solution has successfully achieved one of the following objectives:

- Successfully diagnosed the local-to-OSS upload or download link
- Output upload/download bandwidth with a suggested concurrency value
- Output download time statistics
- Detected whether local symlinks have anomalies

## Step 1: Verify CLI prerequisites

```bash
aliyun version
aliyun configure list
aliyun ossutil version
```

Success indicators:
- `version` outputs a version number >= 3.3.3
- `configure list` shows at least one `Valid` profile
- `ossutil version` returns version information successfully

Failure guardrails:
- If `configure list` does not show a valid profile, stop immediately; do not proceed with `configure set --auto-plugin-install true`, `configure ai-mode enable`, `ossutil version`, or any probe commands
- Do not read `~/.aliyun/config.json`, do not export environment variables, do not log any plaintext credentials

## Step 2: Verify input object or URL when needed

### 2.1 Verify a bucket/object path before download-speed or download-time

```bash
aliyun ossutil stat \
  "oss://<BUCKET_NAME>/<OBJECT_NAME>" \
  --region "<REGION_ID_IF_NEEDED>" \
  --user-agent AlibabaCloud-Agent-Skills
```

Success indicator:
- Command returns object metadata, not `NoSuchKey` or a permission error

### 2.2 Verify download URL mode

For private objects, generate a presigned URL first, then run the URL download probe:

```bash
aliyun ossutil presign \
  "oss://<BUCKET_NAME>/<OBJECT_NAME>" \
  --expires-duration 1h \
  --region "<REGION_ID_IF_NEEDED>" \
  --user-agent AlibabaCloud-Agent-Skills
```

Success indicator:
- Outputs a usable HTTP/HTTPS URL

Security note:
- When logging execution results, do not persist the full presigned URL query string; only keep the base URL, or redact everything after `?`

## Step 3: Verify each probe mode

### 3.1 Upload connectivity probe

```bash
aliyun ossutil probe \
  --upload \
  --bucket "<BUCKET_NAME>" \
  --region "<REGION_ID_IF_NEEDED>" \
  --user-agent AlibabaCloud-Agent-Skills
```

Success indicators:
- Output contains `begin upload file`
- Output contains `upload file:success`
- Output contains `upload time consuming:`
- Output contains `report log file:`

### 3.2 Download connectivity probe by bucket

```bash
aliyun ossutil probe \
  --download \
  --bucket "<BUCKET_NAME>" \
  --object "<OBJECT_NAME_IF_ANY>" \
  --region "<REGION_ID_IF_NEEDED>" \
  --user-agent AlibabaCloud-Agent-Skills
```

Success indicators:
- Output contains `begin download file`
- Output contains `download file:success`
- Output contains `download time consuming:`
- Output contains `download file is`

### 3.3 Download connectivity probe by URL

```bash
aliyun ossutil probe \
  --download \
  --url "<DOWNLOAD_URL>" \
  --user-agent AlibabaCloud-Agent-Skills
```

Success indicators:
- Output contains `download file:success`
- Output contains the target local file path

### 3.4 Upload bandwidth probe

Basic command:
```bash
aliyun ossutil probe \
  --probe-item upload-speed \
  --bucket "<BUCKET_NAME>" \
  --region "<REGION_ID_IF_NEEDED>" \
  --user-agent AlibabaCloud-Agent-Skills
```

To limit runtime, add `--runtime`:
```bash
aliyun ossutil probe \
  --probe-item upload-speed \
  --bucket "<BUCKET_NAME>" \
  --runtime "<RUNTIME_IF_CONFIRMED>" \
  --region "<REGION_ID_IF_NEEDED>" \
  --user-agent AlibabaCloud-Agent-Skills
```

Success indicators:
- Output contains multiple lines of `parallel:<N>,average speed:`
- Output contains `suggest parallel is <N>`

### 3.5 Download bandwidth probe

```bash
aliyun ossutil probe \
  --probe-item download-speed \
  --bucket "<BUCKET_NAME>" \
  --object "<OBJECT_NAME>" \
  --runtime "<RUNTIME_IF_CONFIRMED>" \
  --region "<REGION_ID_IF_NEEDED>" \
  --user-agent AlibabaCloud-Agent-Skills
```

Success indicators:
- Output contains multiple lines of `parallel:<N>,average speed:`
- Output contains `suggest parallel is <N>`
- If the object is smaller than the recommended size or network fluctuations are significant, results may be unstable, but the command should still complete

### 3.6 Download time probe

Basic command:
```bash
aliyun ossutil probe \
  --probe-item download-time \
  --bucket "<BUCKET_NAME>" \
  --object "<OBJECT_NAME>" \
  --region "<REGION_ID_IF_NEEDED>" \
  --user-agent AlibabaCloud-Agent-Skills
```

To explicitly control concurrency and part size, add:
```bash
aliyun ossutil probe \
  --probe-item download-time \
  --bucket "<BUCKET_NAME>" \
  --object "<OBJECT_NAME>" \
  --parallel "<PARALLEL_IF_CONFIRMED>" \
  --part-size "<PART_SIZE_IF_CONFIRMED>" \
  --region "<REGION_ID_IF_NEEDED>" \
  --user-agent AlibabaCloud-Agent-Skills
```

Success indicators:
- Output contains `total bytes:`
- Output contains `cost:`
- Output contains `avg speed:`

### 3.7 Symlink detection

```bash
aliyun ossutil probe \
  --probe-item cycle-symlink \
  "<LOCAL_DIRECTORY_OR_FILE>" \
  --user-agent AlibabaCloud-Agent-Skills
```

Success indicators:
- Command completes normally and outputs elapsed time
- If no anomalies, output should indicate no abnormal symlinks
- If anomalies are found, output should list the abnormal symlink information

Supplementary forensics rules:
- To reconstruct specific link chains, perform read-only local forensics on the same path (e.g. `readlink`, `stat -f "%N -> %Y"`)
- Only write precise chains when the target is successfully read; if `readlink`/`stat` itself fails, report only verified segments and the raw probe error

## Step 4: Verify local probe logs

After probe execution, check whether `logOssProbe*.log` files were generated in the current working directory or the `ossutil` run directory.

```bash
ls -1t logOssProbe*.log
```

Success indicator:
- At least one recent `logOssProbe*.log` file exists

## Step 5: Optional cleanup verification

If a test object was explicitly uploaded and is planned for deletion, execute:

```bash
aliyun ossutil rm \
  "oss://<BUCKET_NAME>/<OBJECT_NAME>" \
  --user-agent AlibabaCloud-Agent-Skills
```

Then verify the object no longer exists:

```bash
aliyun ossutil stat \
  "oss://<BUCKET_NAME>/<OBJECT_NAME>" \
  --region "<REGION_ID_IF_NEEDED>" \
  --user-agent AlibabaCloud-Agent-Skills
```

Success indicator:
- Delete command succeeds
- Subsequent `stat` returns object not found, or the user confirms retaining the object and this step is skipped

## Failure Interpretation

| Symptom | Likely meaning | Next action |
| --- | --- | --- |
| `configure list` shows no valid profile | Credentials are unavailable | Configure credentials outside the session first |
| `probe --download-speed` reports object not found | `object_name` is wrong or the object has not been prepared | Run `ossutil stat` on the same target first; do not enumerate unconfirmed regions/buckets |
| `probe --download --url` returns 404/403 | URL is reachable but object, permission, or bucket conditions are not met | Quote the raw HTTP error; if necessary, run a single `stat` validation on the same `bucket/object/region` |
| `probe` fails during `network detection` phase | Local network, DNS, proxy, or link to the target address is abnormal | Continue troubleshooting with `--addr`, proxy configuration, and local network |
| `The bucket you are attempting to access must be addressed using the specified endpoint` | The current request endpoint does not match the bucket's requirements | Ask the user to confirm the correct region/endpoint or execution environment; do not assert VPC-only on your own |
| Only `--addr` detection fails, but OSS upload/download succeeds | Domain connectivity issue, not necessarily an OSS failure | Use the correct domain or skip this check |
| `cycle-symlink` reports `no such file or directory` | The local path does not exist in the current execution environment | Clearly state this is a missing local path; do not auto-rewrite it as "expected behavior" |
| `cycle-symlink` reports anomalies | Local symlink target is abnormal or a cyclic link exists | Manually fix the link, then retry |
