# PDS Archive Download Guide

**Scenario**: Download multiple files/folders from PDS as a single zip archive.

Archiving is done in **one CLI call** — `aliyun pds archive-download`. The command creates the archive task, polls it to completion, and downloads the result to a local file (with size verification). You do **not** poll manually or run any Python script.

---

## Prerequisites & limits

- Archive download is a paid add-on; it must be enabled for the domain.
- You need read/download permission on all files to be archived.
- zip only. Max 500 top-level files (10,000 after recursion), 10 GB total.

---

## Command

```bash
aliyun pds archive-download \
  --drive-id <DRIVE_ID> \
  --paths <ABSOLUTE_PATH_1> <ABSOLUTE_PATH_2> ... \
  --name <ARCHIVE_NAME>.zip \
  --save-to <LOCAL_PATH>.zip \
  [--max-attempts 60] \
  [--poll-interval 5]
```

| Flag | Description |
|------|-------------|
| `--drive-id` | Drive where the files live. |
| `--paths` / `--file-ids` | Exactly one. Space-separated absolute cloud paths or file/folder IDs (1–500); paths are resolved internally. **Not** JSON array format. |
| `--name` | Archive name, must end with `.zip`. |
| `--save-to` | Local path to save the downloaded zip. |
| `--max-attempts` | Max polling attempts (default 60). |
| `--poll-interval` | Seconds between polls (default 5, range 1–300). |

**On success** returns: `{ "async_task_id": ..., "local_path": ..., "name": ..., "size": <bytes> }`.

The command handles create → poll (`Running`→`Succeed`) → download → size check internally. On `Failed` it returns the task's error message.

---

## Example

```bash
aliyun pds archive-download \
  --drive-id drive123 \
  --paths "/Project/spec.pdf" "/Project/assets" \
  --name project_files.zip \
  --save-to ./project_files.zip
```

---

## Error handling

- **Failed task**: the returned error carries the `message` (size limit exceeded, too many files, permission denied, feature not enabled).
- **Timeout** (max attempts reached): the archive may still be building — re-run the command (a new task is created) or increase `--max-attempts`.
- **OperationNotSupport**: the domain doesn't have archive download enabled — contact PDS support.
