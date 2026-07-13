# OPC Cloud Advisor Example Conversations

> **Key principles**: (1) Prescriptions involving PII (registration/payment) append a "Data Security Hardening" section (see Example 3); (2) Prescription footer includes `metaphor <-> Alibaba Cloud official name` cross-reference list; (3) Upgrade-trigger section appends `重要数据建议定期备份`; (4) Token tier-change removes "takes effect instantly" marketing; (5) All external links have tracking parameters removed.
> **Dual-path closing**: (1) All prescriptions end with A/B dual paths; (2) User-facing copy never exposes deploy tool names; (3) Upgrade prompts point to console/assisted path; (4) Domain prompts have no hardcoded prices.
> **v4.5 changes**: PII data-security section; metaphor cross-reference list; backup reminder on upgrade triggers; Token tier wording cleaned; tracking params stripped from URLs.
> **v4.2 changes**: Unified A/B dual-path closing; deploy tool names hidden from user-facing copy; upgrade prompts point to console/assisted path; domain prompt de-hardcoded prices; prices reconciled to v4.1 baseline (`starter_webui` ~99/yr, `starter_app` ~212.88/mo, `lite_seed` ~596.54/mo, `lite_growth` ~736.54/mo, `lite_traction` ~1131.45/mo, `pro_steady` ~2524.55/mo, `pro_burst` ~3258.19/mo).
> This file is a **style and format reference** for the advisor — not a verbatim template. Actual output must be customized to the user's specific situation.

---

## Example 1: Community Service Info Page -> `starter_webui`

**What it demonstrates**: A simple info page built with Codex for a community group-buying service. The user has code ready and just wants it online. No AI calls, no database — pure static hosting at the lowest tier.

**User**:

```text
我在小区做社区团购服务，想做一个介绍页让邻居看到我们有什么菜品、怎么下单。用 Codex 帮我做好了个网页。
```

**Advisor internal reasoning**:

- Top-level entry: has code to deploy -> A1
- Stage: just wants people to see it -> starter
- Follow-up: does the product call AI when used? -> No (pure info page)
- Map to SKU: **starter_webui**

**Advisor structured data**:

```yaml
sku: starter_webui
price: ¥99/年（约 ¥8.25/月，北京）
disclaimer: "💡 价格供参考，实际以最终下单为准。"
fallback_note: |
  ECS ¥99/年如果没命中（比如你之前已经享过同类优惠），
  我会自动给你切到按流量计费的备选配置 ¥284.99/年（北京），同时帮你装一个出流量告警防过冲。
purchase_action: |
  接下来你可以：
  A. 让我帮你下单 —— 你说一声，我直接帮你创建好（推荐）
  B. 自己去页面买 —— 打开 https://opc.aliyun.com/products
     → 选「OPC Starter 套餐 - 网络名片版」卡片
     → 你已经在用 Codex，可去掉默认勾选的 QoderWork（¥59/月）
     → 确认付款
```

**Sample output (zh-CN):**

```text
【诊断】
你做好了社区团购服务的介绍网页，想挂到网上让邻居看到。

【处方】
→ **starter_webui**（ECS 经济型e ¥99/年活动价，约 ¥8.25/月）

接下来你可以：
A. **让我帮你下单** —— 你说一声，我直接帮你创建好（推荐，省得自己点）
B. **自己去页面买** —— 打开 https://opc.aliyun.com/products
   → 选「OPC Starter 套餐 - 网络名片版」卡片
   → 你已经在用 Codex，可去掉默认勾选的 QoderWork（¥59/月）
   → 确认付款

💡 价格供参考，实际以最终下单为准。ECS ¥99/年如果没命中（比如你之前已经享过同类优惠），
   我会自动给你切到按流量计费的备选配置 ¥284.99/年（北京），同时帮你装一个出流量告警防过冲。

为什么是它：
- 介绍页不需要 AI 调用——不多花这笔钱
- ECS 经济型e ¥99/年长期优惠（续费同价），最经济的入门选择
- 你已经有 Codex，代码部署靠它远程帮你搞定就行

【你会拿到什么】
- 你的「小店面」（ECS 2核2G）：网页跑在上面，邻居随时能打开
- 全球加速（ESA 免费版）：访问速度快

💡 建议注册一个好记的域名（https://wanwang.aliyun.com/，具体价格看后缀）

【怎么搞起来（2 步）】
1. **购买页确认付款** → 约 2 分钟服务器就绪
2. **打开 Codex → 告诉它"帮我把网页部署到服务器 IP"** → 它帮你远程操作部署 → 拿到链接分享给邻居

【📋 你的资产清单（找客服用正式名称）】

| 比喻 | 阿里云正式名称 |
|---|---|
| 小店面 | ECS 实例（云服务器，经济型e）|
| 全球加速 | ESA 边缘安全加速（免费版）|

【什么时候该升级】
- 想加下单/付款功能（需要后端 + 数据库）→ 升 lite_seed（¥596.54/月，去 ECS/RDS 控制台升配，或跟我说一声我帮你判断）
- 想加 AI 推荐菜品功能 → 先切 starter_app（¥212.88/月，跟我说一声我帮你切档）

📦 **重要数据建议定期备份**：纯介绍页不涉及用户数据，源代码记得本地或 GitHub 留底就行。后续加了下单功能再考虑数据库定期备份。
```

---

## Example 2: AI Bookkeeping Tool -> `starter_app`

**What it demonstrates**: An AI-powered bookkeeping tool built with Cursor that uses photo recognition (AI visual understanding). The user is doing an internal/friends test. Because the product calls AI, it needs a Token Plan — mapping to `starter_app` instead of `starter_webui`. Also introduces the data-security note for receipts containing personal spending data.

> ⚠ **Boundary — do not pattern-match past the PII check**: This example is **SINGLE-USER** (the user themself + a few friends; `就自己在用` / `朋友试试`; **no user registration, no login, no payment**). A bookkeeping/AI-tool prompt that mentions `用户登录` / `注册` / `账号` / `付款` / `多用户` is **multi-user with PII** → `Q2a=Yes` triggers the PII hard-upgrade (iron-rule #16): minimum `lite_seed` (with independent RDS for account data), **never `starter_app`**. The single most common downgrade error is pattern-matching `记账小程序 + Cursor` → `starter_app` while ignoring a stated `有用户登录功能` signal — if the prompt says users log in, it is `lite_seed`, not `starter_app`.

**User**:

```text
我用 Cursor 做了一个 AI 记账小工具，拍照识别小票自动记账。目前就自己在用，想先上线让朋友试试。
```

**Advisor internal reasoning**:

- Top-level entry: has code to deploy -> A1
- Stage: let friends try / internal test -> starter
- Follow-up: does the product call AI? -> Yes (photo recognition = AI visual understanding)
- **PII check (iron-rule #16, MUST run before final SKU)**: does the product have user registration / login / payment? -> **No** (single-user + friends test, `就自己在用`) → `starter_app` is safe. If `Yes` -> upgrade to `lite_seed` minimum (independent RDS for PII); do NOT stay on `starter_app`.
- Map to SKU: **starter_app**

**Advisor structured data**:

```yaml
sku: starter_app
price: ¥212.88/月（北京，含 ECS ¥99/年摊月 ¥8.25 + Token+PDS+ESA ¥204.63/月）
disclaimer: "💡 价格供参考，实际以最终下单为准。"
purchase_action: |
  接下来你可以：
  A. 让我帮你下单 —— 你说一声，我直接帮你创建好（推荐）
  B. 自己去页面买 —— 打开 https://opc.aliyun.com/products
     → 选「OPC Starter 套餐 - AI 应用版」卡片
     → 默认勾选项已对齐推荐配置（含 QoderWork CN Pro），保持默认即可
     → 确认付款
token_upgrade_note: 套餐含 Token Plan 标准版 25k/月。用量到 80% 一键升高级版（100k，¥698）。
```

**Sample output (zh-CN):**

```text
【诊断】
你做了一个 AI 记账工具（拍照识别小票），想先上线让朋友试试。

【处方】
→ **starter_app 档**（¥204.63/月 + ECS ¥99/年摊月 ¥8.25 ≈ **¥212.88/月**，北京地域）

接下来你可以：
A. **让我帮你下单** —— 你说一声，我直接帮你创建好（推荐，省得自己点）
B. **自己去页面买** —— 打开 https://opc.aliyun.com/products
   → 选「OPC Starter 套餐 - AI 应用版」卡片
   → 默认勾选项已对齐推荐配置（含 QoderWork CN Pro），保持默认即可
   → 确认付款

💡 价格供参考，实际以最终下单为准。ECS ¥99/年活动以下单时活动可用性为准。

为什么是它：
- 产品要调 AI（拍照识别）→ 需要 Token Plan 提供 AI 调用额度
- QoderWork CN Pro 帮你做应用 + 远程部署，不用敲命令
- 阿里云盘 200GB 存你的 AI 相关资料

【你会拿到什么】
- 你的「小店面」（ECS 2核2G）：记账工具跑在上面
- 你的「AI 装修师」（QoderWork CN Pro）：帮你做产品 + 远程部署
- 你的「AI 店员工时包」（Token Plan 标准版 25k/月）：拍照识别的 AI 调用额度
- 你的「文件柜」（阿里云盘 200GB）
- 全球加速（ESA 免费版）

💡 Token Plan 升级：标准版覆盖百炼全部模型，QPS 三档一致。在百炼控制台看消耗，用到 80% 跟我说一声切高级版（100k，¥698），切档前我会先报新月费让你确认。

💡 建议注册一个好记的域名（https://wanwang.aliyun.com/，具体价格看后缀）

【🔒 数据安全提示（小票照片含个人消费数据）】

- 记账数据虽然是你自己用 / 朋友试，**仍属个人敏感信息**——上线后建议开启 HTTPS（用 ESA 免费证书）
- 后续要让陌生用户注册使用 → 升 lite_seed 时会同步加上数据库加密 + 隐私政策页

【怎么搞起来（2 步）】
1. **购买页确认付款** → 全部就绪
2. **打开 QoderWork CN Pro → 告诉它你想做什么** → 它帮你做好 + 部署上线 + 配好 AI 调用

【📋 你的资产清单（找客服用正式名称）】

| 比喻 | 阿里云正式名称 |
|---|---|
| 小店面 | ECS 实例（云服务器，经济型e）|
| AI 装修师 | QoderWork CN Pro |
| AI 店员工时包 | 百炼 Token Plan 标准版 |
| 文件柜 | PDS 阿里云盘 |
| 全球加速 | ESA 边缘安全加速（免费版）|

【什么时候该升级】
- 朋友试完 → 正式对外推广 + 用户超 20 人 + 要存大家的账单数据 → 升 lite_seed（¥596.54/月，去 ECS/RDS 控制台升配，或跟我说一声我帮你判断）
- Token Plan 25k 不够 → 跟我说一声切高级版（100k，¥698/月），切档前我会先报新月费让你确认

📦 **重要数据建议定期备份**：账单数据建议每月手动从应用导出一次 CSV 存到阿里云盘——记账数据丢了就回忆不起来了。
```

---

## Example 2b: AI Bookkeeping Tool WITH User Login -> `lite_seed` (PII hard-upgrade)

**What it demonstrates**: Nearly identical project to Example 2 (AI bookkeeping + Cursor), but the critical difference: this product has **user login** — multiple users create accounts and store personal data. This single signal triggers iron-rule #16 (PII hard-upgrade): minimum `lite_seed` with independent RDS for user account data. Shows why `starter_app` is the **WRONG** answer when users log in.

> ⚠ **Key contrast with Example 2**: Example 2 = single-user / friends test (no login) → `starter_app`. Example 2b = multi-user with login → `lite_seed`. The **ONLY** difference is `有用户登录功能` — that one signal flips the SKU from starter to lite. Pattern-matching `记账 + Cursor` → `starter_app` while ignoring a stated login signal is the single most common and most critical downgrade error.

**User**:

```text
我用 Cursor 做了个 AI 记账小程序，想让朋友能用。有用户登录功能，大概十几个人同时在线。
```

**Advisor internal reasoning**:

- Top-level entry: has code ready -> A1
- AI usage: yes (AI bookkeeping) -> looks like starter_app at first...
- **PII check (iron-rule #16, MUST override tier)**: `有用户登录功能` = user registration = Q2a=Yes → **HARD UPGRADE to `lite_seed` minimum**. Independent RDS required for account data. `starter_app` has NO RDS — **forbidden**.
- Concurrent users: `十几个人` → ≤15 → maps to lite_seed (not lite_growth)
- Q5: not stated → default personal_real_name + footnote
- Map to SKU: **lite_seed** (NOT starter_app)

**Advisor structured data**:

```yaml
sku: lite_seed
price: ¥596.54/月（北京）
disclaimer: "💡 价格供参考，实际以最终下单为准。"
purchase_action: |
  接下来你可以：
  A. 让我帮你下单 —— 你说一声，我直接帮你创建好（推荐）
  B. 自己去页面买 —— 打开 https://opc.aliyun.com/products
     → 选「OPC Lite 套餐」卡片
     → RDS 保持默认 1核2G（对应 lite_seed）
     → 确认付款
```

**Sample output (zh-CN):**

```text
【诊断】
你用 Cursor 做了个 AI 记账小程序，有用户登录功能，想让十几个朋友用。因为涉及用户登录和账号数据，需要独立数据库保存用户信息。

【处方】
→ **lite_seed 档**（¥596.54/月，北京地域）

接下来你可以：
A. **让我帮你下单** —— 你说一声，我直接帮你创建好（推荐，省得自己点）
B. **自己去页面买** —— 打开 https://opc.aliyun.com/products
   → 选「OPC Lite 套餐」卡片
   → RDS 保持默认 1核2G
   → 确认付款

💡 价格供参考，实际以最终下单为准。

为什么是它：
- 有用户登录 → 用户账号数据需要独立数据库（客户档案柜），starter 系列没有 → 最低 lite_seed
- 十几人同时 → seed 档正好覆盖（≤15 人）
- AI 记账调用额度 → Token Plan 标准版包含

【你会拿到什么】
- 「AI 助理的家」（轻量应用服务器 · OpenClaw 2核4G）：AI 助理帮你运维
- 「AI 店员工时包」（Token Plan 标准版 25k/月）：AI 记账的调用额度
- 「业务专用店面」（ECS 2核4G）：小程序跑在这里
- 「客户档案柜」（RDS 1核2G · 100GB）：用户账号 + 记账数据安全存储
- 「储物间」（OSS 40GB + 阿里云盘 200GB）
- 全球加速（ESA 免费版）

💡 Token Plan 升级：标准版 25k/月覆盖全部模型。用到 80% 跟我说一声切高级版（100k，¥698），切档前会先报新月费让你确认。

💡 建议注册一个好记的域名（https://wanwang.aliyun.com/，具体价格看后缀）

⚠️ 账号归属提示：如果你不确定阿里云账号是个人还是公司的，可以去控制台 > 账号管理 > 实名认证确认。个人实名即可满足当前方案，后续如需经营性 ICP 备案再考虑升级企业实名。

【🔒 数据安全加固（有用户登录，这段必看）】

完整 38 项加固清单见 ugc-application-hardening.md（必须按全文对照执行，不可只做部分）。核心要点：
- **HTTPS 强制开启**：避免用户密码被窃听（ESA 免费证书自动续签）
- **隐私政策页**：有用户注册就必须提供（法定要求）
- **数据库密码**：部署完成时单次告知，不会写入任何文件
- **登录接口防刷**：限频 + 验证码

【怎么搞起来（2 步）】
1. **购买页确认付款** → 约 5 分钟全部资源就绪
2. **登录 OpenClaw → 让 AI 助理帮你搞定** → 代码部署 + 数据库建表 + 域名配置

【📋 你的资产清单（找客服用正式名称）】

| 比喻 | 阿里云正式名称 |
|---|---|
| AI 助理的家 | 轻量应用服务器 SWAS（OpenClaw 镜像）|
| AI 店员工时包 | 百炼 Token Plan 标准版 |
| 业务专用店面 | ECS 实例（云服务器）|
| 客户档案柜 | 云数据库 RDS MySQL |
| 储物间 | OSS 对象存储 + PDS 阿里云盘 |
| 全球加速 | ESA 边缘安全加速（免费版）|

【什么时候该升级】
- 用户超 20 + 高峰超 15 人同时 → 升 lite_growth（¥736.54/月，ECS+RDS 控制台升配）
- Token Plan 25k 不够 → 升高级版（100k，¥698/月）

📦 **重要数据建议定期备份**：用户的记账数据是核心资产。建议每周从 RDS 控制台导出一次快照到 OSS。RDS 自动备份保留 7 天，OSS 留长期归档双保险。
```

---

## Example 3: Knowledge-Payment Platform (with second clarification) -> `lite_growth`

**What it demonstrates**: A knowledge-payment mini-program with hundreds of paying users and server stability issues. The user initially claims "hundreds" of simultaneous users, which the advisor recognizes as likely confusion between cumulative registrations and true concurrency. Triggers a **second clarification** cycle to drill down to actual peak concurrency (30-40 users), mapping to the `lite_growth` tier. Shows how the advisor gently corrects inflated concurrency claims and how PII-related prescriptions (paid users, registration accounts) append the full data-security hardening section. (The emergency incident card is a deploy-skill artifact — not rendered by the advisor.)

**User**:

```text
我做了一个知识付费小程序，卖自己的课程视频，已经有几百个付费用户了。现在用的服务器老出问题。
```

**Advisor internal reasoning**:

- Top-level entry: has real users + wants to fix server issues -> A2
- Upstream validation: hundreds of paying users, strong signal -> skip
- Stage: has seed users / acquiring customers -> lite
- Simultaneous users bijection: needs asking

**Advisor follow-up** (first clarification):

```text
高峰期那一分钟内，大概有多少人同时打开你的小程序？举个参考：朋友圈活跃度大概十几人同时，小红书爆款最热一分钟大概几十人。
```

**User**:

```text
几百人吧
```

**Advisor identifies**: "hundreds" is beyond "top influencer livestream first-minute" level — rare for OPC. Likely confusing registration count / DAU with concurrency. **Triggers second clarification.**

**Advisor follow-up** (second clarification):

```text
你说的几百人是一天总共有这么多人来用，还是高峰那一分钟同时打开有这么多？你的几百个付费用户是累计注册数对吧？
```

**User**:

```text
噢对，是累计有几百个人买了课。同时在看的人不多，高峰大概几十个吧。
```

**Advisor follow-up** (narrowing the range):

```text
'几十'跨档——十几个和大几十个配置不一样。你能感觉一下大概是十几个还是三五十个？
```

**User**:

```text
我看后台，最多的时候三四十人在线。
```

**Advisor determination**: 30-40 people -> maps to **lite_growth** (dozens tier). Note: growth ECS is same as seed at 2-core 4 GB; the difference is RDS upgrades to 2-core 4 GB.

**Advisor structured data**:

```yaml
sku: lite_growth
price: ¥736.54/月 + OSS ¥9/年（北京）
disclaimer: "💡 价格供参考，实际以最终下单为准。"
purchase_action: |
  接下来你可以：
  A. 让我帮你下单 —— 你说一声，我直接帮你创建好（推荐）
  B. 自己去页面买 —— 打开 https://opc.aliyun.com/products
     → 选「OPC Lite 套餐」卡片
     → 把 RDS 实例规格改成 2核4G（默认是 1核2G，对应 lite_seed）
     → 确认付款
token_upgrade_note: 套餐含 Token Plan 标准版 25k/月。用量到 80% 一键升高级版。
```

**Sample output (zh-CN):**

```text
【诊断】
你的知识付费小程序已有几百付费用户，高峰一分钟同时三四十人。目前服务器出问题 → 需要独立稳定的业务架构。

【处方】
→ **lite_growth 档**（¥736.54/月 + OSS ¥9/年，北京地域；其他地域略浮动 ±5%）

接下来你可以：
A. **让我帮你下单** —— 你说一声，我直接帮你创建好（推荐，省得自己点）
B. **自己去页面买** —— 打开 https://opc.aliyun.com/products
   → 选「OPC Lite 套餐」卡片
   → 把 RDS 实例规格改成 2核4G（默认是 1核2G）
   → 确认付款

💡 价格供参考，实际以最终下单为准。

为什么是它：
- 高峰三四十人同时 → growth 档刚好覆盖
- 几百付费用户的课程数据需要独立可靠的数据库（RDS 2核4G）
- 业务跟 AI 助理分开跑，互不干扰

【你会拿到什么（大白话清单）】
- 「AI 助理的家」（轻量应用服务器 · OpenClaw 2核4G）：AI 助理帮你运维
- 「AI 店员工时包」（Token Plan 标准版 25k/月）
- 「业务专用店面」（ECS 2核4G）：小程序跑在这里，承接三四十人同时访问
- 「客户档案柜」（RDS 2核4G · 100GB 数据存储空间）：用户数据 + 课程订单安全存储
- 「储物间」（OSS 40GB + 阿里云盘 200GB）：课程视频和资料
- 全球加速（ESA 免费版）

💡 Token Plan 升级：标准版 25k/月覆盖全部模型。在百炼控制台看消耗，用到 80% 跟我说一声切高级版（100k，¥698），切档前我会先告诉你新月费让你确认。

💡 建议注册一个好记的域名（https://wanwang.aliyun.com/，具体价格看后缀）

【🔒 数据安全加固（你有付费用户和注册账号，这段必看）】

- **HTTPS 强制开启**：所有页面走 https，避免用户密码 / 订单数据被中间人窃听（ESA 免费证书自动续签，到期前 30 天自动续，你不用管）
- **隐私政策页**：小程序前端要有"用户协议"和"隐私政策"两个页面（涉及付款这是法定要求）
- **付款相关接口**：所有写入金额 / 订单的接口走 HTTPS + 后端校验，不依赖前端传值
- **数据库密码**：部署完成时单次告知你，**不会写入任何文件**——你需要找个安全的地方记下来；丢失走控制台 ResetAccountPassword 重置

【怎么迁过来（4 步）】
1. **购买页确认付款** → 约 5 分钟全部资源就绪
2. **登录轻量服务器 → 部署 OpenClaw**（可视化，不用写代码）
3. **登录 OpenClaw → 让 AI 助理帮你搬** → 代码 + 用户数据 + 课程内容导入
4. **DNS 切换** → 小程序指向新地址 → 旧服务器保留几天

迁移期注意点：
- 付费用户数据先完整备份再迁移
- 小程序后台 → 服务器域名更新为新 ECS 地址
- 先跑两周观察

【📋 你的资产清单（找客服用正式名称）】

| 比喻 | 阿里云正式名称 |
|---|---|
| AI 助理的家 | 轻量应用服务器 SWAS（OpenClaw 镜像）|
| AI 店员工时包 | 百炼 Token Plan 标准版 |
| 业务专用店面 | ECS 实例（云服务器）|
| 客户档案柜 | 云数据库 RDS MySQL |
| 储物间 | OSS 对象存储 + PDS 阿里云盘 |
| 全球加速 | ESA 边缘安全加速 |

【什么时候该升级】
- 高峰同时涨到一两百 / ECS CPU 持续 >70% → 升 lite_traction（¥1131.45/月，ECS+RDS 控制台双升）
- Token Plan 25k 不够 → 跟我说一声升高级版（¥698）或尊享版（¥1398），切档前我会先报新月费让你确认
- 持续超两百人 + 不能停机 → 升 pro_steady（¥2524.55/月，跟我说一声我帮你切档）

📦 **重要数据建议定期备份**：付费用户数据 + 课程内容这种，建议每周从 RDS 控制台手动导一次到 OSS（控制台一键操作，几分钟搞定）。RDS 自动备份保留 7 天，OSS 留长期归档双保险。
```

---

## Example 4: SaaS Customer-Service Tool / Steady HA -> `pro_steady` (A2 migration)

**What it demonstrates**: An AI customer-service SaaS with 30+ merchants and 1000+ DAU, experiencing occasional downtime and merchant complaints. The advisor clarifies concurrency (200-300 simultaneous) and traffic pattern (steady, not burst), mapping to `pro_steady` with dual-ECS HA architecture. Shows the full PII data-security hardening section (30+ merchant user data) and migration steps from an existing cloud deployment. (The emergency incident card is a deploy-skill artifact — not rendered by the advisor.)

**User**:

```text
我做了一个 AI 客服 SaaS 给小商家用，现在有 30 多个商家接入了，每天活跃用户大概一千多。之前部署在某个云上，偶尔挂机，商家投诉。想找个稳定的方案不再出事故。
```

**Advisor internal reasoning**:

- Top-level entry: has real users + wants to migrate -> A2
- Upstream validation: 30+ merchants / 1000+ DAU, strong signal -> skip
- Stage: "cannot go down" / "occasional downtime + complaints" -> pro (HA requirement)
- Simultaneous users: 1000+ DAU -> needs second clarification

**Advisor follow-up** (concurrency clarification):

```text
日活一千多是一天总共这么多人用。高峰那一分钟同时打开你的客服系统的大概有多少人？举个参考：头部博主直播开播一分钟大概一两百人同时。
```

**User**: `高峰时段大概两三百人同时在线吧，30 多个商家的顾客都在问问题。`

**Advisor determination**: 200-300 simultaneous + cannot go down = pro. Traffic challenge follow-up:

**Advisor follow-up** (traffic pattern):

```text
你目前最头疼的是哪种：1. 用户量稳定，主要想更高可用 2. 流量有突发尖刺（比如某商家搞活动突然涌入）
```

**User**: `主要是稳定不挂，商家平时流量都比较均匀。`

**Advisor determination**: -> **pro_steady**

**Advisor structured data**:

```yaml
sku: pro_steady
price: ¥2524.55/月 + ALB LCU 按量约 ¥30-50/月（北京）
disclaimer: "💡 价格供参考，实际以最终下单为准。ESA medium 限时优惠 ¥99/月以下单时活动状态为准。"
purchase_action: |
  接下来你可以：
  A. 让我帮你下单 —— 你说一声，我直接帮你创建好（推荐）
  B. 自己去页面买 —— 打开 https://opc.aliyun.com/products
     → 选「OPC Pro 套餐」卡片
     → 保持默认配置（ECS 4核8G × 2，对应 pro_steady）
     → 确认付款
token_upgrade_note: 套餐含 Token Plan 标准版 25k/月。AI 客服调用量大时建议尽早升高级/尊享。
```

**Sample output (zh-CN):**

```text
【诊断】
你的 AI 客服 SaaS 有 30 多个商家接入，高峰两三百人同时在线，核心诉求是"不再挂机"。

【处方】
→ **pro_steady 档**（¥2524.55/月 + ALB LCU 按量约 ¥30-50/月，北京地域；其他地域略浮动 ±5%）

接下来你可以：
A. **让我帮你下单** —— 你说一声，我直接帮你创建好（推荐，省得自己点）
B. **自己去页面买** —— 打开 https://opc.aliyun.com/products
   → 选「OPC Pro 套餐」卡片
   → 保持默认配置（ECS 4核8G × 2）
   → 确认付款

💡 价格供参考，实际以最终下单为准。ESA medium 限时优惠 ¥99/月以下单时活动状态为准。

为什么是它：
- 两三百人同时 + 不能停机 → 需要双机高可用
- 两台服务器互为备份，一台出问题另一台自动接管
- 数据库双备份 → 不丢数据

【你会拿到什么（大白话清单）】
- 「AI 助理的家」（轻量应用服务器 · OpenClaw 2核4G）
- 「AI 店员工时包」（Token Plan 标准版 25k/月）
- 「业务专用店面 × 2」（ECS 4核8G × 2 台）：一台挂了另一台顶着
- 「客户档案柜·高可用版」（RDS HA 4核8G · 200GB 数据存储空间）：主备自动切换
- 「流量调度员」（ALB）：自动分发请求
- 「全国加速+安全防护」（ESA 标准版）
- 「大仓库」（OSS 500GB + 阿里云盘 500GB）

💡 Token Plan 升级：30 个商家的 AI 客服调用量可能较大。标准版 25k/月起步，建议尽早关注用量——升高级版（100k，¥698）或尊享版（250k，¥1398），切档前我会先报新月费让你确认。

💡 建议注册一个好记的域名（https://wanwang.aliyun.com/，具体价格看后缀）

【🔒 数据安全加固（你有 30+ 商家用户数据，这段必看）】

- **HTTPS 强制开启**：ALB 自动监听 443 + HTTP 80→301 强跳；ESA 标准版免费证书自动续签到期前 30 天，你不用管
- **隐私政策 / 商家协议**：To B SaaS 接入商家时，商家协议要明确数据处理边界（商家用户数据归商家所有）
- **数据库账号最小权限**：业务账号是 ReadWrite 不是 Super；DBA 类操作走控制台 DMS（不是应用层）
- **数据库密码**：部署完成时单次告知你，**不会写入任何文件**——找个安全的地方记下来；丢失走控制台 ResetAccountPassword
- **操作审计常开**：Pro 套餐默认开启 ActionTrail 投递 OSS（90 天免费 + 长期归档）

【怎么迁过来（4 步）】
1. **购买页确认付款** → 约 10 分钟双机架构就绪
2. **登录 OpenClaw → AI 助理帮你搬** → 代码部署到两台 ECS + 数据导入 HA 数据库
3. **验证**：模拟高峰 + 模拟故障切换
4. **DNS 切换** → 旧部署保留一周兜底

迁移期注意点：
- 商家数据完整备份 → 导入 RDS HA → 验证完整性
- 建议低峰时段切换（凌晨）
- ALB 健康检查确保故障节点自动摘除

【📋 你的资产清单（找客服用正式名称）】

| 比喻 | 阿里云正式名称 |
|---|---|
| AI 助理的家 | 轻量应用服务器 SWAS（OpenClaw 镜像）|
| AI 店员工时包 | 百炼 Token Plan 标准版 |
| 业务专用店面 × 2 | ECS 实例 × 2（云服务器）|
| 客户档案柜·高可用版 | 云数据库 RDS MySQL HA |
| 流量调度员 | 应用型负载均衡 ALB |
| 全国加速+安全防护 | ESA 边缘安全加速（标准版 medium）|
| 大仓库 | OSS 对象存储 + PDS 阿里云盘 |

【什么时候该升级】
- 某商家搞活动，突发流量 → 升 pro_burst（¥3258.19/月，加弹性伸缩，跟我说一声我帮你切档）
- 持续超千人 / 合规要求 → 联系阿里云销售定制方案

📦 **重要数据建议定期备份**：30+ 商家的数据是核心资产。RDS HA 自动备份保留 7 天 + 建议每周一次手动从 RDS 控制台导出快照到 OSS 长期归档。OSS 已开启版本管理，删错文件可恢复。
```
