---
name: alibabacloud-dts-task-query
description: >
  Query DTS (Data Transmission Service) task status and details across all Alibaba Cloud regions.
  **v12.1: Enhanced reliability** - Timeout increased to 10s, exponential backoff (0.2s, 0.4s) for better timeout handling.
  Parallel execution remains **6-8x faster** than v10 (39s → 6s with --workers 16).
  **API retry logic ensures consistent results (no count variations)**. Supports filtering by instance ID or job name. Automatically polls all 27 regions and 3 job types.
  Strictly filters for PrePaid/PostPaid tasks and outputs a full Chinese report with Region information.
  Tasks are grouped by type (Migration/Sync/Subscribe) and sorted by CreateTime within each group.
  **Use this skill when: checking DTS task status, finding migration/sync tasks, verifying task counts, or filtering tasks by instance ID or job name.**
metadata:

---

# ⚠️ CRITICAL OUTPUT COMPLETENESS REQUIREMENT
**When using this skill, you MUST output the COMPLETE script result without ANY truncation, omission, or summarization. The script outputs EVERY task row in full - your model response MUST do the same. NEVER use "..." placeholders or summarize task counts. Display ALL rows exactly as shown.**

# DTS Task Status Query

Query DTS task status using Alibaba Cloud CLI. Outputs results in Chinese.

## Prerequisites
**CRITICAL: AI-Mode and Plugin Setup Required**

Before using this skill, you MUST configure AI-Mode and update plugins:

```bash
# Enable AI-Mode for plugin-based API calls
aliyun configure ai-mode enable

# Set user agent for proper plugin compatibility
aliyun configure ai-mode set-user-agent --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-dts-task-query"

# Update all plugins to latest version
aliyun plugin update --all

# Verify DTS plugin is installed
aliyun plugin list

# To disable AI-Mode later (if needed)
aliyun configure ai-mode disable
```

**Note**: This skill uses plugin mode commands (`aliyun dts describe-dts-jobs`). AI-Mode must be enabled for these commands to work correctly.

## Required RAM Permissions

See detailed RAM policy requirements in [references/ram-policies.md](references/ram-policies.md).

## Supported Regions
Automatically queries all 27 public cloud regions if no region is specified.

## Usage
```bash
python scripts/query_dts_tasks.py [--region <id>] [--instance-id <id>] [--job-name <name>] [--workers <N>]
```

**⚠️ MANDATORY - Model Response Rules:**
- **ALWAYS output COMPLETE data**: Display every single task row without any omission
- **NEVER truncate**: No "..." placeholders, no "showing first N tasks", no summaries
- **ALWAYS list ALL tasks**: Every task in migration/sync/subscribe groups must be shown line-by-line
- **Script outputs 100%**: The script GUARANTEES complete output - your response MUST match 100%
- **Remember**: When the script has 23 tasks, you output ALL 23 rows. NO EXCEPTIONS.

**Performance Tuning:**
- `--workers`: Number of concurrent API calls (default: 8). Recommended values:
  - **8**: Default, stable performance (~10 seconds full scan)
  - **12-16**: Optimal for high-bandwidth networks (~6-8 seconds full scan)
  - **>16**: May hit API rate limits or local resource constraints

**Reliability Features (v12):**
- **API retry logic**: Retries failed API calls up to 3 times with exponential backoff to ensure consistent results
  - **Problem solved**: Eliminates count variations caused by transient API failures and timeouts
  - **Impact**: Script now always returns the same task count (e.g., consistently 34 tasks instead of 32-34)
  - **v12.1**: Increased timeout to 10s and added exponential backoff (0.2s, 0.4s) for better reliability
- **Thread-safe collection**: Uses Lock to prevent race conditions during parallel data collection
- **Strict response validation**: Only accepts responses with valid "DtsJobList" field
- **Detailed error logging**: Distinguishes between timeout errors and other exceptions for easier debugging
- **Verified**: Tested with 50+ consecutive runs - all returned identical results

## Execution Rules (Mandatory)
1. **Full Polling**: Must iterate through all 27 regions and 3 job types (`MIGRATION`, `SYNC`, `SUBSCRIBE`) unless a specific region is provided.
2. **Region Injection**: The script must inject the `_QueryRegion` field into each task object during the query phase.
3. **Endpoint for Overseas Regions**: For overseas regions, the script must add the `--endpoint` parameter to query tasks successfully.
4. **PayType Filtering**: After reading the temporary file, strictly filter tasks to include ONLY those where `PayType` is `PrePaid` or `PostPaid`.
5. **Chinese Output**: All output (summary and table headers) must be in Chinese. JobType must be mapped (e.g., migration -> 迁移).
6. **Grouped Output**: Tasks are grouped by type (迁移/同步/订阅), with each group sorted by CreateTime (newest first).
7. **Parallel Execution**: The script MUST use ThreadPoolExecutor for parallel queries (v11+). Default 8 workers, configurable via `--workers`.
8. **API Retry**: The script retries failed API calls up to 3 times to ensure reliability (v12+).
9. **Thread Safety**: The script uses Lock for thread-safe data collection to prevent race conditions (v12+).
10. **Parameter Strictness**: MUST use the exact region ID and filter keywords provided in user input. DO NOT substitute regions (e.g. cn-shanghai) even if user input seems ambiguous.
11. **Filter Enforcement**: If --job-name is provided, it MUST be passed to the script without omission.

## Output Format

### 1. 统计摘要
- **任务总量**: [Count]
- **地域分布**: [List of regions and counts]
- **状态分布**: [List of statuses and counts]
- **类型分布**: [List of job types and counts]

### 2. 任务明细
**⚠️ CRITICAL - Output Completeness:**
- **Script GUARANTEES complete output**: The script ALWAYS outputs ALL tasks without truncation
- **ALWAYS display ALL rows**: Every single task MUST be listed row-by-row, no exceptions
- **NEVER use placeholders**: No "..." or similar truncation symbols - show EVERY task with actual data
- **Complete example structure** (actual output contains ALL real data rows, NO truncation):

```
#### 迁移任务
共 [N] 个
| 地域 | 状态 | DTS任务名称 | 过期时间 | DTS任务ID | 创建时间 | DTS实例ID |
|------|------|-------------|----------|-----------|----------|-----------|
| [Region1] | [Status1] | [Name1] | [ExpireTime1] | [JobID1] | [CreateTime1] | [InstanceID1] |
| [Region2] | [Status2] | [Name2] | [ExpireTime2] | [JobID2] | [CreateTime2] | [InstanceID2] |
| [Region3] | [Status3] | [Name3] | [ExpireTime3] | [JobID3] | [CreateTime3] | [InstanceID3] |
```
**The script outputs ALL rows with actual data for EVERY task - NO truncation.**

#### 迁移任务
共 [N] 个
| 地域 | 状态 | DTS任务名称 | 过期时间 | DTS任务ID | 创建时间 | DTS实例ID |
|------|------|-------------|----------|-----------|----------|-----------|
| [Region] | [Status] | [Name] | [ExpireTime] | [JobID] | [CreateTime] | [InstanceID] |

#### 同步任务  
共 [N] 个
| 地域 | 状态 | DTS任务名称 | 过期时间 | DTS任务ID | 创建时间 | DTS实例ID |
|------|------|-------------|----------|-----------|----------|-----------|
| [Region] | [Status] | [Name] | [ExpireTime] | [JobID] | [CreateTime] | [InstanceID] |

#### 订阅任务
共 [N] 个
| 地域 | 状态 | DTS任务名称 | 过期时间 | DTS任务ID | 创建时间 | DTS实例ID |
|------|------|-------------|----------|-----------|----------|-----------|
| [Region] | [Status] | [Name] | [ExpireTime] | [JobID] | [CreateTime] | [InstanceID] |

**Field Definitions:**
- **地域**: The region where the task resides (in Chinese, e.g., 华东1（杭州）).
- **状态**: Task status (e.g., Synchronizing, Completed).
- **任务类型**: Mapped to Chinese (迁移, 同步, 订阅).
- **过期时间**: Only present for PrePaid instances.
- **DTS任务ID**: Unique task identifier (DtsJobId).
- **DTS实例ID**: DTS instance identifier (DtsInstanceID/DtsInstanceId).
- **创建时间**: Task creation timestamp (CreateTime).

## Workflow
1. Parse parameters.
2. **SECURITY & VALIDATION**: 
   - **Region Validation**: `--region` parameter MUST be validated against SUPPORTED_REGIONS whitelist. Invalid regions cause immediate exit with error.
   - **Workers Validation**: `--workers` parameter MUST be within range [1, 32]. Values outside this range cause immediate exit with error.
   - **API Validation**: Attempt a preliminary `describe-dts-jobs` call. If it returns `403` or `400`, immediately halt and report RAM permission issues.
   - **Service Enforcement**: Strictly forbid calling non-DTS services (e.g., SchedulerX, ECS, FC) for DTS task queries; restrict all calls to the DTS API endpoint only.
3. **PERFORMANCE**: Create ThreadPoolExecutor with `--workers` (default 8).
4. Query API for each region/type combo in parallel, injecting `_QueryRegion` and adding `--endpoint` for overseas regions.
5. **RELIABILITY (Fallback Logic)**: If `describe-dts-jobs` fails consecutively 3 times for a specific target, terminate the execution immediately without attempting other DTS interfaces or regions for that target.
6. **PERFORMANCE**: Skip pagination if page 1 returns empty (early exit optimization).
7. **PERFORMANCE**: Use PageSize=200 to minimize API calls (50% reduction vs v10).
8. **PERFORMANCE**: Increased timeout to 10s per API call for reliability (v12.1 - balanced speed/reliability).
9. **RELIABILITY**: Retry failed API calls up to 3 times with exponential backoff (0.2s, 0.4s) for better timeout handling (v12+).
10. **RELIABILITY**: Use Lock for thread-safe data collection (v12).
11. **RELIABILITY**: Validate API responses - only accept those with valid "DtsJobList" field (v12).
12. Save raw JSON to `/tmp/dts_raw_*.json`.
13. Read temp file, filter by `PayType` (PrePaid/PostPaid), then apply user filters.
14. Group tasks by type (Migration/Sync/Subscribe), sort each group by CreateTime (newest first).
15. Format and print Chinese report with complete task list (NO TRUNCATION).
16. Delete temp file.

**Output Completeness Guarantee:**
- ✅ **Script outputs 100% of tasks**: The script ALWAYS outputs ALL tasks without truncation
- ✅ **Format-ready**: The output uses markdown tables ready for direct model response
- ✅ **Zero omissions**: No tasks are hidden, summarized, or omitted under any circumstances
- ✅ **MUST display ALL rows**: When using this skill, you MUST output every single task row exactly
- ✅ **NO truncation allowed**: Never truncate, summarize, or use "..." placeholders
- ✅ **Preserve completeness**: The script output is COMPLETE - your response MUST be COMPLETE
- ✅ **Every task visible**: The script outputs EVERY task - your model response MUST show EVERY task
- ✅ **No exceptions**: Script output = Complete data. Your output MUST = Complete data. ALWAYS.

---

**REMEMBER**: The script output is COMPLETE and GUARANTEED. Your model response MUST preserve 100% of it without ANY truncation, summarization, or omission. Display EVERY task row exactly as shown.
