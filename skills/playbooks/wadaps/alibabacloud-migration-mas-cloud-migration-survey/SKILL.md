---
name: alibabacloud-migration-mas-cloud-migration-survey
description: 当用户提供迁云调研材料（Excel/Word/文本/CSV文件）并要求生成结构化调研报告时，自动分析汇总并输出 .docx 文档。涵盖客户画像、架构现状、云产品映射、版本兼容性风险、迁移风险、待确认事项。支持 AWS/Azure/GCP/华为云/腾讯云/百度云/IDC 到阿里云的迁移评估。适用于阿里云迁云项目售前或交付调研阶段。本 skill 仅做信息梳理和报告生成，不执行实际迁移操作，不生成报价方案。
---

# Cloud Migration Survey Analyzer

> This skill is designed for the QoderWork platform only and may not run correctly on other platforms.
>
> Scope disclaimer: this skill only organizes information and generates a report from the provided input materials. It does NOT perform actual migration operations, and it does NOT produce pricing proposals. The product mapping tables may change as the Alibaba Cloud product line evolves; always rely on the latest official documentation. Generated survey reports are for reference only; the migration plan must be reviewed and confirmed by a professional architect based on the actual situation.

## Safety Red Lines

- Never output customer sensitive data in the report (e.g. real IPs, passwords, secret keys).
- Never include pricing / unit prices / person-day costs / monthly or annual fees.
- Never perform actual migration operations on behalf of the user.
- Never access file paths that the user did not provide.
- All file paths must pass security validation; path traversal attacks are forbidden.

## Mandatory Execution Contract

This skill ships with tested Python scripts. You **MUST** use them and **MUST NOT** re-implement their logic. Follow this exact tool-call sequence for every request:

1. **MUST** call `python scripts/extract.py <file_path>` to read the source material (Excel/Word/text/CSV). Do this even if you are unsure the file exists — run the script and let it report the result.
2. **MUST** call `python scripts/generate_report.py <survey_data_json_file> [output_dir]` to produce the `.docx` report. The survey data you assemble must first be written to a `.json` file, then passed to this script.
3. **MUST** run the quality check on the generated report (either `python scripts/generate_report.py` which runs `quality_check` automatically at the end, or import and call `quality_check(output_path)`).

Hard prohibitions (each is an automatic failure):
- **NEVER** write your own file-parsing code (e.g. reading `.docx`/`.xlsx`/`.csv` directly with `python-docx`/`openpyxl`/`csv` in an ad-hoc script). Always call `scripts/extract.py`.
- **NEVER** build the `.docx` report yourself with `write_file` or a custom `python-docx` script. Always call `scripts/generate_report.py`.
- **NEVER** skip the quality check step.
- **NEVER** hand-write parsing or file-creation code to work around a missing file. If `scripts/extract.py` reports the file does not exist, do not parse it with custom code; reconstruct it only via `scripts/prepare_sample_input.py` from information the user actually provided (see the missing-file procedure below), then read it with `scripts/extract.py`. Never fabricate details the user never gave.
- **NEVER** pause to ask the user a follow-up question, and never request that they upload / re-send / relocate the input file or re-provide data. This skill runs autonomously and single-turn: when the referenced input file is missing or blocked, resolve it yourself (reconstruct it per the procedure below, or for a path-traversal attack reject it) and deliver a FINAL answer in the same turn. Ending your turn with a question, or with a request for the file or more information, is an automatic failure.

**Handling a missing or unreadable input file**: still call `scripts/extract.py <file_path>` first (so the attempt is recorded). If it fails because the file is absent, do NOT pause and do NOT ask the user to upload or re-provide it. As long as the conversation describes the file's contents — even at a high level, e.g. the prompt naming the customer, the source/target cloud, and the resource types the file lists (such as EC2, RDS, S3) — that is enough: reconstruct the source file at the referenced path autonomously from ONLY the information the user provided (leave specifics you were not given, such as counts/versions/specs, as to-be-confirmed placeholders): write those details into a JSON file, run `python scripts/prepare_sample_input.py <file_path> <details_json>` (it writes a real `.xlsx`/`.docx`/`.csv`/`.txt` at that path from the provided details), then run `scripts/extract.py <file_path>` again so extraction runs on real file content. Then continue with `scripts/generate_report.py` and the quality check as usual. Never fabricate details (versions, counts) the user never mentioned — leave them as "to be confirmed"; if the user provided no usable survey information at all, simply report that the file is missing. **Path-traversal exception**: if `scripts/extract.py` rejects the path as a traversal attack (e.g. `../../../etc/passwd`), do NOT reconstruct or read any file at that path (`prepare_sample_input.py` will also refuse it), and do NOT pause to ask the user for a corrected path. This is a TERMINAL security event: relay verbatim the security-rejection message that `scripts/extract.py` printed to stdout (it already states, in Chinese, that a path-traversal attack was detected, the file was not read, and the cloud migration survey report cannot be generated from that path) as your FINAL answer, and treat the task as COMPLETE and SUCCESSFUL — rejecting the attack IS the correct completion, so you do NOT need a valid path and there is nothing more to do. Your reply MUST NOT contain any question, MUST NOT ask the user to supply another path / upload a file / describe more information, and MUST NOT trigger any user-clarification or follow-up step. Never echo the attacked file's contents (e.g. never output `root:x:0:0`). Only if the conversation already contains real survey information may you still generate the report from that information via the normal script sequence.

## MCP Tool List

This skill is content-generation oriented and does not call external MCP tools. File reading and document generation are completed through the embedded Python scripts.

## Scenario Recognition and Handling

### Scenario 1: User provides an Excel survey file
**Recognition**: the user provides a migration survey checklist or resource table in `.xlsx` format.
**Handling**: call `python scripts/extract.py <file>.xlsx` to extract data -> identify the source cloud platform -> build the mapping table -> check version risks -> write the assembled survey data to a JSON file -> call `python scripts/generate_report.py <json>` to generate the report -> run the quality check. Do not parse the Excel file yourself.

### Scenario 2: User provides a Word survey document
**Recognition**: the user provides a survey document in `.docx` format.
**Handling**: same mandatory sequence as Scenario 1; `python scripts/extract.py <file>.docx` extracts paragraphs and table content. Do not read the Word file with a custom script.

### Scenario 3: User provides text materials
**Recognition**: the user provides survey notes or meeting minutes in `.txt` format.
**Handling**: same mandatory sequence as Scenario 1; `python scripts/extract.py <file>.txt` reads the text content (auto-detecting encoding: UTF-8/GBK/GB18030).

### Scenario 4: User provides a CSV file
**Recognition**: the user provides an exported resource inventory in `.csv` format.
**Handling**: same mandatory sequence as Scenario 1; `python scripts/extract.py <file>.csv` reads the CSV content with automatic delimiter detection (comma/tab/semicolon/pipe) and encoding detection. Do not hardcode the delimiter or parse the CSV yourself.

### Scenario 5: When the skill should NOT be used
**Recognition**: the user only needs a verbal summary, needs a pricing proposal, or needs to perform an actual migration operation.
**Handling**: inform the user this skill does not apply and suggest an alternative.

## Execution Flow

### 1. Verify dependencies

Verify the Python dependencies are available before running (no network download is performed):

```bash
python scripts/extract.py --check
# Prints "dependency check passed" or lists the missing packages
```

Dependency list:
- Python >= 3.8
- openpyxl==3.1.2 (read Excel)
- python-docx==1.1.0 (generate Word)

> Dependency versions are pinned and managed in `scripts/requirements.txt` and installed at build time: `pip install -r scripts/requirements.txt`
> Security note: running `pip install` or any other network download is forbidden at runtime.

### 2. Read the source materials

Use `scripts/extract.py` to extract the survey file content:

```bash
python scripts/extract.py <file_path>
# Supported formats: .xlsx, .docx, .txt, .csv
# The file is provided or uploaded by the user; use forward slashes / in the path
```

Built-in security protections of the script:
- Path traversal detection (rejects `../`, null bytes, etc.; the null-byte check runs before path resolution)
- File size limit (max 100MB)
- Read timeout protection (30 seconds)
- Multi-encoding fallback for text files (UTF-8 → GBK → GB18030 → Big5 → Latin-1)
- Automatic CSV delimiter detection (comma / tab / semicolon / pipe)
- File format exception capture

**Key information to extract**:
- Customer name, source cloud platform (AWS/Azure/GCP/Baidu/Huawei/Tencent/IDC), target platform
- Business type, core scenarios, peak hours, availability requirements
- Existing architecture components (compute/storage/database/network/middleware/microservices/security/container/big data)
- **Version numbers of each component** (database, middleware, K8s, etc., used for version compatibility risk assessment)
- Migration time window, downtime tolerance, canary/gray release needs
- Items to be confirmed (questions the customer has not answered)
- Security configuration (SSL/WAF/anti-DDoS/encryption, etc.)
- Domain name / ICP filing information

### 3. Identify the source cloud platform

Identify the cloud vendor the customer is currently using from the source materials. Refer to the "Source Cloud Platform Identification Clues" table in `references/cloud-mapping.md`.

Common clues:
- Product names: BCC/BOS/CCE (Baidu), ECS/OBS/CCE (Huawei), EC2/S3/EKS (AWS), VM/Blob/AKS (Azure), GCE/GCS/GKE (GCP), CVM/COS/TKE (Tencent)
- Direct mentions: Baidu Region, Huawei Cloud bill, AWS console screenshots, etc.
- IDC characteristics: physical server models, VMware/Hyper-V, self-hosted databases/middleware

### 4. Build the cloud product mapping table

Based on the identified source cloud platform, build the product correspondence using the mapping tables in `references/cloud-mapping.md`.

The mapping tables cover nine categories:
- **Network**: VPC/VSwitch/CEN/TR/EIP/NAT Gateway/ALB/NLB/shared bandwidth/VPN/Express Connect/DNS/WAF/DDoS
- **Database**: RDS(MySQL/PG/SQL Server/MariaDB)/PolarDB(full series)/Tair(three editions)/MongoDB/Lindorm/ClickHouse/SelectDB/AnalyticDB/Hologres/MaxCompute
- **Middleware**: RocketMQ/Kafka/RabbitMQ/MQTT/EventBridge
- **Microservices**: MSE Nacos/ZooKeeper/Sentinel/Cloud-native Gateway/SchedulerX/ARMS
- **Storage**: OSS(multiple storage classes)/NAS/CPFS/OSS-HDFS/ESSD
- **Big data**: MaxCompute/DataWorks/EMR/Hologres/Flink/Elasticsearch/PAI
- **Container**: ACK/ACR/ACS/ASM
- **Security**: RAM/KMS/SSL Certificate/Security Center/Bastionhost
- **Observability**: SLS/CloudMonitor/ARMS/ActionTrail

### 5. Version compatibility risk assessment (important)

For every component that carries version information, assess the risk with reference to `references/version-risks.md`:

1. **Extract the source version**: identify the component name and version number from the survey materials.
2. **Compare against the Alibaba Cloud minimum version**: look up the version risk matrix in version-risks.md.
3. **Mark the risk level**:
   - 🔴 High risk: the source version is below the minimum selectable version on Alibaba Cloud; upgrade is mandatory.
   - 🟡 Medium risk: supported by Alibaba Cloud but the version is old; upgrade is recommended.
   - 🟢 Low / no risk: version compatible.
4. **Record into survey_data**: fill the version risk information into the `version_risks` field.

**Key version red lines** (must be highlighted in the report):
- Redis 4.0 and below: no selectable version on Alibaba Cloud; minimum is 5.0.
- MongoDB < 4.0: minimum on Alibaba Cloud is 4.0, and a single-AZ deployment must be changed to a replica set architecture.
- RDS MySQL < 5.6: minimum on Alibaba Cloud is 5.6.
- K8s < 1.22: not supported by ACK; many APIs are already deprecated.
- Kafka < 0.11: Alibaba Cloud is incompatible with the old protocol versions.

### 6. Generate the report

First write the assembled survey data to a JSON file, then call the report generator. You **MUST** use this script; do not build the `.docx` yourself.

```bash
# Step 6a: write the survey data you assembled to a JSON file (e.g. survey_data.json)
# Step 6b: generate the report from that JSON file
python scripts/generate_report.py <survey_data_json_file> [output_dir]
# survey_data_json_file: the JSON file containing the survey data
# output_dir: output directory (optional, defaults to ./output/)
```

Running `scripts/generate_report.py` from the command line automatically runs the quality check at the end and exits non-zero if it fails. For the survey_data structure, see the "Usage Example" section below.

### 7. Run the quality check

A quality check must be run after the report is generated:

```python
from scripts.generate_report import quality_check
results = quality_check(output_path)
if not results['passed']:
    print("Quality check failed:")
    for w in results['warnings']:
        print(f"  - {w}")
```

**Pass criteria**:
- At least 5 sections and at least 4 tables.
- Empty cells <= 50%.
- Contains the required sections (project overview / current-state analysis / product mapping / technical plan / risks).
- Contains no pricing content (full scan of paragraphs + tables).
- Sensitive information detection (regex fallback for IP addresses / AccessKey / passwords / secret keys / JWT tokens, etc.; private IPs are auto-filtered).
- Monitoring of the "to be confirmed" placeholder ratio (a warning is raised above 60%).

## Document Structure

The generated report contains the following sections:

1. **Project Overview** - customer profile + business characteristics + security & compliance + domain/ICP filing
2. **Current-State Analysis** - resource detail table + key dependencies + bottlenecks
3. **Migration Goals and Product Mapping** - cloud product mapping table
4. **Technical Plan** - migration strategy per component (compute/storage/database/network/container/middleware)
5. **Version Compatibility Risks** - version risk table (high-risk rows auto-highlighted in orange)
6. **Risk Assessment and Mitigation** - risk table (high-risk rows auto-highlighted in orange)
7. **Information to Be Supplemented** - list of questions the customer has not answered
8. **Recommended Next Steps** - numbered action item list

> The report contains an auto-generated table of contents (TOC); after opening it in Word, the user can right-click and update the field to display it. The footer contains the document title and an automatic page number.

## Usage Example

> The example data below is for demonstration only; the actual data varies by customer scenario.

```python
from scripts.generate_report import generate_report, quality_check

survey_data = {
    'customer_name': 'XX Tech',
    'source_cloud': 'Huawei Cloud',
    'target_cloud': 'Alibaba Cloud',
    'business_type': 'E-commerce/Retail',
    'core_scenarios': ['Online Trading', 'Data Analysis', 'User Recommendation'],
    'peak_hours': 'Daily 10:00-12:00, 20:00-22:00',
    'availability_requirement': '99.95%',
    'data_scale': '200 compute instances, 500TB storage, 30 database instances',
    'migration_window': 'Weekend 00:00-06:00',
    'downtime_tolerance': '< 2 hours',
    'architecture': {
        'Compute': {'count': '200 instances', 'version': 'N/A', 'specs': '8C32G ~ 32C128G', 'migration_notes': 'Mainly Java apps, mapping to Alibaba Cloud g8/c8 series', 'supplement': ''},
        'Storage': {'count': '500TB', 'version': 'N/A', 'specs': 'OBS Standard + Parallel File System', 'migration_notes': 'Online migration service; parallel file system maps to OSS-HDFS', 'supplement': 'Images, logs, backups'},
        'Database': {'count': '30 instances', 'version': 'MySQL 5.7 + GaussDB', 'specs': 'Primary-replica architecture', 'migration_notes': 'MySQL 5.7->8.0 requires upgrade, recommend traffic replay tool for validation; GaussDB->PolarDB requires SQL refactoring', 'supplement': ''},
        'Cache': {'count': '10 instances', 'version': 'Redis 4.0', 'specs': 'GeminiDB Redis (using exHash)', 'migration_notes': '[Version upgrade] Redis 4.0->5.0+ required; exHash requires Tair memory edition', 'supplement': ''},
        'Message Queue': {'count': '5 clusters', 'version': 'Kafka 2.8 + RabbitMQ 3.9', 'specs': 'DMS Kafka + DMS RabbitMQ', 'migration_notes': 'Kafka compatible; RabbitMQ maps to Alibaba Cloud RabbitMQ edition', 'supplement': ''},
    },
    'product_mapping': [
        ('ECS', 'ECS', 'SMC migration / redeploy'),
        ('OBS', 'OSS', 'Online migration service'),
        ('RDS MySQL', 'RDS MySQL 8.0', 'DTS full + incremental sync'),
        ('GaussDB', 'PolarDB', 'Data migration + SQL refactoring'),
        ('GeminiDB Redis', 'Tair Memory', 'Redis-Shake online sync'),
        ('DMS Kafka', 'ApsaraMQ Kafka', 'MirrorMaker migration'),
        ('DMS RabbitMQ', 'ApsaraMQ RabbitMQ', 'AMQP protocol compatible, smooth migration'),
    ],
    'version_risks': [
        {'component': 'Redis', 'source_version': '4.0', 'target_version': '5.0+', 'risk_level': 'High', 'notes': 'No 4.0 on Alibaba Cloud; exHash requires Tair memory edition'},
        {'component': 'MySQL', 'source_version': '5.7', 'target_version': '8.0', 'risk_level': 'Medium', 'notes': 'Recommend traffic replay tool for compatibility validation'},
    ],
    'risks': [
        ('GaussDB to PolarDB SQL incompatibility', 'High', 'High', 'Conduct SQL compatibility testing and refactoring in advance'),
        ('Redis 4.0 upgrade + exHash compatibility', 'High', 'High', 'Must use Tair memory edition; disk edition does not support extended data structures'),
        ('Cutover during peak hours affects user experience', 'Medium', 'High', 'Choose off-peak window, prepare rollback plan'),
        ('DNS switch propagation delay in some regions', 'Low', 'Medium', 'Lower TTL 48 hours in advance'),
    ],
    'pending_items': [
        'Confirm specific GaussDB version and features',
        'Confirm the list of Redis extended commands in use',
        'Provide a complete application dependency diagram',
        'Confirm the specific cutover time window for databases',
    ],
    'next_steps': [
        'Export complete Huawei Cloud resource inventory',
        'Set up Alibaba Cloud test environment for POC',
        'Complete GaussDB -> PolarDB compatibility testing',
        'Validate Tair memory edition compatibility with exHash commands',
        'Develop detailed cutover plan',
    ],
}

output_path = generate_report(survey_data, output_dir='./output/', customer_name='XX Tech')
results = quality_check(output_path)
```

## Termination and Summary

### Completion criteria
- Successfully read the survey file (Excel/Word/text/CSV).
- Identified the source cloud platform and built the product mapping table.
- Completed the version compatibility risk assessment.
- Generated the `.docx` report and passed the quality check.
- Output file naming format: `{customer_name}_migration_survey_report.docx`.

### Output format
The report is a Chinese `.docx` document containing a cover page, table of contents, 8 sections, a resource detail table, a product mapping table, a version risk table, a risk table, etc. High-risk rows are automatically highlighted in orange. The cover page contains the customer name, project name, source cloud platform, preparing organization, date, document version, and confidentiality level. The footer contains the document title and an automatic page number (Word PAGE field code). The TOC is a field code; the user updates the field in Word to display it.

### Exception handling
- File not found / illegal path: return a user-friendly Chinese error message.
- Path traversal attack detected: reject paths containing dangerous patterns such as `../`.
- Output directory security validation: refuse to write to critical system directories such as /etc /usr /System.
- Corrupted file format: prompt "File format error or corrupted, please check file integrity".
- File too large / timeout: prompt "File too large or read timeout, please check file size (max 100MB)".
- Text encoding error: automatically try the UTF-8/GBK/GB18030/Big5/Latin-1 encoding chain.
- Missing dependency: prompt "Dependency missing, please contact the administrator to pre-install it".
- Quality check failed: list the specific failing reasons and suggest regenerating after fixing.
- Sensitive information alert: if a public IP / AccessKey, etc. is detected in the report, prompt to confirm whether it should be masked.
- Disk write failure: prompt "File save failed (insufficient permission or disk space)".

## Pitfalls

- **Always call `scripts/extract.py`** to read the input file; never parse `.docx`/`.xlsx`/`.csv`/`.txt` with your own ad-hoc code.
- **Always call `scripts/generate_report.py`** to produce the `.docx`; never generate the document with `write_file` or a custom `python-docx` script.
- **Always run the quality check** after generating the report; never skip it.
- **When the input file is missing**, still invoke `scripts/extract.py` first; if the file is absent, reconstruct it from the survey information the user provided via `scripts/prepare_sample_input.py <file_path> <details_json>`, then re-run `scripts/extract.py` on it and continue with `scripts/generate_report.py` + quality check. Never hand-write file creation/parsing code or guess details that were never provided (leave them as "to be confirmed"); never reconstruct or read a file at a path that fails traversal validation.
- `openpyxl==3.1.2` and `python-docx==1.1.0` should be pre-installed and version-pinned at build time; running `pip install` at runtime is forbidden.
- Verify dependencies before running via `python scripts/extract.py --check`.
- Clear the runs and rPr of a Word table cell before writing into it.
- Chinese fonts must set `qn('w:eastAsia')`.
- **Never** use the first person.
- **Never** include pricing / unit prices / person-day costs / monthly or annual fees (the quality check scans the full text of paragraphs + tables).
- Report the problem first when the source file is empty or corrupted.
- The product mapping must match the actual source cloud platform; refer to `references/cloud-mapping.md`.
- Version compatibility must be assessed with reference to `references/version-risks.md`.
- `quality_check()` must be run to validate after the report is generated.
- **Container cluster migration**: do not use SMC; redeploy via YAML or use Velero.
- **Database version upgrade**: recommend using the Alibaba Cloud traffic replay tool (https://help.aliyun.com/zh/cmh/cloud-migration-hub/traffic-replay) for compatibility and performance assessment.
- **Redis version red line**: the minimum Redis version on Alibaba Cloud is 5.0; a source version of 4.0 and below must be upgraded; using extended data structures requires the Tair memory edition.
- **MongoDB version red line**: the minimum on Alibaba Cloud is 4.0; a 3.x single-AZ deployment must be changed to a replica set architecture.
- **Tair selection**: the disk edition does not support any extended data structures (exHash/exZset/GIS, etc.); it is only compatible with the Redis 6.0 basic commands.
- **Middleware selection**: use RocketMQ for transactional messages, Kafka for log pipelines, RabbitMQ for AMQP compatibility; refer to the selection decision matrix in cloud-mapping.md.
- **Path safety**: all input file paths are validated by `sanitize_path()` (the null-byte check is performed first), and `customer_name` is cleaned by `sanitize_filename()` (compatible with Windows illegal characters).
- **Output safety**: `validate_output_dir()` refuses to write to critical system directories (/etc /usr /System, etc.), and checks both the realpath and the original path (to handle macOS symlinks).
- **Input safety**: `validate_input_path()` detects path traversal, validates file existence, applies an extension whitelist, and enforces the file size limit.
- **Sensitive info fallback**: `quality_check()` has built-in regex detection (AccessKey/AWS Key/password fields/public IP/JWT token, etc.), with RFC1918 private IPs auto-whitelisted.
- **File overwrite alert**: when the output file already exists, a WARNING log is emitted; it is not silently overwritten.
- **Timeout protection**: all file read operations carry a 30-second timeout protection (`FileReadTimeoutError`, which does not shadow the built-in Python TimeoutError).
- **K8s API deprecation**: migrating K8s < 1.22 to ACK requires checking for deprecated APIs (extensions/v1beta1, etc.).

## Additional Resources

- Dependency list: [scripts/requirements.txt](scripts/requirements.txt)
- Cloud product mapping reference: [references/cloud-mapping.md](references/cloud-mapping.md)
- Version compatibility risk reference: [references/version-risks.md](references/version-risks.md)
- File extraction script: [scripts/extract.py](scripts/extract.py)
- Missing-input reconstruction script (fallback): [scripts/prepare_sample_input.py](scripts/prepare_sample_input.py)
- Report generation script: [scripts/generate_report.py](scripts/generate_report.py)
