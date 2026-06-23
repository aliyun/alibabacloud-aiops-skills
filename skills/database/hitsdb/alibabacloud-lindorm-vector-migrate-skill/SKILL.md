---
name: alibabacloud-lindorm-vector-migrate-skill
description: |
  向量数据库迁移助手 — 从 Milvus、Elasticsearch、Lindorm 或 Qdrant 迁移向量数据至阿里云 Lindorm。支持从源库导出为 CSV 文件后上传 OSS 再导入。通过对话收集参数，直接生成并执行代码完成迁移。支持断点续传、字段排除、DDL 预览确认等。
  Triggers: "迁移", "向量数据", "向量迁移", "数据迁移", "vector transfer", "migration", "vector database", "Lindorm 迁移", "迁移到 Lindorm", "ES 迁移", "Qdrant 迁移", "断点续传", "csv 文件导入", "oss 导入", "导出到 CSV", "导出为 CSV", "export to CSV", "CSV 导出".
---

# Vector Database Migration Assistant

Migrate vector data from Milvus / Elasticsearch / Lindorm / Qdrant / CSV files to Alibaba Cloud Lindorm Search Engine. Supports exporting source indices to CSV files. The Agent is responsible for collecting parameters, generating and executing code to complete all operations.

## Core Capability Matrix

| Category | Sub-Scenarios | Reference Docs |
|---------|--------------|----------------|
| **01-Dev** | Source migration guides (Milvus/ES/Lindorm/Qdrant/CSV), CSV export, complete workflow | `references/01-dev/` |
| **02-Ops** | Pre-checks, post-migration validation, TTL configuration, checkpoint resume | `references/02-ops/` |
| **03-Ref** | Type mapping, bulk write API, code migration, official documentation | `references/03-ref/` |

## Decision Tree

```
User Request
├── Complete migration workflow → references/01-dev/workflow.md
│
├── Source data reading → 01-dev
│   ├── Milvus → references/01-dev/milvus-migrate.md
│   ├── Elasticsearch → references/01-dev/elasticsearch-migrate.md
│   ├── Lindorm source → references/01-dev/lindorm-migrate.md
│   ├── Qdrant → references/01-dev/qdrant-migrate.md
│   ├── CSV file (OSS) → references/01-dev/csv-import.md
│   └── Export to CSV → references/01-dev/csv-export.md
│
├── Migration operations → 02-ops
│   ├── Post-migration validation → references/02-ops/postcheck.md
│   ├── TTL configuration / source TTL conversion → references/02-ops/ttl-config.md
│   └── Checkpoint resume mechanism → references/02-ops/checkpoint-resume.md
│
├── Reference materials → 03-ref
│   ├── CSV file format specification → references/03-ref/csv-format.md
│   ├── Field types / distance metrics / DDL generation → references/03-ref/type-mapping.md
│   ├── Bulk write / index creation / index building → references/03-ref/bulk-write.md
│   ├── Application code migration advice → references/03-ref/code-migration.md
│   └── API details uncertain → references/03-ref/official-refs.md
```

## Workflow Overview

Complete workflow (Step 1-7) is detailed in `references/01-dev/workflow.md`.

| Step | Summary | Detailed Guide |
|------|---------|---------------|
| 1. Collect information | Source/target connection parameters, migration options, network type | `workflow.md#step-1` |
| 1.5 Export to CSV (optional) | Export from source index to CSV → user uploads to OSS → connect to CSV import flow | `references/01-dev/csv-export.md` |
| 2. Pre-checks | Connection validation, space estimation, type compatibility, TTL detection | `workflow.md#step-2` |
| 3. Generate DDL | Lindorm ES-compatible mapping generation and confirmation | `workflow.md#step-3` |
| 4. Create index | Target index creation | `workflow.md#step-4` |
| 5. Execute migration | Source scan → Lindorm bulk write, checkpoint resume | `workflow.md#step-5` |
| 6. Post-migration validation | Row count validation, random sampling, vector similarity, TTL validation | `workflow.md#step-6` |
| 7. Code migration | Advice for migrating application code from source to Lindorm | `workflow.md#step-7` |

## Guardrails

- Pre-checks (Step 2) MUST be executed and MUST NOT be skipped. On FAIL, MUST inform the user of the risk and wait for user confirmation; on WARN, MUST use AskUserQuestion to confirm before proceeding
- DDL confirmation (Step 3) MUST present the complete DDL JSON to the user via AskUserQuestion for confirmation. MUST NOT skip automatically, and MUST NOT substitute a brief description for the full display
- When using IVFPQ/IVFBQ index methods, the DDL MUST include `"knn.offline.construction": true`; after triggering Build, MUST poll until `ready` or `failed`, MUST NOT exit polling while in `building` status; MUST NOT use `_forcemerge` as a substitute for the Build API
- Before migration, MUST advise the user to stop writes and use AskUserQuestion to confirm (already stopped / acknowledge risk and continue / cancel). If user cancels, MUST NOT execute the migration script
- Post-migration validation (Step 6) MUST be executed and MUST NOT be skipped, and does not require asking the user whether to execute. When all validations pass, proceed directly to Step 7; if issues are found, MUST use AskUserQuestion for user confirmation before proceeding
- Application code migration advice (Step 7) MUST be proactively provided after migration completes. MUST display the corresponding source-specific migration checklist (with concrete API replacement code) based on the source type; MUST NOT provide only generic advice
- Source is read-only; MUST NOT modify user data
- Connection failures must display full error information; MUST NOT silently retry
- Progress must be actively reported; MUST NOT silently wait for completion
- Required parameters that are missing must be asked for; MUST NOT guess
- Migration scripts MUST use TeeWriter to simultaneously write all output to stdout and a log file, ensuring checkpoint information is reliably persisted in any execution mode
- Agent MUST NOT write any credentials, passwords, Access Keys, Tokens, or other secrets to files (including scripts, configurations, logs, etc.). All credentials MUST be passed via environment variables or collected interactively at runtime; MUST NOT be written in plaintext to disk. **Credential fallback values MUST be empty string or None** (e.g., `os.environ.get("LINDORM_PASSWORD", "")`), MUST NOT use the user's actual password as a fallback default value
- When resuming from interruption, the Agent MUST extract checkpoint information from the log file (prioritize `[INTERRUPTED]`, fall back to `[PROGRESS]`), parse the cursor value while preserving its original type (int/str/list) for the resume parameters, and MUST NOT silently restart from the beginning. If parsing fails, MUST inform the user and display the raw log content
- Excluded fields MUST take effect in both DDL generation and data migration stages
- When choosing to clear the target, MUST require a second confirmation before deleting the target index
- When importing from CSV, the original data source MUST be one of Milvus / Elasticsearch / Lindorm / Qdrant. When "Other" is selected, MUST reject processing
