# 相关命令与内部接口边界

## 公开 CLI 可用命令

当前 `create-project` 只能使用公开 `dataphin-public` 项目查询、依赖校验、白名单和成员管理命令；不能直接创建、更新或删除项目本体。

| 命令 | OpenAPI | 用途 | 类型 |
|---|---|---|---|
| `list-projects` | `ListProjects` | 分页查询项目列表 | 读 |
| `get-project` | `GetProject` | 通过项目 ID 获取项目详情 | 读 |
| `get-project-by-name` | `GetProjectByName` | 通过项目名获取项目详情 | 读 |
| `check-project-has-dependency` | `CheckProjectHasDependency` | 检查项目是否被任务等对象依赖 | 读 |
| `get-project-white-lists` | `GetProjectWhiteLists` | 获取项目白名单 | 读 |
| `replace-project-white-lists` | `ReplaceProjectWhiteLists` | 替换项目白名单 | 写 |
| `list-project-members` | `ListProjectMembers` | 查询项目成员列表 | 读 |
| `add-project-member` / `update-project-member` / `remove-project-member` | 项目成员管理 | 成员增删改，建议交给 `manage-project-member` | 写 |

## 当前未暴露的项目生命周期能力

以下能力在 autotest / 页面内部 REST 中存在业务语义，但未出现在当前 `aliyun dataphin-public --help` 的公开项目命令中。

| 内部 REST 语义 | 业务用途 | 外部 Skill 处理方式 |
|---|---|---|
| `/api/project/basic` | 创建 Basic 模式项目 | 仅作为语义参考，不执行 |
| `/api/project/update` | 更新项目信息 | 仅作为语义参考，不执行 |
| `DELETE /api/project/{projectId}` | 删除项目 | 仅作为语义参考，不执行 |
| `/api/datacatalog/project/search` | 页面项目搜索与创建后验证 | 公开替代为 `get-project-by-name` / `list-projects` |
| `/api/v1/schedule/resource/config/list` | 获取调度资源组 | 仅作为语义参考，不执行 |
| `/api/project/relation` | 查询项目依赖关系 | 公开替代为 `check-project-has-dependency` |

## 参数清单

| 参数 | 来源 | 说明 |
|---|---|---|
| `tenant-id` | 用户确认 | 租户 ID，大整数建议字符串传 |
| `project-name` | 用户确认 | 项目英文名或项目名，用于查重 |
| `project-id` | 公开查询回读 | 项目 ID，用于详情、依赖、白名单、成员管理 |
| `project-display-name` | 用户确认 | 项目显示名 |
| `project-mode` | 用户确认 | `BASIC` 或 `DEV_PROD` |
| `biz-unit-id` | 用户确认 | 所属数据板块 ID |
| `compute-engine-id` | 用户确认 | 项目绑定计算源 |
| `resource-group-id` | 内部创建链路需要 | 调度资源组 ID；当前公开 CLI 不负责获取 |
| `white-list` | 用户确认 / 回读 | 更新白名单前必须先回读存量 |
| `member-list` | 用户确认 | 项目成员与角色，建议路由到 `manage-project-member` |

## 正确公开检查示例

```bash
TENANT_ID="<租户 ID>"
SESSION_ID="<inherited from alibabacloud-dataphin-skills>"
UA="AlibabaCloud-Agent-Skills/create-project/$SESSION_ID"

aliyun dataphin-public get-project-by-name --tenant-id "$TENANT_ID" \
  --project-name "dummy_practice_dev" \
  --user-agent "$UA" --format json

aliyun dataphin-public list-projects --tenant-id "$TENANT_ID" \
  --page-no 1 --page-size 10 \
  --user-agent "$UA" --format json

aliyun dataphin-public check-project-has-dependency --tenant-id "$TENANT_ID" \
  --project-id "<项目ID>" \
  --user-agent "$UA" --format json
```

## 白名单写操作示例

`replace-project-white-lists` 是覆盖式写操作，执行前必须先回读旧值并让用户确认。

```bash
aliyun dataphin-public get-project-white-lists --tenant-id "$TENANT_ID" \
  --project-id "<项目ID>" \
  --user-agent "$UA" --format json

# 仅在用户确认后执行。具体参数以 --help 输出为准。
aliyun dataphin-public replace-project-white-lists --help
```

## 常见错误

| 错误做法 | 风险 | 正确做法 |
|---|---|---|
| 写 `create-project` 命令 | 当前公开 CLI 无此命令 | 先验证 `dataphin-public --help`，输出能力缺口 |
| 用内部 `/api/project/basic` 执行 | 绕过公开 OpenAPI 边界 | 仅作为语义参考 |
| 不查重就申请项目 | 项目名冲突或重复申请 | 先 `get-project-by-name` |
| 混淆 Basic / DevProd | 后续发布和清理口径错误 | 创建前必须确认项目模式 |
| 覆盖项目白名单 | 误删存量白名单 | 先回读、合并、确认再替换 |
| 删除前不查依赖 | 删除失败或破坏对象链路 | 先 `check-project-has-dependency` |

## 业务边界

- 本 Skill 不直接创建项目，不调用内部 REST，也不绕过公开 OpenAPI 权限边界。
- 成员管理建议路由到 `manage-project-member`，本 Skill 只整理成员初始化需求。
- 若未来公开 OpenAPI 增加项目创建/删除命令，应更新本文件、RAM 策略和 L2/L3 测试报告后再允许写操作。
