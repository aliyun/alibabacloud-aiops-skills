# Cluster Information Template

Use this template to document source cluster database and table information.

## Template Constraints

> **IMPORTANT:** When filling this template:
> - **Output language** - If not explicitly specified, use the same language as the main conversation (e.g., if user speaks Chinese, output in Chinese; if English, output in English)
> - Copy SQL query results directly into the tables below
> - Keep all table formatting intact
> - Fill in all applicable fields
> - **Local references → Read, analyze, write as needed** - When referencing local files (e.g., `references/*.md`), read and analyze the content, then write relevant SQL/content into the output file as needed
> - **Public URLs → Link directly** - Public web URLs (e.g., `help.aliyun.com`) can be directly linked

---

## Cluster Overview

| Item | Value |
|------|-------|
| Cluster Type | [Self-built / Alibaba Cloud Community / Alibaba Cloud Enterprise] |
| Cluster Version | [e.g., 24.3.1] |
| Node Count | [N nodes] |
| Instance Spec | [e.g., 8C32G / 16CCU] |
| Total Data Size | [X.XX TB / GB] |
| Collection Date | [YYYY-MM-DD] |

---

## Database Information

Execute SQL from [references/sql.md](../references/sql.md) Section 1.1 and paste ALL results:

| database_name | engine |
|---------------|--------|
| [db1] | [Atomic/Ordinary/...] |
| [db2] | [...] |

---

## Table Information

Execute SQL from [references/sql.md](../references/sql.md) Section 1.2 and paste ALL results:

| table_name | engine | engine_full | part_count | data_bytes | write_speed_bytes_per_sec |
|------------|--------|-------------|------------|------------|---------------------------|
| [`db`.`table1`] | [MergeTree] | [...] | [N] | [bytes] | [bytes/s] |
| [`db`.`table2`] | [...] | [...] | [...] | [...] | [...] |

---

## Formatted Table Summary

| Table | Engine | Size | Partitions | Write Speed | TTL | Status |
|-------|--------|------|------------|-------------|-----|--------|
| [db.table1] | [MergeTree] | [X GB] | [N] | [X MB/s] | [N days / None] | ✅/⚠️/❌ |
| [db.table2] | [...] | [...] | [...] | [...] | [...] | [...] |

**Status Legend:**
- ✅ Supported - No issues
- ⚠️ Warning - Requires attention (e.g., TTL ≤3 days, high write speed)
- ❌ Not Supported - Cannot migrate with cksync (e.g., MaterializedMySQL, Kafka engine)

---

## Compatibility Checklist

| Check Item | Result | Notes |
|------------|--------|-------|
| MaterializedMySQL engines | ✅ None / ❌ Found: [list] | Use DTS instead |
| TTL ≥ 3 days | ✅ All pass / ⚠️ Tables: [list] | Data count may differ |
| Partitions < 10,000 | ✅ All pass / ❌ Tables: [list] | Merge partitions first |
| Kafka/RabbitMQ tables | ✅ None / ⚠️ Found: [list] | Manual migration required |
| Total write speed | [X MB/s] | Check if < migration speed |
