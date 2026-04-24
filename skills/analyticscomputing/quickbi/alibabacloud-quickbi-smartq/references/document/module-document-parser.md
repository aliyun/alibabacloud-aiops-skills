---
name: quickbi-document-parser
description: >
  文档智能解析与结构化提取工具。当用户需要识别 PDF、Word、Excel、CSV、图片等文档内容，
  或提取关键字段并生成结构化 Excel 报表时使用。支持单文件、批量文件和文件夹递归处理。
---

# QuickBI 文档解析工具

**核心能力**:
1. 📄 **文档内容识别**: 解析 PDF、Word、Excel、CSV、图片等非结构化文件为可读取的文本内容
2. 📊 **字段提取与汇总**: 从文档中智能提取核心字段，自动生成带格式的多 Sheet Excel 报表

## Scope

**Does:**
- 识别 PDF、Word(.doc/.docx)、Excel(.xls/.xlsx)、CSV、图片(.png/.jpg/.jpeg) 等文档内容
- 支持单文件、多文件批量处理、文件夹递归扫描
- 优先本地提取文本，失败后自动降级到远程 OCR
- 根据预定义分类体系(10 大分类组、37 个子类型)智能提取核心字段
- 支持未知文档的动态结构化提取(5+ 字段需用户确认)
- 生成带格式的多 Sheet Excel 报表(汇总统计 + 分类数据)

**Does NOT:**
- 不支持修改原始文档内容
- 不支持在线编辑 Excel
- 不支持非文档类文件(如视频、音频、可执行文件)
- 严禁杜撰或编造任何提取数据

## Instructions

本技能提供 **2 种使用模式**,根据用户意图自动选择:

### ⚠️ 模式判定规则(重要)

**严格按以下规则判断使用哪个模式**:

| 用户意图关键词 | 使用模式 | 说明 |
|--------------|---------|------|
| 识别、读取、提取文本、转成文本、查看内容 | **模式 A** | 仅需文档内容,不需要结构化 |
| 提取字段、生成 Excel、汇总报表、结构化、分类提取 | **模式 B** | 需要字段提取和 Excel 输出 |
| 解析 + 无后续说明 | **模式 A** | 默认仅识别内容 |
| 解析 + 明确提到字段/Excel/汇总 | **模式 B** | 需要完整流程 |

**关键原则**:
- 📌 **"解析"、"识别"、"读取" 等动词默认指向模式 A**
- 📌 **只有用户明确要求"提取字段"、"生成 Excel"、"汇总报表"时才使用模式 B**
- 📌 **不确定时,优先使用模式 A,然后询问用户是否需要生成 Excel**

---

### 模式 A: 文档内容识别
**适用场景**: 用户仅需读取文档中的文本内容,无需结构化提取

**处理流程**: Step 1 (文本识别)

**示例**:
- "帮我读取这个 PDF 的内容"
- "解析这个 PDF 的内容"
- "提取这些 Word 文档的文本"
- "扫描文件夹,把所有文档转成文本"

---

### 模式 B: 字段提取与 Excel 汇总
**适用场景**: 用户需要从众多文档中，提取核心字段并生成结构化的Excel

**处理流程**: Step 1 (文本识别) → Step 2 (字段提取) → Step 3 (生成 Excel)

**示例**:
- "解析这些发票,提取关键字段并生成 Excel"
- "扫描合同文件夹,汇总所有合同信息到Excel"
- "批量处理文档,按分类提取字段并导出"

---

### 工作流程概览

```
用户上传文件/文件夹
  ↓
┌─────────────────────────────────────┐
│  Step 1: 文本识别                    │
│  本地解析优先 → 失败降级远程 OCR      │
│  输出: JSON (file + parsedText)      │
└─────────────────────────────────────┘
  ↓
[模式 A: 到此结束,返回文本内容]
  ↓
┌─────────────────────────────────────┐
│  Step 2: 字段提取                    │
│  智能分类 → 提取核心字段             │
│  输出: JSON (分类 + 字段数据)        │
└─────────────────────────────────────┘
  ↓
┌─────────────────────────────────────┐
│  Step 3: 生成 Excel 报表             │
│  多 Sheet + 格式化 + 汇总统计        │
│  输出: .xlsx 文件                    │
└─────────────────────────────────────┘
  ↓
输出总结 + Excel 交付物
```

### Step 1: 文档内容识别

**目标**: 提取文档中的原始文本内容,生成 JSON 文件

**核心能力**: 📄 支持 PDF、Word、Excel、CSV、图片等多种格式的智能识别

**执行逻辑**:

1. **优先调用本地解析** (`document_local_parse.py`)
   ```bash
   # 单文件
   python scripts/document/document_local_parse.py <文件路径> --json
   
   # 多文件
   python scripts/document/document_local_parse.py <文件1> <文件2> <文件3> --json
   
   # 文件夹（递归扫描）
   python scripts/document/document_local_parse.py <文件夹路径> --json
   ```

2. **如果本地解析失败**，尝试远程 OCR (`document_remote_ocr.py`)
   ```bash
   # 文件夹扫描
   python scripts/document/document_remote_ocr.py <文件夹路径>
   
   # 多文件
   python scripts/document/document_remote_ocr.py --files <文件1> <文件2>
   ```

3. **输出格式**:
   ```json
   [
     {
       "file": "filename.pdf",
       "parsedText": "提取的完整文本内容..."
     }
   ]
   ```

**注意事项**:
- 本地解析支持: PDF(PyMuPDF)、Word(python-docx)、Excel(openpyxl)、CSV(pandas)、图片(Tesseract OCR)
- 远程 OCR 支持: PDF、图片、Word、Excel、PPT（通过 QuickBI API）
- 单文件最大 10MB
- 默认输出到 `output/` 目录，带时间戳

### Step 2: 字段提取与智能分类

**目标**: 根据文档分类体系,从原始文本中提取核心字段

**核心能力**: 📊 智能分类 + 动态提取 + 用户确认机制

**执行逻辑**:

1. **加载分类体系**: 参考 `references/document_classification.md`
    - 10 大分类组: A.财务与税务、B.人力资源、C.供应链与采购、D.行政与法务、E.医疗、F.保险、G.物流、H.技术与运维、I.客服与销售、J.政务与合规
    - 37 个子类型: 每个子类型有明确的字段定义和中文表头。

2. **文档分类与字段提取**: 按照以下优先级策略处理

   **第一优先级: 匹配预定义分类体系**
    - 参考 `references/document_classification.md` 进行分类
    - 优先匹配标题/抬头（如"增值税发票"、"银行回单"）
    - 根据关键字段路由（如含税号→A1,含流水号→A2/A3）
    - 匹配成功后,严格按照对应子类型的字段定义提取数据

   **第二优先级: 动态结构化提取**
    - 如果无法匹配预定义的 37 个子类型,评估文档是否具备结构化提取价值
    - 判断标准: 能否从文本中识别并提取 **至少 5 个有效字段**
    - 如果可以提取 5+ 个字段:
        - 智能识别字段名称和对应值
        - **必须使用 AskUserQuestion 工具让用户确认字段定义**
        - 用户确认后,按确认的字段结构进行提取
        - 为新类型创建临时 Sheet 名(格式: `自定义_{类型名}`)

   **第三优先级: 归入未识别类**
    - 如果无法匹配预定义分类 **且** 无法结构化提取 5+ 个字段
    - 归入"未识别"类,记录内容预览和疑似类型

3. **字段提取**: 严格按照分类体系定义的字段提取
    - 字段命名: 英文 `snake_case`
    - Excel 表头: 中文名（括号内英文字段名）
    - 每个子类型的隐含首列: `filename`（源文件名）

4. **组装 JSON**:
   ```json
   {
     "scan_time": "2026-04-07 15:00:00",
     "total_files": 10,
     "extraction_data": {
       "增值税发票": {
         "headers_cn": ["源文件名", "发票类型", "发票代码", "发票号码", "开票日期", "购买方名称", "销售方名称", "价税合计"],
         "rows": [
           ["invoice_001.pdf", "专用", "033002100511", "03933249", "2023-05-14", "购买方公司", "销售方公司", "118.00"]
         ]
       },
       "未识别": {
         "headers_cn": ["源文件名", "内容预览", "疑似类型", "置信度"],
         "rows": [
           ["unknown.pdf", "这是一段文本...", "合同", "中"]
         ]
       }
     }
   }
   ```

**⚠️ 核心原则: 严禁杜撰数据**

- ✅ **允许**: 从 `parsedText` 中提取存在的字段值
- ✅ **允许**: 字段缺失时留空（空字符串）
- ❌ **禁止**: 编造不存在的字段和字段值，禁止杜撰数据
- ❌ **禁止**: 根据上下文推测或补全数据
- ❌ **禁止**: 修改原始文本内容
- ❌ **禁止**: 填充默认值（除非分类体系明确说明，如"币种默认 CNY"）

**提取示例**:

```python
# ✅ 正确: 从文本中提取
if "发票代码" in text:
    invoice_code = extract_value(text, "发票代码")  # 提取实际值
else:
    invoice_code = ""  # 留空，不编造

# ❌ 错误: 杜撰数据
invoice_code = "1234567890"  # 文本中没有，禁止编造
```

### Step 3: 生成 Excel 汇总报表

**目标**: 将提取的字段数据生成结构化、带格式的 Excel 报表

**核心能力**: 📈 多 Sheet 自动化 + 格式化 + 汇总统计

**执行命令**:
```bash
# 默认输出到 output/doc_scan_result_{timestamp}.xlsx
python scripts/document/generate_excel.py <Step2的JSON路径>

# 自定义输出路径
python scripts/document/generate_excel.py <Step2的JSON路径> /path/to/output.xlsx
```

**Excel 结构**:
- **excel名称** ：`{category名称}_{timestamp}.xlsx`
- **汇总 Sheet**（首页）: 统计各分类组的文件数量和提取字段
- **数据 Sheet**（每个子类型一个）: 带格式的表格数据
    - 蓝色表头（`#4472C4`）+ 白色粗体
    - 自动筛选 + 冻结首行
    - 自动列宽 + 单元格换行

### 最终交付

在窗口中输出:

1. **处理总结**:
   ```

   文档解析完成

   文件总数: 10
   成功识别: 9
   识别失败: 1
   
   分类统计:
   - A.财务与税务: 5 个文件（增值税发票 3, 银行回单 2）
   - B.人力资源: 2 个文件（简历 1, 劳动合同 1）
   - 未识别: 1 个文件
   
   提取字段: 45 个
   ```

2. **Excel 交付物路径**:
   ```
   ✓ Excel 已生成: /path/to/output/invoice_20260407_150000.xlsx
   ```

## Examples

### 模式 A 示例

**Example 1: 解析单个文件内容**

Input:
```
请帮我读取这个 PDF 的内容: /Users/user/document.pdf
```

Expected output:
```
[Step 1] 本地解析 document.pdf...
[PDF提取] 成功提取 2350 字符
[保存] JSON 结果已保存到: output/extract_results_1775575200.json


文档解析完成

文件总数: 1
成功识别: 1
提取文本: 2350 字符

✓ 文本内容已保存: output/extract_results_1775575200.json
```

**Example 2: 批量解析文件夹**

Input:
```
扫描并解析 /Users/user/documents/ 下的所有文档,提取文本内容
```

Expected output:
```
[Step 1] 扫描文件夹...
[扫描] 在 /Users/user/documents/ 中找到 15 个支持的文件
[并行提取] 开始处理 15 个文件 (最大并行数: 10)
...


文档解析完成

文件总数: 15
成功识别: 14
识别失败: 1
总文本量: 45,230 字符

✓ 文本内容已保存: output/extract_results_1775576400.json
```

---

### 模式 B 示例

**Example 3: 解析发票并生成 Excel 表格**

Input:
```
请解析这些发票文件,提取关键字段并生成 Excel 报表: /Users/user/invoices/
```

Expected output:
```
[Step 1] 本地解析 invoices/ 文件夹...
[扫描] 找到 10 个支持的文件
[并行提取] 开始处理 10 个文件 (最大并行数: 10)
...

[Step 2] 智能分类与字段提取...
- 增值税发票: 5 个文件 (提取 13 个字段/文件)
- 银行回单: 3 个文件 (提取 11 个字段/文件)
- 未识别: 2 个文件

[Step 3] 生成 Excel 汇总报表...
[格式化] 应用蓝色表头 + 自动筛选 + 冻结首行
[保存] ✓ Excel 结果已保存到: output/doc_scan_result_20260407_150000.xlsx

文档解析完成

文件总数: 10
文件总数: 10
成功识别: 8
未识别: 2

分类统计:
- A.财务与税务: 8 个文件 (增值税发票 5, 银行回单 3)
- 未识别: 2 个文件

提取字段: 98 个

✓ Excel 报表已生成: output/doc_scan_result_20260407_150000.xlsx
```

**Example 4: 本地解析失败,降级到远程 OCR**

Input:
```
解析这个扫描件 PDF 并提取字段: /Users/user/scanned_invoice.pdf
```

Expected output:
```
[Step 1] 本地解析 scanned_invoice.pdf...
[PDF提取] 警告: 本地提取文本较少 (12 字符),可能是扫描件,尝试 OCR...
[PDF提取] 降级到 Tesseract OCR 识别...
[OCR降级] OCR 识别质量不佳,尝试远程 OCR...

[远程 OCR] 上传 scanned_invoice.pdf...
[上传] ✓ scanned_invoice.pdf -> taskId: abc123
[轮询] ✓ 任务解析成功 (850 字符)

[Step 2] 智能分类: 增值税发票 (vat-invoice)
提取字段: 发票代码、发票号码、开票日期、购买方名称... (从 OCR 文本中提取)

[Step 3] 生成 Excel 汇总报表...
[保存] ✓ Excel 结果已保存到: output/doc_scan_result_20260407_160000.xlsx

文档解析完成

文件总数: 1
成功识别: 1 (远程 OCR)
文件总数: 1
成功识别: 1 (远程 OCR)

分类统计:
- A.财务与税务: 1 个文件 (增值税发票 1)

提取字段: 13 个

✓ Excel 报表已生成: output/doc_scan_result_20260407_160000.xlsx
```

**Example 5: 未知文档动态提取(需用户确认)**

Input:
```
解析这个自定义文档并提取字段: /Users/user/custom_report.pdf
```

Expected output:
```
[Step 1] 本地解析 custom_report.pdf...
[PDF提取] 成功提取 1580 字符

[Step 2] 智能分类...
⚠️ 无法匹配预定义的 37 个标准分类
🔍 评估文档结构化提取价值...
✓ 识别到 8 个潜在字段: 报告编号、检测日期、样品名称、检测项目、结果值、检测员、审核人、检测机构

[AskUserQuestion] 检测到未知文档类型,确认识别字段:
┌─────────────────────────────────────┐
│ 文档类型: 检测报告 (自定义)          │
│ 识别字段:                            │
│ 1. 报告编号 (report_no)             │
│ 2. 检测日期 (test_date)             │
│ 3. 样品名称 (sample_name)           │
│ 4. 检测项目 (test_items)            │
│ 5. 结果值 (results)                 │
│ 6. 检测员 (inspector)               │
│ 7. 审核人 (reviewer)                │
│ 8. 检测机构 (testing_org)           │
│                                     │
│ 是否确认按此结构提取?                │
└─────────────────────────────────────┘
用户确认: ✓ 是

[Step 2] 按确认结构提取字段...
[提取] 成功提取 8 个字段

[Step 3] 生成 Excel 汇总报表...
[创建 Sheet] 自定义_检测报告
[保存] ✓ Excel 结果已保存到: output/doc_scan_result_20260407_170000.xlsx

============================================================
文档解析完成
============================================================
文件总数: 1
成功识别: 1 (自定义类型)

分类统计:
- 自定义_检测报告: 1 个文件

提取字段: 8 个
============================================================
✓ Excel 报表已生成: output/doc_scan_result_20260407_170000.xlsx
```

## Additional Resources

- **分类体系详细定义**: [document_classification.md](./document_classification.md)

## 脚本接口参考

### 1. 本地解析脚本 (`document_local_parse.py`)

**功能**: 纯本地文本提取,支持 PDF/Word/Excel/CSV/图片,不依赖外部 API

**支持格式**:
- PDF(.pdf)、Word(.doc/.docx)、Excel(.xls/.xlsx)、CSV(.csv)
- 图片(.png/.jpg/.jpeg/.bmp/.tiff/.webp) - 使用 Tesseract OCR

**命令行用法**:
```bash
# 单文件
python scripts/document/document_local_parse.py <文件路径> --json

# 多文件
python scripts/document/document_local_parse.py <文件1> <文件2> <文件3> --json

# 文件夹递归扫描
python scripts/document/document_local_parse.py <文件夹路径> --json

# 自定义输出目录
python scripts/document/document_local_parse.py <路径> --json --output-dir /custom/output/

# 禁用 OCR 降级
python scripts/document/document_local_parse.py <文件路径> --json --no-ocr
```

**核心参数**:
| 参数 | 说明 | 默认值 |
|------|------|-------|
| `--json` | 保存 JSON 结果 | False |
| `--output-dir` | JSON 输出目录 | `output/` |
| `--no-ocr` | 禁用 OCR 降级 | False |

**输出格式**:
```json
[
  {"file": "filename.pdf", "parsedText": "提取的文本内容..."}
]
```

**系统依赖**:
```bash
# macOS
brew install tesseract tesseract-lang

# Ubuntu/Debian
sudo apt-get install tesseract-ocr tesseract-ocr-chi-sim tesseract-ocr-eng
```

---

### 2. 远程 OCR 脚本 (`document_remote_ocr.py`)

**功能**: 基于 QuickBI API 的远程 OCR 识别,支持批量并发处理

**支持格式**:
- PDF、图片(.png/.jpg/.jpeg/.webp/.bmp/.gif/.jp2)
- Word(.doc/.docx)、PPT(.ppt/.pptx)、Excel(.xls/.xlsx/.csv)
- **文件大小限制**: 单文件 ≤ 10MB

**命令行用法**:
```bash
# 文件夹扫描(递归)
python scripts/document/document_remote_ocr.py <文件夹路径>

# 多文件
python scripts/document/document_remote_ocr.py --files <文件1> <文件2> <文件3>

# 自定义输出路径
python scripts/document/document_remote_ocr.py <路径> --output /custom/result.json

# JSON 模式(仅输出JSON,无日志)
python scripts/document/document_remote_ocr.py <路径> --json

# 调整并发数
python scripts/document/document_remote_ocr.py <路径> --upload-workers 5 --poll-workers 10
```

**核心参数**:
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `directory` | 可选 | - | 目录路径(递归扫描) |
| `--files` | 可选 | - | 文件列表(与 directory 二选一) |
| `--upload-workers` | int | 5 | 上传并发数(最大10) |
| `--poll-workers` | int | 10 | 轮询并发数(最大10) |
| `--output` | str | - | 输出 JSON 路径 |
| `--json` | flag | false | 仅输出JSON(无日志) |

**输出格式**:
```json
[
  {"file": "filename.pdf", "parsedText": "识别文本..."},
  {"file": "error.pdf", "parsedText": null, "error": "错误信息"}
]
```

**配置说明**：请参见主文件的「配置」章节。

---

### 3. Excel 生成脚本 (`generate_excel.py`)

**功能**: 将分类提取的 JSON 数据转换为多 Sheet Excel 报表

**命令行用法**:
```bash
# 默认输出到 output/doc_scan_result_{timestamp}.xlsx
python scripts/document/generate_excel.py <JSON路径>

# 自定义输出路径
python scripts/document/generate_excel.py <JSON路径> /path/to/output.xlsx
```

**输入 JSON 格式**:
```json
{
  "scan_time": "2026-04-07 15:00:00",
  "total_files": 10,
  "extraction_data": {
    "增值税发票": {
      "headers_cn": ["源文件名", "发票类型", "发票代码", "..."],
      "rows": [["file.pdf", "专用", "033002100511", "..."]]
    },
    "未识别": {
      "headers_cn": ["源文件名", "内容预览", "疑似类型", "置信度"],
      "rows": [["unknown.pdf", "文本...", "合同", "中"]]
    }
  }
}
```

**Excel 结构**:
- **汇总 Sheet**(首页): 统计各分类组文件数量和提取字段
- **数据 Sheet**(每子类型一个): 蓝色表头 + 自动筛选 + 冻结首行 + 自动列宽

## 依赖安装

```bash
# 安装所有 Python 依赖（requirements.txt 位于 scripts 目录下）
pip install -r <项目根目录>/scripts/requirements.txt

# 系统依赖(仅本地解析需要)
# macOS
brew install tesseract tesseract-lang

# Ubuntu/Debian
sudo apt-get install tesseract-ocr tesseract-ocr-chi-sim tesseract-ocr-eng
```

**核心 Python 依赖**:
- 本地解析: `PyMuPDF`, `python-docx`, `openpyxl`, `xlrd`, `pandas`, `pytesseract`, `Pillow`
- 远程 OCR: `requests`, `pyyaml`
- Excel 生成: `openpyxl>=3.1.0`

## 注意事项

1. **模式判定优先级**: 严格按"模式判定规则"表格判断,不确定的话**优先使用模式 A**,然后询问用户是否需要生成 Excel
2. **数据真实性**: Step 2 字段提取严禁杜撰,所有数据必须来源于 Step 1 的 `parsedText`
3. **字段缺失处理**: 如果文本中不存在某字段,留空(`""`),不要编造
4. **分类容错**: 无法匹配预定义分类的文档,优先尝试动态提取(5+ 字段),失败后归入"未识别"类
5. **动态提取确认**: 未知文档提取 5+ 字段时,**必须**使用 AskUserQuestion 让用户确认
6. **输出路径**: 所有输出文件默认在 `output/` 目录,带时间戳避免覆盖
7. **并发限制**: 远程 OCR 最大并发 10 个文件,本地解析最大并行 10 个文件
8. **文件大小**: 单文件最大 10MB(远程 OCR 限制)
9. **OCR 降级策略**: 本地解析 PDF 提取文本 < 50 字符时,自动降级到 Tesseract OCR;仍失败则尝试远程 OCR

