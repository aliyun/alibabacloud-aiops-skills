---
name: quickbi-document-parser
description: >
  Intelligent document parsing and structured extraction tool. Use when users need to recognize content from
  PDF, Word, Excel, CSV, image files, or extract key fields and generate structured Excel reports.
  Supports single file, batch file, and recursive folder processing.
---

# QuickBI Document Parser

**Core Capabilities**:
1. 📄 **Document Content Recognition**: Parse PDF, Word, Excel, CSV, images, and other unstructured files into readable text content
2. 📊 **Field Extraction & Consolidation**: Intelligently extract core fields from documents and automatically generate formatted multi-Sheet Excel reports

## Scope

**Does:**
- Recognize content from PDF, Word(.doc/.docx), Excel(.xls/.xlsx), CSV, images(.png/.jpg/.jpeg), and other document formats
- Support single file, batch multi-file processing, and recursive folder scanning
- Prioritize local text extraction; automatically fall back to remote OCR on failure
- Intelligently extract core fields based on predefined classification system (10 classification groups, 37 subtypes)
- Support dynamic structured extraction for unknown documents (5+ fields require user confirmation)
- Generate formatted multi-Sheet Excel reports (summary statistics + categorized data)

**Does NOT:**
- Does NOT support modifying original document content
- Does NOT support online Excel editing
- Does NOT support non-document files (e.g. video, audio, executables)
- MUST NOT fabricate or invent any extracted data

## Instructions

This skill provides **2 usage modes**, automatically selected based on user intent:

### ⚠️ Mode Determination Rules (Important)

**Strictly follow these rules to determine which mode to use**:

| User Intent Keywords | Mode | Description |
|--------------|---------|------|
| recognize, read, extract text, convert to text, view content | **Mode A** | Only needs document content, no structuring required |
| extract fields, generate Excel, summary report, structured, categorized extraction | **Mode B** | Requires field extraction and Excel output |
| parse + no further instructions | **Mode A** | Default to content recognition only |
| parse + explicitly mentions fields/Excel/summary | **Mode B** | Requires full workflow |

**Key Principles**:
- 📌 **Verbs like "parse", "recognize", "read" default to Mode A**
- 📌 **ONLY use Mode B when the user explicitly requests "extract fields", "generate Excel", or "summary report"**
- 📌 **When uncertain, prefer Mode A first, then ask the user if they need Excel generation**

---

### Mode A: Document Content Recognition
**Applicable scenario**: User only needs to read the text content from documents, no structured extraction required

**Processing flow**: Step 1 (Text Recognition)

**Examples**:
- "Help me read the content of this PDF"
- "Help me read the content of this PDF"
- "Parse the content of this PDF"
- "Parse the content of this PDF"
- "Extract the text from these Word documents"
- "Extract text from these Word documents"
- "Scan the folder and convert all documents to text"
- "Scan the folder and convert all documents to text"

---

### Mode B: Field Extraction & Excel Consolidation
**Applicable scenario**: User needs to extract core fields from numerous documents and generate structured Excel

**Processing flow**: Step 1 (Text Recognition) → Step 2 (Field Extraction) → Step 3 (Generate Excel)

**Examples**:
- "Parse these invoices, extract key fields and generate Excel"
- "Parse these invoices, extract key fields and generate Excel"
- "Scan the contract folder, consolidate all contract information into Excel"
- "Scan the contract folder and summarize all contract info into Excel"
- "Batch process documents, extract fields by category and export"
- "Batch process documents, extract fields by category and export"

---

### Workflow Overview

```
User uploads file/folder
  ↓
┌─────────────────────────────────────┐
│  Step 1: Text Recognition            │
│  Local parse first → Fallback to     │
│  remote OCR on failure               │
│  Output: JSON (file + parsedText)    │
└─────────────────────────────────────┘
  ↓
[Mode A: Ends here, return text content]
  ↓
┌─────────────────────────────────────┐
│  Step 2: Field Extraction            │
│  Intelligent classification →        │
│  Extract core fields                 │
│  Output: JSON (category + field data)│
└─────────────────────────────────────┘
  ↓
┌─────────────────────────────────────┐
│  Step 3: Generate Excel Report       │
│  Multi-Sheet + Formatting +          │
│  Summary Statistics                  │
│  Output: .xlsx file                  │
└─────────────────────────────────────┘
  ↓
Output summary + Excel deliverable
```

### Step 1: Document Content Recognition

**Goal**: Extract raw text content from documents and generate a JSON file

**Core Capability**: 📄 Supports intelligent recognition of multiple formats including PDF, Word, Excel, CSV, images, etc.

**⚠️ Pre-execution Setup**:
```bash
# Install Python dependencies (required only once)
cd skills/quickbi-smartq-chat
pip3 install -r requirements.txt

# Optional system dependencies for local parsing:
# macOS: brew install tesseract tesseract-lang
# Linux: sudo apt install tesseract-ocr tesseract-ocr-chi-sim
```

**Execution Logic**:

1. **Prioritize local parsing** (`document_local_parse.py`)
   ```bash
   # Single file
   python scripts/document/document_local_parse.py <file_path> --json
   
   # Multiple files
   python scripts/document/document_local_parse.py <file1> <file2> <file3> --json
   
   # Folder (recursive scanning)
   python scripts/document/document_local_parse.py <folder_path> --json
   ```

2. **Fallback to remote OCR** (`document_remote_ocr.py`) if local parsing fails
   ```bash
   # Folder scanning
   python scripts/document/document_remote_ocr.py <folder_path>
   
   # Multiple files
   python scripts/document/document_remote_ocr.py --files <file1> <file2>
   ```

3. **JSON output format**:
   ```json
   [
     {
       "file": "filename.pdf",
       "parsedText": "Extracted full text content..."
     }
   ]
   ```

**Notes**:
- Local parsing supports: PDF (PyMuPDF), Word (python-docx), Excel (openpyxl), CSV (pandas), Images (Tesseract OCR)
- Remote OCR supports: PDF, Images, Word, Excel, PPT (via QuickBI API)
- Maximum file size: 5MB per file; **when a file exceeds 5MB, the Agent MUST present the upgrade prompt message to the user as-is (including the upgrade link) — MUST NOT bypass the limit by processing the file locally**
- Default output directory: `$WORKSPACE_DIR/.qbi/output/` with timestamp
- Remember file paths and output directories for use in Step 2

### Step 2: Field Extraction & Intelligent Classification

**Objective**: Based on the JSON output from Step 1, extract core fields according to the document classification system and generate structured JSON file

**Core Capability**: 📊 Intelligent classification + Dynamic extraction + User confirmation mechanism

**Execution Logic**:
0. **Load JSON File**: Load raw JSON data from the JSON file generated in Step 1
1. **Load Classification System**: Refer to `references/document_classification.md`
    - 10 major categories: A. Finance & Tax, B. Human Resources, C. Supply Chain & Procurement, D. Administration & Legal, E. Medical, F. Insurance, G. Logistics, H. Technology & Operations, I. Customer Service & Sales, J. Government & Compliance
    - 37 subtypes: Each subtype has clearly defined fields and Chinese headers

2. **Document Classification & Field Extraction**: Process according to the following priority strategy

   **First Priority: Match Predefined Classification System**
    - Refer to `references/document_classification.md` for classification
    - Prioritize matching titles/headers (e.g., "VAT Invoice", "Bank Receipt")
    - Route based on key fields (e.g., contains tax number → A1, contains transaction number → A2/A3)
    - After successful matching, strictly extract data according to the corresponding subtype's field definitions

   **Second Priority: Dynamic Structured Extraction**
    - If unable to match any of the 37 predefined subtypes, evaluate whether the document has value for structured extraction
    - Criteria: Can **at least 5 valid fields** be identified and extracted from the text?
    - If 5+ fields can be extracted:
        - Intelligently identify field names and corresponding values
        - **Must use AskUserQuestion tool to let users confirm field definitions**
        - After user confirmation, extract according to the confirmed field structure
        - Create a temporary sheet name for the new type (format: `Custom_{Type Name}`)

   **Third Priority: Categorize as Unrecognized**
    - If unable to match predefined categories **and** cannot extract 5+ fields through dynamic extraction
    - Categorize as "Unrecognized", record content preview and suspected type

3. **Field Extraction**: Strictly extract fields according to the classification system definitions
    - Field naming: English `snake_case`
    - Excel headers: Chinese names (with English field names in parentheses)
    - Implicit first column for each subtype: `filename` (source file name)

4. **JSON Output Format Requirements**:
   ```json
   {
     "scan_time": "2026-04-07 15:00:00",
     "total_files": 10,
     "extraction_data": {
       "VAT Invoice": {
         "headers": ["Source Filename", "Invoice Type", "Invoice Code", "Invoice Number", "Invoice Date", "Buyer Name", "Seller Name", "Total Amount"],
         "rows": [
           ["invoice_001.pdf", "Special", "033002100511", "03933249", "2023-05-14", "Buyer Company", "Seller Company", "118.00"]
         ]
       },
       "Unrecognized": {
         "headers": ["Source Filename", "Content Preview", "Suspected Type", "Confidence"],
         "rows": [
           ["unknown.pdf", "This is some text...", "Contract", "Medium"]
         ]
       }
     }
   }
   ```

**⚠️ Step 2 Execution Constraints**:
- ✅ **Required**: Directly use AI model to read the JSON file generated by Step 1, perform classification and field extraction in memory
- ✅ **Allowed**: Extract existing field values from `parsedText`
- ✅ **Allowed**: Leave fields empty (empty string) when data is missing
- ❌ **Prohibited**: Write Python scripts or other code to perform field extraction
- ❌ **Prohibited**: Call external scripts or command-line tools to process JSON data
- ❌ **Prohibited**: Fabricate non-existent fields or field values, no data invention
- ❌ **Prohibited**: Infer or fill in data based on context
- ❌ **Prohibited**: Modify original text content
- ❌ **Prohibited**: Fill in default values (unless explicitly stated in the classification system, e.g., "currency defaults to CNY")
- ✅ **Correct Approach**:
  - 1. Read the JSON file content from Step 1
  - 2. Perform intelligent classification and field extraction according to the classification system
  - 3. Assemble extracted results into the JSON format required by Step 2
  - 4. Save the JSON file to `$WORKSPACE_DIR/.qbi/output/` directory
  - 5. Remember the JSON file path for use as input to Step 3

**Extraction Example**:

```python
# ✅ Correct: Extract from text
if "Invoice Code" in text:
    invoice_code = extract_value(text, "Invoice Code")  # Extract actual value
else:
    invoice_code = ""  # Leave empty, do not fabricate

# ❌ Wrong: Fabricate data
invoice_code = "1234567890"  # Not in text, prohibited from fabricating
```

### Step 3: Generate Excel Summary Report

**Objective**: Generate structured, formatted Excel reports from the JSON data extracted in Step 2

**Core Capability**: 📈 Multi-sheet automation + Formatting + Summary statistics

**Execution Command**:
```bash
# Default output to $WORKSPACE_DIR/.qbi/output/doc_scan_result_{timestamp}.xlsx
python scripts/document/generate_excel.py <Step2_JSON_path>

# Custom output path
python scripts/document/generate_excel.py <Step2_JSON_path> /path/to/output.xlsx
```

**Excel Structure**:
- **Excel filename**: `{category_name}_{timestamp}.xlsx`
- **Summary Sheet** (first sheet): Statistics on file count and extracted fields by category
- **Data Sheets** (one per subtype): Formatted table data
    - Blue headers (`#4472C4`) + white bold text
    - Auto-filter + freeze first row
    - Auto column width + cell text wrapping

### Final Delivery

Output in the conversation window:

1. **Processing Summary**:
   ```
   Document parsing completed

   Total files: 10
   Successfully recognized: 9
   Recognition failed: 1
   
   Category Statistics:
   - A. Finance & Tax: 5 files (VAT Invoice 3, Bank Receipt 2)
   - B. Human Resources: 2 files (Resume 1, Labor Contract 1)
   - Unrecognized: 1 file
   
   Extracted fields: 45
   ```

2. **Excel Deliverable Path**:
   ```
   ✓ Excel generated: $WORKSPACE_DIR/.qbi/output/invoice_20260407_150000.xlsx
   ```

## Examples

### Mode A Examples

**Example 1: Parse Single File Content**

Input:
```
Please read the content of this PDF: /Users/user/document.pdf
```

Expected output:
```
[Step 1] Locally parsing document.pdf...
[PDF Extraction] Successfully extracted 2350 characters
[Save] JSON results saved to: $WORKSPACE_DIR/.qbi/output/extract_results_1775575200.json


Document parsing completed

Total files: 1
Successfully recognized: 1
Extracted text: 2350 characters

✓ Text content saved: $WORKSPACE_DIR/.qbi/output/extract_results_1775575200.json
```

**Example 2: Batch Parse Folder**

Input:
```
Scan and parse all documents in /Users/user/documents/, extract text content
```

Expected output:
```
[Step 1] Scanning folder...
[Scan] Found 15 supported files in /Users/user/documents/
[Parallel Extraction] Processing 15 files (max concurrency: 10)
...


Document parsing completed

Total files: 15
Successfully recognized: 14
Recognition failed: 1
Total text: 45,230 characters

✓ Text content saved: $WORKSPACE_DIR/.qbi/output/extract_results_1775576400.json
```

---

### Mode B Examples

**Example 3: Parse Invoices and Generate Excel Report**

Input:
```
Please parse these invoice files, extract key fields, and generate an Excel report: /Users/user/invoices/
```

Expected output:
```
[Step 1] Locally parsing invoices/ folder...
[Scan] Found 10 supported files
[Parallel Extraction] Processing 10 files (max concurrency: 10)
...

[Step 2] Intelligent classification and field extraction...
- VAT Invoice: 5 files (13 fields/file extracted)
- Bank Receipt: 3 files (11 fields/file extracted)
- Unrecognized: 2 files

[Step 3] Generating Excel summary report...
[Formatting] Applying blue headers + auto-filter + freeze first row
[Save] ✓ Excel results saved to: $WORKSPACE_DIR/.qbi/output/doc_scan_result_20260407_150000.xlsx

Document parsing completed

Total files: 10
Successfully recognized: 8
Unrecognized: 2

Category Statistics:
- A. Finance & Tax: 8 files (VAT Invoice 5, Bank Receipt 3)
- Unrecognized: 2 files

Extracted fields: 98

✓ Excel report generated: $WORKSPACE_DIR/.qbi/output/doc_scan_result_20260407_150000.xlsx
```

**Example 4: Local Parsing Fails, Fallback to Remote OCR**

Input:
```
Parse this scanned PDF and extract fields: /Users/user/scanned_invoice.pdf
```

Expected output:
```
[Step 1] Locally parsing scanned_invoice.pdf...
[PDF Extraction] Warning: Local extraction returned minimal text (12 characters), possibly a scanned document, attempting OCR...
[PDF Extraction] Falling back to Tesseract OCR...
[OCR Fallback] OCR quality insufficient, attempting remote OCR...

[Remote OCR] Uploading scanned_invoice.pdf...
[Upload] ✓ scanned_invoice.pdf -> taskId: abc123
[Poll] ✓ Task parsed successfully (850 characters)

[Step 2] Intelligent classification: VAT Invoice (vat-invoice)
Extracted fields: Invoice Code, Invoice Number, Invoice Date, Purchaser Name... (extracted from OCR text)

[Step 3] Generating Excel summary report...
[Save] ✓ Excel results saved to: $WORKSPACE_DIR/.qbi/output/doc_scan_result_20260407_160000.xlsx

Document parsing completed

Total files: 1
Successfully recognized: 1 (Remote OCR)

Category Statistics:
- A. Finance & Tax: 1 file (VAT Invoice 1)

Extracted fields: 13

✓ Excel report generated: $WORKSPACE_DIR/.qbi/output/doc_scan_result_20260407_160000.xlsx
```

**Example 5: Unknown Document Dynamic Extraction (Requires User Confirmation)**

Input:
```
Parse this custom document and extract fields: /Users/user/custom_report.pdf
```

Expected output:
```
[Step 1] Locally parsing custom_report.pdf...
[PDF Extraction] Successfully extracted 1580 characters

[Step 2] Intelligent classification...
⚠️ Unable to match 37 predefined standard categories
🔍 Evaluating document structured extraction value...
✓ Identified 8 potential fields: Report Number, Test Date, Sample Name, Test Items, Result Values, Inspector, Reviewer, Testing Organization

[AskUserQuestion] Unknown document type detected, confirm identified fields:
┌─────────────────────────────────────┐
│ Document Type: Test Report (Custom)  │
│ Identified Fields:                   │
│ 1. Report Number (report_no)        │
│ 2. Test Date (test_date)            │
│ 3. Sample Name (sample_name)        │
│ 4. Test Items (test_items)          │
│ 5. Result Values (results)          │
│ 6. Inspector (inspector)            │
│ 7. Reviewer (reviewer)              │
│ 8. Testing Organization (testing_org)│
│                                     │
│ Confirm extraction with this structure?│
└─────────────────────────────────────┘
User confirmation: ✓ Yes

[Step 2] Extracting fields according to confirmed structure...
[Extraction] Successfully extracted 8 fields

[Step 3] Generating Excel summary report...
[Creating Sheet] Custom_Test Report
[Save] ✓ Excel results saved to: $WORKSPACE_DIR/.qbi/output/doc_scan_result_20260407_170000.xlsx

============================================================
Document parsing completed
============================================================
Total files: 1
Successfully recognized: 1 (Custom type)

Category Statistics:
- Custom_Test Report: 1 file

Extracted fields: 8
============================================================
✓ Excel report generated: $WORKSPACE_DIR/.qbi/output/doc_scan_result_20260407_170000.xlsx
```

## Additional Resources

- **Detailed Classification System Definitions**: [document_classification.md](./document_classification.md)

## Script Interface Reference

### 1. Local Parsing Script (`document_local_parse.py`)

**Functionality**: Pure local text extraction, supports PDF/Word/Excel/CSV/Images without external API dependency

**Supported Formats**:
- PDF (.pdf), Word (.doc/.docx), Excel (.xls/.xlsx), CSV (.csv)
- Images (.png/.jpg/.jpeg/.bmp/.tiff/.webp) - Using Tesseract OCR

**Command Line Usage**:
```bash
# Single file
python scripts/document/document_local_parse.py <file_path> --json

# Multiple files
python scripts/document/document_local_parse.py <file1> <file2> <file3> --json

# Folder recursive scanning
python scripts/document/document_local_parse.py <folder_path> --json

# Custom output directory
python scripts/document/document_local_parse.py <path> --json --output-dir /custom/output/

# Disable OCR fallback
python scripts/document/document_local_parse.py <file_path> --json --no-ocr
```

**Core Parameters**:
| Parameter | Description | Default |
|------|------|-------|
| `--json` | Save JSON result | False |
| `--output-dir` | JSON output directory | `$WORKSPACE_DIR/.qbi/output/` |
| `--no-ocr` | Disable OCR fallback | False |

**Output Format**:
```json
[
  {"file": "filename.pdf", "parsedText": "Extracted text content..."}
]
```

**System Dependencies**:
```bash
# macOS
brew install tesseract tesseract-lang

# Ubuntu/Debian
sudo apt-get install tesseract-ocr tesseract-ocr-chi-sim tesseract-ocr-eng
```

---

### 2. Remote OCR Script (`document_remote_ocr.py`)

**Function**: Remote OCR recognition based on QuickBI API, supports batch concurrent processing

**Supported formats**:
- PDF, Images(.png/.jpg/.jpeg/.webp/.bmp/.gif/.jp2)
- Word(.doc/.docx), PPT(.ppt/.pptx), Excel(.xls/.xlsx/.csv)
- **File size limit**: Single file ≤ 5MB; **when the limit is exceeded, the Agent MUST present the upgrade prompt message to the user as-is (including the upgrade link) — MUST NOT bypass the limit by processing the file locally**

**Command line usage**:
```bash
# Folder scanning (recursive)
python scripts/document/document_remote_ocr.py <folder_path>

# Multiple files
python scripts/document/document_remote_ocr.py --files <file1> <file2> <file3>

# Custom output path
python scripts/document/document_remote_ocr.py <path> --output /custom/result.json

# JSON mode (output JSON only, no logs)
python scripts/document/document_remote_ocr.py <path> --json

# Adjust concurrency
python scripts/document/document_remote_ocr.py <path> --upload-workers 5 --poll-workers 10
```

**Core parameters**:
| Parameter | Type | Default | Description |
|------|------|--------|------|
| `directory` | Optional | - | Directory path (recursive scan) |
| `--files` | Optional | - | File list (mutually exclusive with directory) |
| `--upload-workers` | int | 5 | Upload concurrency (max 10) |
| `--poll-workers` | int | 10 | Polling concurrency (max 10) |
| `--output` | str | - | Output JSON path |
| `--json` | flag | false | JSON output only (no logs) |

**Output format**:
```json
[
  {"file": "filename.pdf", "parsedText": "Recognized text..."},
  {"file": "error.pdf", "parsedText": null, "error": "Error message"}
]
```

**Configuration**: Please refer to the Configuration section in the main file.

---

### 3. Excel Generation Script (`generate_excel.py`)

**Function**: Convert categorized extraction JSON data into multi-Sheet Excel reports

**Command line usage**:
```bash
# Default output to $WORKSPACE_DIR/.qbi/output/doc_scan_result_{timestamp}.xlsx
python scripts/document/generate_excel.py <JSON_path>

# Custom output path
python scripts/document/generate_excel.py <JSON_path> /path/to/output.xlsx
```

**Input JSON format**:
```json
{
  "scan_time": "2026-04-07 15:00:00",
  "total_files": 10,
  "extraction_data": {
    "VAT Invoice": {
      "headers": ["Source Filename", "Invoice Type", "Invoice Code", "..."],
      "rows": [["file.pdf", "Special", "033002100511", "..."]]
    },
    "Unrecognized": {
      "headers": ["Source Filename", "Content Preview", "Suspected Type", "Confidence"],
      "rows": [["unknown.pdf", "Text...", "Contract", "Medium"]]
    }
  }
}
```

**Note**:
- The input JSON is NOT the JSON generated by `document_remote_ocr.py` or `document_local_parse.py`. Refer to Step 2 output.

**Excel Structure**:
- **Summary Sheet** (first sheet): Statistics on file count and extracted fields by category
- **Data Sheets** (one per subtype): Blue headers + auto-filter + freeze first row + auto column width

## Dependency Installation

```bash
# Install all Python dependencies
pip install -r requirements.txt

# System dependencies (only needed for local parsing)
# macOS
brew install tesseract tesseract-lang

# Ubuntu/Debian
sudo apt-get install tesseract-ocr tesseract-ocr-chi-sim tesseract-ocr-eng
```

**Core Python dependencies**:
- Local parsing: `PyMuPDF`, `python-docx`, `openpyxl`, `xlrd`, `pandas`, `pytesseract`, `Pillow`
- Remote OCR: `requests`, `pyyaml`
- Excel generation: `openpyxl>=3.1.0`

## Important Notes

1. **Mode Determination Priority**: Strictly follow the "Mode Determination Rules" table. When uncertain, **prefer Mode A first**, then ask if the user needs Excel generation
2. **Data Authenticity**: Step 2 field extraction strictly prohibits fabrication. All data must originate from Step 1's `parsedText`
3. **Missing Field Handling**: If a field does not exist in the text, leave it empty (`""`), do not fabricate
4. **Classification Fallback**: For documents that cannot match predefined categories, prioritize dynamic extraction (5+ fields), then categorize as "Unrecognized" if it fails
5. **Dynamic Extraction Confirmation**: When extracting 5+ fields from unknown documents, **must** use AskUserQuestion to let the user confirm
6. **Output Path**: All output files default to `$WORKSPACE_DIR/.qbi/output/` directory with timestamps to prevent overwriting
7. **Concurrency Limits**: Remote OCR maximum concurrency is 10 files, local parsing maximum concurrency is 10 files
8. **File Size**: Maximum 5MB per file (remote OCR limit); **when the limit is exceeded, the Agent MUST present the upgrade prompt message to the user as-is (including the upgrade link) — MUST NOT bypass the limit by processing the file locally**
9. **OCR Fallback Strategy**: When local PDF parsing extracts < 50 characters, automatically fallback to Tesseract OCR; if still failing, attempt remote OCR

