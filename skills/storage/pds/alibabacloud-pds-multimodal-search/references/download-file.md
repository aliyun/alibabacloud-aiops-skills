# PDS File Download Guide

**Scenario**: When you have obtained the drive_id and file_id of the file to download and need to download that file
**Purpose**: Download file to local

---

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
curl --max-time 3600 -o <output_filename> "<download_URL>"
```

Or use `wget`:

```bash
wget --timeout=3600 -O <output_filename> "<download_URL>"
```

---

### Step 3: Verify Local File Exists

