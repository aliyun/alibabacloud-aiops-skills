# Related APIs and Commands: alibabacloud-oss-manage-network-probe

## Overview

`aliyun ossutil probe` is a composite client-side diagnostic command.
It is not a single OSS OpenAPI, but rather a combination of local diagnostic logic and a set of OSS data access capabilities.
Therefore, this table lists:

1. The actual Alibaba Cloud CLI commands executed
2. The related underlying OSS capabilities or local behaviors
3. Minimum permission or constraint notes

## Command and Capability Table

| Workflow Step | CLI Command | Underlying OSS capability / local behavior | Minimum RAM action / permission | Notes |
| --- | --- | --- | --- | --- |
| CLI version check | `aliyun version` | Local CLI behavior | None | Verifies CLI version >= 3.3.3 |
| Enable auto plugin install | `aliyun configure set --auto-plugin-install true` | Local CLI behavior | None | Not a cloud OpenAPI |
| Enable AI safety mode | `aliyun configure ai-mode enable` | Local CLI behavior | None | Enables safety mode; dangerous operations are blocked |
| Credential gate | `aliyun configure list` | Local CLI behavior | None | Only checks whether the local profile is valid |
| Integrated ossutil check | `aliyun ossutil version` | Local CLI behavior | None | Verifies `ossutil 2.0` is integrated |
| Upload connectivity probe | `aliyun ossutil probe --upload --bucket <bucket> [<local_file>] --user-agent AlibabaCloud-Agent-Skills` | Composite probe using upload workflow and optional temporary object cleanup | Documented minimum: `oss:GetObject`, `oss:PutObject`, `oss:DeleteObject` | `--upmode` accepts `normal` / `append` / `multipart` |
| Download connectivity probe by URL | `aliyun ossutil probe --download --url "<http_url>" [<local_path>] --user-agent AlibabaCloud-Agent-Skills` | Download via HTTP/HTTPS URL | `oss:GetObject` when the URL points to an OSS object | Private objects require a presigned URL first |
| Download connectivity probe by bucket/object | `aliyun ossutil probe --download --bucket <bucket> [--object <object>] [<local_path>] --user-agent AlibabaCloud-Agent-Skills` | `GetObject`; if `--object` is omitted, probe creates and deletes a temporary object | With explicit object: `oss:GetObject`; with temporary object workflow: `oss:GetObject`, `oss:PutObject`, `oss:DeleteObject` | Suitable for directly verifying Bucket/Object paths |
| Symlink detection | `aliyun ossutil probe --probe-item cycle-symlink <local_path> --user-agent AlibabaCloud-Agent-Skills` | Local filesystem inspection only | None | Does not access OSS |
| Upload bandwidth probe | `aliyun ossutil probe --probe-item upload-speed --bucket <bucket> --user-agent AlibabaCloud-Agent-Skills` | Repeated upload diagnostics plus concurrency recommendation | Documented minimum: `oss:GetObject`, `oss:PutObject`, `oss:DeleteObject` | Outputs `suggest parallel is <N>` |
| Download bandwidth probe | `aliyun ossutil probe --probe-item download-speed --bucket <bucket> --object <object> --user-agent AlibabaCloud-Agent-Skills` | Repeated download diagnostics plus concurrency recommendation | `oss:GetObject` | Official recommendation: object larger than 5 MiB |
| Download time probe | `aliyun ossutil probe --probe-item download-time --bucket <bucket> --object <object> --user-agent AlibabaCloud-Agent-Skills` | Timed download with optional part size and parallelism | `oss:GetObject` | `--parallel` / `--part-size` only valid for this mode |
| Optional prep upload | `aliyun ossutil cp "<local_file>" "oss://<bucket>/<object>" --user-agent AlibabaCloud-Agent-Skills` | Upload local file to OSS | `oss:PutObject` | Prepares test objects for `download-speed` |
| Optional presigned URL | `aliyun ossutil presign "oss://<bucket>/<object>" --expires-duration 1h --user-agent AlibabaCloud-Agent-Skills` | Local signing for a specific OSS object URL | Usually no additional OSS call for a single object URL | May require `oss:ListObjects` for recursive/batch URL generation |
| Optional cleanup | `aliyun ossutil rm "oss://<bucket>/<object>" --user-agent AlibabaCloud-Agent-Skills` | Delete probe object | `oss:DeleteObject` | Only used when the user confirms deletion of explicitly created test objects |

## Important Notes

1. `probe` is not a command under `aliyun oss api`; do not write `aliyun oss api probe`.
2. `--url` mode only accepts HTTP/HTTPS URLs; it cannot take `oss://bucket/object`.
3. `cycle-symlink` has no cloud API counterpart; it performs local filesystem inspection.
4. `--user-agent AlibabaCloud-Agent-Skills` must be added only to API-calling commands (e.g., `probe`, `cp`, `presign`, `rm`). Local CLI commands (`aliyun version`, `aliyun configure ...`, `aliyun ossutil version`) do not support this flag.
5. For API-calling commands, `--user-agent` is passed as a trailing flag after all other arguments.

## Validated Command Set

The following commands have been validated against their help output during skill generation:

- `aliyun version`
- `aliyun configure list`
- `aliyun configure set --auto-plugin-install true`
- `aliyun configure ai-mode enable`
- `aliyun ossutil version`
- `aliyun ossutil probe --help --user-agent AlibabaCloud-Agent-Skills`
- `aliyun ossutil cp --help --user-agent AlibabaCloud-Agent-Skills`
- `aliyun ossutil presign --help --user-agent AlibabaCloud-Agent-Skills`
- `aliyun ossutil rm --help --user-agent AlibabaCloud-Agent-Skills`
