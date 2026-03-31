import json

# 定义了文件元数据搜索的查询语法json结构
param_schema = {
    "type": "object",
    "properties": {
        "Query": {
            "type": "object",
            "$id": "#query",
            "description": "定义了用于文件元数据搜索的查询条件。支持嵌套的查询结构。",
            "properties": {
                "Operation": {
                    "type": "string",
                    "enum": ["not", "or", "prefix", "and", "lt", "match", "gte", "eq", "lte", "gt"],
                    "description": "必需字段。指定操作的类型。可用的操作包括：\n- 逻辑操作符：and, or, not (需要 SubQueries 参数)\n- 比较操作符：lt, lte, gt, gte, eq\n- 字符串操作：prefix, match-phrase",
                    "examples": ["and"]
                },
                "Field": {
                    "type": "string",
                    "description": "指定要查询的元数据字段名。除了逻辑操作符（and, or, not）之外，所有操作都必须提供此字段。",
                    "examples": ["Size"]
                },
                "Value": {
                    "type": "string",
                    "description": "要查询的目标值。所有类型的值（包括数字和时间戳）都必须以字符串形式提供。不适用于逻辑操作符（and, or, not）。",
                    "examples": ["10"]
                },
                "SubQueries": {
                    "type": "array",
                    "description": "当操作为逻辑操作符（and, or, not）时，此字段为必需。它包含一组嵌套的查询条件，这些条件遵循父操作符的逻辑。例如，当父操作的 Operation 为 'and' 时，SubQueries 中的所有条件必须同时满足（AND 逻辑）。",
                    "items": {
                        "$ref": "#query"
                    }
                }
            }
        },
        "Sort": {
            "type": "string",
            "description": "定义排序所依据的字段，多个字段之间用逗号分隔。最多可以指定5个字段。字段的顺序决定了排序的优先级。例如：'Size,Filename'",
            "examples": ["Size,Filename"]
        },
        "Order": {
            "type": "string",
            "enum": ["asc", "desc"],
            "description": "指定 Sort 字段中每个字段的排序顺序。可选值：\n- asc: 升序（默认值）\n- desc: 降序\n可以使用逗号分隔来为多个字段指定不同的排序顺序（例如：'asc,desc'）。顺序的数量不能超过 Sort 字段的数量。如果某个字段的顺序未指定，则默认为 'asc'。",
            "examples": ["asc,desc"]
        }
    },
    "required": []
}


# 定义了文件元数据的字段和对应的值类型
field_schema = {
    "parent_file_id": {
        "type": "string",
        "description": "父文件夹 ID。",
        "examples": ["root"]
    },
    "name": {
        "type": "string",
        "description": "文件名（支持 match 模糊匹配）。",
        "examples": ["sampleobject.jpg"]
    },
    "type": {
        "type": "string",
        "enum": ["file", "folder"],
        "description": "文件类型：file（文件）、folder（文件夹）。",
        "examples": ["file"]
    },
    "file_extension": {
        "type": "string",
        "description": "文件后缀（不含点），如 pdf、jpg。",
        "examples": ["pdf"]
    },
    "description": {
        "type": "string",
        "description": "描述（single_word分词），可短语匹配。",
        "examples": ["项目文档"]
    },
    "mime_type": {
        "type": "string",
        "description": "表示文件格式的MIME类型。",
        "examples": ["image/jpeg"]
    },
    "starred": {
        "type": "boolean",
        "description": "是否收藏。",
        "examples": ["true"]
    },
    "created_at": {
        "type": "date",
        "description": "创建时间（UTC），格式为 2006-01-02T00:00:00。",
        "examples": ["2025-01-01T00:00:00"]
    },
    "updated_at": {
        "type": "date",
        "description": "最后修改时间（UTC），格式为 2006-01-02T00:00:00。",
        "examples": ["2025-01-01T00:00:00"]
    },
    "status": {
        "type": "string",
        "description": "文件状态：available（可用）。",
        "examples": ["available"]
    },
    "hidden": {
        "type": "boolean",
        "description": "是否隐藏文件。",
        "examples": ["false"]
    },
    "size": {
        "type": "long",
        "description": "文件大小，单位为字节（bytes）。",
        "examples": ["1000"]
    },
    "image_time": {
        "type": "date",
        "description": "图片或视频的拍摄时间（来自 EXIF），格式为 2006-01-02T00:00:00。",
        "examples": ["2025-01-01T00:00:00"]
    },
    "last_access_at": {
        "type": "date",
        "description": "最近一次访问的时间，格式为 2006-01-02T00:00:00。",
        "examples": ["2025-01-01T00:00:00"]
    },
    "category": {
        "type": "string",
        "enum": ["image", "video", "audio", "doc", "app", "others"],
        "description": "文件分类：image（图片）、video（视频）、audio（音频）、doc（文档）、app（应用）、others（其他）。",
        "examples": ["image"]
    },
    "label": {
        "type": "string",
        "description": "系统标签名称。",
        "examples": ["风景"]
    },
    "face_group_id": {
        "type": "string",
        "description": "人脸分组ID，由分组列表接口获取，通过该字段进行查询分组下的照片。",
        "examples": ["group-id-xxx"]
    },
    "address": {
        "type": "string",
        "description": "地址，只能选择一个行政等级查询，如想查国家则填'中国'，查省份则填'浙江省'，查城市则填'杭州市'，区县则填'西湖区'或'桐庐县'、街道或镇则填'西溪街道'或'三墩镇'。",
        "examples": ["杭州市"]
    }
}

# 标准标量查询的 json schema
def get_json_schema(param_schema: dict) -> dict:
    json_schema = {
        "type": "object",
        "properties": {
            "valid": {
                "type": "boolean",
                "description": "一个布尔标志，用于指示用户的输入是否能够映射到所定义的查询模式。在以下两种情况下，该值将为 `false`：1) 输入中不包含任何针对已定义字段的可识别关键词。2) 输入中仅包含用于未在模式（schema）中定义的字段的术语（例如，按 'color' 或 'importance' 进行查询）。"
            }, 
            "result": param_schema
        }, 
        "required": ["valid"]
    }
    return json_schema


# 描述了是否需要用标准标量查询来搜索文件，以及如何提取标量查询的参数
def schalar_search_prompt() -> str:
    output = f"""
# 任务

我需要你将自然语言转换为数据库查询参数：

{json.dumps(param_schema, ensure_ascii = False, indent = None)}

## 查询字段定义

{json.dumps(field_schema, ensure_ascii = False, indent = None)}

## 查询字段校验

在处理任何查询之前，你必须：
1. 仅处理明确引用到已定义字段的查询。
2. 如果输入查询违反此规则（例如不包含对任何已定义字段的引用，或只包含无法映射的术语），你必须返回一个输出，其中 "valid" 设为 false。

应返回 {json.dumps({"valid": False}, ensure_ascii = False)} 的查询示例：
- "乐山大佛"（未指定字段，不要假设是文件名）
- "红色的"（color 不是已定义字段）
- "重要文件"（importance 不是已定义字段）

不应判定为无效的查询示例：
- "图片文件"（category eq image）

## 查询操作使用指南

每个操作都有特定的使用场景与语义：

### 数值比较操作

- 'eq'：精确相等比较（"等于"、"是"、"为"）
- 'gt'：大于（"大于"、"超过"）
- 'gte'：大于等于（"大于等于"、"不少于"）
- 'lt'：小于（"小于"、"低于"）
- 'lte'：小于等于（"小于等于"、"不超过"）

### 文本检索操作

- 'match'：用于在字段内检索特定文本内容（"包含文字"、"内容有"）
- 'prefix'：用于路径/URI 前缀匹配（"目录下"、"文件夹中"）或字符串前缀匹配

### 逻辑操作

- 'and'：所有条件均需为真（"且"、"并且"、"同时"）
- 'or'：任一条件为真即可（"或者"、"或"）
- 'not'：对条件取反（"不"、"非"）

## 排序与顺序使用指南

### 排序（Sort）

支持最多 5 个用逗号分隔的排序字段，字段顺序决定排序优先级。常见用法：
- 单字段："size"
- 多字段："size,name"（先按 size 排序，若 size 相同再按 name 排序）

常见表达：
- "按大小排序" -> "size"
- "按拍摄时间排" -> "image_time"
- "按名称排列" -> "name"
- "先按大小再按时间排序" -> "size,image_time"

推荐字段组合：
- "size,name"：适用于按文件大小排序，并保证同大小文件的稳定顺序
- "image_time,name"：适用于按时间顺序列出，并保证确定性的次序
- "name"：按字母顺序列出

### 顺序（Order）

用逗号分隔指定排序方向：
- "asc"：升序（"升序"、"从小到大"）
- "desc"：降序（"降序"、"从大到小"）

如果指定的 Order 值少于 Sort 字段数，剩余字段默认使用 "asc"。例如：
- Sort: "Size,FileModifiedTime,Filename", Order: "desc" -> 等价于 Order: "desc,asc,asc"

## 重要使用说明

1. 'match' 只能用于文件名（name）和描述（description）的检索
2. 'prefix' 不可用于文件名（name）的前缀匹配
3. **遵循简约原则**：构造查询时，应严格避免过度推断。只添加用户输入中明确要求的过滤条件。例如，若用户没有提及文件名，则查询中不得包含 `name` 相关的条件。此原则适用于所有字段。
""".strip()
    output += "\n\n"
    output += """
## 示例

### 示例 1

一些自然语言输入可能较为口语化并使用缩写。示例：

"文件的mime类型为docx"

你应优先将口语化缩写转换为其完整形式：

{'Query': {'Operation': 'eq', 'Field': 'mime_type', 'Value': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'}}

"搜索pdf文件"

你应优先将口语化缩写转换为其完整形式：

{'Query': {'Operation': 'eq', 'Field': 'extension', 'Value': 'pdf'}}

### 示例 2：时间范围查询

时间表达通常意味着区间，而非单一时间点。示例：

UserQueryDatetime: 2025-05-26T11:33:52+08:00
输入："6月6日创建的文件"
应转换为整天范围，且必须采用UTC时间，因此对于北京时间的6月6日的一整天，对应的UTC起始时间应为2025-06-05T16:00:00，结束时间应为2025-06-06T16:00:00。一天的起始时间（以及结束时间边界）必须始终严格为 16:00:00。不要在日界限使用非零的分钟/秒：
{"Query": {"Operation":"and","SubQueries":[{"Operation":"gte","Field":"image_time","Value":"2025-06-05T16:00:00"},{"Operation":"lt","Field":"image_time","Value":"2025-06-06T16:00:00"}]}}

UserQueryDatetime: 2025-05-26T11:33:52+08:00
输入："最近三个半小时访问过"
应转换为UTC时间跨度：
{"Query": {"Operation":"and","SubQueries":[{"Operation":"gte","Field":"last_access_at","Value":"2025-05-26T00:03:52"},{"Operation":"lte","Field":"last_access_at","Value":"2025-05-26T03:33:52"}]}}

关键模式：
- 日期 = 整天范围
- "最近" = 到当前时间为止的区间
- "之前/之后" = 带边界的区间
- 最后必须统一从北京时间转换为UTC时间，时间在“秒”之后就结束，不带任何毫秒、时区信息。

### 示例 3：语言一致性

始终保持输出与输入查询相同的语言。例如：

输入："查找文件名为蛋糕的文件"
正确：{"Query": {"Operation": "eq", "Field": "name", "Value": "蛋糕"}}

错误：{"Query": {"Operation": "eq", "Field": "name", "Value": "cake"}}

### 示例 4：时间字段选择

四个不同的时间字段：
- image_time：用于图片的拍摄时间
  * 示例："2023年夏天拍的照片" -> 使用 image_time
- last_access_at：上次从云盘访问图片的时间
  * 示例："昨天访问的文件" -> 使用 last_access_at
- create_at：将文件上传到云盘或者在云盘中创建的时间
  * 示例："昨天新建的文件" -> 使用 create_at
  * 示例："昨天上传的文件" -> 使用 create_at
- update_at：文件最后更新的时间
  * 示例："昨天更新的文件" -> 使用 update_at

关于照片拍摄时间的查询，始终优先使用 image_time。

### 示例 5：基础排序

输入："查找大于1GB的文件并按大小降序排列"
{"Query": {"Operation": "gt", "Field": "size", "Value": "1073741824"}, "Sort": "size", "Order": "desc"}

### 示例 6：多字段排序

输入："查找docx文件,按修改时间降序,同时按名称升序排列"
{"Query": {"Operation": "eq", "Field": "mime_type", "Value": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}, "Sort": "image_time,name", "Order": "desc,asc"}

### 示例 7：纯排序（无查询条件）

输入："所有文件按名称排序"
{"Sort": "name"}

### 示例 8：多字段排序且使用默认顺序

输入："所有文件按大小和创建时间排序"
{"Sort": "size,image_time"}

### 示例 9：查询简化
输入："文档文件或文本文件"
{"Query": {"Operation": "eq", "Field": "category", "Value": "doc"}}
"""
    output += "\n\n"
    json_schema = get_json_schema(param_schema = param_schema)
    output += f"""
## JSON 输出格式

你的输出必须严格遵守以下 JSON 模式：

```json
{json.dumps(json_schema, indent = None, ensure_ascii = False)}
```

### 输出要求

- 你的响应必须是一个单一的、有效的 JSON 对象。
- 至关重要：不要在 JSON 对象之外添加任何说明文字、注释或其他内容。你的整个响应必须只包含该 JSON。
""".strip()
    return output


if __name__ == "__main__":
    print(schalar_search_prompt())
