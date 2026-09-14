# 相关命令

> 本 skill 涉及的 `aliyun dataphin-public` 命令清单。

| 命令 | 用途 |
|------|------|
| `aliyun dataphin-public get-file-storage-credential` | 获取对象存储上传凭证（StorageType=oss/ceph） |
| `aliyun dataphin-public create-resource` | 创建 Dataphin 资源 |
| `aliyun dataphin-public get-resource` | 获取资源最新版本 |
| `aliyun dataphin-public get-resource-by-version` | 获取资源指定版本 |
| `aliyun dataphin-public update-resource` | 更新资源 |
| `aliyun dataphin-public delete-resource` | 删除资源 |
| `aliyun dataphin-public --help` | 查看全部命令 |

## 本地工具命令

| 命令 | 用途 |
|------|------|
| `ossutil cp` | 上传文件到 OSS（oss 类型，需 `--sts-token`） |
| `mc alias set` | 配置 ceph 别名（ceph 类型） |
| `mc cp` | 上传文件到 ceph（ceph 类型） |
