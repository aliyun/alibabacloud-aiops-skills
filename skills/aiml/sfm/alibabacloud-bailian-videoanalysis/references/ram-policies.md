# RAM Permissions

This Skill requires the following Alibaba Cloud RAM permissions to function properly.

## Required Permissions

| Product          | Action                                     | Description                          |
|------------------|--------------------------------------------|--------------------------------------|
| ModelStudio      | `modelstudio:ListWorkspaces`               | List Bailian workspaces              |
| OSS              | `ossutil:ls`                               | List buckets or objects              |
| OSS              | `ossutil:cp`                               | Upload, Download or Copy Objects     |
| OSS              | `ossutil:presign`                          | Generate a pre-signed URL for object |
| QuanMiaoLightApp | `quanmiaolightapp:SubmitVideoAnalysisTask` | Submit video analysis task           |
| QuanMiaoLightApp | `quanmiaolightapp:GetVideoAnalysisTask`    | Get video analysis task results      |

## Permission Details

### modelstudio:ListWorkspaces

Used to query the list of available Bailian workspaces.

### ossutil:ls, ossutil:cp, ossutil:presign

Used to manage OSS buckets and objects, including listing buckets/objects, uploading/downloading files, and generating temporary access URLs.

### quanmiaolightapp:SubmitVideoAnalysisTask

Used to submit video analysis tasks to Bailian service.

### quanmiaolightapp:GetVideoAnalysisTask
Used to query video analysis task results.

## Authorization Methods

### Use System Policies (Recommended)

1. Visit [Alibaba Cloud RAM Console](https://ram.console.aliyun.com/users)
2. Select the target RAM user
3. Click "Add Permissions" button
4. Search and select the following system policies:
   - `AliyunBailianFullAccess` (includes Bailian-related permissions)
   - `AliyunModelStudioReadOnlyAccess` (includes ModelStudio-related permissions)
   - `AliyunQuanMiaoLightAppFullAccess` (includes QuanMiao-related permissions)
   - `AliyunOSSFullAccess` (includes OSS-related permissions, can be restricted to specific buckets)
5. Confirm and add permissions


## Notes

- There may be a delay of approximately 30 seconds after authorization before permissions take effect
- If you encounter `403` or `Index.NoWorkspacePermissions` errors, please check:
  1. Whether the RAM user has been granted the above permissions
  2. Whether workspace permissions have been granted to the user in the Bailian console

---

## Permission Failure Handling

When any command or API call fails due to permission errors at any point during execution, follow this process:

1. **Read this file** (`references/ram-policies.md`) to get the full list of permissions required by this SKILL
2. **Use `ram-permission-diagnose` skill** to guide the user through requesting the necessary permissions
3. **Pause and wait** until the user confirms that the required permissions have been granted
4. **Retry the failed operation** after permissions are confirmed

**Important:** Never proceed with operations that require permissions the user does not have. Always pause and wait for explicit confirmation.
