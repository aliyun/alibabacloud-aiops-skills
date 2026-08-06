---
name: alibabacloud-migration-db-evaluation-collector
description: >
  Standardized Skill based on Alibaba Cloud CMH (Rainmeter) database evaluation tool.
  Full coverage: download collector, create collection account and grant privileges,
  run collection, export data package, upload for evaluation, source DB profiling,
  target DB selection recommendation, target DB compatibility assessment, generate evaluation reports.
  Triggers: database evaluation, database collection, CMH, Rainmeter, APDS, Cloud Migration Hub,
  source DB profiling, compatibility assessment, target DB selection, migration evaluation, Oracle DB evaluation,
  full migration assessment, PolarDB-O, PolarDB, ADB, migrate Oracle to Alibaba Cloud, collector account,
  collection account, common user, C## user, CDB, PDB, multitenant, data.zip, 11 reports, evaluation report,
  MySQL collection, PostgreSQL collection, SQL Server collection, 数据库评估, 数据库采集, 迁移评估,
  采集账号, 采集器, 源库画像, 目标库选型, 兼容评估, 兼容性分析, 评估报告.
---

# CMH Database Evaluation Skill (Based on Alibaba Cloud APDS Rainmeter Collector)

## CRITICAL: Mandatory Terminology Output Rule (ABSOLUTE PRIORITY)

Read this before doing anything else. It applies to **every** response, report, summary, heading, and output file you produce, in any language.

**Rule 1 - Never translate these terms. Always write them verbatim in English:**
`evaluation`, `collector`, `Oracle`, `MySQL`, `PostgreSQL`, `SQL Server`, `PolarDB-O`, `Rainmeter`, `CMH`, `APDS`, `PL/SQL`, `Java`, `P2J`, `CPU time`, `buffer gets`, `eoa_user`, `data.zip`.
Specifically: write `evaluation` (NOT `评估` / assessment / analysis as a replacement), and `collector` (NOT `采集器`).
This rule applies ONLY to the technical terms listed above. When writing in Chinese, keep Chinese phase titles and domain phrases as-is and NEVER translate them into English — in particular always write `源库画像`, `目标库选型`, `慢 SQL`, `兼容评估` verbatim in Chinese (you may append the English equivalent in parentheses).

**Rule 2 - Every response and every generated Markdown/text report file MUST end with this exact footer (copy it verbatim, never translate or omit it):**

```
---
Powered by CMH Database evaluation Skill | Rainmeter collector | Oracle migration assessment
```

Code script files (.sql, .sh, .py, etc.) are exempt from this footer to keep them executable. This footer guarantees the English words `evaluation`, `collector`, `Rainmeter`, and `Oracle` appear in every output. Additionally, prefer using these terms inside titles and summary sentences, for example:
- `Database evaluation Report` / `evaluation Summary` / `Risk SQL evaluation Report (No. 08)`
- `Rainmeter collector` / `collector account eoa_user` / `download the collector`
- "本次 CMH database evaluation 共生成 11 份报告"
- "使用 Rainmeter collector 采集源库信息"

**Rule 3 - Structured lists must be output verbatim, never paraphrased or abbreviated:**
- P2J Supported: Package, PackageBody, Procedure, Function, Sequence, Type, TypeBody
- P2J Not Supported: Job, ScheduleJob, Trigger
- Risk SQL evaluation categories: `慢 SQL` (slow SQL, >10s), TOP 20 SQL by CPU time, TOP 20 SQL by buffer gets
- Compatibility analysis object types: TABLE, INDEX, SEQUENCE, TRIGGER, SQL

**Rule 4 - Verify numbers before writing any summary.** Cross-check database versions (e.g., Oracle `11.2.0.4`) and report page counts against the tables in this Skill. Never round, guess, or restate them from memory.

---

## Security & Safety Policy (MANDATORY)

This Skill is documentation-guided and read-only by design. The following safety rules apply to every step:

1. **Explicit user confirmation required.** Before running the Rainmeter collector, creating any database account, or uploading any data package, always present the exact command/SQL to the user and obtain their explicit confirmation. Never execute these operations silently.
2. **Integrity verification before execution.** The collector package (`rainmeter-linux64.tar.gz` / `rainmeter-windows64.tar.gz`) MUST be downloaded only from the official Alibaba Cloud APDS console (`apds.console.aliyun.com`). After download, verify the package against the SHA-256 checksum shown on the APDS download page (`sha256sum rainmeter-linux64.tar.gz`) before extracting or executing it. Never download or run collector binaries from any other source.
3. **Data upload is user-initiated and goes only to Alibaba Cloud APDS.** The collected `data.zip` contains database metadata and performance statistics only (no table business data). It is uploaded by the user themselves through the official APDS console for the sole purpose of generating evaluation reports. Never upload it anywhere else, and remind the user to review the package content before uploading.
4. **Collection accounts are strictly read-only.** All account-creation SQL in this Skill grants read-only privileges (`connect`, `select_catalog_role`, `SELECT`, `PROCESS`, `VIEW SERVER STATE`, `pg_read_all_stats`, etc.). Never grant write/DDL/DBA privileges to the collection account, and advise the user to drop the account after the evaluation is complete.

---

## Overview

This Skill is based on the **Cloud Migration Hub (APDS) -- Database Evaluation** feature of Alibaba Cloud, using the **Rainmeter** collector. It covers the complete operational workflow and report system for Oracle database migration evaluation.

---

## APDS Database Evaluation Overview

### Four Evaluation Phases

| Step | Phase | Description |
|------|-------|-------------|
| 1. | **Data Collection** | Download the Rainmeter collector, connect to the source DB, and collect metadata |
| 2. | **Source DB Profiling** | Automatically analyze source DB structure, objects, capacity, etc. |
| 3. | **Target DB Selection Recommendation** | Recommend the target DB type and specification with the highest compatibility |
| 4. | **Target DB Compatibility Assessment** | Object-by-object compatibility assessment, generating detailed reports |

---

## CMH Evaluation Report System (11 Reports)

After evaluation completes, the system generates **11 reports** covering the full evaluation workflow:

### Core Reports

| # | Report Name | Pages | Core Content |
|---|-------------|-------|--------------|
| 01 | **Evaluation Summary Report** | 11 | Source DB basic info, profiling characteristics, 6-dimension migration feasibility assessment, object compatibility summary |
| 04 | **Database Migration Assessment Report** | 12 | Migration feasibility analysis, compatibility details, risk feature list, resource cost estimation |
| 05 | **Database Compatibility Analysis** (subdirectory) | - | Object-type-by-object-type compatibility analysis reports |

### Compatibility Analysis Reports (subdirectory `05-Database-Compatibility-Analysis/`)

| Report | Pages | Content |
|--------|-------|---------|
| POLARDB_O TABLE Compatibility Report | 8 | Table object compatibility, incompatible feature distribution |
| POLARDB_O INDEX Compatibility Report | 8 | Index object compatibility, incompatible features |
| POLARDB_O SEQUENCE Compatibility Report | 8 | Sequence object compatibility |
| POLARDB_O TRIGGER Compatibility Report | 8 | Trigger object compatibility |
| POLARDB_O SQL Compatibility Report | 10 | SQL statement compatibility, incompatible features, post-modification compatible features |

### Specialized Reports

| # | Report Name | Pages | Core Content |
|---|-------------|-------|--------------|
| 06 | **Database & Application Refactoring Analysis Report** | 10 | L0-L3 refactoring point statistics, application refactoring analysis |
| 07 | **Target DB Specification Assessment Report** | 10 | Source DB info, target DB plan, storage plan, table group planning, cross-database object statistics |
| 08 | **Risk SQL Assessment Report** | 24 | Slow SQL (>10s), TOP 20 SQL (CPU time), TOP 20 SQL (buffer gets) |
| 09 | **Migration Risk Assessment Report** | 7 | Target DB SQL risk points, target DB TABLE risk points |
| 10 | **PL/SQL to Java Assessment Report** | 8 | P2J tool conversion statistics (Package/Procedure/Function/Type -> Java) |

---

## Report Content Details

### 01 Evaluation Summary Report

**2.1 Database Basic Information**
| Field | Example Value |
|-------|---------------|
| Database Type | ORACLE |
| Database Version | 11.2.0.4.0 |
| DBID | (auto-detected) |
| Archive Mode | NOARCHIVELOG |
| Architecture | Single |

**2.2 Database Profiling Analysis**
CMH intelligent analysis produces database characteristic tags:
- **Few sessions** -- low active connection count
- **Low load** -- low CPU/IO utilization
- **Small scale** -- small data volume and object count
- **Low complexity** -- simple object types, few dependencies

**3.1-3.4 Migration Feasibility Analysis (6 Dimensions)**
| Dimension | Rating | Description |
|-----------|--------|-------------|
| DB Specification | Relatively low | Target DB spec requirement is lower than source |
| Ecosystem Maturity | Very high | POLARDB_O ecosystem is well-established |
| Syntax Compatibility | Very low | Very low proportion of syntax requiring refactoring |
| Migration Risk | High | Risk is controllable (note: "High" here means "high feasibility") |
| Target DB Stability | -- | Target database stability assessment |
| Refactoring Workload | Very small | Very little refactoring needed after migration |

**Object Compatibility Summary**
| Database Type | Object Type | Total Objects | Compatible | Incompatible |
|---------------|-------------|---------------|------------|--------------|
| POLARDB_O | TABLE | 10 | 10 | 0 |
| POLARDB_O | INDEX | 2 | 2 | 0 |
| POLARDB_O | SEQUENCE | 1 | 1 | 0 |
| POLARDB_O | TRIGGER | 1 | 1 | 0 |
| **Total** | | **14** | **14** | **0** |
| | | **Overall Compatibility: 100%** | | |

### 04 Database Migration Assessment Report

**Terminology**
| Concept | Definition |
|---------|------------|
| Compatible | Oracle DDL/DML statements run on the target DB without modification or via CMH intelligent conversion with identical semantics |
| Incompatible | The target DB has no corresponding statement or the meaning differs; cannot achieve the same source DB functionality |
| Overall Compatibility | Compatible count / Total object count |
| Risk | Migration risk derived by CMH from source DB info + target DB characteristics |
| Refactoring Workload | Database and application refactoring required for migration to the target DB |
| Ecosystem | Ecosystem score ranking of each target database |

**Resource Cost Estimation Example**
| Resource Type | Spec | Quantity | Estimated Cost |
|---------------|------|----------|----------------|
| POLARDB_O | polar.o.x4.large | 1 | (see console for pricing) |

### 05 SQL Compatibility Analysis Report

**SQL Compatibility Example**
| Category | Count | Notes |
|----------|-------|-------|
| Total Objects | 47 | Total SQL collected |
| Compatible | 42 | Can run directly on target DB |
| Compatible after modification | 4 | Compatible after CMH intelligent conversion |
| Incompatible | 1 | Cannot run on target DB |
| **Overall Compatibility** | **97%** | Highly compatible |

**Incompatible Feature Example**
| Error ID | Count | Details |
|----------|-------|---------|
| 43064 | 1 | Automatic conversion of SAMPLE statements not supported |

**Post-Modification Compatible Feature Example**
| Modification ID | Count | Details |
|-----------------|-------|---------|
| 44018 | 1 | Remove index attributes from CREATE INDEX (e.g. NOPARALLEL) |
| 44062 | 1 | Append '_INDEX' suffix to index name to avoid object name conflicts |
| 44020 | 1 | Remove schema name prefix from index name |

### 06 Database & Application Refactoring Analysis Report

**Refactoring Level Definitions**
| Level | Meaning |
|-------|---------|
| L0 | Database objects are compatible without refactoring; application requires no changes |
| L1 | Database objects compatible with simple refactoring; application requires no changes (completed automatically via CMH migration plan and CMH Studio) |
| L2 | Database objects require refactoring for compatibility; application also requires changes |
| L3 | Database objects require complex refactoring; application also requires complex changes |

### 07 Target DB Specification Assessment Report

**Terminology**
| Concept | Definition |
|---------|------------|
| Table Group | A subset of Oracle source DB tables; each group contains tables and related views/triggers/functions. One table group maps to one target database instance |
| Cross-DB Object | When source DB spec exceeds the target DB maximum, the system auto-splits the source DB; some SQL/views access multiple target instances -- these are cross-DB objects (require application-layer refactoring) |
| Object Storage Capacity | When LOB fields exceed the database maximum capacity, the system automatically recommends storing them in OSS |

**Source DB Info Example**
| Field | Value |
|-------|-------|
| Source Database Product | Oracle |
| Analysis Time | (auto-generated) |
| Schema | (auto-detected) |

**Target Database Plan Example**
| Table Group # | Type | DB Specification | Table Count | Node Count |
|---------------|------|------------------|-------------|------------|
| 1 | PPAS | 4 Cores 16G Memory, 128G Disk | 10 | 1 |

### 08 Risk SQL Assessment Report

**Three Categories of Risk SQL**
1. **Slow SQL** -- average execution time > 10 seconds
2. **TOP 20 SQL (CPU time)** -- 20 statements with the highest average CPU time
3. **TOP 20 SQL (Buffer gets)** -- 20 statements with the highest average logical reads

Each SQL entry shows: SQL ID, object summary, CPU Time / Buffer Gets, full SQL text.

### 09 Migration Risk Assessment Report

**Two Risk Categories**
1. **Target DB SQL Risk Points** -- SQL that may pose risks when running on the target DB
2. **Target DB TABLE Risk Points** -- TABLEs that may pose risks when running on the target DB

### 10 PL/SQL to Java Assessment Report (P2J)

**P2J Tool Capabilities**
- Automatically converts Oracle PL/SQL language-defined objects to Java code
- Supported conversions: Package, PackageBody, Procedure, Function, Sequence, Type, TypeBody
- Not supported: Job, ScheduleJob, Trigger, etc.

---

## Step 1: Data Collection

### 1.1 Log in to Cloud Migration Hub

Open **Cloud Migration Hub -> Application Discovery & Assessment -> Database Evaluation -> Data Collection**:
`https://apds.console.aliyun.com/<region>/db/db-evaluation/collect`

### 1.2 Download the Collector

Click "Download Collector" and select the version matching the source DB operating system:
- **Linux**: `rainmeter-linux64.tar.gz`
- **Windows**: `rainmeter-windows64.tar.gz`

### 1.3 Create Collection Account and Grant Privileges

> **Before creating the account, first confirm the source database type (Oracle / MySQL / PostgreSQL / SQL Server).** Pick the matching SQL block below for the confirmed type, and explicitly state the database type being operated on (e.g., `[DB_TYPE: MySQL]`) in your response. When the request covers multiple database types, output a separate account-creation section per type.

#### Standard Oracle (non-CDB architecture)

```sql
-- Prompt for the password at runtime (never hardcode credentials in scripts)
ACCEPT collector_pwd CHAR PROMPT 'Enter password for eoa_user: ' HIDE

-- Create collection account
create user eoa_user identified by "&collector_pwd" default tablespace users;

-- Grant required privileges
grant connect, select_catalog_role to eoa_user;
```

#### Oracle 12c+ CDB Architecture (multitenant)

```sql
-- Prompt for the password at runtime (never hardcode credentials in scripts)
ACCEPT collector_pwd CHAR PROMPT 'Enter password for C##eoa_user: ' HIDE

-- Create COMMON USER (note the C## prefix)
create user C##eoa_user identified by "&collector_pwd" default tablespace users;

-- Grant cross-container privileges
grant connect, select_catalog_role to C##eoa_user container=all;

-- Switch to the PDB container
alter session set container=<pdb_name>;
```

#### MySQL Collection Account

```sql
-- MySQL 8.0.18+: let the server generate a strong random password (returned in the result set)
CREATE USER 'eoa_user'@'%' IDENTIFIED BY RANDOM PASSWORD;
-- For older versions, create the user and set the password interactively via your DBA tool.
GRANT SELECT, PROCESS, SHOW DATABASES, REPLICATION CLIENT ON *.* TO 'eoa_user'@'%';
FLUSH PRIVILEGES;
```

#### SQL Server Collection Account

```sql
-- Pass the password as a sqlcmd scripting variable at runtime: sqlcmd -v collector_pwd="..."
CREATE LOGIN eoa_user WITH PASSWORD = N'$(collector_pwd)';
CREATE USER eoa_user FOR LOGIN eoa_user;
GRANT VIEW SERVER STATE TO eoa_user;
GRANT VIEW ANY DATABASE TO eoa_user;
```

#### PostgreSQL Collection Account

```sql
CREATE USER eoa_user;
-- Set the password interactively in psql (input is hidden, nothing is written to scripts or history):
\password eoa_user
GRANT pg_read_all_stats TO eoa_user;
GRANT pg_read_all_settings TO eoa_user;
GRANT CONNECT ON DATABASE target_db TO eoa_user;
\c target_db
GRANT USAGE ON SCHEMA public TO eoa_user;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO eoa_user;
```

### 1.4 Deploy the Collector

> Before extracting, verify package integrity against the SHA-256 checksum shown on the APDS download page, and only proceed after the user confirms.

```bash
# Verify integrity first (compare with the checksum from the APDS console download page)
sha256sum rainmeter-linux64.tar.gz

mkdir -p /opt/rainmeter && cd /opt/rainmeter
tar -xzvf "rainmeter-linux64.tar.gz"
```

### 1.5 Run Collection

> Present the command to the user and run it only after explicit user confirmation. The collection account is read-only.

| Oracle Version | Collection Script | Command |
|----------------|-------------------|---------|
| 10g | `collect_10g.sh` | `./collect_10g.sh -h <host> -u <user> -p <pass> -d <service_name>` |
| 11g R1 (<11.2) | `collect_11gR1.sh` | `./collect_11gR1.sh -h <host> -u <user> -p <pass> -d <service_name>` |
| 11g R2 (>=11.2) | `collect_11gR2.sh` | `./collect_11gR2.sh -h <host> -u <user> -p <pass> -d <service_name>` |
| 12c/18c/19c | `collect_12c.sh` | `./collect_12c.sh -h <host> -u <user> -p <pass> -d <service_name>` |

### 1.6 Export Collection Results

Collection results are located at `rainmeter/out/data.zip`.

---

## Step 2: Source DB Profiling

1. Select "**Source DB Profiling**" on the Database Evaluation page
2. Upload `data.zip` (user-initiated, official APDS console only; the package contains metadata and statistics, no business data -- review it before uploading)
3. Wait for analysis to complete

Profiling dimensions: database version, character set, instance type, data file count, total object count, user/system object distribution, object type counts and proportions, total storage size, schema count.

---

## Step 3: Target DB Selection Recommendation

After profiling completes, select "**Target DB Selection Recommendation**", which shows:
- Compatibility ranking of various target databases against Oracle
- Specification recommendations (CPU/memory/storage/IOPS)
- Architecture recommendations

---

## Step 4: Target DB Compatibility Assessment

1. Select "**New Target DB Evaluation**"
2. Choose the target database type and version
3. 11 evaluation reports are automatically generated
4. View report details and download reports

---

## Tools and Services Provided by CMH

| Tool/Service | Description |
|--------------|-------------|
| **Rainmeter Collector** | Source DB data collection tool (Linux/Windows) |
| **CMH Intelligent Conversion Engine** | Automatic DDL/DML compatibility analysis |
| **CMH Studio** | Migration plan execution tool |
| **SQL Real-time Translation** | Translate Oracle SQL to target DB SQL |
| **PL/SQL to Java (P2J)** | Automatic PL/SQL to Java code conversion |
| **Refactoring Lab** | Simulated refactoring environment and testing |
| **Expert Support** | Migration escort, O&M, and optimization expert services |

---

## Quick Start Guide

```
1. Log in to the APDS console (Cloud Migration Hub -> Application Discovery & Assessment -> Database Evaluation)
2. Download the Rainmeter collector (Linux/Windows)
3. Create collection account eoa_user and grant privileges (connect + select_catalog_role)
4. Upload the collector to the source DB environment and extract
5. Run the collection script for the corresponding version (collect_*.sh)
6. Obtain the data.zip collection result (rainmeter/out/data.zip)
7. Upload data.zip to APDS Source DB Profiling
8. View source DB profiling analysis results
9. View target DB selection recommendations
10. Create new target DB evaluation -> generate 11 reports
11. View report details (summary/migration assessment/compatibility/refactoring analysis/specification/risk SQL/migration risk/P2J)
12. Download reports (concise/detailed version)
```
