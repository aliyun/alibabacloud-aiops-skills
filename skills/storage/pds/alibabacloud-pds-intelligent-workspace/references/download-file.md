# PDS File Download Guide

**Scenario**: When you need to download a file from PDS to local
**Purpose**: Download file to local

---

## Finding the File

Before downloading, you need the file's `drive_id` and `file_id`. Choose the method based on what you know:

| What you have | Method |
|---|---|
| **file_id** | Go directly to [Download File](#download-file) |
| **File path** (e.g., `/Photos/vacation.jpg`) | Use [Get File ID from File Path](#get-file-id-from-file-path) below |
| **Filename only** (e.g., `apple1.jpg`) | Use `references/search-file.md` to search by filename first, then download with the returned file_id |

---

## Get File ID from File Path

If you want to download a file from a PDS drive but only have the file path (e.g., /Photos/2026/04/vacation.jpg), you need to traverse each level of the path to find the corresponding file's file_id. The steps are as follows:  
For example, to download the file /Photos/2026/04/vacation.jpg from a personal space:

1. First, use the `aliyun pds list-file --drive-id <drive_id> --type folder --parent-file-id root --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pds-intelligent-workspace` command to list all directories under the root directory (parent-file-id=root) and find the file_id of the Photos directory:   
   a. If the Photos directory exists, note down its file_id  
   b. If the Photos directory does not exist, the file path is invalid
2. Use the `aliyun pds list-file --drive-id <drive_id> --type folder --parent-file-id <parent_file_id> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pds-intelligent-workspace` command to list all directories under the parent directory (parent-file-id=<Photos directory's file_id>) and find the file_id of the 2026 directory:  
   a. If the 2026 directory exists, note down its file_id  
   b. If the 2026 directory does not exist, the file path is invalid
3. Use the `aliyun pds list-file --drive-id <drive_id> --type folder --parent-file-id <2026 directory's file_id> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pds-intelligent-workspace` command to list all directories under the parent directory (parent-file-id=<2026 directory's file_id>) and find the file_id of the 04 directory:  
   a. If the 04 directory exists, note down its file_id  
   b. If the 04 directory does not exist, the file path is invalid
4. Use the `aliyun pds list-file --drive-id <drive_id> --type file --parent-file-id <04 directory's file_id> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pds-intelligent-workspace` command to list all files under the parent directory (parent-file-id=<04 directory's file_id>) and find the file_id of the vacation.jpg file:  
   a. If the vacation.jpg file exists, note down its file_id  
   b. If the vacation.jpg file does not exist, the file path is invalid  
5. After obtaining the file_id of vacation.jpg, you can use this file_id to download the file

**Note:** When executing the `aliyun pds list-file` command, if there are no valid items returned and the next_marker is not empty, it means that the query is not complete and the next_marker needs to be used as the --marker parameter for the next list query until next_marker is empty.

---

## Download File

### Step 1: Get Download URL

Get the download link for the file:

```bash
aliyun pds get-download-url \
  --drive-id <drive_id> \
  --file-id <file_id> \
  --expire-sec 3600 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pds-intelligent-workspace
```

**Parameter Description**:
- `--drive-id`: The drive_id of the space where the file is located (obtained from search results)
- `--file-id`: The file_id of the file to download (obtained from search results)
- `--expire-sec`: Download link validity period (seconds), default 900, maximum 115200 (32 hours)

**Output**: Returns a JSON object containing `url` (download link), `expiration`, `method`, `size`, and other information.

**Example Output**:
```json
{
  "url": "https://pds-data.aliyuncs.com/...",
  "expiration": "2024-01-15T11:30:00Z",
  "method": "GET",
  "size": 1048576
}
```

---

### Step 2: Download File

Save the download URL to a variable first, then pass it to curl. This avoids shell parsing errors caused by special characters (`&`, `+`, `=`, security tokens) in PDS/OSS signed URLs.

```bash
# Save the URL from Step 1 response into a variable
DOWNLOAD_URL="<url_from_get-download-url_response>"

# Download using the variable
curl -fL --max-time 3600 --retry 3 --retry-delay 5 -o <output_filename> "${DOWNLOAD_URL}"
```

**Parameter Description**:
- `-f`: Fail on HTTP errors (returns non-zero exit code instead of saving error response to file)
- `-L`: Follow redirects automatically (PDS download URLs redirect to the actual OSS storage URL)
- `--max-time 3600`: Maximum time for the entire download operation (seconds)
- `--retry 3`: Retry up to 3 times on transient failures
- `--retry-delay 5`: Wait 5 seconds between retries

**Important**: Always use a shell variable for the URL. PDS download URLs contain query parameters with `&`, STS security tokens with `+`/`=`, and URL-encoded characters that will break if pasted directly into the command line without correct quoting. Using `"${DOWNLOAD_URL}"` with double quotes ensures the entire URL is passed intact.

Or use `wget`:

```bash
wget --timeout=3600 --max-redirect=10 -O <output_filename> "${DOWNLOAD_URL}"
```

---

### Step 3: Verify Local File Exists

