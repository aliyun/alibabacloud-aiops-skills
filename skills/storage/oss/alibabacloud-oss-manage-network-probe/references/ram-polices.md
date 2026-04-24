# RAM Policies: alibabacloud-oss-manage-network-probe

## Overview

The minimum permission set for this skill depends on the probe mode.
`aliyun ossutil probe` may directly access existing objects, or temporarily upload and delete objects for diagnostics.
Therefore, permissions should be granted per scenario at the minimum required level, rather than granting `oss:*`.

## Scenario Permission Matrix

| Scenario | Required RAM actions | Why |
| --- | --- | --- |
| CLI version / local config check | None | Local CLI behavior only |
| `probe --probe-item cycle-symlink <local_path>` | None | Local symlink check only |
| `probe --download --url <signed_or_public_url>` | `oss:GetObject` | Downloads OSS object content |
| `probe --download --bucket <bucket> --object <object>` | `oss:GetObject` | Downloads the specified object |
| `probe --download --bucket <bucket>` with temporary object | `oss:GetObject`, `oss:PutObject`, `oss:DeleteObject` | Creates a temporary object, downloads it, then cleans up |
| `probe --upload --bucket <bucket>` | `oss:GetObject`, `oss:PutObject`, `oss:DeleteObject` | Official docs require these three for upload bandwidth/upload probe |
| `probe --probe-item upload-speed --bucket <bucket>` | `oss:GetObject`, `oss:PutObject`, `oss:DeleteObject` | Repeatedly uploads for diagnostics and cleans up test objects |
| `probe --probe-item download-speed --bucket <bucket> --object <object>` | `oss:GetObject` | Repeatedly downloads the object and measures throughput |
| `probe --probe-item download-time --bucket <bucket> --object <object>` | `oss:GetObject` | Downloads and calculates elapsed time |
| `ossutil cp <local_file> oss://<bucket>/<object>` | `oss:PutObject` | Prepares test objects |
| `ossutil rm oss://<bucket>/<object>` | `oss:DeleteObject` | Cleans up explicitly created test objects |
| `ossutil stat oss://<bucket>/<object>` | `oss:GetObject` | Views object metadata |
| `ossutil ls oss://<bucket>/<prefix>` | `oss:ListObjects` | Lists objects to confirm paths |
| `ossutil presign oss://<bucket>/<object>` | Usually none extra for single object; `oss:ListObjects` if recursive/batch | Local signing; listing is required for recursive operations |

## Least-Privilege Recommendations

1. For symlink detection only, do not grant any OSS data permissions.
2. For download-only probes, prefer granting only `oss:GetObject`.
3. Only add `oss:PutObject` and `oss:DeleteObject` for upload probes, upload bandwidth probes, or temporary-object download probes.
4. Only add `oss:ListObjects` when object listing or recursive processing is needed.
5. If the test object is a user-specified business object, grant delete permission cautiously and confirm the cleanup strategy first.

## Summary Table by Product

| Product | RAM Action | Resource Scope | Description |
| --- | --- | --- | --- |
| OSS | `oss:GetObject` | `acs:oss:*:*:<bucket>/<object-or-prefix>` or `*` | Download objects, read object content, partial probe workflows |
| OSS | `oss:PutObject` | `acs:oss:*:*:<bucket>/<object-or-prefix>` or `*` | Upload probes, prepare test objects, create temporary objects |
| OSS | `oss:DeleteObject` | `acs:oss:*:*:<bucket>/<object-or-prefix>` or `*` | Delete explicit test objects or temporary objects |
| OSS | `oss:ListObjects` | `acs:oss:*:*:<bucket>` or `*` | List objects, recursive presign, or path confirmation |

## Example Policy: download-only probing

Applicable to:
- `aliyun ossutil probe --download --bucket <bucket> --object <object> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-oss-manage-network-probe`
- `aliyun ossutil probe --probe-item download-speed --bucket <bucket> --object <object> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-oss-manage-network-probe`
- `aliyun ossutil probe --probe-item download-time --bucket <bucket> --object <object> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-oss-manage-network-probe`

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "oss:GetObject"
      ],
      "Resource": "*"
    }
  ]
}
```

## Example Policy: upload / temporary-object probing

Applicable to:
- `aliyun ossutil probe --upload --bucket <bucket> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-oss-manage-network-probe`
- `aliyun ossutil probe --probe-item upload-speed --bucket <bucket> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-oss-manage-network-probe`
- `aliyun ossutil probe --download --bucket <bucket> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-oss-manage-network-probe` without explicit object

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "oss:GetObject",
        "oss:PutObject",
        "oss:DeleteObject"
      ],
      "Resource": "*"
    }
  ]
}
```

## Example Policy: full troubleshooting workflow

Applicable to:
- Listing objects to confirm paths
- Pre-uploading test objects
- Download bandwidth testing
- Cleaning up objects after completion

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "oss:GetObject",
        "oss:PutObject",
        "oss:DeleteObject",
        "oss:ListObjects"
      ],
      "Resource": "*"
    }
  ]
}
```

## Notes

- Official `probe` documentation states: upload bandwidth probing requires at minimum `oss:GetObject`, `oss:PutObject`, `oss:DeleteObject`; download bandwidth probing requires at minimum `oss:GetObject`.
- The `configure list`, `configure set --auto-plugin-install true`, `configure ai-mode enable`, and `version` commands in this skill are all local CLI operations and do not correspond to RAM permissions.
- If the user requires stricter resource scoping, narrow the `Resource` from `*` to specific bucket/object ARN ranges.
