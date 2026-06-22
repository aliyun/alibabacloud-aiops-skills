---
name: alibabacloud-network-health-inspection
description: >
  Comprehensive health inspection tool for Alibaba Cloud network products (EIP, CBWP,
  NAT Gateway, CEN, Transit Router, Physical Connection, VBR, Global Accelerator, CLB,
  ALB, NLB). Analyzes bandwidth utilization, connection count, QPS, and packet loss
  using Cloud Monitor data; generates a Markdown inspection report with monitoring
  charts, risk assessment, and scaling recommendations. All API calls are read-only.
  Use when users want to inspect network product usage, check bandwidth headroom,
  assess capacity before a business launch, or identify over-limit risk.
  Triggered by: inspect network products, network health check, bandwidth inspection,
  EIP/NAT/CLB/ALB/NLB/CEN/VBR/GA inspection, network utilization analysis,
  pre-launch network inspection, capacity assessment, bandwidth over-limit risk.
license: Apache-2.0
compatibility: >
  Requires aliyun CLI with configured credentials (aliyun configure),
  Python 3.7+, and matplotlib library (pip install matplotlib).
metadata:
  domain: aiops
  owner: vpc-team
  contact: vpc-agent@alibaba-inc.com
allowed-tools: Bash Read
---

## Prerequisites

- **aliyun CLI**: Must be installed and configured with access credentials (`aliyun configure`). If not installed, use `brew install aliyun-cli` (macOS) or download from [GitHub Releases](https://github.com/aliyun/aliyun-cli/releases)
- **Python 3.7+**: Required for running inspection scripts and generating monitoring charts
- **matplotlib**: Python charting library for generating monitoring charts. If not installed, run `pip3 install matplotlib`

## Required RAM Permissions

All API calls in this Skill are **read-only queries** and do not involve any resource creation, modification, or deletion. The following permissions are required:

| Cloud Product | API Permission | Purpose |
|--------------|----------------|---------|
| Cloud Monitor (CMS) | `cms:DescribeMetricList` | Query monitoring metric data for all network products (core permission) |
| VPC | `vpc:DescribeEipAddresses` | Query EIP list |
| VPC | `vpc:DescribeCommonBandwidthPackages` | Query Common Bandwidth Package list |
| VPC | `vpc:DescribeNatGateways` | Query NAT Gateway list |
| VPC | `vpc:DescribePhysicalConnections` | Query Physical Connection list |
| VPC | `vpc:DescribeVirtualBorderRouters` | Query VBR list |
| Cloud Enterprise Network (CEN) | `cbn:DescribeCens` | Query CEN list |
| Cloud Enterprise Network (CEN) | `cbn:DescribeCenBandwidthPackages` | Query CEN bandwidth packages |
| Cloud Enterprise Network (CEN) | `cbn:ListTransitRouters` | Query Transit Router list |
| Cloud Enterprise Network (CEN) | `cbn:ListTransitRouterVpcAttachments` | Query TR VPC attachments |
| Cloud Enterprise Network (CEN) | `cbn:ListTransitRouterVbrAttachments` | Query TR VBR attachments |
| Cloud Enterprise Network (CEN) | `cbn:ListTransitRouterRouteTables` | Query TR route tables |
| Global Accelerator (GA) | `ga:ListAccelerators` | Query Global Accelerator instance list |
| CLB | `slb:DescribeLoadBalancers` | Query CLB list |
| ALB | `alb:ListLoadBalancers` | Query ALB list |
| NLB | `nlb:ListLoadBalancers` | Query NLB list |

For the recommended RAM policy JSON and detailed security notes, see `references/ram-policies.md`.

If a product lacks sufficient API permissions, the Skill will skip that product and mark it as an error in the report, without affecting the inspection of other products.

## Operational Safety Statement (PreToolUse Hook)

This Skill **does not configure a PreToolUse Hook** for the following reasons:

1. **Pure read-only operations**: All API calls are `Describe*` / `List*` read-only queries, not involving any resource creation, modification, or deletion
2. **Restricted tool scope**: `allowed-tools` only declares `Bash Read`; the Skill cannot invoke Write, Edit, or other file-writing tools
3. **Restricted Bash usage**: The Bash tool is only used to execute `aliyun` CLI read-only query commands and `python3` inspection scripts, never for write operations
4. **No high-risk operations**: There are no deletion, batch write, or permission change operations that require human confirmation (HITL)

Therefore, this Skill has no operations that need interception or secondary confirmation, and no PreToolUse Hook is required. If future versions add write-operation capabilities, corresponding PreToolUse Hook interception mechanisms must be added accordingly.

## Input Parameters

The user needs to provide the following information (extracted from the user's natural language):

- **Region** (optional): Default `cn-hangzhou`; supports multiple regions separated by commas, e.g., `cn-hangzhou,cn-shanghai`
- **Time range** (required, no default): The user must explicitly specify the inspection time range. Converted to days:
  - "last week" / "past 7 days" → `--days 7`
  - "last 24 hours" / "last day" → `--days 1`
  - "last 3 days" / "past 3 days" → `--days 3`
- **Data aggregation period** (required, no default): The user must explicitly specify the monitoring data aggregation granularity (unit: seconds). Data queries and chart generation use this granularity uniformly. Common values:
  - `60` — 1-minute granularity, finest data resolution, suitable for short-term troubleshooting
  - `300` — 5-minute granularity, balance between resolution and data volume
  - `900` — 15-minute granularity, less data, suitable for long-period overview
- **Inspection product scope** (optional): Default is to inspect all 11 network product categories. The user can specify only certain products to inspect; product names are identified from the user's natural language, referring to the mapping table below to determine the list of products to inspect.

### Product Name Recognition Mapping

Extract product keywords from user input and map them to the corresponding inspection products. **The same product may have multiple expressions**; all must be recognized:

| Product ID | Possible User Expressions |
|-----------|--------------------------|
| EIP | EIP, Elastic IP, Elastic Public IP, Public IP |
| CBWP | CBWP, Common Bandwidth Package, Shared Bandwidth, Bandwidth Package |
| NAT | NAT, NAT Gateway, NAT Gateway |
| CEN | CEN, Cloud Enterprise Network |
| TR | TR, Transit Router |
| PhysConn | Physical Connection, Express Connect, Dedicated Line |
| VBR | VBR, Virtual Border Router, Border Router |
| GA | GA, Global Accelerator |
| CLB | CLB, Classic Load Balancer, SLB (Note: when users say "SLB" they usually mean CLB) |
| ALB | ALB, Application Load Balancer |
| NLB | NLB, Network Load Balancer |

**Special case handling:**
- User says "load balancer" without specifying a type → inspect CLB + ALB + NLB (all three types)
- User says "dedicated line" without distinguishing → inspect Physical Connection + VBR (VBR is the traffic monitoring entry point for dedicated lines)
- User says "SLB" → map to CLB (Classic Load Balancer)

### Product Scope Processing Logic

1. **User does not specify products**: Inspect all 11 network product categories (default behavior)
2. **User specifies products**: Only inspect the products mentioned by the user; skip products not mentioned
3. **User mentions unsupported products**: Explicitly inform the user that the product is not currently supported for inspection by this Skill. For example:
   > This Skill does not currently support inspecting "VPN Gateway". The 11 supported network product categories are: EIP, Common Bandwidth Package, NAT Gateway, Cloud Enterprise Network, Transit Router, Physical Connection, VBR, Global Accelerator, CLB, ALB, NLB.

   After informing, continue inspecting other supported products mentioned by the user (if any).

### Required Parameter Confirmation Logic

Before starting the inspection, you must confirm that the user has provided both the **time range** and **data aggregation period** parameters. If the user has not specified them, you must ask:

1. **When time range is not specified**, ask:
   > How long of data would you like to inspect? For example: last 1 day, last 3 days, last 7 days, etc.

2. **When data aggregation period is not specified**, ask and clarify the meaning:
   > What aggregation period would you like for the monitoring data? The aggregation period determines the time interval between monitoring data points:
   > - **60 seconds (1 minute)**: One data point per minute, finest resolution, suitable for short time range troubleshooting
   > - **300 seconds (5 minutes)**: One data point every 5 minutes, good balance between resolution and data volume
   > - **900 seconds (15 minutes)**: One data point every 15 minutes, less data volume, suitable for long-period overall trend overview
   >
   > Note: The smaller the aggregation period, the more data points need to be fetched, and the inspection time will increase significantly. For example, inspecting 7 days of data with 60-second granularity requires approximately 10,080 data points per metric, while 900-second granularity only requires about 672 data points per metric.

After both parameters are confirmed, proceed with the inspection workflow.

## Supported 11 Network Product Categories

| # | Product | Script | Cloud Monitor Namespace | Key Metrics |
|---|---------|--------|------------------------|-------------|
| 1 | Elastic IP (EIP) | `inspect_eip.py` | `acs_vpc_eip` | Outbound/inbound bandwidth, rate-limit packet loss |
| 2 | Common Bandwidth Package (CBWP) | `inspect_cbwp.py` | `acs_bandwidth_package` | Outbound/inbound bandwidth, utilization, rate-limit packet loss |
| 3 | NAT Gateway | `inspect_nat.py` | `acs_nat_gateway` | Outbound/inbound bandwidth, SNAT connection count, connection packet loss |
| 4 | Cloud Enterprise Network (CEN) | `inspect_cen.py` | `acs_cen` | Cross-region outbound/inbound bandwidth, bandwidth package capacity |
| 5 | Transit Router (TR) | `inspect_tr.py` | - | TR connection status, VPC/VBR attachment count |
| 6 | Physical Connection | `inspect_physconn.py` | - | Connection status (for traffic, see VBR) |
| 7 | VBR | `inspect_vbr.py` | `acs_physical_connection` | Outbound/inbound bandwidth, health check latency/packet loss |
| 8 | Global Accelerator (GA) | `inspect_ga.py` | `acs_global_acceleration` | Outbound/inbound bandwidth, packet rate |
| 9 | Classic Load Balancer (CLB) | `inspect_clb.py` | `acs_slb_dashboard` | Traffic, connection count, QPS, packet loss |
| 10 | Application Load Balancer (ALB) | `inspect_alb.py` | `acs_alb` | QPS, HTTP status codes, connection count |
| 11 | Network Load Balancer (NLB) | `inspect_nlb.py` | `acs_nlb` | Bandwidth, active connections, new connections |

## Important Technical Notes

### Cloud Monitor (CMS) Query Key Points

1. **CMS is a global service**: Always use `cn-hangzhou` as the CMS endpoint region; monitoring data ownership is determined by the instanceId in Dimensions, independent of the endpoint region
2. **VBR's CMS namespace is `acs_physical_connection`**, not `acs_express_connect`
3. **CBWP metric names**: `bwp_tx_rate`/`bwp_rx_rate`, not `net_tx.rate`/`net_rx.rate`
4. **NAT Gateway packet loss metric**: `SessionLimitDropRate`, not `SessionLimitDropConnection`
5. **VBR health check latency**: `VbrHealthyCheckLatency` unit is microseconds (us), needs to be divided by 1000 to convert to milliseconds (ms)
6. **VBR packet loss rate**: `VbrHealthyCheckLossRate` return value is already a percentage, no need to multiply by 100
7. **ALB/NLB CMS dimension key**: Use `loadBalancerId`, not `instanceId`
8. **Physical Connection has no Cloud Monitor metrics**: Physical connection traffic monitoring must be viewed through the associated VBR

### API Call Declaration

**All API calls in this Skill are read-only queries and do not involve any resource creation, modification, or deletion.**

List of read-only APIs used:
- `cms:DescribeMetricList` - Query Cloud Monitor data
- `vpc:DescribeEipAddresses` - Query EIP list
- `vpc:DescribeCommonBandwidthPackages` - Query Common Bandwidth Package list
- `vpc:DescribeNatGateways` - Query NAT Gateway list
- `vpc:DescribePhysicalConnections` - Query Physical Connection list
- `vpc:DescribeVirtualBorderRouters` - Query VBR list
- `cbn:DescribeCens` - Query CEN list
- `cbn:DescribeCenBandwidthPackages` - Query CEN bandwidth packages
- `cbn:ListTransitRouters` - Query Transit Router list
- `cbn:ListTransitRouterVpcAttachments` - Query TR VPC attachments
- `cbn:ListTransitRouterVbrAttachments` - Query TR VBR attachments
- `cbn:ListTransitRouterRouteTables` - Query TR route tables
- `ga:ListAccelerators` - Query Global Accelerator instance list
- `slb:DescribeLoadBalancers` - Query CLB list
- `alb:ListLoadBalancers` - Query ALB list
- `nlb:ListLoadBalancers` - Query NLB list

## aliyun CLI AI-Mode Configuration

All aliyun CLI calls in this Skill are made through Python inspection scripts. Before executing any script, configure AI-Mode globally so every CLI invocation carries the correct User-Agent header.

```bash
# Enable AI-Mode (run once before any aliyun CLI usage)
aliyun configure ai-mode enable

# Set User-Agent to identify this Skill
aliyun configure ai-mode set-user-agent --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-network-health-inspection"

# Update plugins to ensure latest versions
aliyun plugin update 2>/dev/null || true
```

```bash
# Disable AI-Mode after all CLI calls are complete
aliyun configure ai-mode disable
```

## Execution Workflow

### Step 1: Environment and Dependency Check

```bash
# Check aliyun CLI version
aliyun version 2>&1 | head -1

# Enable AI-Mode and set User-Agent (must run at the start of each Skill execution)
aliyun configure ai-mode enable
aliyun configure ai-mode set-user-agent --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-network-health-inspection"

# Update aliyun CLI plugins (ensure latest plugin versions)
aliyun plugin update 2>/dev/null || true

# Check Python and matplotlib
python3 -c "import matplotlib; print('matplotlib', matplotlib.__version__)" 2>&1

# If matplotlib is not installed, install it automatically
pip3 install matplotlib
```

> **AI-Mode explanation**: Enabling AI-Mode causes aliyun CLI to include a User-Agent header in requests, allowing the Alibaba Cloud platform to identify read-only queries initiated by AI Agents. After the Skill execution completes, you must run `aliyun configure ai-mode disable` to disable AI-Mode and restore the default state.

### Step 2: Create Inspection Working Directory

```bash
INSPECT_DIR=$(mktemp -d /tmp/network_inspect_XXXXXX)
CHARTS_DIR="$INSPECT_DIR/charts"
mkdir -p "$CHARTS_DIR"
echo "Inspection data directory: $INSPECT_DIR"
```

### Step 3: Run Product Inspection Scripts One by One

**Only run the inspection scripts corresponding to the products specified by the user.** If the user has not specified a product scope, run all 11 scripts. Run each script sequentially and save the results as JSON files:

```bash
SCRIPTS_DIR="<skill_path>/scripts"
REGIONS="cn-hangzhou"  # Based on user-specified region
DAYS=7                 # Based on user-specified time range
PERIOD=300             # Based on user-specified aggregation period (seconds)

# The following scripts are executed based on the user's product selection; unselected products are skipped

# 1. EIP inspection (Product ID: EIP)
python3 "$SCRIPTS_DIR/inspect_eip.py" --regions "$REGIONS" --days $DAYS --period $PERIOD > "$INSPECT_DIR/eip.json"

# 2. CBWP inspection (Product ID: CBWP)
python3 "$SCRIPTS_DIR/inspect_cbwp.py" --regions "$REGIONS" --days $DAYS --period $PERIOD > "$INSPECT_DIR/cbwp.json"

# 3. NAT Gateway inspection (Product ID: NAT)
python3 "$SCRIPTS_DIR/inspect_nat.py" --regions "$REGIONS" --days $DAYS --period $PERIOD > "$INSPECT_DIR/nat.json"

# 4. CEN inspection (Product ID: CEN, global resource, no Region needed)
python3 "$SCRIPTS_DIR/inspect_cen.py" --days $DAYS --period $PERIOD > "$INSPECT_DIR/cen.json"

# 5. Transit Router inspection (Product ID: TR, no Cloud Monitor metrics, no --period needed)
python3 "$SCRIPTS_DIR/inspect_tr.py" --regions "$REGIONS" --days $DAYS > "$INSPECT_DIR/tr.json"

# 6. Physical Connection inspection (Product ID: PhysConn, no Cloud Monitor metrics, no --period needed)
python3 "$SCRIPTS_DIR/inspect_physconn.py" --regions "$REGIONS" --days $DAYS > "$INSPECT_DIR/physconn.json"

# 7. VBR inspection (Product ID: VBR)
python3 "$SCRIPTS_DIR/inspect_vbr.py" --regions "$REGIONS" --days $DAYS --period $PERIOD > "$INSPECT_DIR/vbr.json"

# 8. Global Accelerator inspection (Product ID: GA, global resource)
python3 "$SCRIPTS_DIR/inspect_ga.py" --days $DAYS --period $PERIOD > "$INSPECT_DIR/ga.json"

# 9. CLB inspection (Product ID: CLB)
python3 "$SCRIPTS_DIR/inspect_clb.py" --regions "$REGIONS" --days $DAYS --period $PERIOD > "$INSPECT_DIR/clb.json"

# 10. ALB inspection (Product ID: ALB)
python3 "$SCRIPTS_DIR/inspect_alb.py" --regions "$REGIONS" --days $DAYS --period $PERIOD > "$INSPECT_DIR/alb.json"

# 11. NLB inspection (Product ID: NLB)
python3 "$SCRIPTS_DIR/inspect_nlb.py" --regions "$REGIONS" --days $DAYS --period $PERIOD > "$INSPECT_DIR/nlb.json"
```

> **On-demand execution rule**: Only run the scripts for products selected by the user. For example, if the user only requests inspection of "EIP and NAT Gateway", only execute scripts 1 and 3; skip the other 9 scripts. Products that are not executed will not generate JSON files, and subsequent steps 4 (chart generation) and 5 (report generation) will automatically ignore non-existent product data.

### Step 4: Generate Monitoring Charts

**Note: Generate charts before generating the report; the report will automatically embed chart references.**

```bash
# Generate charts for instances with monitoring data
python3 "$SCRIPTS_DIR/inspect_charts.py" \
  --dir "$INSPECT_DIR" \
  --days $DAYS \
  --period $PERIOD \
  --output-dir "$CHARTS_DIR"
```

### Step 5: Generate Inspection Report (with Chart References)

```bash
# Generate Markdown inspection report; --charts-dir parameter embeds chart references in the report
python3 "$SCRIPTS_DIR/inspect_report.py" \
  --dir "$INSPECT_DIR" \
  --days $DAYS \
  --charts-dir "$CHARTS_DIR" \
  --output "$INSPECT_DIR/report.md"
```

> If output to DingTalk Docs is needed, generate the local version report first for display; the DingTalk version report is generated separately in Step 7 (using the `--image-url-map` parameter to replace local paths with cloud URLs).

### Step 6: Present Results

1. **Read the complete report file**: Use the Read tool to read the full contents of `$INSPECT_DIR/report.md`
2. **Present the report in full**: Present **all contents** of the Markdown report to the user, including but not limited to:
   - Executive summary and health score
   - Inspection overview table
   - Region-level statistics
   - Instances requiring attention (with warning/critical reasons)
   - Traffic insights
   - **Detailed inspection results for each product** (all 11 products displayed)
   - **In-depth analysis for each product** (bandwidth analysis, traffic patterns, packet loss analysis, cost optimization, etc.)
   - **Monitoring chart references and analysis for each product** (charts are embedded in the report Markdown; no need to display image files separately)
   - Scaling recommendations and optimization directions
   - Capacity planning suggestions
   - Appendix (risk level descriptions, specification limit references, methodology notes)
3. **If no instances exist**: The report will clearly state "No XXX instances found within the inspection scope for this account"

> **Important: Do not abbreviate, truncate, or summarize the report content in any way. Every word, every table, and every in-depth analysis section of the report must be displayed in full.**
> **Note: Monitoring charts only need to be displayed in the final report (local report or DingTalk document); do not read individual PNG files and display them to the user in the conversation.**

```bash
# Disable AI-Mode after inspection completes, restore default state
aliyun configure ai-mode disable
```

### Step 7: Output to DingTalk Docs (Optional)

If the user requests outputting the report to DingTalk Docs, use the DingTalk Docs MCP service.

> **Core principle: The report must be written to DingTalk Docs in its entirety; no abbreviation, omission, or truncation of any content is allowed. In-depth analysis, chart references, all tables, and all text must be included without exception. If the content is long, it must be written in multiple segments; reducing content to shorten length is strictly prohibited.**

**Prerequisite: Check if DingTalk Docs MCP is installed**

Check whether the current environment has DingTalk Docs MCP tools available (tool names containing `dingtalk` with document operation capabilities such as `create_document`, `update_document`, `get_doc_attachment_upload_info`, etc.).
If the DingTalk Docs MCP is not installed, guide the user through the following installation steps:

1. Open the DingTalk MCP service installation page: https://aihub.dingtalk.com/#/detail?instanceId=474175&detailType=instanceMcpDetail&mcpId=9629
2. Follow the page instructions to complete the MCP service installation and authorization configuration
3. Ensure the MCP environment variable `DINGTALK_MCP_DOCS_URL` is correctly configured
4. After installation is complete, re-run this Skill

**Complete workflow for publishing the report using DingTalk Docs MCP:**

**7.1 Create a DingTalk Document**

Use the DingTalk Docs MCP `create_document` to create a document in the target folder, with the document name "Alibaba Cloud Network Product Inspection Report YYYY-MM-DD". Record the returned document `dentryUuid` (used for all subsequent operations).

**7.2 Batch parallel upload of charts to DingTalk Docs (obtain image URLs)**

**Efficiently and in parallel** upload all PNG chart files under `$CHARTS_DIR` to the DingTalk document:

**Phase 1: Batch obtain upload credentials**

Call `get_doc_attachment_upload_info` for all PNG files at once, with parameters:
- `dentryUuid`: The document ID returned in Step 7.1
- `fileName`: Image file name (e.g., `eip_eip-xxx_bandwidth.png`)
- `fileSize`: File size in bytes
- `mediaType`: `image/png`

> **Performance critical**: Issue **all** `get_doc_attachment_upload_info` MCP calls **in a single message** (do not call them one by one waiting for each return before calling the next). DingTalk MCP supports concurrent calls, so all credentials can be returned in parallel.

**Phase 2: Parallel curl upload**

Put all `curl -X PUT` commands into **a single Bash call** for parallel execution:

```bash
# All curls execute in parallel, wait at the end for all to complete
curl -s -X PUT "<uploadUrl_1>" -H "Content-Type: image/png" --data-binary @"$CHARTS_DIR/file1.png" &
curl -s -X PUT "<uploadUrl_2>" -H "Content-Type: image/png" --data-binary @"$CHARTS_DIR/file2.png" &
curl -s -X PUT "<uploadUrl_3>" -H "Content-Type: image/png" --data-binary @"$CHARTS_DIR/file3.png" &
# ... all images ...
wait
echo "All uploads done"
```

> **Note**: If there are more than 20 images, split into 2-3 parallel batches (10-15 per batch), with parallelism within each batch and sequential execution between batches, to avoid too many connections.

**Phase 3: Build the mapping**

Collect all `resourceUrl` values returned by `get_doc_attachment_upload_info`, build an image_url_map (`{filename: resourceUrl}` mapping), and write it to `$INSPECT_DIR/image_url_map.json`.

**Example image_url_map.json:**
```json
{
  "eip_eip-xxx_bandwidth.png": "<resourceUrl>",
  "nat_ngw-xxx_snat.png": "<resourceUrl>"
}
```

**7.3 Generate DingTalk version report (using cloud image URLs)**

Regenerate the report using the `--image-url-map` parameter, replacing image references with DingTalk OSS resourceUrls:

```bash
python3 "$SCRIPTS_DIR/inspect_report.py" \
  --dir "$INSPECT_DIR" \
  --days $DAYS \
  --charts-dir "$CHARTS_DIR" \
  --image-url-map "$INSPECT_DIR/image_url_map.json" \
  --output "$INSPECT_DIR/report_dingtalk.md"
```

> All `![xxx](...)` image paths in the generated `report_dingtalk.md` have been replaced with DingTalk OSS resourceUrls, ensuring proper rendering in DingTalk Docs.

**7.4 Write the complete report to DingTalk Docs in segments**

Report content is typically very long (detailed analysis of 11 products + in-depth analysis + charts), so it **must be written in segments**.

**Optimal write strategy (tested and verified; follow this directly without adjustment):**

1. **Read all contents of `$INSPECT_DIR/report_dingtalk.md`**
2. **Split by `## ` second-level headings into multiple segments**: Use lines starting with `## ` as delimiters to split the report into multiple chunks. The first chunk includes the report title header (from `# Alibaba Cloud Network Product Comprehensive Inspection Report` to before the first `## `). **Special attention: The `## Product Inspection Details` section contains the complete content for 11 products, which is much larger than other sections, and must be further split by `### ` third-level headings into one independent chunk per product.**
3. **Each product is written as a complete chunk**: Each product's `### ` segment includes "detail table + in-depth analysis + monitoring chart references", which form an inseparable whole. `![](url)` image references are just Markdown text (approximately 100 characters each), not binary images, and will not cause timeouts. **Do not separate image references from the product segment and write them independently.**
4. **Large product splitting rule**: If a single product's chunk exceeds **10000** characters (e.g., EIP with 18 instances' monitoring charts), split at the `#### Monitoring Charts` boundary into two chunks:
   - chunk A: Product title + detail table + in-depth analysis
   - chunk B: `#### Monitoring Charts` and all chart references below it
   - If chunk B still exceeds 10000 characters, further split into batches of 8-10 instances
   - **chunk A and chunk B must be written consecutively**; no other product's content may be inserted between them
5. **Aggressively merge small segments (reducing API calls is the key to speed optimization)**: Adjacent small sections (e.g., products with no instances, or product segments with few words) **must be merged as much as possible**. As long as the merged result does not exceed **10000** characters, merge into one chunk. Typical scenario: multiple products without instances + 1-2 products with few instances can be merged into a single chunk for writing.
6. **Write order**:
   - 1st chunk → `update_document`, `mode: overwrite` (overwrite)
   - 2nd through Nth chunk → `update_document`, `mode: append` (append)
   - **Minimize the number of `update_document` calls**; target is **8-12 calls** (not 20+), as each call has network overhead
7. **Write segment by segment until the end of the report**: All sections including the appendix must be written in full

> **Note**: A single `update_document` call should not be too large, otherwise it may trigger a DingTalk HSFTimeOutException (3000ms timeout). A single chunk is recommended to be no more than **10000** characters. Tested: 10000 characters or less will not trigger a timeout.

**Write example (typical report, note total calls significantly reduced after merging):**

| Write Batch | Content | mode | Estimated Characters |
|------------|---------|------|---------------------|
| Batch 1 | Report title + Executive summary + Inspection overview + Instances requiring attention + Traffic insights | overwrite | ~5000-8000 |
| Batch 2 | Product 1 (EIP) details + In-depth analysis (split out charts if including them exceeds 10000 chars) | append | ~6000-9000 |
| Batch 3 | Product 1 (EIP) monitoring charts (only if previous step was split) | append | ~5000-8000 |
| Batch 4 | Product 2 (CBWP) + Product 3 (NAT) complete content (including chart references, merged write) | append | ~6000-9000 |
| Batch 5 | Product 4 (CEN) + Product 5 (TR) + Product 6 (Physical Connection) + Product 7 (VBR) (merged write) | append | ~5000-8000 |
| Batch 6 | Product 8 (GA) + Product 9 (CLB) complete content (merged write) | append | ~5000-8000 |
| Batch 7 | Product 10 (ALB) + Product 11 (NLB) complete content (merged write) | append | ~5000-8000 |
| Batch 8 | Scaling recommendations + Capacity planning + Appendix (risk descriptions + specification references + methodology notes + disclaimer) | append | ~4000-6000 |

> **Key rules (strictly follow):**
> - **Chart references for each product must be written immediately after that product's text content**; never concentrate all products' charts at the end of the report
> - Report format reference: Under `#### Monitoring Charts` for each product, charts are listed per instance (`**Instance ID (Name) — Metric:**` + `![](url)`); instances without monitoring data will have a text description
> - All content must be written in full; no section, table, in-depth analysis, or image reference may be omitted
> - Products without instances ("No XXX instances found") can be merged with adjacent empty products for writing
> - **Speed optimization core**: Reduce `update_document` calls from 20+ to 8-12 through aggressive merging

**7.5 Return the Document Link**

Return the DingTalk document link to the user, confirming that the report has been written in full (including all text content and charts).

## Risk Level Definitions

| Level | Mark | Criteria |
|-------|------|----------|
| Critical | [!!!] | Utilization >=90%, packet loss present, VBR latency >100ms or packet loss >5%, abnormal status |
| Warning | [!] | Utilization >=70%, VBR latency >50ms or packet loss >1%, ALB 5XX error rate >1% |
| OK | [OK] | Utilization <70%, all metrics normal |
| Error | [ERR] | API error occurred during inspection |

## Error Handling

- **aliyun CLI not installed**: Prompt `brew install aliyun-cli` or download from GitHub
- **Authentication failure**: Prompt to run `aliyun configure` to configure access credentials
- **No instances found**: Explicitly output "No XXX instances found within the inspection scope for this account"; never silently skip
- **Insufficient API permissions**: Skip that product and mark as error in the report; see `references/ram-policies.md`
- **No monitoring data**: Possible causes: instance newly created, no traffic, or metric name mismatch
- **matplotlib not installed**: Prompt `pip3 install matplotlib`
