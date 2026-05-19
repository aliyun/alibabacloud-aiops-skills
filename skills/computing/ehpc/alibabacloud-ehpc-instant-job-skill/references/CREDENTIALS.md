# SDK 凭证配置说明

本目录下的 Python SDK 脚本使用 **默认凭证链**（`AcsClient(region_id='cn-shanghai')`），SDK 会按以下优先级自动查找凭证：

## 凭证解析顺序

1. **环境变量** — 设置以下环境变量即可：

   ```bash
   export ALIBABA_CLOUD_ACCESS_KEY_ID=<your-access-key-id>
   export ALIBABA_CLOUD_ACCESS_KEY_SECRET=<your-access-key-secret>
   ```

   如需使用 STS 临时凭证，额外设置：

   ```bash
   export ALIBABA_CLOUD_SECURITY_TOKEN=<your-security-token>
   ```

2. **配置文件** — 通过 `aliyun configure` 命令生成的 `~/.aliyun/config.json`：

   ```bash
   aliyun configure
   # 按提示输入 Access Key ID、Access Key Secret、默认区域（cn-shanghai）
   ```

   配置完成后 SDK 会自动读取该文件中的凭证信息。

3. **ECS RAM 角色** — 在 ECS 实例上运行时，SDK 自动通过实例元数据获取关联 RAM 角色的临时凭证，无需任何配置。

## 推荐方式

| 场景 | 推荐方式 |
|------|----------|
| 本地开发/调试 | 方式 2：`aliyun configure` 配置文件 |
| CI/CD 流水线 | 方式 1：环境变量 |
| ECS 实例上运行 | 方式 3：ECS RAM 角色（零配置） |
| 临时/跨账号访问 | 方式 1：环境变量 + STS Token |

## 注意事项

- 所有脚本默认使用 `cn-shanghai` 区域，如需修改请调整 `AcsClient(region_id='...')` 参数
- 禁止在代码中硬编码 AccessKey，应始终使用上述凭证链机制
- 确保 AccessKey 对应的 RAM 用户/角色具备 E-HPC Instant 相关权限（参考 `references/ram-policies.md`）
