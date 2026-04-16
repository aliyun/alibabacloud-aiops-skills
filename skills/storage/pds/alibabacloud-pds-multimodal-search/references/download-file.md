# PDS File Download Guide

**Scenario**: When you have obtained the drive_id and file_id of the file to download and need to download that file
**Purpose**: Download file to local

---

## Get File ID from File Path

If you want to download a file from a PDS drive but only have the file path (e.g., /Photos/2026/04/vacation.jpg), you need to traverse each level of the path to find the corresponding file's file_id. The steps are as follows:  
For example, to download the file /Photos/2026/04/vacation.jpg from a personal space:

1. First, use the `aliyun pds list-file --drive-id <drive_id> --type folder --parent-file-id root --user-agent AlibabaCloud-Agent-Skills` command to list all directories under the root directory (parent-file-id=root) and find the file_id of the Photos directory:   
   a. If the Photos directory exists, note down its file_id  
   b. If the Photos directory does not exist, the file path is invalid
2. Use the `aliyun pds list-file --drive-id <drive_id> --type folder --parent-file-id <parent_file_id> --user-agent AlibabaCloud-Agent-Skills` command to list all directories under the parent directory (parent-file-id=<Photos directory's file_id>) and find the file_id of the 2026 directory:  
   a. If the 2026 directory exists, note down its file_id  
   b. If the 2026 directory does not exist, the file path is invalid
3. Use the `aliyun pds list-file --drive-id <drive_id> --type folder --parent-file-id <2026 directory's file_id> --user-agent AlibabaCloud-Agent-Skills` command to list all directories under the parent directory (parent-file-id=<2026 directory's file_id>) and find the file_id of the 04 directory:  
   a. If the 04 directory exists, note down its file_id  
   b. If the 04 directory does not exist, the file path is invalid
4. Use the `aliyun pds list-file --drive-id <drive_id> --type file --parent-file-id <04 directory's file_id> --user-agent AlibabaCloud-Agent-Skills` command to list all files under the parent directory (parent-file-id=<04 directory's file_id>) and find the file_id of the vacation.jpg file:  
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
  --user-agent AlibabaCloud-Agent-Skills
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

Use the obtained download URL to download the file:

```bash
curl -L --max-time 3600 --max-redirs 10 -o <output_filename> '<download_URL>'
```

**Parameter Description**:
- `-L`: Follow redirects automatically (when download_URL returns a redirect URL, curl will continue downloading from the new location)
- `--max-redirs 10`: Maximum number of redirects to follow (prevents infinite redirect loops)
- `--max-time 3600`: Maximum time for the entire download operation (seconds)

**Note**: The `-L` parameter is critical because PDS download URLs often return a redirect to the actual OSS storage URL. Without this parameter, curl will fail with a 3xx redirect response.

Or use `wget`:

```bash
wget --timeout=3600 --max-redirect=10 -O <output_filename> '<download_URL>'
```

**Parameter Description**:
- `--max-redirect=10`: Maximum number of redirects to follow
- `--timeout=3600`: Timeout for the download operation (seconds)

---

### Step 3: Verify Local File Exists

