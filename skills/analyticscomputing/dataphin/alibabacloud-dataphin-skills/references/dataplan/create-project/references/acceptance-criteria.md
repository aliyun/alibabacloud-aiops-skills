# 验收标准

## 功能验收

- [ ] 能识别“创建项目”“新建 Dataphin 项目”“初始化 DevProd / Basic 项目”等自然语言意图。
- [ ] 能提示当前公开 `dataphin-public` CLI 未暴露项目创建、更新、删除命令。
- [ ] 能使用 `get-project-by-name` 按项目名查重。
- [ ] 能使用 `list-projects` 分页查询项目列表。
- [ ] 能使用 `get-project` 按项目 ID 回读详情。
- [ ] 能使用 `check-project-has-dependency` 做删除/迁移前依赖检查。
- [ ] 能使用 `get-project-white-lists` 查询项目白名单。
- [ ] 能输出完整项目创建需求清单：项目名、显示名、模式、数据板块、计算源、资源组、成员、白名单、验证方式。

## 安全验收

- [ ] 不伪造 `create-project`、`update-project`、`delete-project` 等不存在的公开 CLI 命令。
- [ ] 不直接调用页面内部 `/api/project/basic`、`/api/project/update` 或 `DELETE /api/project/{projectId}`。
- [ ] 白名单更新必须先回读旧值，并确认合并后的新值。
- [ ] 项目成员初始化建议路由到 `manage-project-member`，避免本 Skill 混入成员全生命周期。
- [ ] 任何未来写操作都必须先 HITL 确认命令全文、影响范围和回滚方案。

## 业务语义验收

- [ ] 清楚区分项目查询、项目创建、项目成员管理、项目白名单管理四类能力。
- [ ] 能说明 Basic 与 DevProd 模式差异及后续发布/清理影响。
- [ ] 能说明项目是数据源、计算源、任务、成员权限等后续 Skill 的容器。
- [ ] 能说明删除项目前必须先处理任务、模型、发布对象和资源依赖。

## 测试验收

- [ ] L1 子 Skill 静态检查通过。
- [ ] L1 父套件静态检查通过。
- [ ] L2 确认 `dataphin-public --help` 无 `create-project` / `delete-project` 命令。
- [ ] L2 公开查询命令 dry-run 通过。
- [ ] L3 poc 只读验证能查询项目列表与项目详情。
- [ ] 测试报告必须同步到 Aone 开发任务正文后再修改工单状态。
