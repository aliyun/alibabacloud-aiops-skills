# 数据解读模块 (Data Insight Module)

通过 Quick BI 小Q解读开放 API，将上传的 Excel 文件（.xls / .xlsx）解析为 Markdown 表格，经 base64 编码后发送至数据解读流式接口，生成深度分析结果。

> 配置说明请参见主文件的「配置」章节。

## 环境依赖

安装命令：

```bash
pip install requests pyyaml openpyxl xlrd
```

| 依赖包 | 必要性 | 用途 |
|--------|--------|------|
| `requests` | **必需** | HTTP 请求（OpenAPI 调用、SSE 流式请求） |
| `pyyaml` | **必需** | 读取 `config.yaml` 配置文件 |
| `openpyxl` | **必需**（`.xlsx` 文件） | 解析 Office Open XML 格式的 Excel 文件 |
| `xlrd` | **必需**（`.xls` 文件） | 解析旧版 Excel 97-2003 格式的文件 |

# 前置条件

- 用户提供 `.xls` 或 `.xlsx` 格式的 Excel 数据文件
- 当数据超限或存在多文件时，Agent 必须先执行数据预处理（详见下方「数据过滤」章节）

## 数据过滤

**当满足以下任一条件时，Agent 必须在调用脚本前执行数据过滤；否则可直接调用脚本，跳过过滤：**
- 用户传入**多份 Excel 文件**
- 单个 Excel 文件的数据量**可能超过 10 万字符**（大文件）
- 用户问题有**明确的过滤条件**（如特定地区、时间范围等）

> 脚本在数据超过 10 万字符时会直接报错退出（不会截断），要求 Agent 先完成过滤后重新调用。

过滤步骤：
1. 用 Python（pandas / openpyxl）读取 Excel 文件
2. 根据用户问题，只保留与问题相关的行和列
3. 将过滤后的数据另存为新的 Excel 文件
4. 用新文件调用本脚本

```python
# 示例：用户问"华东地区销售情况"，先过滤出华东数据
import pandas as pd

df = pd.read_excel("/path/to/data.xlsx")
df_filtered = df[df["地区"] == "华东"]
df_filtered.to_excel("/tmp/filtered_data.xlsx", index=False)
# 然后用 filtered_data.xlsx 调用本脚本
```

> 若数据超限但用户问题是泛泛的"解读这份数据"，没有明确过滤条件，则保留全部列，按行截取前 N 行（确保转 Markdown 后不超过 10 万字符），并将截取后的数据另存为新文件调用。

## 数据量处理策略

脚本单次调用仅支持 **一个 Excel 文件**，且最大支持 **10 万字符**的 Markdown 数据。**超限时脚本会报错退出，不会截断数据。** 当数据超过此限制或用户传入多份 Excel 时，**调用方（Agent）必须在调用脚本之前**完成预处理。

> **用户可见性约束：**
> - 多文件合并时，向用户输出："正在整合多份数据并进行综合分析..."
> - 数据过滤时，向用户输出："正在根据您的问题进行数据过滤，缩小分析范围..."
> - 分批调用时，向用户输出："正在对数据进行分批解读并汇总结果..."
> - **禁止**向用户暴露数据量限制、字符数上限、调用失败等技术细节

### 多文件处理（用户传入多份 Excel 时必须执行）

脚本只接受单个 `--excel-file`，因此多文件场景需先合并。具体步骤：
1. 用 Python 分别读取每份 Excel
2. 根据用户问题，对每份数据进行行/列过滤，只保留与问题相关的数据
3. 将过滤后的多份数据合并为一个 Excel 文件
4. 用合并后的文件调用本技能

```python
# 示例：用户传入 3 份文件，问"华东地区销售情况"
import pandas as pd

files = ["/path/to/sales_2023.xlsx", "/path/to/sales_2024.xlsx", "/path/to/sales_2025.xlsx"]
dfs = []
for f in files:
    df = pd.read_excel(f)
    # 根据用户问题过滤相关数据
    if "地区" in df.columns:
        df = df[df["地区"] == "华东"]
    dfs.append(df)

merged = pd.concat(dfs, ignore_index=True)
merged.to_excel("/tmp/merged_data.xlsx", index=False)
# 然后用 merged_data.xlsx 调用本技能
```

#### 策略一：精细过滤（优先）

在前置过滤的基础上，若数据仍超限，进一步缩小过滤范围：减少保留的列数、增加过滤条件、限制时间范围等。

### 策略二：分批调用 + 汇总

若无法通过过滤缩减数据量，则将 Excel 按行拆分为多份（每份不超过 10 万字符），分批调用本技能，最后将各批次的解读结果合并为一份完整报告。

具体步骤：
1. 用 Python 读取 Excel，按行数拆分为多个子文件（每个子文件保留原始表头）
2. 对每个子文件依次调用 `python scripts/insight/q_insights.py "问题" --excel-file "/tmp/part_N.xlsx"`
3. 收集所有批次的解读结果
4. 将所有结果汇总，生成一份完整、连贯的分析报告，去除重复内容，保留所有关键数据和结论
5. 向用户仅输出最终合并后的报告，禁止展示中间分片结果

```python
# 示例：拆分大文件为多份
import pandas as pd
import math

df = pd.read_excel("/path/to/big_data.xlsx")
ROWS_PER_CHUNK = 500  # 根据列数调整，确保每份转 Markdown 后不超过 10 万字符
total_chunks = math.ceil(len(df) / ROWS_PER_CHUNK)

for i in range(total_chunks):
    chunk = df.iloc[i * ROWS_PER_CHUNK : (i + 1) * ROWS_PER_CHUNK]
    chunk.to_excel(f"/tmp/part_{i+1}.xlsx", index=False)
# 然后逐份调用本技能，最后汇总结果
```

## 工作流程

```mermaid
flowchart TB
  input["解读问题 + Excel 文件"] --> needFilter{"多文件 / 大文件 / 有明确过滤条件?"}
  needFilter -- 是 --> filter["Agent 根据用户问题过滤数据"]
  needFilter -- 否 --> parseExcel["解析 Excel → Markdown 表格"]
  filter --> saveFile["另存为新 Excel 文件"]
  saveFile --> parseExcel
  parseExcel --> checkLimit{"数据 ≤ 10万字符?"}
  checkLimit -- 是 --> encode["Markdown 文本 base64 编码"]
  checkLimit -- 否 --> errorExit["报错退出，要求过滤或分批"]
  encode --> interpret["POST 数据解读流式接口"]
  interpret --> parseSSE["实时解析 SSE 事件"]
  parseSSE --> reasoning["输出推理过程"]
  parseSSE --> text["输出解读结果"]
```

### 执行命令

```bash
# 通过 Excel 文件解读（支持 .xls 和 .xlsx）
python scripts/insight/q_insights.py "各分公司业绩有什么趋势？" --excel-file "/path/to/data.xlsx"
python scripts/insight/q_insights.py "这个报表有什么异常？" --excel-file "/path/to/data.xls"
```

### 内部处理流程

1. **解析 Excel 文件**：根据文件扩展名自动选择解析库（`.xlsx` → `openpyxl`，`.xls` → `xlrd`），支持多 Sheet，每个 Sheet 的第一行作为表头，转换为 Markdown 表格文本

2. **数据编码**：将 Markdown 表格文本进行 UTF-8 + base64 双重编码

3. **调用数据解读流式接口**：`POST /openapi/v2/smartq/dataInterpretationStream`，请求体为 JSON（`stringData`（base64 编码）、`userQuestion`、`modelCode`），响应为 SSE 事件流

**SSE 事件解析：**

- `reasoning` → 输出推理过程
- `text` / `summary` → 输出解读结果
- `finish` → 解读结束

## 输出说明

脚本运行时会实时输出以下内容：

- `[Excel]` Excel 文件解析状态
- `[推理过程]` AI 的分析推理
- `[解读结果]` 最终的数据解读内容
- `[完成]` 解读结束

## 关键接口

| 接口 | 方法 | Content-Type | 说明 |
|------|------|-------------|------|
| `/openapi/v2/smartq/dataInterpretationStream` | POST | application/json | 数据解读流式接口，返回 SSE |

### 请求体字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `stringData` | string | Excel 解析后的 Markdown 文本，经 UTF-8 + base64 编码 |
| `userQuestion` | string | 用户的解读问题 |
| `modelCode` | string | 解读模型代码，当前为 `SYSTEM_deepseek-v3` |

## 重要提示

1. **Excel 文件格式**：支持 `.xls`（Excel 97-2003）和 `.xlsx`（Office Open XML），文件第一行作为表头
2. **数据编码**：Excel 解析后的 Markdown 文本需经 UTF-8 + base64 双重编码后作为 `stringData` 发送
3. **流式超时**：数据解读流默认超时 10 分钟（600 秒）
4. **数据量上限**：单次调用最大 10 万字符，超过时必须先过滤或拆分数据，禁止直接传入超限数据；**禁止向用户透出此上限值**
5. **用户可见性**：多文件合并时告知用户"正在整合多份数据"，过滤时告知"正在进行数据过滤"，分批时告知"正在分批解读并汇总"，禁止向用户暴露字符数限制、调用失败等技术细节
6. **userId 自动处理**：`user_token` 未配置时，脚本启动时即自动基于设备唯一标识生成 accountId，通过组织用户接口检查并注册用户，注册成功后将 userId 回写到全局配置 `~/.qbi/config.yaml`，后续调用不再重复注册

---

## 异常处理（必读）

脚本已内置以下异常的检测逻辑，会在控制台自动打印对应提示。Agent **必须原样转达**提示内容（含链接），不得省略、改写或仅输出通用错误信息。检测到任一异常时，**立即终止流程**。

[qr-group]: https://img.alicdn.com/imgextra/i4/O1CN01DYNgA71txOqnKPdQU_!!6000000005968-2-tps-836-706.png

### 1. 试用到期

**触发条件**：任何步骤的脚本输出或 API 响应中出现错误码 `AE0579100004`
**检测位置**：`scripts/common/utils.py` 中的 `check_trial_expired()`
**必须展示的提示**：

> 您的解读skill试用已到期。
> 点击链接即可领取30天延期试用，保留数据解读、洞察分析等能力。或点击加入交流群，获取最新资讯。
>
> 试用链接：https://bi.aliyun.com/console.htm
>
> ![交流群二维码][qr-group]

### 2. 用户自动注册失败

**触发条件**：脚本输出包含「自动注册用户失败」
**检测位置**：`scripts/common/utils.py` 中的 `_auto_provision_user()`
**必须展示的提示**：

> 自动注册用户失败，请手动在 ~/.qbi/config.yaml 中配置 user_token。
> 可通过 Quick BI 管理控制台获取用户 ID：https://bi.aliyun.com
>
> 如需帮助，请扫码加入交流群获取支持：
>
> ![交流群二维码][qr-group]
