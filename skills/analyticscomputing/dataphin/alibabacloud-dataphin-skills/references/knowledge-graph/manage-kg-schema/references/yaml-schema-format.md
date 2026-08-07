# KG Schema YAML 格式参考

## 完整示例

```yaml
name: 我的知识图谱
description: 示例 Schema 描述
workspaceId: "{WorkspaceId}"
entityTypes:
- code: COMPANY
  icon: icon-XF-yuancangzuhu-xian1 v2
  name: 公司
  useSysPk: false
  description: 企业实体
  properties:
  - isRequired: true
    isIndexed: true
    code: name
    defaultValue: ''
    dataType: STRING
    name: 公司名称
    description: 公司全称
    isPrimaryKey: true
    isUsedShow: true
  - isRequired: false
    isIndexed: true
    code: credit_code
    defaultValue: ''
    dataType: STRING
    name: 统一社会信用代码
    description: 18 位统一社会信用代码
    isPrimaryKey: false
    isUsedShow: false
  - isRequired: false
    isIndexed: false
    code: registered_capital
    defaultValue: ''
    dataType: FLOAT
    name: 注册资本
    description: 注册资本（万元）
    isPrimaryKey: false
    isUsedShow: false
- code: PERSON
  icon: icon-XF-yuancangzuhu-xian1 v2
  name: 人物
  useSysPk: true
  description: 自然人实体（使用系统主键）
  properties:
  - isRequired: true
    isIndexed: true
    code: person_name
    defaultValue: ''
    dataType: STRING
    name: 姓名
    description: 人物姓名
    isPrimaryKey: false
    isUsedShow: true
  - isRequired: false
    isIndexed: false
    code: birth_date
    defaultValue: ''
    dataType: DATE
    name: 出生日期
    description: 出生日期
    isPrimaryKey: false
    isUsedShow: false
relationTypes:
- targetEntityCode: COMPANY
  code: WORK_AT
  hasDirection: true
  name: 任职于
  cardinalType: ONE_TO_MANY
  description: 人物在公司任职
  sourceEntityCode: PERSON
  properties:
  - isRequired: false
    isIndexed: false
    code: title
    defaultValue: ''
    dataType: STRING
    name: 职位
    description: 职位名称
    isPrimaryKey: false
    isUsedShow: false
```

## 字段说明速查

### 顶层
| 字段 | 必填 | 说明 |
|------|------|------|
| `name` | 否 | 空间名称 |
| `description` | 否 | 描述 |
| `workspaceId` | 否 | 空间 ID（不参与写入） |
| `entityTypes` | 条件 | 实体类型列表（与 relationTypes 至少一个非空） |
| `relationTypes` | 条件 | 关系类型列表 |

### 实体类型
| 字段 | 必填 | 说明 |
|------|------|------|
| `code` | 是 | 大写字母开头，仅含 A-Z/0-9/_ |
| `name` | 是 | 显示名称 |
| `useSysPk` | 否 | `true`=系统主键（`_sys_id`），`false`=业务主键 |
| `icon` | 否 | 图标标识符 |
| `properties` | 是 | 属性列表 |

### 关系类型
| 字段 | 必填 | 说明 |
|------|------|------|
| `code` | 是 | 关系编码 |
| `name` | 是 | 关系名称 |
| `sourceEntityCode` | 是 | 起始实体编码 |
| `targetEntityCode` | 是 | 目标实体编码 |
| `hasDirection` | 否 | 是否有向（默认 true） |
| `cardinalType` | 否 | `MULTI_TO_MULTI`/`ONE_TO_MANY`/`ONE_TO_ONE` |
| `properties` | 否 | 关系属性列表 |

### 属性定义
| 字段 | 必填 | 说明 |
|------|------|------|
| `code` | 是 | 小写字母开头，仅含 a-z/0-9/_ |
| `name` | 是 | 属性显示名称 |
| `dataType` | 是 | 全大写：`STRING`/`INTEGER`/`FLOAT`/`BOOLEAN`/`DATE`/`TIMESTAMP`/`DECIMAL` |
| `isPrimaryKey` | 否 | 是否主键（每实体至少一个 true，useSysPk=true 时全 false） |
| `isRequired` | 否 | 是否必填 |
| `isIndexed` | 否 | 是否索引 |
| `isUsedShow` | 否 | **是否用于展示（每实体至少一个 true）** |
| `defaultValue` | 否 | 默认值，无默认值传空字符串 `''` |

## 常见错误

| 错误信息 | 原因 |
|----------|------|
| 至少包含一个主键属性或者配置系统主键 | useSysPk=false 但无 `isPrimaryKey: true` 属性 |
| 至少包含一个用于展示的属性 | 无 `isUsedShow: true` 属性 |
| 属性编码格式不合法 | code 须小写字母开头，仅含小写字母/数字/下划线 |
| 实体类型编码不能为空 | 缺少 `code` 字段 |
