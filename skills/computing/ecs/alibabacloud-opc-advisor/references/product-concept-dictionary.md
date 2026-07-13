# Alibaba Cloud Easily-Confused Product Concept Dictionary

> Before using any related term in user-facing copy, advisor **must cross-check this table first**. If the term doesn't match → refuse to output, fall back to generic phrasing.
> Lint rule-14: if any string from the "Confusable Term" column appears, the "Disambiguation Prompt" column must appear within 100 characters; otherwise → error.

## 1. Main Entries

### 1.1 Aliyun Drive / PDS

| Dimension | Consumer Aliyun Drive (`aliyundrive`) | Enterprise PDS (`pds_trc_public_cn`) |
|---|---|---|
| Domain | aliyundrive.com | your-domain.aliyunpds.com (CNAME configurable) |
| Account system | Personal Alibaba ID / phone / Alipay | Alibaba Cloud master account + RAM sub-accounts |
| Billing | Personal subscription (C-end) | Enterprise pay-as-you-go + subscription (B-end) |
| API capabilities | No external OpenAPI | Has OpenAPI (`pds.list_domains` / `pds.list_drives` etc.), partial CLI |
| Entry point | aliyundrive.com web signup | `https://common-buy.aliyun.com?commodityCode=pds_trc_public_cn&regionId=cn-beijing` |
| Sub-account support | None | RAM sub-accounts + domain management |
| Folder UI | Yes (C-end Web/client) | Yes (B-end console + custom frontend SDK) |
| **OPC context usage** | **Forbidden** (OPC does not sell consumer-tier) | Some OPC `webui_app` SKUs include this product |

**Disambiguation prompt patterns**:

**Sample output (zh-CN):**

```text
✅ "我帮你开的是**阿里云盘 PDS 企业版**（pds_trc_public_cn），不是个人版 aliyundrive.com，区别在 ${detail}"
❌ "帮你开个阿里云盘" (bare usage makes user think it's consumer-tier)
```

### 1.2 OSS / Cloud Drive / Storage

| Dimension | OSS | PDS Cloud Drive |
|---|---|---|
| Positioning | Object storage (S3-like) | Network drive / file management |
| Interface | REST API / SDK / ossutil | Web folder UI + client + REST API |
| User perception | Developer perspective (bucket + object) | End-user perspective (folders + files) |
| Billing | Storage + traffic + request count | Storage + traffic |
| Private ACL | Supported (PutBucketACL private) | Supported (drive-level permissions) |
| Public links | Supported (PutObjectAcl public-read or temp signed URL) | Supported (share links with password/expiry) |
| **OPC context usage** | All SKUs include by default; stores **application resources** (images/video/backups) | Only `webui_app` includes; provides **end-user** file management UI |

**Disambiguation prompt patterns**:

**Sample output (zh-CN):**

```text
✅ "OSS 存网站后端用的图片/视频（程序员视角），PDS 给你的最终用户看（网盘界面）"
❌ "用 OSS 当用户的网盘" (root cause of confusion)
```

### 1.3 Token Plan / Bailian / DashScope

| Dimension | Bailian | DashScope |
|---|---|---|
| Positioning | LLM app dev platform + Workspace + Token Plan billing | Model inference API endpoint (qwen-max / qwen-vl-max etc.) |
| Entry point | `https://bailian.console.aliyun.com` (Workspace) + `https://common-buy.aliyun.com/token-plan` (Token Plan purchase) | `https://dashscope.console.aliyun.com` |
| API key | Generated within Bailian Workspace | Independent DashScope API key |
| Billing | Subscription Token Plan + pay-as-you-go | Pure per-token pay-as-you-go |
| Token Plan entry | **Sold only under Bailian**: `https://common-buy.aliyun.com/token-plan` | DashScope has **no** token-plan entry |
| **OPC context usage** | `webui_app` preferred; subscription makes costs predictable | Flexible pay-as-you-go; OPC does not recommend currently (unpredictable costs) |

**Disambiguation prompt patterns**:

**Sample output (zh-CN):**

```text
✅ "OPC 推荐百炼 + Token Plan，包年包月便于成本控制"
❌ "用灵积的 Token Plan" (does not exist)
```

### 1.4 CDT / Public Traffic Pack / Outbound Bandwidth

| Dimension | CDT (Cloud Data Transfer) | Public Traffic Pack | EIP Outbound Bandwidth |
|---|---|---|---|
| Positioning | Cross-region/cross-account public data transfer billing | Single-region public outbound traffic prepaid bundle | ECS instance EIP peak upstream bandwidth |
| Billing | Per-GB post-paid | Per-GB prepaid (XX GB/month or half-year) | Per-Mbps monthly or per-traffic post-paid |
| Entry point | `https://cdt.console.aliyun.com` click "Upgrade" (**only way**) | `https://common-buy.aliyun.com?commodityCode=internet_traffic_pkg` | At ECS instance creation time |
| OpenAPI | **None** (CLI v3.4.1 has no cdt product code) | Available | Available |
| **Common error** | "220 GB CDN traffic" (CDN is CDN, CDT is CDT) | — | — |
| **OPC context usage** | All SKUs enable by default (manual prerequisite step) | Some SKUs include | All SKUs include |

**Disambiguation prompt patterns**:

**Sample output (zh-CN):**

```text
✅ "CDT = 公网出方向数据传输计费，必须在 cdt.console.aliyun.com 手动升级开通"
❌ "CDT 包含 220GB 流量" (completely wrong)
```

### 1.5 ICP / Real-Name Verification / Filing

| Dimension | Alibaba Cloud Account Real-Name Verification | ICP Filing |
|---|---|---|
| Object | Alibaba Cloud account (personal/enterprise) | Domain (operating on mainland China servers) |
| Entry point | `https://account.console.aliyun.com/v2/realname` | `https://beian.aliyun.com` |
| Completion time | Instant (personal) / 1–3 days (enterprise) | 7–20 days |
| OpenAPI | Available (verification status) | **None** (CLI false) |
| Prerequisite relationship | Prerequisite for ICP filing | Domain + server purchase required before filing |
| Common failures | ID card/business license expired | Domain suffix blocklist (.io/.dev cannot file), entity already has ICP |

**Disambiguation prompt patterns**:

**Sample output (zh-CN):**

```text
✅ "先实名认证（一次性），再做域名 ICP 备案（按域名走）"
❌ "实名认证就是备案" (they are different)
```

## 2. Confusable-Term Reverse-Lookup Index (for lint)

```
Confusable Term              → Required disambiguation fragment
"阿里云盘" (Aliyun Drive)    → "PDS 企业版" or "pds_trc_public_cn" or "不是个人版 aliyundrive"
"OSS"                        → "对象存储" or "API" or "bucket"
"云盘" (Cloud Drive)         → "PDS" or "网盘界面" or "aliyundrive" (if consumer-tier semantics)
"Token Plan"                 → "百炼" or "common-buy.aliyun.com/token-plan"
"CDT"                        → "公网传输" or "cdt.console.aliyun.com" or "无 OpenAPI"
"备案" (Filing)              → "ICP" or "beian.aliyun.com" or "前置实名"
"实名" (Real-Name)           → "账号实名" or "realname" or "备案前置"
```
