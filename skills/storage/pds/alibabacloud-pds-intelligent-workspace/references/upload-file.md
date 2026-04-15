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
  --user-agent AlibabaCloud-Agent-Skills
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
  --user-agent AlibabaCloud-Agent-Skills
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
  --user-agent AlibabaCloud-Agent-Skills
```

### Enable Rapid Upload

Calculate file SHA-1 for rapid upload attempt (completes instantly if identical file exists in cloud):

```bash
aliyun pds upload-file \
  --drive-id "100" \
  --local-path "/path/to/file.jpg" \
  --enable-rapid-upload \
  --user-agent AlibabaCloud-Agent-Skills
```

### Large File Multipart Upload

Custom part size (suitable for large file uploads):

```bash
aliyun pds upload-file \
  --drive-id "100" \
  --local-path "/path/to/large-file.zip" \
  --part-size 10485760 \
  --user-agent AlibabaCloud-Agent-Skills
```

### Upload File to Specified Directory
If you want to upload a file to a specified directory in a PDS drive, you need to convert the cloud directory name to the cloud directory `file_id`, and use this `file_id` as the value of the `--parent-file-id` parameter.  
For example, to upload a file to the /Photos/2026/04 directory in a personal space, you need to traverse each level of the /Photos/2026/04 path to find the corresponding directory's file_id. If a directory does not exist in the cloud, you need to create it. After finding the `file_id` of the final directory, use this `file_id` as the value for the --parent-file-id parameter. The steps are as follows:  
1. First, use the `aliyun pds list-file --drive-id <drive_id> --type folder --parent-file-id root --user-agent AlibabaCloud-Agent-Skills` command to list all directories under the root directory (parent-file-id=root) and find the file_id of the Photos directory:  
   a. If the Photos directory exists, note down its file_id  
   b. If the Photos directory does not exist, you need to create it first and get the file_id from the creation response. Create directory command: `aliyun pds create-file --drive-id <drive_id> --parent-file-id root --name Photos --type folder --user-agent AlibabaCloud-Agent-Skills`
2. Use the `aliyun pds list-file --drive-id <drive_id> --type folder --parent-file-id <parent_file_id> --user-agent AlibabaCloud-Agent-Skills` command to list all directories under the parent directory (parent-file-id=<Photos directory's file_id>) and find the file_id of the 2026 directory:  
   a. If the 2026 directory exists, note down its file_id  
   b. If the 2026 directory does not exist, you need to create it first and get the file_id from the creation response. Create directory command: `aliyun pds create-file --drive-id <drive_id> --parent-file-id <Photos directory's file_id> --name 2026 --type folder --user-agent AlibabaCloud-Agent-Skills`
3. Use the `aliyun pds list-file --drive-id <drive_id> --type folder --parent-file-id <2026 directory's file_id> --user-agent AlibabaCloud-Agent-Skills` command to list all directories under the parent directory (parent-file-id=<2026 directory's file_id>) and find the file_id of the 04 directory:  
   a. If the 04 directory exists, note down its file_id  
   b. If the 04 directory does not exist, you need to create it first and get the file_id from the creation response. Create directory command: `aliyun pds create-file --drive-id <drive_id> --parent-file-id <2026 directory's file_id> --name 04 --type folder --user-agent AlibabaCloud-Agent-Skills`
4. After obtaining the file_id of the 04 directory, you can use this file_id as the value for the --parent-file-id parameter to upload the file to the /Photos/2026/04 directory

**Note:** When executing the `aliyun pds list-file` command, if there are no valid items returned and the next_marker is not empty, it means that the query is not complete and the next_marker needs to be used as the --marker parameter for the next list query until next_marker is empty.

### Upload File to Specified Parent File ID
Upload a file to a specified parent file ID, first you need to verify whether the parent directory with the specified ID exists. You can use Get File to query and verify:
```bash
aliyun pds get-file \
  --drive-id "100" \
  --file-id "1000" \
  --user-agent AlibabaCloud-Agent-Skills
```
If the specified Parent File ID does not exist, it will prompt that the parent directory does not exist and ask the user to confirm again.  
If this directory exists, take the response file's `parent_file_id` as the new Parent File ID and continue to query through Get File until the `parent_file_id` is `root`, indicating that the top-level directory has been found. Then concatenate the queried levels to get the full path of the file in this PDS drive space after upload.  
**Note:** Before uploading, you must query the full path relative to the root directory. Only after that can you proceed with the subsequent upload operations.

After the query is completed, use the following command line to complete the file upload:

```bash
aliyun pds upload-file \
  --drive-id "100" \
  --local-path "/path/to/file.jpg" \
  --parent-file-id "1000" \
  --user-agent AlibabaCloud-Agent-Skills
```

After the upload is completed, inform the user that the file upload was successful and display the full path relative to the root directory of the file. For example, the file has been uploaded to the `personal space`(or `team space`) and the full path is /Photos/2026/04/01/file.jpg.

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