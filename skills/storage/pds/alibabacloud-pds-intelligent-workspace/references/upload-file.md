# PDS File Upload Guide

> The common upload (into a folder by id, into a cloud path with `--create-missing`, or overwrite) is covered inline in `SKILL.md` — you usually don't need this file. Read on for the full parameter table and edge cases.

**Scenario**: When you have obtained the target drive_id and directory file_id and need to upload files to PDS drive
**Purpose**: Upload local files to PDS drive (supports enterprise space, team space, personal space)

---

## File Upload Command

Use the `aliyun pds upload-file` command to directly upload local files to PDS. It automatically completes create → upload → complete, and handles rapid (instant) upload and multipart part sizing internally.

```bash
aliyun pds upload-file \
  --drive-id <drive_id> \
  --local-path <local_file_path> \
  --parent-file-id <parent_file_id> \
  --name <cloud_file_name> \
  --check-name-mode <auto_rename|ignore|refuse>
```

---

## Parameter Description

| Parameter | Type | Required | Description |
|------|------|------|------|
| `--drive-id` | string | Yes | Target space ID (obtained from space list) |
| `--local-path` | string | Yes | Full path to local file |
| `--parent-file-id` | string | No | Parent directory ID, default is `root`. Ignored when `--file-id`/`--path` (overwrite) is set. |
| `--parent-path` | string | No | Cloud **directory** path to upload into (e.g. `/Photos/2026/04`). The command resolves it to `parent_file_id` internally — no need to run `resolve-path` or parse its output. Alternative to `--parent-file-id`. |
| `--create-missing` | bool | No | When resolving `--parent-path`, create any missing folders along the way. |
| `--name` | string | No | Cloud file name, defaults to local file name |
| `--file-id` | string | No | **Overwrite upload**: the `file_id` of an existing file to replace. When set, the command overwrites that file's content in place (a new revision) instead of creating a new file. Omit it for a normal new-file upload. |
| `--path` | string | No | **Overwrite upload by path**: the cloud path of an existing file to replace. Resolved to its `file_id` internally. Alternative to `--file-id` (do not set both). |
| `--check-name-mode` | string | No | Name conflict handling mode: `ignore` (allow a same-name file to coexist — does **not** overwrite), `auto_rename` (auto rename, appends a timestamp), `refuse` (reject and return the existing file), default is `ignore`. Only relevant for new-file uploads (no `--file-id`/`--path`). |

Rapid (instant) upload and multipart part sizing are automatic — you do not need to configure them:
- **Rapid upload** is on by default (SHA-1 is computed to complete instantly if an identical file already exists). Pass `--disable-rapid-upload` only if you explicitly want to skip it.
- **Part size** is chosen automatically (4MB, or 8MB for files larger than 1GB). Override with `--part-size <bytes>` only in special cases.

---

## Common Examples

### Basic Upload

Upload to root directory using local file name:

```bash
aliyun pds upload-file \
  --drive-id "100" \
  --local-path "/path/to/file.jpg"
```

### Specify Directory and File Name

Upload to specified directory with custom cloud file name:

```bash
aliyun pds upload-file \
  --drive-id "100" \
  --local-path "/path/to/file.jpg" \
  --parent-file-id "root" \
  --name "my-photo.jpg" \
  --check-name-mode "auto_rename"
```

### Upload File to a Directory Path

To upload into a directory path (e.g., `/Photos/2026/04`), just pass `--parent-path` — the command resolves it to `parent_file_id` internally, in **one command** (no `resolve-path`, no JSON parsing, no extra tools). Add `--create-missing true` to create any missing folders along the way:

```bash
aliyun pds upload-file \
  --drive-id <drive_id> \
  --local-path "/path/to/file.jpg" \
  --parent-path "/Photos/2026/04" \
  --create-missing true
```

When you already have the directory's `parent_file_id`, pass it to `--parent-file-id` directly instead.

### Overwrite an Existing File (Overwrite Upload)

PDS **does** support overwrite upload. Provide the existing file — either its `--file-id`, or its cloud path via `--path` (resolved to the `file_id` internally) — and the command replaces that file's content in place (a new revision) instead of adding a new file. `--parent-file-id` / `--check-name-mode` are not needed.

```bash
# Overwrite by known file_id
aliyun pds upload-file \
  --drive-id <drive_id> \
  --local-path "/path/to/new-content.jpg" \
  --file-id <existing_file_id>

# Overwrite by cloud path (the file must already exist)
aliyun pds upload-file \
  --drive-id <drive_id> \
  --local-path "/path/to/new-content.jpg" \
  --path "/Photos/2026/04/vacation.jpg"
```

**To overwrite, name the target directly — don't fish for it with `--check-name-mode`.** If you know the cloud path, pass `--path` (it resolves to the `file_id` for you); if you already have the `file_id`, pass `--file-id`. Both replace the content in place in **one** command. Do **not** try to force an overwrite by re-uploading with different `--check-name-mode` values (`refuse`→`ignore`→…): `check-name-mode` only governs *new-file* naming and will never overwrite — that path just creates duplicates or wastes round-trips. If you don't yet have the path or id, resolve it once (`resolve-path`, or a `search-file`/`list-file` lookup) and then overwrite by `--file-id`.

---

## Output Description

On success the command prints **a single JSON object to stdout** (progress messages go to stderr, so stdout stays clean and parseable). The **rapid-upload** path and the normal **multipart** path return the **same set of fields** — field names are unified (there is always `name`, never `file_name`) and any value the server omits is filled from the upload's local metadata:

- `file_id`: Unique file ID
- `name`: Cloud file name (always `name`, unified across both paths)
- `drive_id`: Target drive ID
- `parent_file_id`: Parent directory ID
- `size`: File size in bytes
- `type`: Always `file`
- `rapid_upload`: `true` if the file was instant-uploaded (already existed in the domain), otherwise `false`

The multipart path additionally surfaces server-only metadata when present, e.g. `created_at`, `updated_at`, `content_hash`, `revision_id`.

Example:

```json
{
  "file_id": "66e7...974e",
  "name": "my-photo.jpg",
  "drive_id": "100",
  "parent_file_id": "root",
  "size": 20480,
  "type": "file",
  "rapid_upload": false
}
```

---

## Notes

1. **New file vs overwrite**:
   - **New-file upload** (no `--file-id`): `--check-name-mode` controls same-name handling. `ignore` (the default) lets a new file coexist with an existing same-name file (it does **not** overwrite); `auto_rename` appends a timestamp to keep names unique; `refuse` rejects when a same-name file already exists.
   - **Overwrite upload** (with `--file-id`): PDS **does** support replacing an existing file's content in place — pass the target file's `--file-id` and the command overwrites it (new revision) rather than creating a new file. See the "Overwrite an Existing File" example above.
2. **Rapid upload & multipart**: Handled automatically by the command (rapid upload on by default; part size auto-selected, 8MB for files >1GB). No configuration needed.
3. **Network stability**: Ensure stable network when uploading large files to avoid interruptions