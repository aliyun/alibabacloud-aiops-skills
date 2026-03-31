# Acceptance Criteria: alibabacloud-oss-manage-network-probe

**Scenario**: `Use aliyun ossutil probe to diagnose OSS network state, bandwidth, download time, and symlink issues`
**Purpose**: Skill testing acceptance criteria

---

# Correct CLI Command Patterns

## 1. Product and command structure

#### CORRECT
```bash
aliyun ossutil probe --help --user-agent AlibabaCloud-Agent-Skills
aliyun ossutil version
aliyun configure list
```

Why correct:
- Uses `aliyun` plugin-mode command structure
- Uses integrated `ossutil 2.0` entrypoint
- Includes the required `--user-agent AlibabaCloud-Agent-Skills`

#### INCORRECT
```bash
aliyun oss Probe
aliyun oss api probe
oss probe --bucket examplebucket
```

Why incorrect:
- `Probe` is not the supported command form
- `probe` is not an `aliyun oss api` OpenAPI action
- `oss` is the old command family; this skill targets `aliyun ossutil`

## 2. Credential and CLI pre-check

#### CORRECT
```bash
aliyun version
aliyun configure list
aliyun configure set --auto-plugin-install true
aliyun configure ai-mode enable
```

Why correct:
- Verifies CLI version
- Checks local profile validity without printing secrets
- Enables auto plugin install using a supported CLI flag
- Enables AI safety mode to block dangerous operations

#### INCORRECT
```bash
echo $ALIBABA_CLOUD_ACCESS_KEY_ID
aliyun configure set --access-key-id <ak> --access-key-secret <sk>
cat ~/.aliyun/config.json
```

Why incorrect:
- Exposes or handles secrets directly
- Violates the credential safety gate for this skill

#### ALSO INCORRECT
```bash
aliyun configure list --output json --user-agent AlibabaCloud-Agent-Skills
printenv | grep ALIBABA_CLOUD
```

Why incorrect:
- `configure list --output json` is not a valid command pattern for this skill's documented workflow
- Dumping environment variables to inspect credentials is treated as secret handling

## 3. Upload probe patterns

#### CORRECT
```bash
aliyun ossutil probe \
  --upload \
  --bucket "examplebucket" --user-agent AlibabaCloud-Agent-Skills
```

```bash
aliyun ossutil probe \
  --upload \
  "/tmp/test.bin" \
  --bucket "examplebucket" \
  --upmode multipart --user-agent AlibabaCloud-Agent-Skills
```

Why correct:
- `--upload` is present
- `--bucket` is provided
- Optional local file path is passed as a positional argument
- `--upmode` uses a documented enum value

#### INCORRECT
```bash
aliyun ossutil probe --upload --object test.bin --user-agent AlibabaCloud-Agent-Skills
aliyun ossutil probe --upload --bucket examplebucket --upmode parallel --user-agent AlibabaCloud-Agent-Skills
```

Why incorrect:
- Upload probe requires `--bucket`
- `parallel` is not a valid `--upmode` value; valid values are `normal`, `append`, `multipart`

## 4. Download probe patterns

#### CORRECT
```bash
aliyun ossutil probe \
  --download \
  --bucket "examplebucket" \
  --object "dir/example.txt" --user-agent AlibabaCloud-Agent-Skills
```

```bash
aliyun ossutil probe \
  --download \
  --url "https://examplebucket.oss-cn-hangzhou.aliyuncs.com/example.txt" --user-agent AlibabaCloud-Agent-Skills
```

Why correct:
- Uses one of the two documented download modes
- URL mode supplies an HTTP/HTTPS URL
- Bucket mode uses bucket/object parameters correctly

#### INCORRECT
```bash
aliyun ossutil probe --download --url "oss://examplebucket/example.txt" --user-agent AlibabaCloud-Agent-Skills
aliyun ossutil probe --download --object "dir/example.txt" --user-agent AlibabaCloud-Agent-Skills
```

Why incorrect:
- `--url` does not accept `oss://` URIs
- Bucket-based download probe needs `--bucket`

## 5. Probe-item patterns

#### CORRECT
```bash
aliyun ossutil probe --probe-item cycle-symlink "/data/links" --user-agent AlibabaCloud-Agent-Skills
aliyun ossutil probe --probe-item upload-speed --bucket "examplebucket" --user-agent AlibabaCloud-Agent-Skills
aliyun ossutil probe --probe-item download-speed --bucket "examplebucket" --object "big/test.bin" --user-agent AlibabaCloud-Agent-Skills
aliyun ossutil probe --probe-item download-time --bucket "examplebucket" --object "big/test.bin" --parallel 3 --part-size 10000000 --user-agent AlibabaCloud-Agent-Skills
```

Why correct:
- `cycle-symlink`, `upload-speed`, `download-speed`, `download-time` are documented valid values
- `download-speed` and `download-time` provide bucket and object
- `--parallel` and `--part-size` are used on `download-time`

#### INCORRECT
```bash
aliyun ossutil probe --probe-item symlink-check "/data/links" --user-agent AlibabaCloud-Agent-Skills
aliyun ossutil probe --probe-item download-speed --bucket "examplebucket" --user-agent AlibabaCloud-Agent-Skills
aliyun ossutil probe --probe-item upload-speed --bucket "examplebucket" --parallel 3 --user-agent AlibabaCloud-Agent-Skills
```

Why incorrect:
- `symlink-check` is not a valid enum value
- `download-speed` requires `--object`
- `--parallel` is only meaningful for `download-time` in this documented workflow

## 6. Supporting command patterns

#### CORRECT
```bash
aliyun ossutil stat "oss://examplebucket/big/test.bin" --user-agent AlibabaCloud-Agent-Skills
aliyun ossutil presign "oss://examplebucket/private/test.bin" --expires-duration 1h --user-agent AlibabaCloud-Agent-Skills
aliyun ossutil cp "/tmp/test.bin" "oss://examplebucket/probe/test.bin" --user-agent AlibabaCloud-Agent-Skills
aliyun ossutil rm "oss://examplebucket/probe/test.bin" --user-agent AlibabaCloud-Agent-Skills
```

Why correct:
- All commands exist in `aliyun ossutil`
- Positional arguments and flags follow the CLI help

#### INCORRECT
```bash
aliyun ossutil stat --bucket examplebucket --object big/test.bin --user-agent AlibabaCloud-Agent-Skills
aliyun ossutil presign --bucket examplebucket --object private/test.bin --user-agent AlibabaCloud-Agent-Skills
aliyun ossutil ls --bucket examplebucket --user-agent AlibabaCloud-Agent-Skills
aliyun oss api GetBucketLocation --bucket examplebucket
```

Why incorrect:
- `stat` and `presign` use `oss://bucket/object` positional targets, not `--bucket` / `--object` flags
- `ossutil ls --bucket ...` is not the documented CLI shape
- `aliyun oss api ...` / `GetBucketLocation` is outside this skill's accepted command patterns

---

# Correct Common SDK Code Patterns (if applicable)

This skill uses `aliyun ossutil` as its primary tool; the current workflow does not require a Python Common SDK implementation.

#### CORRECT
- Clearly state that this scenario is powered by `aliyun ossutil probe`
- If supplementary scripts are needed, they should only wrap CLI invocations, parse output, and organize logs; do not fabricate a non-existent OSS OpenAPI `probe`

#### INCORRECT
```python
# Non-existent OSS OpenAPI example
client.probe_state(bucket='examplebucket')
```

Why incorrect:
- There is no documented OSS OpenAPI named `probe` or `probe_state` that can replace `ossutil probe`

---

# Success Output Expectations

#### CORRECT
- Upload probe output contains `upload file:success`
- Download probe output contains `download file:success`
- Bandwidth probe output contains `suggest parallel is <N>`
- Download time probe output contains `total bytes`, `cost`, `avg speed`
- After probe execution, `report log file:` or a local `logOssProbe*.log` file should be present

#### INCORRECT
- Only CLI help output is shown without actual probe results
- After an error, still claiming the probe succeeded, or describing a failure as "task completed successfully"
- Retaining or deleting user test objects without confirmation
- Writing the full presigned URL, STS token, or local credential file contents in logs or the final answer
- After `NoSuchBucket` / `AccessDenied`, enumerating unconfirmed regions, buckets, or endpoints and drawing conclusions from them
- In a `cycle-symlink` scenario, writing a complete cyclic chain as verified fact when supplementary forensics did not actually read a particular segment's target

---

# Boundary Acceptance Criteria

#### CORRECT
- Clearly state that `cycle-symlink` can only detect, not auto-fix
- Clearly state that `download-speed` requires an existing object; if none exists, a test object must be confirmed and uploaded first
- Clearly state that `probe` is a composite client-side command, not a standalone OpenAPI

#### INCORRECT
- Claiming the same workflow can be achieved via `aliyun oss api probe`
- Claiming all symlink anomalies can be auto-fixed
- Auto-creating and permanently retaining test objects without user confirmation
