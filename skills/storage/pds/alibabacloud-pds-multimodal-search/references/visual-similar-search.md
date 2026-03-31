# Alibaba Cloud PDS Visual Similar Search Guide

**Scenario**: When you have prepared a local image file or have obtained the drive_id, file_id, revision_id of an image file, and want to perform image search, similar image search, visual similarity search, or multimodal image retrieval
**Purpose**: Search for similar images in the cloud drive based on user-provided image

## Step 1 [Optional]: Upload Local Image File to Drive System Space

**Prerequisites**

If the user has already provided the image file's drive_id, file_id, revision_id, skip this step

### Step 1.1 Get System Space

Execute the following command to get the domain's system space configuration:
```bash
aliyun pds get-domain --domain-id <domain-id> --user-agent AlibabaCloud-Agent-Skills
```

Response example:
```json
{
  "domain_id": "bj1093",
  "system_drive_config": {
    "enable": true,
    "drive_id": 1,
    "resource_parent_file_id_map": {
      "value-add": "68d2348822056f5eea514146b4ad7183cdb94d2f"
    }
  }
}
```

Extract the system space ID and upload parent file ID from the response. In the above example, system space ID is 1, and upload parent file ID is `68d2348822056f5eea514146b4ad7183cdb94d2f` (the `value-add` item).

If `enable` in `system_drive_config` is false, or `drive_id` is empty, or `resource_parent_file_id_map` does not contain `value-add`, there is an issue with system space configuration. Please contact PDS technical support for assistance.

### Step 1.2 Upload Local File to Drive System Space

Upload the local file to the drive's system space, where `drive_id` is set to the system space ID obtained in the previous step, `parent_file_id` is set to the upload parent file ID obtained in the previous step, and record the file's `file_id` and `revision_id`.

## Step 2: Construct x-pds-process

If the user searches using a local file, the source file information comes from the file uploaded to the drive in Step 1.2; otherwise, the source file information comes from the drive file information provided by the user.

Must call the existing Python script `scripts/render_visual_similar_search_process.py` to generate `x-pds-process`. The script will output `x-pds-process` to the terminal.

**Parameter Description**
- `source_domain_id`: Domain where the source image is located
- `source_file_id`: File ID of the source image
- `source_drive_id`: Drive ID of the source image
- `source_revision_id`: Revision ID of the source image
- `query`: Search semantic text, not required if none
- `limit`: Maximum number of similar images to return, not required if none

```bash
python scripts/render_visual_similar_search_process.py \
  --source_domain_id <SOURCE_DOMAIN_ID> \
  --source_file_id <SOURCE_FILE_ID> \
  --source_drive_id <SOURCE_DRIVE_ID> \
  --source_revision_id <SOURCE_REVISION_ID> \
  --query <QUERY> \
  --limit <LIMIT>
```

---

## Step 3: Perform Image Search

**Parameter Description**
- `search_drive_id`: Drive ID to search in
- `search_folder_id`: File ID of the folder to search in

### Search Entire Drive
```bash
aliyun pds process \
  --resource-type drive \
  --drive-id ${SEARCH_DRIVE_ID} \
  --x-pds-process ${X_PDS_PROCESS} \
  --user-agent AlibabaCloud-Agent-Skills
```

### Search Specific Folder
```bash
aliyun pds process \
  --resource-type file \
  --drive-id ${SEARCH_DRIVE_ID} \
  --file-id ${SEARCH_FOLDER_ID} \
  --x-pds-process ${X_PDS_PROCESS} \
  --user-agent AlibabaCloud-Agent-Skills
```

---

## Response

**Success Response**:
```json
{
  "similar_files": [
    {
      "similarity": 0.95,
      "domain_id": "bj1093",
      "drive_id": "2",
      "file_id": "5d79206586bb5dd69fb34c349282718146c55da7",
      "name": "similar_image1.jpg",
      "type": "file",
      "category": "image",
      "size": 102400,
      "created_at": "2019-08-20T06:51:27.292Z",
      "thumbnail": "https://..."
    },
    {
      "similarity": 0.84,
      "domain_id": "bj1093",
      "drive_id": "2",
      "file_id": "69c0e5c9432208927ca14d1f8af5e897486c6337",
      "name": "similar_image2.jpg",
      "type": "file",
      "category": "image",
      "size": 102400,
      "created_at": "2023-08-20T06:51:27.292Z",
      "thumbnail": "https://..."
    }
  ]
}
```

**Field Description**:
- `similarity`: Similarity score, range [0, 1], closer to 1 means more similar
- `drive_id`: Drive where the result file is located (the search scope drive)
- `file_id`: Similar file ID
- `name`: File name
- `thumbnail`: Thumbnail URL

---

## Error Handling

| HTTP Status | Error Code | Description | Solution |
|------------|--------|------|---------||
| 400 | InvalidParameter.xxx | Invalid parameter | Check parameter format and encoding |
| 400 | OperationNotSupport | Feature not enabled | Contact PDS technical support to enable feature |
| 403 | ForbiddenNoPermission.xxx | No permission | Check AccessToken permissions |

**Common Errors**:

### 1. Feature Not Enabled
```json
{
  "code": "OperationNotSupport",
  "message": "This operation is not supported."
}
```
**Solution**: Contact PDS technical support to enable image search feature.

### 2. Insufficient Permissions
```json
{
  "code": "ForbiddenNoPermission.file",
  "message": "No Permission to access resource file"
}
```
**Solution**:
- Ensure current user has `FILE.LIST` permission on the search space or folder
- Ensure current user has `FILE.PREVIEW` permission on the source file

---

## Best Practices

### 1. Set Appropriate limit Parameter
- Quick preview: `l_10` or `l_20`
- Regular search: `l_50`
- Comprehensive search: `l_100` (maximum)

### 2. Prefer Image-Only Retrieval
Unless the user explicitly requests image-text hybrid retrieval, prefer using image-only retrieval for better accuracy

---

## FAQ

**Q: Why are fewer results returned than expected?**
limit only indicates the maximum number of results, it does not guarantee that limit images will be returned.
A: Possible reasons:
1. Actual number of similar images is less than limit
2. Some files were filtered due to insufficient permissions
3. Total number of images in search scope is small

**Q: Can I search for videos or documents?**
A: Not supported, only similar image search is supported.
