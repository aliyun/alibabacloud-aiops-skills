# SLS 函数参考文档

本目录包含 SLS SQL 和 SPL 分析语句支持的所有函数，按功能分类。

## 目录结构

| 文件 | 类别 | 描述 | 支持 |
|------|------|------|------|
| `aggregate.yaml` | 聚合函数 | count、sum、avg、max、min 等统计函数 | SQL |
| `string.yaml` | 字符串函数 | 文本拼接、截取、大小写转换、查找替换 | SQL + SPL |
| `regex.yaml` | 正则表达式函数 | 正则匹配、提取、替换 | SQL + SPL |
| `datetime.yaml` | 日期时间函数 | 时间格式化、解析、截断、转换 | SQL + SPL |
| `type_conversion.yaml` | 类型转换函数 | cast、try_cast 类型转换 | SQL + SPL |
| `conditional.yaml` | 条件函数 | if、case、coalesce 条件判断 | SQL + SPL |
| `json.yaml` | JSON函数 | JSON 数据提取和解析 | SQL + SPL |
| `math.yaml` | 数学函数 | 数值计算、取整、幂运算 | SQL + SPL |
| `url.yaml` | URL函数 | URL 解析和参数提取 | SQL + SPL |
| `ip_geo.yaml` | IP地理位置函数 | IP 转省份、城市、国家、经纬度 | 仅SPL |
| `encoding.yaml` | 编码解码函数 | URL、Base64 编码解码 | SQL + SPL |
| `hash.yaml` | 哈希函数 | MD5、SHA1、SHA256 哈希计算 | SQL + SPL |

## 使用说明

### 1. 查找函数

- **按功能查找**：根据上表选择对应的分类文件
- **按名称查找**：在对应分类的 YAML 文件中查找具体函数
- **按场景查找**：参考 `overview.yaml` 中的常见场景示例

### 2. 查看函数详情

每个 YAML 文件包含以下信息：

```yaml
functions:
  - name: 函数名
    syntax: 函数语法
    description: 功能描述
    examples:
      sql: SQL 示例
      spl: SPL 示例
    note: 注意事项（可选）
```

### 3. 重要提示

#### 类型转换
- 字段默认为 VARCHAR 类型
- 数值比较和运算前必须使用 `cast()` 或 `try_cast()` 转换
- SPL 中尤其需要注意类型转换

示例：
```sql
-- ✅ 正确
* | SELECT * WHERE cast(status as BIGINT) >= 500

-- ❌ 错误
* | SELECT * WHERE status >= 500
```

#### SQL vs SPL
- **SQL**：使用 SELECT、WHERE、GROUP BY 语法
- **SPL**：使用 extend、where、stats 语法
- **聚合函数**主要用于 SQL
- **IP地理函数**仅用于 SPL

#### 正则表达式
- SPL 使用 RE2 正则引擎
- 不支持：后向引用(\1)、环视(?<=...)等
- 反斜杠不需要双重转义：`\d` 直接写 `\d`

## 快速示例

### 统计分析
```sql
-- 按状态码统计
* | SELECT status, count(*) AS pv GROUP BY status ORDER BY pv DESC
```

### 时间分组
```sql
-- 按小时统计
* | SELECT date_trunc('hour', __time__) AS hour, count(*) AS pv GROUP BY hour
```

### 正则提取
```sql
-- 提取错误码
* | SELECT regexp_extract(message, 'code:(\d+)', 1) AS error_code, count(*) GROUP BY error_code
```

### JSON 解析
```sql
-- 提取 JSON 字段
* | SELECT json_extract_scalar(payload, '$.user.name') AS user, count(*) GROUP BY user
```

### IP 地理分析（SPL）
```spl
# 按省份统计
* | extend province = ip_to_province(client_ip) | stats pv = count(*) by province
```

## 相关文档

- [函数索引](./overview.yaml) - 函数分类索引和使用指南
- [SQL 查询语法](../query_analysis/sql.yaml) - SQL 查询完整语法
- [SPL 基础语法](../spl/overview.yaml) - SPL 查询基础
- [索引查询](../query_analysis/indexSearch.yaml) - 关键字搜索语法
