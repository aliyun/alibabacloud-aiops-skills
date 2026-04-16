# RAM 权限声明

本 Skill 需要以下阿里云 RAM 权限才能正常运行。

## 所需权限清单

| 产品   | Action                | 说明                                    |
|------|-----------------------|---------------------------------------|
| modelstudio | `modelstudio:ListWorkspaces` | 查询工作空间列表                              |
| oss  | `ossutil:ls`          | List buckets or objects               |
| oss  | `ossutil:cp`          | Upload, Download or Copy Objects      |
| oss  | `ossutil:presign`     | Generate a pre-signed URL for object  |

## 权限详情

### modelstudio:ListWorkspaces

用于查询可用的 ModelStudio 工作空间列表。


## 授权方式

### 方式一：使用系统策略（推荐）

1. 访问 [阿里云 RAM 访问控制](https://ram.console.aliyun.com/users)
2. 选择对应的 RAM 用户
3. 点击「新增授权」按钮
4. 在权限策略中搜索并选择以下系统策略：
   - `AliyunBailianFullAccess`（包含 bailian 相关权限）
   - `AliyunModelStudioReadOnlyAccess`（包含 modelstudio 相关权限）
   - `AliyunQuanMiaoLightAppFullAccess`（包含 quanmiao 相关权限）
   - `AliyunOSSFullAccess`（包含 oss 相关权限，可按需授予指定bucket的读写权限）
5. 确认新增授权


## 注意事项

- 授权后权限生效可能存在 30 秒左右的延迟
- 如遇到 `403` 或 `Index.NoWorkspacePermissions` 错误，请检查：
  1. RAM 用户是否已授予上述权限
  2. 百炼控制台中是否已为该用户授予工作空间权限
