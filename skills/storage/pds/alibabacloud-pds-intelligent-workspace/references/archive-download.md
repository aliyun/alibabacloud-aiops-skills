# PDS Archive Download Guide

**Scenario**: When you need to download multiple files/folders as a single zip archive from PDS
**Purpose**: Package multiple files into one zip file and download it

---

## Prerequisites

- The archive download feature must be enabled for the PDS domain (it's a paid add-on feature)
- You need read and download permissions on all files to be archived
- You must have the `drive_id` and `file_id` list of the files to archive

## Limitations

- Archive format: only zip is supported
- Maximum 500 files in the top-level file list; maximum 10,000 files after recursive traversal
- Maximum total file size: 10GB

---

## Step 1: Create Archive Task

Create an archive download task using the `aliyun pds archive-files` command:

```bash
aliyun pds archive-files \
  --drive-id <drive_id> \
  --name "<archive_name>.zip" \
  --file-ids <file_id_1> <file_id_2> <file_id_3> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pds-intelligent-workspace
```

**Parameter Description**:
- `--drive-id`: The drive_id of the space where the files are located
- `--name`: Name for the generated zip archive (must end with `.zip`)
- `--file-ids`: Space-separated list of file IDs to be archived (supports files and folders). Do NOT use JSON array format.

**Output**: Returns a JSON object containing `async_task_id`:

```json
{
  "async_task_id": "testAsyncTaskId"
}
```

**Note**: The HTTP response code is 202, indicating the task has been accepted and is being processed asynchronously.

---

## Step 2: Poll Task Status

Archive download is an asynchronous operation. You need to poll the task status until it completes.

Use the automated polling script:

```bash
python3 /skills/pds/scripts/pds_archive_poller.py \
  --async-task-id <async_task_id> \
  --max-attempts 60
```

**Parameter Description**:
- `--async-task-id`: The async_task_id returned from Step 1
- `--max-attempts`: Maximum number of polling attempts (default: 60, with 5-second intervals)

**Output on Success**: The script prints the download URL when the task completes:

```
✅ Archive task completed!
Download URL: https://pds-data.aliyuncs.com/...
```

**Alternative Manual Polling**:

If the script is not available, you can manually poll using:

```bash
aliyun pds get-async-task \
  --async-task-id <async_task_id> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pds-intelligent-workspace
```

**Polling Response Fields**:
- `state`: Task state - `Running` (in progress), `Succeed` (completed), `Failed` (failed)
- `url`: Download URL for the archive (available when state is `Succeed`)
- `message`: Error message (available when state is `Failed`)

**Example Success Response**:
```json
{
  "async_task_id": "testAsyncTaskId",
  "state": "Succeed",
  "url": "https://pds-data.aliyuncs.com/..."
}
```

---

## Step 3: Download the Archive

Once you have the download URL from Step 2, save it to a variable first, then pass it to curl. This avoids shell parsing errors caused by special characters (`&`, `%27`, etc.) in the URL.

```bash
# Save URL to variable (from polling output or get-async-task response)
DOWNLOAD_URL="<download_URL_from_step2>"

# Download using the variable
curl -fL --max-time 3600 --retry 3 --retry-delay 5 -o <archive_name>.zip "${DOWNLOAD_URL}"
```

**Parameter Description**:
- `-f`: Fail on HTTP errors (returns non-zero exit code)
- `-L`: Follow redirects automatically
- `--max-time 3600`: Maximum time for the entire download operation (seconds)
- `--retry 3`: Retry up to 3 times on transient failures
- `--retry-delay 5`: Wait 5 seconds between retries

**Important**: Always use a shell variable for the URL rather than pasting it directly into the command. URLs from PDS contain query parameters with `&`, encoded quotes (`%27`), and security tokens that can break shell parsing if not handled correctly.

**Note**: The download URL has a default validity of 10 minutes. If expired, re-poll the task to get a new URL.

---

## Complete Example

Archive three files from drive `drive123` into `project_files.zip`:

```bash
# Step 1: Create archive task
aliyun pds archive-files \
  --drive-id drive123 \
  --name "project_files.zip" \
  --file-ids fileId1 fileId2 fileId3 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pds-intelligent-workspace

# Step 2: Poll until complete (using the automated script)
python3 /skills/pds/scripts/pds_archive_poller.py \
  --async-task-id <returned_async_task_id> \
  --max-attempts 60

# Step 3: Save URL to variable and download
DOWNLOAD_URL="<download_URL_from_step2>"
curl -fL --max-time 3600 --retry 3 --retry-delay 5 -o project_files.zip "${DOWNLOAD_URL}"
```

---

## Error Handling

1. If the archive task fails (state is `Failed`), check the `message` field for the error reason.
2. Common errors:
   - Files exceed size limit (10GB total)
   - Too many files (>500 top-level or >10,000 recursive)
   - Insufficient permissions on one or more files
   - Archive download feature not enabled for the domain
3. If polling times out, the task may still be running. Wait and retry polling with the same `async_task_id`.
