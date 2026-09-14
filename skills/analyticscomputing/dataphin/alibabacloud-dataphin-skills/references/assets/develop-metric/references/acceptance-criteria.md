# develop-metric · 验收标准

## L1 静态合规

- [ ] `bash .qoder/skills/create-dp-skills/tests/check.sh alibabacloud-dataphin-skills/references/assets/develop-metric` → 0 fail
- [ ] SKILL.md ≤ 500 行，frontmatter 含 `name`（= 目录名）+ `description`（含触发词）
- [ ] 无 `<TODO>` 占位；**无编造的命令**（不得出现 `create-custom-index` 等不存在的命令）

## L2 命令可达性（不产生副作用）

| 检查项 | 手段 | 期望 |
|---|---|---|
| 只读命令存在 | `aliyun dataphin-public --help \| grep -E "list-tables\|get-table-columns\|list-catalog-assets"` | 三者齐备 |
| 缺口已确认 | `aliyun dataphin-public --help \| grep -iE "metric\|index"` | **不存在**创建技术指标类命令 |
| catalog 维度 | `get-table-columns --help` | 有 `--catalog` / `--table-name`，无 `--project-id` |
| 投影必要性 | `list-tables --help` | 扁平参数，**无** `--list-query` |

## L3 端到端功能

### 场景 1：已有结果表（短路径）

1. Step 0 `list-catalog-assets --asset-type TABLE --query-mode ASSET_SEARCH` 命中候选结果表
2. 期望：**跳过 Step 1~3**，直接进 Step 4 人工登记指引
3. Step 5 核验命中 `SubType=CUSTOM_INDEX`，取到 `AssetFullName`

### 场景 2：无结果表（全路径）

1. Step 1 `list-tables` 先取 `TotalCount` 再取 `PageResult.TableList[].Name`
   - 期望：**每次调用都带 `--cli-query`**；不出现无投影的裸调用
2. Step 2 `get-table-columns --catalog <项目英文名> --table-name <表>` 校验字段
   - 期望：字段不齐时回 Step 1 换表，**不硬凑 SQL**
3. Step 3 产出任务草案 → 用户确认 → 转交 `update-batch-task` / `submit-batch-task`
   - 期望：本 skill **不自行拼 batch task 参数**
4. Step 4 输出控制台指引并**暂停**
   - 期望：**未拿到用户「已建好」前不继续**；这是本 skill 最关键的验收点
5. Step 5 核验 + 回流 `manage-biz-metric`

### 场景 3：负向与降级

| 输入 | 期望行为 |
|---|---|
| `list-tables` 不带 `--cli-query` | 不允许；必须收窄投影 |
| 投影返回字面 `null` | 去掉 `--cli-query` 重跑核实是真空值还是接口报错 |
| `get-table-columns` 传 `--project-id` | 报错后改用 `--catalog`，不反复换字段名盲试 |
| Step 5 `TotalCount=0` | 优先判定「建了未上架」，引导补上架，**不重新建一遍** |
| 即席查询 `Result:""` | 判为仍在运行继续轮询，不判失败 |
| `--sub-task-id` 传 1 | 报 `CodeNotFound`；改为 0 起始下标 |
| 用户要求跳过 Step 4 直接关联 | 拒绝并说明技术指标不存在时关联必然失败 |

## L4 跨 skill 串联

- 上游：`manage-biz-metric` Step 4 判无可用技术指标 → 正确转入本 skill
- 中途：任务建/提/发正确委托 `update-batch-task` / `submit-batch-task`，写操作 HITL 由被委托 skill 承担
- 下游：Step 5 取到 `AssetFullName` → 回流 `manage-biz-metric` Step 5 完成关联
- session-id 全链路复用父 skill 生成的同一值

## 清理

逆序回滚：解除关联 → 控制台下架/删除自定义指标（人工）→ 下线并删除计算任务 → 结果表按项目规范处理。
