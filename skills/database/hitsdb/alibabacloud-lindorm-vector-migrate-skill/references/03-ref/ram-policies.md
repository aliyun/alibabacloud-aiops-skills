# RAM Permissions Reference

This Skill does not use Alibaba Cloud POP APIs or platform-managed credentials. All cloud service access uses user-provided AK/SK via environment variables. This document lists the minimum RAM permission set users must grant to their AccessKey for each service.

---

## OSS (Object Storage Service)

Used by: CSV import flow (`csv-import.md`) — reading CSV files from OSS for vector data import.

### Minimum Required Permissions

| Permission | Used By | Purpose |
|------------|---------|---------|
| `oss:GetObject` | `bucket.get_object(object_key)` | Stream-read CSV file content |
| `oss:GetObjectMeta` | `bucket.get_object_meta(object_key)` | Pre-check: verify file exists and get file size |

### Recommended RAM Policy

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "oss:GetObject",
        "oss:GetObjectMeta"
      ],
      "Resource": "acs:oss:*:*:<bucket-name>/<object-prefix>*"
    }
  ]
}
```

- Replace `<bucket-name>` with the actual OSS bucket name.
- Replace `<object-prefix>` with the object key prefix to scope access (e.g., `csv-exports/`). Use `*` to allow access to all objects in the bucket.

### Notes

- This Skill only performs **read operations** on OSS; no write, delete, or list permissions are required.
- Credentials are read from environment variables `OSS_ACCESS_KEY_ID` and `OSS_ACCESS_KEY_SECRET`; they are never written into generated scripts.
- CSV export (`csv-export.md`) writes to a **local file**; OSS upload is done by the user outside this Skill.
