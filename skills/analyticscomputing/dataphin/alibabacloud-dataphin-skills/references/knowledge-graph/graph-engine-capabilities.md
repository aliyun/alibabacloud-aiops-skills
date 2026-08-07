# 知识图谱图引擎能力矩阵（Neo4j / Lindorm 图引擎）

> **本文件是 KG 三个子 skill 的共享事实源**。查询语言、属性数据类型、业务识别规则都随图引擎变化——动手前先确认空间绑的是哪个引擎。
>
> 事实来源：Dataphin V6.2.3「新增 Lindorm 图引擎适配说明」+ 工作台 trace `f3781307` 实测（env21 Lindorm 空间）。
>
> 适用版本：Lindorm 图引擎自 **V6.2.3** 起支持。图数据库 GDB 亦在规划中，本文件暂不覆盖。

## 1. 先确认引擎（硬前置）

知识图谱空间在创建时绑定一个图引擎数据源，之后不可跨源类型切换。**OpenAPI 没有「查图谱空间详情/引擎」的接口**（全部 KG 命令中无 list/get-workspace 类命令），因此引擎只能来自：

1. 用户直接告知；
2. Dataphin 控制台「知识图谱 → 空间配置」页；
3. Dataphin 智能工作台右栏「图谱空间」条目上的引擎标签。

**不要默认按 Neo4j 处理**——在 Lindorm 空间上按 Neo4j 心智操作，会直接撞上下面的 Cypher 空洞。

## 2. 图查询能力（差异最大，务必先看）

| 能力 | Neo4j | Lindorm 图引擎 |
|---|---|---|
| `ExecKgCypher`（Cypher 查询） | ✅ 支持 | ❌ **不支持**（Lindorm 实测：返回 `DPN.Commons.InternalError`） |
| `ExecKgGremlin`（Gremlin 查询） | ❌ 不适用 | ⚠️ **API 规划中，尚未上线**（CLI 插件 0.7.x 实测无 `exec-kg-gremlin` 命令） |
| `GetKgNeighbor`（邻居遍历） | ✅ | ✅ **Lindorm 实测通过** |
| `SearchKgBySemantic`（关键词+语义混合搜索，V6.2.3 新增） | ✅ | ✅ **Lindorm 实测通过** |
| `ListKgEntity` / `GetKgEntity` / `ListKgRelation` / `GetKgRelation` | ✅ | ✅ **Lindorm 实测通过**（含 `--list-query` 的 `Keyword` 模糊过滤） |
| 控制台图谱视图 / 路径发现 | ✅ | ✅（语义检索能力随引擎实现差异） |

> “**Lindorm 实测通过**”= 已在 V6.2.3 环境的 Lindorm 图引擎空间上真实调用成功，不再仅靠适配说明推定（工作台 trace `743fc964` / `c7f7e478` / `62374e25` / `864ffe1f`）。

### Lindorm 空间的图查询正解

Gremlin OpenAPI 未上线期间，**Lindorm 空间没有自由图查询语言通道**。请组合使用引擎无关的接口：

| 目标 | 用什么 |
|---|---|
| 按类型 + 属性条件找实体 | `list-kg-entity`（`--entity-type` + `--list-query` 的 `Keyword` / `FilterList`） |
| 看某实体的关联关系 / 一度~多度邻居 | `get-kg-neighbor`（`--entity-data-id` + `--entity-type` + `--neighbors-query`） |
| 自然语言 / 近义词找实体 | `search-kg-by-semantic`（body 字段 `SearchCommand` 的 `QueryText`，**仅实体**） |
| 取某实体全部属性 | `get-kg-entity`（`--entity-type` + `--entity-id`） |
| 复杂多跳分析 / 图算法 | 引导用户到 Dataphin 控制台图谱视图完成，不要试图用 OpenAPI 拼 |

### 三条反模式（trace f3781307 实测踩过）

1. **不要在 Lindorm 空间重试 Cypher**：`DPN.Commons.InternalError` 不是环境抖动，改写语句、缩小 `Limit`、换标签都无效。
2. **不要把 Gremlin 语句塞进 `--exec-command` 的 `Query` 字段**：`exec-kg-cypher` 只解析 Cypher，传 `g.V().hasLabel('Company')` 依旧 InternalError。
3. **不要尝试 `aliyun dataphin-public exec-kg-gremlin`**：命令不存在（`aliyun dataphin-public --help` 实测 18 个 KG 命令中无此项）；也不要用 `aliyun dataphin-public --version` 探版本（该用法非法，报 `parse failed --version must be assigned with value`）。

### SearchKgBySemantic 的 body 字段名（trace fdbd9ed2 实测）

body 字段名是 **`SearchCommand`**，**不是**接口设计文档上的 `SearchKgBySemanticCommand`——后者服务端不认，报：

```
Dataphin.OpenAPI.BadRequest: Missing required argument: SearchCommand
```

命名风格与其他 KG 写/执行类接口一致（`ExecCommand` / `CreateCommand` / `UpdateCommand` / `ImportCommand`）。内层字段（`QueryText` / `EntityTypeCodes` / `PropertyCode` / `TopK` / `MinSimilarity`）按接口文档不变。

### 语义检索开启方式与向量索引（trace 72c13131 实测，fb_fed8381b4c）

**开启语义检索 = Schema 属性层开关，引擎无关**：在实体/关系属性上置 `isSemanticEnabled: true` → `import-kg-schema` → `publish-kg-schema`，平台在发布时**自动**创建向量索引（Neo4j 上为 `CREATE VECTOR INDEX em_idx_<type>_<prop> ... ON (n.__system_kg_embedding__<prop>__)`）。

- **不需要也不能用 Cypher 手建向量索引**：`exec-kg-cypher` 是只读通道，CREATE/MERGE/SET 会被拒；也不要引导用户去图库控制台手敲索引语句。
- **Neo4j 版本门槛 5.11+**：`CREATE VECTOR INDEX` 是 Neo4j 5.11+ 新语法。低版本实例发布带语义属性的 Schema 必失败，报：

  ```
  【编辑实体类型-编辑属性】属性新增向量索引：<Type>.<prop> 失败
  Invalid input 'VECTOR': expected "(", "allShortestPaths" or "shortestPath"
  ```

  这是**引擎版本限制不是操作错误**，改写/重试无效；正解：升级 Neo4j 到 5.11+，或由管理员确认实例支持向量索引（控制台可用 `CALL dbms.components() YIELD name, versions RETURN name, versions` 查版本）。
- **`publish-kg-schema` 返回 ok 只是受理**：向量索引创建等实际执行结果必须用 `get-kg-schema-publish-result` 复核（trace 中 publish `ok:true` 但索引创建实际失败），不要凭发布返回成功就宣布语义检索已开启。
- `SearchKgBySemantic` 的 `MatchSource` 全为 `keyword` 时，优先排查：目标属性未开 `isSemanticEnabled` / 发布时向量索引创建失败（引擎版本）/ 空间未配向量模型。

## 3. 属性数据类型支持

建模（`manage-kg-schema` 的 YAML `dataType`）时按引擎裁剪。「不支持」= 该引擎上不可选用，控制台对应选项隐藏。

| 分类 | 类型 | Neo4j | Lindorm |
|---|---|---|---|
| 基础 | `STRING` | ✅ String | ✅ String |
| 基础 | `INTEGER` | ✅ Long | ✅ Long |
| 基础 | `FLOAT` | ✅ Double | ✅ Double |
| 基础 | `BOOLEAN` | ✅ Boolean | ✅ Boolean |
| 基础 | `DATE` | ✅ Date | ❌ 不支持 |
| 基础 | `TIMESTAMP` | ✅ DateTime | ❌ 不支持 |
| 基础 | `LIST` | ✅ List\<T\> | ❌ 不支持 |
| 基础 | `SET`（V6.2.3 新增） | ❌ 不支持 | ✅ Set |
| 高级 | `REGEXSTRING` / `ENUM` / `URL` / `EMAIL` | ✅ String | ✅ String |
| 高级 | `DECIMAL` / `BIGINTEGER` / `DATETIMERANGE` | ❌ | ❌ |
| 高级 | `DURATION` | ✅ Duration | ❌ 不支持 |
| 空间/复杂 | `GEOPOINT` | ✅ Point | ✅ 落 String |
| 空间/复杂 | `GEOPOLYGON` / `GEOLINESTRING` / `JSON` / `BLOB` | ✅ String | ✅ String |
| 空间/复杂 | `EMBEDDED` | ✅ Map | ❌ 不支持 |
| 特殊 | `UNKNOWN` | ✅ String | ❌ 不支持 |
| 特殊 | `MAP<K,V>` | ✅ Map | ❌ 不支持 |

**Lindorm 建模替代写法**：

- 日期 / 时间戳 → `STRING` 存 ISO 8601 字串（如 `2024-01-28` / `2024-01-28T14:30:00Z`），排序与范围过滤按字符串语义；
- 多值属性 → `SET`（不是 `LIST`）；
- 嵌套对象 / 键值对 → `STRING` 存 JSON 文本，由消费方自行解析。

## 4. 业务识别规则（实体消歧）匹配策略

| 策略 | Neo4j | Lindorm |
|---|---|---|
| 精确匹配 | ✅ | ✅ |
| 忽略大小写 | ✅ | ✅ |
| 包含 | ✅ | ✅ |
| 等于 | ✅ | ✅ |
| 数值 | ✅ | ✅ |
| 语义相似度 | ✅ | ✅ |
| 编辑距离 | ✅ | ❌ 不支持（选项隐藏） |
| 日期 / 时间类型规则 | ✅ | ❌ 不支持（随 DATE/TIMESTAMP 一并隐藏） |

## 5. 数据源接入（供确认引擎与排障参考）

| 项 | Neo4j | Lindorm 图引擎 |
|---|---|---|
| 数据源类型 | Neo4j | Lindorm（连接类型选「图引擎」） |
| 连接地址格式 | `bolt://host:port` | `server_host:gremlin_port`（Gremlin 服务端口，host 为 IP 或域名） |
| Database / 子图 | 一个 Database 仅能绑定一个图谱空间 | 可选择该实例下的数据库（子图），默认 `default` |
| 多租户环境 | VPC 反向代理访问 | VPC 反向代理访问 |
| 向量索引配置 | 支持 | 支持（与 Neo4j 一致） |

## 6. 引擎无关的部分（不用为引擎分叉）

以下能力两个引擎行为一致，按各自 skill 正常操作即可：

- **知识数据 CRUD**（`manage-kg-knowledge` 的 12 个实体/关系接口）；
- **Schema 导出 / 导入 / 发布 / 查发布结果**（`manage-kg-schema` 的 4 个接口）——只是 YAML 里的 `dataType` 要按 §3 裁剪；
- **空间管理、成员与角色权限、AI 智能抽取（文档抽实体/关系）、离线集成任务写入图谱**：均为平台级能力，与图引擎无关。

## 7. 一句话决策表

| 场景 | Neo4j 空间 | Lindorm 空间 |
|---|---|---|
| 「用 Cypher 查一下…」 | `exec-kg-cypher`（节点必须带类型标签） | 说明 Cypher 不可用 → 改 `list-kg-entity` / `get-kg-neighbor` / `search-kg-by-semantic` |
| 「找出与 X 相关的实体」 | `search-kg-by-semantic` 或 Cypher | `search-kg-by-semantic` |
| 「看 X 的关系网络」 | `get-kg-neighbor` | `get-kg-neighbor` |
| 「建个带创建时间的实体类型」 | `dataType: TIMESTAMP` | `dataType: STRING`（存 ISO 字串） |
| 「按姓名近似去重」 | 可用编辑距离规则 | 用语义相似度 / 忽略大小写 / 包含 |
