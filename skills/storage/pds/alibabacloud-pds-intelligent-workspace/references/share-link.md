# File Sharing (Share Link)

## Overview

The file sharing feature allows users to create share links for files/folders in personal drives or team drives, supporting cross-organization sharing with external users. It supports access passwords, expiration periods, and permission controls (preview/download/upload/edit).

## Prerequisites

1. PDS configuration is complete (domain_id, user_id, authentication-type). See `references/config.md`.
2. **A super administrator or drive administrator has enabled the sharing feature**: Admin Console > Security Policy > Share Settings Management > Enable "Share Settings".

> **Important Notes**:
> - A maximum of 500 share creations and 500 share accesses are supported per day.
> - If a share link does not have "Only accessible by enterprise users" enabled, APK and IPA files are prohibited from downloading (to lift this restriction, an administrator must complete custom domain configuration).
> - After the administrator enables share settings, if the share button does not appear in the user interface, refresh the webpage or restart the client.

---

## Workflow

### Before Creating a Share: Resolve the Target File

Creating a share requires first confirming the target drive's `drive_id`. Sharing regular files/folders also requires obtaining the `file_id` of the object to share; when sharing an entire drive, use `--share-all-files true` and do not resolve or pass `--file-id-list`.

- If the user has already provided `drive_id` and `file_id`, proceed directly to creating the share.
- If the user explicitly requests to share an entire drive, first obtain the `drive_id`, then create the share using `--share-all-files true` without passing `--file-id-list`.
- If the user provides a drive name, file name, or cloud path, resolve in the following order:
  1. Read `references/drive.md` to identify the target drive and obtain the `drive_id`.
  2. Read `references/search-file.md` to search for the target file/folder by name or path and obtain the `file_id`.
  3. If multiple candidates are found, present the candidates' paths, types, and update times to the user and ask for confirmation.
  4. If the target file/folder is not found, stop creating the share and inform the user that the target object cannot be located.

Do not guess `file_id` from file names, and do not create a share without confirming a unique target object.

### Creating a Share

After confirming the `drive_id`, choose `--file-id-list` or `--share-all-files true` based on the target type, then create the share link:

```bash
aliyun pds create-share-link \
  --drive-id <drive_id> \
  --file-id-list <file_id_1> <file_id_2> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pds-intelligent-workspace
```

**Expiration Time Rules**:

- Only pass `--expiration` when the user explicitly requests the share to expire at a certain time.
- If the user explicitly states "expire after N days" (e.g., "expire after 7 days"), add the corresponding number of days to the current system time and convert to RFC 3339 format, e.g., `2026-05-28T15:04:05.000+08:00`.
- If the user explicitly provides a specific date or time, convert it to RFC 3339 format and use it as `--expiration`.
- If the user does not explicitly specify an expiration time, do not pass `--expiration`, meaning the share link never expires.

**Parameter Reference**:

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--drive-id` | Yes | Drive ID |
| `--file-id-list` | Conditionally required | List of file IDs to share (1-100 items); not effective when `share-all-files` is true |
| `--share-all-files` | No | Whether to share all files in the entire drive |
| `--share-name` | No | Share name; defaults to the first file name; maximum 128 characters |
| `--share-pwd` | No | Access password (extraction code), 0-64 bytes; leave empty for password-free access |
| `--expiration` | No | Expiration time in RFC 3339 format; do not pass this parameter when the user has not explicitly specified an expiration time, meaning the share never expires |
| `--disable-preview` | No | Whether to disable preview |
| `--disable-download` | No | Whether to disable download |
| `--disable-save` | No | Whether to disable save-to-drive |
| `--preview-limit` | No | Preview count limit; 0 means unlimited |
| `--download-limit` | No | Download count limit; 0 means unlimited |
| `--save-limit` | No | Save-to-drive count limit; 0 means unlimited |
| `--creatable` | No | Whether to allow uploading files to the shared folder; requires specifying `creatable-file-id-list` simultaneously |
| `--creatable-file-id-list` | No | List of folder IDs that allow uploads |
| `--office-editable` | No | Whether to allow online document editing |
| `--require-login` | No | Whether to restrict access to logged-in users only |
| `--description` | No | Share description/message; maximum 1024 characters |
| `--user-id` | No | User ID |

**Response Example**:
```json
{
  "share_id": "<share_id>",
  "share_url": "",
  "share_pwd": "<share_pwd>",
  "share_name": "<share_name>",
  "expiration": "<RFC3339_expiration>",
  "created_at": "<RFC3339_created_at>"
}
```

**Post-processing Before Returning to User**:

- After creating the share, first check the `share_url` returned by `create-share-link`.
- If `share_url` is non-empty, return that URL directly to the user by default.
- If `share_url` is empty, first obtain the `share_id`, `share_pwd`, and `domain_id`, then query whether the current domain has a custom domain configured:
  ```bash
  aliyun pds get-domain \
    --domain-id <domain_id> \
    --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pds-intelligent-workspace
  ```
- Determine `<share_host>`:
  - If the `get-domain` response contains a non-empty `endpoints.app_endpoint`, use that value as the custom domain; if the value includes an `http://` or `https://` prefix, strip the protocol prefix first.
  - If the `endpoints` object does not exist, or `endpoints` does not contain an `app_endpoint` field, or `app_endpoint` is empty, it means no custom domain is configured; use the default domain `<domain_id>.apps.aliyunfile.com`.
- When `share_url` is empty, assemble and return the share URL according to the following rules:
  - With a share password: `https://<share_host>/disk/s/<share_id>?pwd=<share_pwd>&domainId=<domain_id>`.
  - If `<share_pwd>` is empty, do not include the `pwd` parameter: `https://<share_host>/disk/s/<share_id>?domainId=<domain_id>`.
- `<domain_id>` uses the user-provided or currently configured PDS domain ID; `<share_id>` uses the `share_id` returned from the create-share response; `<share_pwd>` uses the share password set or returned during share creation.

---

### Listing Shares

List all shares created by the current user:

```bash
aliyun pds list-share-link \
  --limit 20 \
  --order-by created_at \
  --order-direction DESC \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pds-intelligent-workspace
```

**Parameter Reference**:

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--creator` | No | Creator user ID |
| `--include-cancelled` | No | Whether to include cancelled shares |
| `--limit` | No | Maximum number of results per page, 0-100 |
| `--marker` | No | Pagination marker; do not pass on the first request |
| `--order-by` | No | Sort field: `created_at` (default), `updated_at`, `share_name`, `description` |
| `--order-direction` | No | Sort direction: `ASC` / `DESC` |

**Pagination Handling**:

If the response contains a non-empty `next_marker`, there is more data on the next page. Continue executing the same `list-share-link` command with the returned `next_marker` as the `--marker` parameter for the next request, until `next_marker` is empty. When counting, filtering, or batch-processing shares, all pages must be traversed first.

---

### Searching Shares

Search share links by conditions (supports fuzzy name search, filtering by status/time):

```bash
aliyun pds search-share-link \
  --query "share_name_for_fuzzy = '<share_name_keyword>'" \
  --limit 50 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pds-intelligent-workspace
```

**Parameter Reference**:

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--query` | No | Search condition; supported fields: `created_at`, `updated_at`, `share_name_for_fuzzy`, `status` (enabled/disabled), `expired_time` |
| `--creators` | No | List of creator IDs (administrators can query all users) |
| `--limit` | No | Maximum number of results per page, 1-100, default 100 |
| `--marker` | No | Pagination marker |
| `--order-by` | No | Sort field |
| `--order-direction` | No | Sort direction |
| `--return-total-count` | No | Whether to return the total count |

**Pagination Handling**:

If the response contains a non-empty `next_marker`, there is more data on the next page. Continue executing the same `search-share-link` command with the returned `next_marker` as the `--marker` parameter for the next request, until `next_marker` is empty. When counting, filtering, or batch-processing shares, all pages must be traversed first.

---

### Viewing Share Details

Query detailed information about a share link by share_id:

```bash
aliyun pds get-share-link \
  --share-id <share_id> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pds-intelligent-workspace
```

---

### Modifying Share Settings

Modify permissions, password, expiration, etc. for an existing share. Only pass fields that the user explicitly requests to modify; do not pass fields that were not requested for modification:

```bash
aliyun pds update-share-link \
  --share-id <share_id> \
  --<requested-field> <value> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pds-intelligent-workspace
```

**Parameter Reference**:

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--share-id` | Yes | Share ID |
| `--share-name` | No | Modify share name |
| `--share-pwd` | No | Modify access password |
| `--expiration` | No | Modify expiration time; calculate according to the expiration time rules for creating shares; do not modify this field when the user has not explicitly specified an expiration time |
| `--description` | No | Modify description |
| `--disable-preview` | No | Whether to disable preview |
| `--disable-download` | No | Whether to disable download |
| `--disable-save` | No | Whether to disable save-to-drive |
| `--office-editable` | No | Whether to allow online editing |
| `--preview-limit` | No | Preview count limit |
| `--download-limit` | No | Download count limit |
| `--save-limit` | No | Save-to-drive count limit |
| `--status` | No | Share status: `enabled` (active) / `disabled` (cancelled) |

---

### Cancelling a Share

Cancel (delete) a share link:

```bash
aliyun pds cancel-share-link \
  --share-id <share_id> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pds-intelligent-workspace
```

Once cancelled, the share link becomes immediately invalid and recipients can no longer access it.

---

### Anonymous Share Access (Optional)

#### Anonymously Get Share Information

View basic information about a share without logging in:

```bash
aliyun pds get-share-link-by-anonymous \
  --share-id <share_id> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pds-intelligent-workspace
```

#### Get Share Token

Obtain an access token using the share ID and extraction code:

```bash
aliyun pds get-share-link-token \
  --share-id <share_id> \
  --share-pwd <share_pwd> \
  --expire-sec 7200 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pds-intelligent-workspace
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--share-id` | Yes | Share ID |
| `--share-pwd` | No | Access password (required when the share has a password set) |
| `--expire-sec` | No | Token validity period; range (0, 7200], default 7200 seconds |

---

## Common Scenarios

### Create a Password-Free, Never-Expiring Share

```bash
aliyun pds create-share-link \
  --drive-id <drive_id> \
  --file-id-list <file_id> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pds-intelligent-workspace
```

### Create a Password-Protected, 7-Day, Preview-Only Share

```bash
aliyun pds create-share-link \
  --drive-id <drive_id> \
  --file-id-list <file_id> \
  --share-pwd "<share_pwd>" \
  --expiration "<current_time_plus_7_days_rfc3339>" \
  --disable-download true \
  --disable-save true \
  --require-login true \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pds-intelligent-workspace
```

### Create a Share That Allows External Users to Upload Files

```bash
aliyun pds create-share-link \
  --drive-id <drive_id> \
  --file-id-list <folder_id> \
  --creatable true \
  --creatable-file-id-list <folder_id> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pds-intelligent-workspace
```

---

## CLI Command Quick Reference

| CLI Command | Description | Required Parameters |
|-------------|-------------|---------------------|
| `aliyun pds create-share-link` | Create a share link | `--drive-id` |
| `aliyun pds cancel-share-link` | Cancel a share link | `--share-id` |
| `aliyun pds get-share-link` | Query share details | `--share-id` |
| `aliyun pds list-share-link` | List shares | None |
| `aliyun pds search-share-link` | Search shares | None |
| `aliyun pds update-share-link` | Modify share settings | `--share-id` |
| `aliyun pds get-share-link-by-anonymous` | Anonymously get share information | `--share-id` |
| `aliyun pds get-share-link-token` | Get share access token | `--share-id` |

**Note**: All commands must include `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-pds-intelligent-workspace`

---

## Error Handling

| Error Scenario | Possible Cause | Solution |
|----------------|----------------|----------|
| Share creation failed | Administrator has not enabled the sharing feature | Contact the administrator to enable it in "Security Policy > Share Settings Management" |
| Cannot select "Allow editing" | Administrator has not enabled "Share Online Editing" | Contact the administrator to enable it, then restart the client |
| Daily limit exceeded | More than 500 share creations/accesses in a single day | Wait until the next day, or contact the administrator to configure a custom domain to lift the restriction |
| Cannot download APK/IPA | Not supported for share access; requires login-only access | Set `--require-login true` or have the administrator configure a custom domain |
| Share link inaccessible | Share has expired/been cancelled/file has been deleted | Contact the share creator to create a new share |

---

## Best Practices

1. Always set an access password and expiration period when sharing sensitive files.
2. Use `--require-login true` to restrict access to logged-in users only, improving security.
3. Use `--preview-limit` / `--download-limit` to limit operation counts and prevent abuse.
4. Periodically clean up shares with `disabled` status:

   First search for share links with `disabled` status, traversing all pages following pagination rules:

   ```bash
   aliyun pds search-share-link \
     --query "status = 'disabled'" \
     --limit 100 \
     --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pds-intelligent-workspace
   ```

   For each `share_id` confirmed for cleanup, execute cancel-share:

   ```bash
   aliyun pds cancel-share-link \
     --share-id <share_id> \
     --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pds-intelligent-workspace
   ```

5. Confirm the file ID is correct before creating a share (use `references/search-file.md` to search for files and obtain the file_id).
