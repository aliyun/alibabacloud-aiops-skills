# "Opening a Shop" Metaphor Glossary

> In all user-facing output, cloud product terms **must be expressed per this table**. Bare use of ECS/RDS/OSS/ALB/ESA/VPC/PDS etc. is forbidden.
> Format: `「plain-language role」(cloud product name)`

## UX Softening Rules

**System disk** — Always say "X GiB system disk"; on first mention append the Chinese clarification below. **Forbidden** to show ESSD / PL0 / Entry / SSD / cloud disk technical terms to users.

**Sample output (zh-CN):**
```text
（类似你电脑的系统盘）
```

**SWAS network** — For the host lightweight plan, use the Chinese description below.

**Sample output (zh-CN):**
```text
200Mbps 峰值带宽 · 套餐内含流量，不另收费（类似手机流量套餐）
```

**ECS network** — Use the Chinese description below.

**Sample output (zh-CN):**
```text
100Mbps 峰值带宽 · 流量按使用量计费，每月送 220GB 免费额度（类似手机流量套餐——超出免费额度才计费）
```

**RDS storage** — Always show users the Chinese phrase below with the actual size substituted for X. **Forbidden** to bare-use general_essd / ESSD literals.

**Sample output (zh-CN):**
```text
XGB 数据存储空间
```

**OSS** — In user-facing step reports, show only the bucket name. Endpoint / internal Endpoint stays in YAML for programmatic use — never shown to users.

**SSH** — For lite/pro user-facing copy mentioning server login, use the label plus the parenthetical note below; starter never shows login info. Sample copy (zh-CN):

```text
登录到服务器（这一步是远程登入服务器执行命令；通常由 OpenClaw 帮你操作，你不用自己敲）
```

**OpenClaw** — Starter does not include the OpenClaw path — only lite/pro use it.

---

## Metaphor Translation Table

Format: `metaphor role (English gloss) = cloud product`, followed by the full Chinese expression the agent renders verbatim. All Chinese below is sample user-facing wording, kept inside this fenced block.

```text
「你的小店面」 (your little storefront) = ECS Economy e (Starter)
  → 「小店面」（ECS 2核2G）——产品跑在上面，随时在线
「AI 装修师」 (AI decorator) = QoderWork CN Pro
  → 「AI 装修师」（QoderWork CN Pro）——帮你做应用 + 远程部署到服务器
「AI 助理的家」 (AI assistant's home) = SWAS Lightweight Server (Lite/Pro)
  → 「AI 助理的家」（轻量应用服务器）——OpenClaw 住在里面，常驻云端 7×24 帮你部署/扩容/排障；你的 Cursor/Bolt/QoderWork 是本地编码工具，关机就没，干不了云端运维，所以套餐默认带这台（但如果你已有云上常驻的运维 agent，可以跟我说去掉这项）
「业务专用店面」 (dedicated business storefront) = ECS Cloud Server (Lite/Pro)
  → 「业务专用店面」（ECS XX核XXG）——跟 AI 助理物理分开，专门承接真实流量
「店铺招牌」 (shop signboard) = Domain
  → 「店铺招牌」（域名）——别人找到你的门牌号
「AI 店员工时包」 (AI clerk shift package) = Token Plan
  → 「AI 店员工时包」（Token Plan 标准版 25k/月）——每月 AI 调用额度
「客户档案柜」 (customer file cabinet) = RDS Database
  → 「客户档案柜」（RDS XX核XXG）——专门存数据，安全可靠
「客户档案柜·高可用版」 (file cabinet HA) = RDS HA
  → 「客户档案柜·高可用版」（RDS HA）——双备份，主挂了备自动接管
「储物间 / 大仓库」 (storage room / warehouse) = OSS Object Storage
  → 「储物间」（OSS）——存图片、文件、附件
「文件柜」 (file cabinet) = PDS Enterprise Edition
  → 「文件柜」（阿里云盘 200GB/500GB）——你和 AI 相关的文件资料
「全球加速」 (global acceleration) = ESA Edge Acceleration
  → 「全球加速」（ESA 免费版/标准版）——国内外访问都快
「全国加速+安全防护」 (national accel + security) = ESA Standard (Pro)
  → 「全国加速+安全防护」（ESA 标准版）——50 条 WAF 规则 + 全球 CDN
「流量调度员」 (traffic dispatcher) = ALB Load Balancer
  → 「流量调度员」（ALB）——客人多的时候自动分发到多台店面
「自动伸缩」 (auto-scaling) = ESS Auto Scaling (pro_burst)
  → 「自动伸缩」（ESS）——流量来了自动加机器，走了自动缩
```

---

## Starter Translation Focus

QWCN Pro = `「AI 装修师」` — helps users "describe requirements → build app → remotely deploy to ECS"

- **Never let Starter users set up environments, install software, or run commands** — QWCN Pro handles everything
- **Users who already have Codex/WorkBuddy or similar desktop assistants** may skip QWCN Pro (−¥59/month)

---

## Critical Prohibitions

- ECS row: **`「业务专用店面」（ECS XX核XXG）`** — physically a separate machine from the SWAS where the AI assistant lives
- **Never** describe it as "branch store offloading traffic from the main store" — ECS is business decoupling, not traffic overflow
- **Never** recommend OpenClaw / SWAS / OSS static hosting to Starter users — these paths are deprecated
- ECS spec phrasing / upgrade scripts → see the concurrency mapping § ECS User-Facing Wording Rules
- SKU composition details → see the SKU matrix Part 2
