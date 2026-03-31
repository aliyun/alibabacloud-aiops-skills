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