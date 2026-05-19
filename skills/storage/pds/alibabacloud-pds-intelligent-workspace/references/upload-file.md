# PDS File Upload Guide

**Scenario**: When you have obtained the target drive_id and directory file_id and need to upload files to PDS drive
**Purpose**: Upload local files to PDS drive (supports enterprise space, team space, personal space)

---

## File Upload Command

Use the `aliyun pds upload-file` command to directly upload local files to PDS. This command automatically completes the three steps: create file, upload content, and complete upload.

```bash
aliyun pds upload-file \
  --drive-id <drive_id> \
  --local-path <local_file_path> \
  --parent-file-id <parent_file_id> \
  --name <cloud_file_name> \
  --check-name-mode <auto_rename|ignore|refuse> \
  --enable-rapid-upload <true|false> \
  --part-size <part_size> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pds-intelligent-workspace
```

---

## Parameter Description

| Parameter | Type | Required | Description |
|------|------|------|------|
| `--drive-id` | string | Yes | Target space ID (obtained from space list) |
| `--local-path` | string | Yes | Full path to local file |
| `--parent-file-id` | string | No | Parent directory ID, default is `root` |
| `--name` | string | No | Cloud file name, defaults to local file name |
| `--check-name-mode` | string | No | Name conflict handling mode: `ignore` (overwrite), `auto_rename` (auto rename), `refuse` (reject), default is `ignore` |
| `--enable-rapid-upload` | bool | No | Calculate file SHA-1 for rapid upload attempt, default is `false` |
| `--part-size` | int | No | Size of each part (bytes), default is 5242880 (5MB) |

---

## Common Examples

### Basic Upload

Upload to root directory using local file name:

```bash
aliyun pds upload-file \
  --drive-id "100" \
  --local-path "/path/to/file.jpg" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pds-intelligent-workspace
```

### Specify Directory and File Name

Upload to specified directory with custom cloud file name:

```bash
aliyun pds upload-file \
  --drive-id "100" \
  --local-path "/path/to/file.jpg" \
  --parent-file-id "root" \
  --name "my-photo.jpg" \
  --check-name-mode "auto_rename" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pds-intelligent-workspace
```

### Enable Rapid Upload

Calculate file SHA-1 for rapid upload attempt (completes instantly if identical file exists in cloud):

```bash
aliyun pds upload-file \
  --drive-id "100" \
  --local-path "/path/to/file.jpg" \
  --enable-rapid-upload \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pds-intelligent-workspace
```

### Large File Multipart Upload

Custom part size (suitable for large file uploads):

```bash
aliyun pds upload-file \
  --drive-id "100" \
  --local-path "/path/to/large-file.zip" \
  --part-size 10485760 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pds-intelligent-workspace
```

### Upload File to Specified Directory

If you want to upload a file to a specified directory in a PDS drive, you need to convert the cloud directory name to the cloud directory `file_id`, and use this `file_id` as the value of the `--parent-file-id` parameter.

For example, to upload a file to the `/Photos/2026/04` directory in a personal space, you need to traverse each level of the path to find the corresponding directory's `file_id`. If a directory does not exist in the cloud, you need to create it first.

#### Step 1: Find or Create Photos Directory

List all directories under the root directory to find the `Photos` directory:

```bash
aliyun pds list-file \
  --drive-id <drive_id> \
  --type folder \
  --parent-file-id root \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pds-intelligent-workspace
```

- **If Photos directory exists**: Note down its `file_id`
- **If Photos directory does not exist**: Create it first and get the `file_id` from the response:

```bash
aliyun pds create-file \
  --drive-id <drive_id> \
  --parent-file-id root \
  --name Photos \
  --check-name-mode refuse \
  --type folder \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pds-intelligent-workspace
```

#### Step 2: Find or Create 2026 Directory

List all directories under the Photos directory to find the `2026` directory:

```bash
aliyun pds list-file \
  --drive-id <drive_id> \
  --type folder \
  --parent-file-id <Photos_directory_file_id> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pds-intelligent-workspace
```

- **If 2026 directory exists**: Note down its `file_id`
- **If 2026 directory does not exist**: Create it first:

```bash
aliyun pds create-file \
  --drive-id <drive_id> \
  --parent-file-id <Photos_directory_file_id> \
  --name 2026 \
  --check-name-mode refuse \
  --type folder \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pds-intelligent-workspace
```

#### Step 3: Find or Create 04 Directory

List all directories under the 2026 directory to find the `04` directory:

```bash
aliyun pds list-file \
  --drive-id <drive_id> \
  --type folder \
  --parent-file-id <2026_directory_file_id> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pds-intelligent-workspace
```

- **If 04 directory exists**: Note down its `file_id`
- **If 04 directory does not exist**: Create it first:

```bash
aliyun pds create-file \
  --drive-id <drive_id> \
  --parent-file-id <2026_directory_file_id> \
  --name 04 \
  --check-name-mode refuse \
  --type folder \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pds-intelligent-workspace
```

#### Step 4: Upload File

After obtaining the `file_id` of the `04` directory, use it as the `--parent-file-id` parameter value to upload the file:

```bash
aliyun pds upload-file \
  --drive-id <drive_id> \
  --local-path "/path/to/file.jpg" \
  --parent-file-id <04_directory_file_id> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pds-intelligent-workspace
```

> **Note:** When executing the `aliyun pds list-file` command, if there are no valid items returned and the `next_marker` is not empty, it means that the query is not complete. Use the `next_marker` as the `--marker` parameter for the next list query until `next_marker` is empty.

### Upload File to Specified Parent File ID

When uploading a file to a specified parent file ID, first verify whether the parent directory with the specified ID exists using the Get File command:

```bash
aliyun pds get-file \
  --drive-id "100" \
  --file-id "1000" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pds-intelligent-workspace
```

**Verification Logic:**

- **If the specified Parent File ID does not exist**: The system will prompt that the parent directory does not exist. Ask the user to confirm again.
- **If the directory exists**: Take the response file's `parent_file_id` as the new Parent File ID and continue to query through Get File until the `parent_file_id` is `root`, indicating that the top-level directory has been found.

After finding all levels, concatenate them to get the full path of the file in this PDS drive space after upload.

> **Note:** Before uploading, you must query the full path relative to the root directory. Only after that can you proceed with the subsequent upload operations.

**Upload Command:**

After completing the path query, use the following command to upload the file:

```bash
aliyun pds upload-file \
  --drive-id "100" \
  --local-path "/path/to/file.jpg" \
  --parent-file-id "1000" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pds-intelligent-workspace
```

**Post-Upload:**

After the upload is completed, inform the user that the file upload was successful and display the full path relative to the root directory. For example:

> The file has been uploaded to the `personal space` (or `team space`) with the full path: `/Photos/2026/04/01/file.jpg`

---

## Output Description

After successful command execution, returns a JSON object with complete file information, main fields include:

- `file_id`: Unique file ID
- `name`: Cloud file name
- `size`: File size
- `created_at`: Creation time
- `updated_at`: Update time
- `parent_file_id`: Parent directory ID

---

## Notes

1. **Same name file handling**: Recommend using `--check-name-mode auto_rename` to avoid overwriting existing files
2. **Rapid upload feature**: Enable `--enable-rapid-upload` to complete upload instantly when identical file exists in cloud
3. **Multipart upload**: Large files are automatically uploaded in parts, adjust part size via `--part-size`
4. **Network stability**: Ensure stable network when uploading large files to avoid interruptions