# A1 Branch Output Template: Zero-Start Five-Section Format

> **Applies to**: user starting from scratch / has an idea but hasn't started / has local code not yet deployed / has code ready to deploy.
> **Key design**: Starter uses unified ECS Economy e + QWCN Pro base (no more OpenClaw/OSS paths); starter_blank/starter_static deprecated; single-question tier determination (calls AI or not); exact pricing; Token Plan unified Standard + upgrade advice.
> **Pricing notes**: (1) starter_webui defaults to ECS ¥99/year promo; if ECS ¥99/year promo not eligible, deploy auto-fallback to ECS Economy e + 40G ESSD Entry + pay-by-traffic + 100 Mbps peak at ¥284.99/year (Beijing), with an outbound-traffic alarm (advisor no longer asks promotion history). (2) All quotes must include the disclaimer (zh-CN):

```text
💡 价格供参考，实际以最终下单为准。
```

> **Dual-path closing**: (1) All prescriptions end with A/B paths (A = let me place the order / B = self-service at opc.aliyun.com/products) — never expose advisor/deploy tool names; (2) Self-service path guides to specific card (4 main cards: `Starter-网络名片版` / `Starter-AI应用版` / `Lite` / `Pro`) with default-checkbox guidance; (3) starter_webui ECS Economy e ¥284.99/year pay-by-traffic fallback available only via assisted path; (4) Upgrade prompts point to "console upgrade" or "tell me and I'll help," never to purchase page; (5) Domain registration removes hardcoded prices.
> **Companion references**: see the SKILL.md references table (SKU matrix / concurrency mapping / glossary / domain & ICP)

## Decision Steps

### Step 1: Determine Stage

| Stage Keywords | Maps To |
|---|---|
| "just want to go live / let people see it / small-scale trial / internal test" | **starter** (→ proceed to Step 2) |
| "already have seed users / acquiring customers / need a database / need to store user data / going public" | **lite** (→ proceed to Step 3) |
| "business accelerating / need HA / multiple machines / can't keep up" | **pro** (→ proceed to Step 4) |

### Step 2: Starter Single-Question Tier Determination

**One question — does the product call AI**:

Ask whether the product heavily calls AI (AI chat / image generation / translation). Sample wording (zh-CN):

```text
你做的产品，用户用的时候会不会大量调 AI？比如 AI 对话、AI 生图、AI 翻译这类。
```

- Yes → **starter_app** (¥212.88/month)
- No → **starter_webui** (ECS Economy e ¥99/year, ~¥8.25/month)

> 💡 If deploy-side pricing doesn't qualify for ¥99 (may have used similar promotion before), deploy auto-fallback to ECS Economy e + 40G ESSD Entry + pay-by-traffic + 100 Mbps peak at ¥284.99/year (Beijing), with an outbound-traffic alarm — advisor no longer asks user promotion history.

Follow-up confirmation — ask whether they already use Codex / WorkBuddy or similar desktop AI assistants; if yes, can skip QWCN Pro (−¥59). Sample wording (zh-CN):

```text
你是不是已经在用 Codex / WorkBuddy 等桌面 AI 助手了？
```

### Step 3: Lite Simultaneous-Users Bijection

Map to lite_seed / lite_growth / lite_traction per the concurrent-users bijection.

### Step 4: Pro Traffic-Challenge Follow-Up

Ask which situation gives them the biggest headache right now. Sample wording (zh-CN):

```text
你目前最头疼的是哪种情况？
```

> 1. Stable user volume, steady access, mainly want higher availability → **pro_steady** (¥2524.55/month + ALB LCU pay-as-you-go)
> 2. Traffic concentrated in specific periods (livestream/campaign/flash-sale) → **pro_burst** (¥3258.19/month min=2, burst machines billed separately)

---

## Output Template (Dual-Track)

### Structured Section

Structured fields (sku / price / scope_declaration / fallback_ecs_config / image) are produced for the downstream deploy skill and **not dumped to the user** — render the Chinese prescription below. Full schema: SKILL.md Output Contract.

### Plain-Language Section (Five-Section Format)

#### If starter_webui

**Sample output (zh-CN):**

```text
【诊断】
你想做 [product form]（展示类/名片类），产品不调 AI。

【处方】
→ **starter_webui**（ECS 经济型e ¥99/年活动价，约 ¥8.25/月）

接下来你可以：
A. **让我帮你下单** —— 你说一声，我直接帮你创建好（推荐，省得自己点）
B. **自己去页面买** —— 打开 https://opc.aliyun.com/products
   → 选「OPC Starter 套餐 - 网络名片版」卡片
   → 如果你已经在用 Cursor/Codex 等桌面 AI 工具，可去掉默认勾选的 QoderWork（¥59/月）
   → 确认付款

💡 价格供参考，实际以最终下单为准。ECS ¥99/年如果没命中（比如你之前已经享过同类优惠），
   我会自动给你切到按流量计费的备选配置 ¥284.99/年（北京），同时帮你装一个出流量告警防过冲。

为什么是它：
- 展示类产品不需要 AI 调用额度——不多花这笔钱
- ECS 经济型e ¥99/年长期优惠（续费同价），最经济的入门选择
- QoderWork CN Pro 桌面端帮你做应用 + 一键部署到服务器，不用敲命令

【你会拿到什么】
- 你的「小店面」（ECS 经济型e 2核2G）：产品跑在上面，随时在线
- 你的「AI 装修师」（QoderWork CN Pro）：帮你做产品 + 远程部署
- 全球加速（ESA 免费版）：国内外访问都快

[domain prompt]

【怎么搞起来（2 步）】
1. **购买页确认付款** → 约 2 分钟服务器就绪
2. **打开 QoderWork CN Pro → 告诉它你想做什么** → 它帮你做好 + 部署上线

【什么时候该升级】
- 产品开始有用户量（几十人持续用） + 需要独立数据库 → 升 lite_seed（¥596.54/月，去 ECS/RDS 控制台升配，或跟我说一声我帮你判断）
- 想加 AI 功能 → 先切 starter_app（+¥204.63/月 加 Token Plan + 云盘）
```

#### If starter_app

**Sample output (zh-CN):**

```text
【诊断】
你想做 [product form]，产品会调 AI（[specific AI usage]）。

【处方】
→ **starter_app 档**（¥204.63/月 含 Token+PDS+ESA + ECS ¥99/年摊月 ¥8.25 ≈ **¥212.88/月**，北京地域；其他地域略浮动 ±5%）

接下来你可以：
A. **让我帮你下单** —— 你说一声，我直接帮你创建好（推荐，省得自己点）
B. **自己去页面买** —— 打开 https://opc.aliyun.com/products
   → 选「OPC Starter 套餐 - AI 应用版」卡片
   → 默认勾选项已对齐推荐配置（含 QoderWork CN Pro），保持默认即可
   → 确认付款

💡 价格供参考，实际以最终下单为准。ECS ¥99/年活动以下单时活动可用性为准。

为什么是它：
- 产品调 AI → 需要 Token Plan 提供 AI 调用额度
- QoderWork CN Pro 帮你做应用 + 远程部署，不用敲命令
- 阿里云盘 200GB 存你和 AI 相关的文件资料

【你会拿到什么】
- 你的「小店面」（ECS 经济型e 2核2G）：产品跑在上面，随时在线
- 你的「AI 装修师」（QoderWork CN Pro）：帮你做产品 + 远程部署
- 你的「AI 店员工时包」（Token Plan 标准版）：每月 25,000 次 AI 调用额度
- 你的「文件柜」（阿里云盘 200GB）
- 全球加速（ESA 免费版）

[Token Plan upgrade advice]
[domain prompt]

【怎么搞起来（2 步）】
1. **购买页确认付款** → 约 2 分钟全部就绪
2. **打开 QoderWork CN Pro → 告诉它你想做什么** → 它帮你做好 + 部署上线 + 配好 AI 调用

【什么时候该升级】
- Token Plan 25k/月不够 → 控制台一键升高级版（100k，¥698/月，升档前先报新月费你确认才执行）
- 用户量涨到几十人正式对外 + 需要独立数据库 → 升 lite_seed（¥596.54/月，去 ECS/RDS 控制台升配，或跟我说一声我帮你判断）
- 服务器 2核2G 资源吃紧 → 升 lite_seed
```

#### If lite (seed/growth/traction)

**Sample output (zh-CN):**

```text
【诊断】
你的 [product form] [stage description]——按你的同时访问规模，落在 [SKU tier name]。

【处方】
→ **[lite_seed/growth/traction] 档**（¥[596.54/736.54/1131.45]/月 + OSS ¥9/年，北京地域；其他地域略浮动 ±5%）

接下来你可以：
A. **让我帮你下单** —— 你说一声，我直接帮你创建好（推荐，省得自己点）
B. **自己去页面买** —— 打开 https://opc.aliyun.com/products
   → 选「OPC Lite 套餐」卡片
   → 配置调整：
     · lite_seed → 保持默认（ECS 2核4G + RDS 1核2G）
     · lite_growth → 把 RDS 实例规格改成 2核4G
     · lite_traction → ECS 改成 4核8G、RDS 改成 4核8G
   → 确认付款

💡 价格供参考，实际以最终下单为准。

为什么是它：
- [Reason 1: fits stage]
- [Reason 2: fits scale]
- [Reason 3: business decoupling — AI assistant stays on SWAS, business runs on dedicated ECS]

【你会拿到什么（大白话清单）】
- 「AI 助理的家」（轻量应用服务器 · OpenClaw 镜像 2核4G）：AI 助理住这里帮你运维
- 「AI 店员工时包」（Token Plan 标准版 25k/月）：AI 调用额度
- 「业务专用店面」（ECS [2核4G/2核4G/4核8G]）：跟 AI 助理物理分开，对外承接真实流量
- 「客户档案柜」（RDS [1核2G/2核4G/4核8G]）：用户数据安全存储
- 「储物间」（OSS 40GB + 阿里云盘 200GB）
- 全球加速（ESA 免费版）

[Token Plan upgrade advice]
[domain prompt]

【怎么搞起来（3 步）】
1. **购买页确认付款** → 约 5 分钟全部资源就绪
2. **登录轻量应用服务器控制台 → 完成 OpenClaw 部署**（可视化配置）→ 拿到 AI 助理地址
3. **登录 OpenClaw** → AI 助理帮你把代码部署到 ECS + 配好数据库

【什么时候该升级】
- [seed→growth] RDS CPU 持续 >70% / 高峰同时从十几涨到几十 → 升 lite_growth（¥736.54/月，去 RDS 控制台升档，或跟我说一声我帮你判断）
- [growth→traction] ECS CPU 持续 >70% / 稳定到一两百人 → 升 lite_traction（¥1131.45/月，ECS+RDS 控制台双升）
- [traction→pro] 持续超两百人 + 不能停机 → 升 pro_steady（¥2524.55/月，多机+高可用，跟我说一声我帮你切档）
- Token Plan 25k 不够 → 控制台一键升高级版（100k，¥698/月）或尊享版（250k，¥1398/月），升档前先报新月费你确认才执行
- ECS 升配不停机（如 2核4G→4核8G），热迁移支持
```

#### If pro (steady/burst)

**Sample output (zh-CN):**

```text
【诊断】
你的 [product form] 同时访问超两百人，[steady/has burst spikes]——需要多机高可用架构。

【处方】
→ **[pro_steady/pro_burst] 档**（¥[2524.55/3258.19]/月 + ALB LCU 按量约 ¥30-50/月，北京地域；其他地域略浮动 ±5%）

接下来你可以：
A. **让我帮你下单** —— 你说一声，我直接帮你创建好（推荐，省得自己点）
B. **自己去页面买** —— 打开 https://opc.aliyun.com/products
   → 选「OPC Pro 套餐」卡片
   → 配置调整：
     · pro_steady → 保持默认（ECS 4核8G × 2）
     · pro_burst → ECS 改成 8核16G × 2，并启用弹性伸缩
   → 确认付款

💡 价格供参考，实际以最终下单为准。ESA medium 限时优惠 ¥99/月以下单时活动状态为准。

为什么是它：
- 超两百人同时 → 单台扛不住，需要双机保障
- [steady] 访问稳定 → 两台互为备份，一台挂了另一台接着
- [burst] 有突发尖刺 → 弹性伸缩自动加机器扛住峰值

【你会拿到什么（大白话清单）】
- 「AI 助理的家」（轻量应用服务器 · OpenClaw 2核4G）
- 「AI 店员工时包」（Token Plan 标准版 25k/月）
- 「业务专用店面」（ECS [4核8G×2 / 8核16G×2-3]）：多台分担流量
- 「客户档案柜·高可用版」（RDS HA 4核8G · 200GB 数据存储空间）：双份备份，数据不丢
- 「流量调度员」（ALB 应用型负载均衡）：自动分发请求 + 健康检查
- 「全国加速+安全防护」（ESA 标准版）：50 条 WAF 规则 + 全球 CDN
- [burst] 「自动伸缩」（ESS）：流量来了自动加机器，走了自动缩
- 「大仓库」（OSS 500GB + 阿里云盘 500GB）

[Token Plan upgrade advice]

【怎么搞起来（3 步）】
1. **购买页确认付款** → 约 10 分钟多机架构全部就绪
2. **登录 OpenClaw** → AI 助理帮你把代码分别部署到多台 ECS + 配好 ALB 分流
3. **验证**：模拟多人访问确认负载均衡正常 → 切换 DNS → 正式上线

【什么时候该升级】
- [steady→burst] 出现突发尖刺（直播/活动）→ 升 pro_burst（加弹性伸缩，跟我说一声我帮你切档）
- [burst→enterprise] 持续超千人 / 多地域 / 合规要求 → 联系阿里云销售定制方案
- Token Plan 25k 不够 → 一键升高级/尊享，升档前先报新月费你确认才执行
```
