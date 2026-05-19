---
name: alibabacloud-ehpc-instant-job-skill
description: 阿里云E-HPC Instant计算平台作业管理工具包，支持E-HPC Instant（EHPC Instant/ehpcinstant）作业的创建/提交、查询、获取详情、查询日志、删除等操作。当用户需要创建作业、查询作业列表、获取作业详情、删除作业、查询作业日志时使用。
---

# 阿里云E-HPC Instant作业管理技能

## 技能概述
通过阿里云CLI（优先）或SDK工具，实现对E-HPC Instant计算平台作业及计算资源的全生命周期管理。

## 交互原则
- **用户友好**：使用"您"而非"你"，保持专业而友好的语调
- **透明操作**：所有关键配置信息必须向用户展示并获得确认
- **安全第一**：遵循最小权限原则，避免意外操作
- **错误处理**：提供清晰的错误信息和解决方案
- **格式规范**：使用简单、清晰、易读的输出格式

## 执行流程
- Step1: 配置预加载
- Step2: 前置条件校验
- Step3: 作业管理执行
- Step4: 作业任务执行结果输出

### Step 1: 配置预加载
> **[MUST]** 必须首先尝试读取 `./jobconfig/pre-config.json` 文件，严禁跳过此检查步骤。
> - **文件存在且读取成功**：加载其中的参数值，向用户提示预配置已加载并展示关键参数摘要，然后进入 Step 2。
> - **文件不存在**：向用户提示未检测到预配置文件，将在 Step 2 中通过交互方式获取必要参数，然后进入 Step 2。
> - **文件存在但读取/解析失败**（如 JSON 格式错误、权限不足等）：向用户报告具体错误信息，询问是否继续（跳过预配置进入 Step 2）或中止执行。

### Step 2: 前置条件校验
#### 所有作业管理任务通用校验
1. **阿里云CLI配置**：验证CLI已安装并配置AccessKey
   - **CLI版本要求 >= 3.3.3**：运行 `aliyun version` 验证版本 >= 3.3.3。若未安装或版本过低，参考 [references/aliyun-cli.md](./references/aliyun-cli.md) 中的安装说明进行安装或更新。
   - [MUST] 运行 `aliyun configure set --auto-plugin-install true` 启用自动插件安装。
   - [MUST] 运行 `aliyun plugin update` 确保已安装插件始终为最新版本。
   - 若无配置，引导用户交互式安装和配置
   - 参考：[references/aliyun-cli.md](./references/aliyun-cli.md)
   - **[MUST] CLI User-Agent** — 每个 `aliyun` CLI 命令调用必须包含：`--user-agent AlibabaCloud-Agent-Skills/alibabacloud-ehpc-instant-job-skill`
   - **启用阿里云CLI AI模式**：运行以下初始化命令，附加本Skill执行的AI身份信息：
    > ```bash
    > aliyun configure ai-mode enable
    > aliyun configure ai-mode set-user-agent --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ehpc-instant-job-skill"
    > aliyun plugin update
    > ```
    > 阿里云CLI提供了AI模式。启用后，CLI会自动附加AI身份信息，使服务端能够识别并优化Agent调用链路。
    > **[MUST] 在每个退出点禁用AI模式** — 在因任何原因交付最终响应之前，务必先禁用AI模式。这适用于所有退出路径：工作流成功、工作流失败、错误/异常、用户取消、会话结束，或任何不再执行CLI命令的场景。
    > AI模式仅用于Agent Skill调用场景，技能停止运行后**必须**保持禁用状态。
    > ```bash
    > aliyun configure ai-mode disable
    > ```
2. **地域信息**：获取用户指定区域或使用默认区域`cn-shanghai`
3. **权限验证**：确保AccessKey具备E-HPC Instant相关权限

#### 创建作业任务专项校验
1. **镜像准备**：容器/VM镜像已添加至E-HPC Instant平台
   - 若无镜像，引导用户交互式添加
   - 参考：[references/instant-image.md](./references/instant-image.md)
2. **网络配置**：vSwitch已创建并可用
   - 若无vSwitch，引导用户交互式创建
   - 参考：[references/vswitch.md](./references/vswitch.md)
3. **存储配置**：NAS挂载路径已准备（如需要）
   - 若需NAS，引导用户交互式配置
   - 参考：[references/storage.md](./references/storage.md)
4. **计算资源配置**：Cores/Memory或InstanceType规格已指定
   - 引导用户选择合适的资源配置
   - 参考：[references/resource.md](./references/resource.md)
5. **执行命令**：作业执行命令行已指定
   - 确保命令格式正确（特别是JSON数组格式）
   - 参考：[references/job-command.md](./references/job-command.md)

### Step 3: 作业管理执行
根据用户需求执行相应的作业管理操作
#### 创建作业
1. Container容器作业
```bash
aliyun ehpcinstant CreateJob \
    --region cn-shanghai \
    --JobName 'container-job' \
    --Tasks '[{
        "TaskSpec": {
            "TaskExecutor": [{
                "Container": {
                    "Image": "registry.cn-shanghai.aliyuncs.com/registry/image:tag",
                    "Command": "[\"/bin/sh\", \"-c\", \"python /app/main.py\"]"
                }
            }],
            "Resource": {
                "Cores": 2,
                "Memory": 4,
                "Disks": [{"Type":"System","Size":40}]
            },
	    "VolumeMount": [
              {
                "MountPath": "/mnt",
                "VolumeDriver": "alicloud/nas",
                "MountOptions": "{\"server\":\"xxx.cn-shanghai.nas.aliyuncs.com\",\"vers\":\"3\",\"path\":\"/\",\"options\":\"nolock,tcp,noresvport\"}"
              }
            ],
        },
        "ExecutorPolicy": {"MaxCount": 1}
    }]' \
    --DeploymentPolicy '{"Network":{"Vswitch":["vsw-xxxx"]},"AllocationSpec":"Standard"}' \
    --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ehpc-instant-job-skill
```

2. VM虚拟机作业
```bash
aliyun ehpcinstant CreateJob \
    --region cn-shanghai \
    --JobName 'longrunning-job' \
    --JobDescription 'Long-running VM job' \
    --Tasks '[{
        "TaskSpec": {
            "TaskExecutor": [{
                "VM": {
                    "Image": "m-xxxx",
                    "Script": "base64_encoded_script"
                }
            }],
            "Resource": {
                "Disks": [{"Type":"System","Size":50}],
                "InstanceTypes": ["ecs.c6.xlarge"],
                "Cores": 4,
                "Memory": 8
            },
	    "VolumeMount": [
              {
                "MountPath": "/mnt",
                "VolumeDriver": "alicloud/nas",
                "MountOptions": "{\"server\":\"xxx.cn-shanghai.nas.aliyuncs.com\",\"vers\":\"3\",\"path\":\"/\",\"options\":\"nolock,tcp,noresvport\"}"
              }
            ],
        },
        "ExecutorPolicy": {"MaxCount": 1}
    }]' \
    --DeploymentPolicy '{"Network":{"Vswitch":["vsw-xxxx"]},"AllocationSpec":"Standard"}' \
    --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ehpc-instant-job-skill
```

#### 查询作业列表
```bash
# 基本列表查询
aliyun ehpcinstant ListJobs --region cn-shanghai \
    --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ehpc-instant-job-skill

# 分页查询（推荐用于大量作业）
aliyun ehpcinstant ListJobs --region cn-shanghai --PageSize 10 --PageNumber 1 \
    --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ehpc-instant-job-skill

# 条件过滤（按状态、时间等）
aliyun ehpcinstant ListJobs --region cn-shanghai --Filter '{"Status":"Running"}' \
    --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ehpc-instant-job-skill
```

#### 获取作业详情
```bash
aliyun ehpcinstant GetJob --region cn-shanghai --JobId 'job-xxxx' \
    --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ehpc-instant-job-skill
```

#### 查询作业日志
```bash
aliyun ehpcinstant DescribeJobResults --region cn-shanghai --JobId 'job-sh145rw47pegztzdpu7s' --TaskName Task0 --ArrayIndex 0 \
    --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ehpc-instant-job-skill
```

#### 删除作业
```bash
# 删除单个作业
aliyun ehpcinstant DeleteJobs --region cn-shanghai --JobSpec '[{"JobId":"job-xxxx"}]' \
    --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ehpc-instant-job-skill

# 批量删除（安全方式）
aliyun ehpcinstant DeleteJobs --region cn-shanghai --JobSpec '[{"JobId":"job-xxxx"},{"JobId":"job-yyyy"}]' \
    --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ehpc-instant-job-skill
```

> **[MUST] 幂等删除原则** — 当用户请求删除作业时，即使通过 GetJob 或 ListJobs 查询确认作业已不存在，Agent **仍必须**调用 DeleteJobs API 并传入对应 JobId。DeleteJobs API 具备幂等性：作业存在时执行删除，作业不存在时返回标准 NotFound 响应。严禁 Agent 以"作业已不存在"为由自行跳过 API 调用 — 必须让服务端确认最终状态。

### Step 4: 结果输出与后续建议
- 格式化输出执行结果
- 提供后续操作建议（如监控、日志查看等）
- 记录关键信息供后续参考

### 作业管理参考执行脚本
路径：`/home/admin/.openclaw/workspace/skills/ehpcinstant-job-skill/scripts/`

**CLI脚本**：
- `create_container_job.sh` - 创建容器作业
- `create_vm_job_batch.sh` - 创建VM作业
- `create_vm_job_longrunning.sh` - 创建长期运行的VM作业
- `list_jobs.sh` - 列出作业（支持分页）
- `get_job.sh` - 获取作业详情
- `delete_jobs.sh` - 删除作业

**SDK脚本**：
- 对应的Python SDK版本脚本，位于`scripts/sdk/`目录
- `create_container_job.py` - 创建容器作业
- `create_vm_job_batch.py` - 创建VM作业
- `create_vm_job_longrunning.py` - 创建长期运行的VM作业
- `list_jobs.py` - 列出作业（支持分页）
- `get_job.py` - 获取作业详情
- `delete_jobs.py` - 删除作业

### 注意事项
1. **CLI命令准确性**：E-HPC Instant使用`aliyun ehpcinstant`命令，不是`aliyun ehpc`！
2. **区域一致性**：所有资源必须在同一区域，跨区域操作会失败
3. **配额限制**：注意账户配额限制，避免操作失败
4. **成本意识**：作业运行会产生费用，及时清理不需要的资源
5. **权限最小化**：为AccessKey配置最小必要权限，提高安全性

## 故障排查与最佳实践

### 常见问题解决方案
| 问题 | 根本原因 | 解决方案 |
|------|---------|----------|
| **InvalidCommand错误** | Command参数格式不正确 | 使用正确的JSON数组格式：`["/bin/sh", "-c", "command"]` |
| **认证失败** | AccessKey配置错误或权限不足 | 检查`~/.aliyun/config.json`配置，确保具备E-HPC Instant权限 |
| **镜像不存在** | 镜像ID错误或区域不匹配 | 确认镜像ID正确且在相同区域，参考[references/instant-image.md](./references/instant-image.md) |
| **网络配置错误** | VSwitch ID错误或不可用 | 检查VSwitch ID和安全组配置，参考[references/vswitch.md](./references/vswitch.md) |
| **资源配额不足** | 账户配额限制 | 联系阿里云增加配额，或调整资源配置 |
| **命令执行失败** | 容器内命令路径错误 | 确保命令在镜像环境中可执行，使用绝对路径 |

### 最佳实践指南
1. **命名规范**：
   - 作业名称：`应用-算例-时间戳`（如：`prod-training-20260411`）
   - 资源名称：包含用途、环境、区域信息

2. **资源配置优化**：
   - 根据应用特性选择合适的实例规格
   - 避免过度配置造成资源浪费

3. **成本控制**：
   - 及时清理已完成的作业
   - 使用适当的作业超时设置
   - 监控资源使用情况

4. **可靠性保障**：
   - 实现作业状态监控和重试机制
   - 配置适当的错误处理和告警
   - 定期备份重要配置和数据

5. **安全性增强**：
   - 使用私有镜像仓库
   - 配置最小权限的AccessKey
   - 启用网络访问控制和加密

## 参考资料与扩展

### 完整API参考
如仍有作业管理执行参数不确定，可参考如下链接:
- [references/ehpcinstant.md](./references/ehpcinstant.md) - E-HPC Instant完整CLI命令手册
- CLI帮助命令：`aliyun ehpcinstant <ApiName> --help`

### 专项配置指南
- [references/aliyun-cli.md](./references/aliyun-cli.md) - 阿里云CLI配置指南
- [references/instant-image.md](./references/instant-image.md) - 镜像管理指南
- [references/vswitch.md](./references/vswitch.md) - 网络vSwitch管理指南
- [references/storage.md](./references/storage.md) - NAS存储管理指南
- [references/resource.md](./references/resource.md) - 计算资源配置指南
- [references/job-command.md](./references/job-command.md) - 作业命令配置指南

### 官方文档
- 阿里云E-HPC Instant产品文档：https://help.aliyun.com/product/ehpcinstant.html
- E-HPC Instant API文档：https://api.aliyun.com/document/EhpcInstant/2023-07-01/overview
- 阿里云CLI官方文档：https://help.aliyun.com/document_detail/121529.html

## 安全策略与风险控制

### 操作风险等级分类
| 风险级别 | 操作类型 | Agent行为准则 |
|---------|---------|--------------|
| **低风险** | 查询类操作 (list, get, check, describe) | 直接执行，无需额外确认 |
| **中风险** | 配置类操作 (configure, modify, update) | 提示影响范围，获得用户确认后执行 |
| **高风险** | 创建/删除类操作 (create, delete, remove) | **必须完整展示所有配置信息，用户明确确认后执行** |

> **[MUST] 禁止跳过 API 调用** — Agent 在执行删除等操作时，不得基于查询结果（如 GetJob 返回 NotFound）自行判定"无需操作"而跳过实际的 API 调用。查询与变更之间存在时间窗口，服务端状态可能已变化。Agent 必须始终执行用户请求的目标 API（如 DeleteJobs），由服务端返回权威的最终结果。

### 安全检查清单
- ✅ **区域一致性**：确保所有资源在同一区域
- ✅ **配额检查**：验证资源配额是否充足
- ✅ **依赖验证**：确认依赖资源（镜像、网络、存储）存在且可用
- ✅ **权限验证**：确保AccessKey具备必要权限
- ✅ **成本提醒**：对于可能产生较高费用的操作给予提醒

### 敏感操作确认流程
1. **信息汇总**：展示所有关键配置参数
2. **影响说明**：说明操作的影响范围和潜在风险
3. **用户确认**：等待用户明确确认（"是"、"确认"、"继续"等）
4. **执行操作**：执行确认后的操作
5. **结果反馈**：提供详细的操作结果和后续建议