# Domain & ICP Filing Appendix (Compact)

## Domain

**Purchase entry**: https://wanwang.aliyun.com/ (Wanwang — Alibaba Cloud domain service)

**Pricing**: varies by suffix (.com / .cn mainstream suffixes start at tens of RMB/year; .io / .app / .ai are more expensive). Actual price subject to checkout; includes free SSL certificate.

**Unified user-facing script (zh-CN)** — never hardcode prices:

```text
建议注册一个好记的域名（https://wanwang.aliyun.com/，具体价格看后缀）
```

**Common talking points for users**:
- If user already has a domain from elsewhere (GoDaddy / Namecheap / Tencent Cloud / other registrars) — no need to transfer. Just change DNS resolution to point at Alibaba Cloud resources.
- If user has no domain, recommend purchasing directly from Wanwang — natively integrated with Alibaba Cloud, easiest configuration.
- One domain supports multiple subdomains (e.g., `app.yourdomain.com` / `api.yourdomain.com`) — no need to buy each subdomain separately.
- **Some domain suffixes do not support mainland China ICP filing** (e.g., `.io` / `.dev` / `.app` / `.me`) — these can only deploy to non-mainland regions (e.g., Hong Kong). Benefit: no filing required + OSS non-mainland regions include 5 GB/month free traffic.

## ICP Filing

**What is ICP filing**: a compliance requirement for real-name registration of websites/apps within mainland China. **As long as your server is in mainland China** (including SWAS/ECS in mainland regions) and provides public-facing web/mini-program/service-account services, you **must file** — this is the hard prerequisite for domestic business.

**Approximate timeline**: ~7–20 business days (varies by provincial authority, assuming complete materials). Recommend starting **before** migration/launch rather than waiting until everything is built.

**Common user Q&A talking points**:
- If the domain already has ICP filing elsewhere, migrating to Alibaba Cloud requires an ICP filing transfer (`备案接入`) operation (not a re-filing, but requires re-review with similar timeline).
- If user doesn't want to file: choose an **overseas region** (Hong Kong/Singapore etc.), but mainland access will be slower and some scenarios won't work (e.g., WeChat service accounts require a filed domain).
- WeChat service accounts / official accounts / mini-programs callback domains **must have ICP filing** — this is Tencent's hard requirement.

**Filing entry**: Alibaba Cloud Console → Filing → New Filing. Material preparation checklist available at Alibaba Cloud ICP Filing Center real-time announcements.

## Scenarios Requiring ICP Filing

| Scenario | Filing Required? |
|----------|-----------------|
| Independent site / personal website / brand site open to public | Required |
| Mini-program backend, official account callback | Required (mini-program business domains also need separate configuration) |
| WeChat service account callback | Required (domain must be bound to service account after filing) |
| AI tool providing public service (web version or API) | Required |
| Internal/team-only access, not public-facing | Not mandatory |
| Server and domain both overseas, users also overseas | No mainland China ICP filing needed |

## Chinese Original Reference (zh-CN)

**Sample reference document (zh-CN):**

````text
【域名 & ICP 备案附录（简版）】

【域名】

**单买入口**：https://wanwang.aliyun.com/（万网，阿里云域名服务）

**价格**：按后缀不同价格有差异（.com / .cn 等主流后缀几十块一年起，.io / .app / .ai 等较贵），具体以下单时为准；含免费 SSL 证书。

**对客文案统一口径**："建议注册一个好记的域名（https://wanwang.aliyun.com/，具体价格看后缀）"——不报硬编码价。

**几个对客可直接转述的常识点**：
- 如果用户已经在别处（GoDaddy / Namecheap / 腾讯云 / 别的注册商）买过域名，不用搬过来——只需要把 DNS 解析改向阿里云资源即可
- 如果用户没有域名，建议直接在万网买，跟阿里云资源天然打通，配置最省事
- 一个域名可以挂多个二级域名（比如 `app.yourdomain.com` / `api.yourdomain.com`），不用每个二级域名再买
- **部分域名后缀不支持国内 ICP 备案**（如 `.io` / `.dev` / `.app` / `.me`）——这些域名只能选非中国内地地域（如香港）部署，无需也无法备案。好处是免备案 + OSS 非中国内地地域每月前 5GB 流量免费

【ICP 备案】

**ICP 备案是什么**：中国大陆境内对网站/应用进行实名登记的合规要求。**只要你的服务器在中国大陆境内**（包括轻量应用服务器/ECS 在大陆地域），且对外提供网站/小程序/服务号等服务，就**必须备案**——这是国内业务的硬门槛。

**大致周期**：约 7–20 个工作日（材料齐全的情况下，各省管局审核时长不同），建议在迁移/上线**之前**就启动，别等业务都搭好了卡在这一步。

**几个对客常见问题的口径**：
- 如果原域名已经在他处备案，搬到阿里云时需要做"**备案接入**"操作（不是重新备案，但仍需重新过审，时长接近）
- 如果不想备案：服务器选**境外地域**（香港/新加坡等），但国内访问会慢、且某些场景不适用（如微信服务号必须备案域名）
- 微信服务号 / 公众号 / 小程序的回调域名都**必须备过案**——这是腾讯硬性要求

**备案入口**：阿里云控制台 → 备案 → 新增备案。资料准备清单见阿里云备案中心实时公告。

【哪些场景必须备案】

| 场景 | 是否必须备案 |
|---|---|
| 独立站 / 个人网站 / 品牌站对外开放 | 必须 |
| 小程序后端、公众号回调 | 必须（且小程序业务域名也要单独配置） |
| 微信服务号回调 | 必须（域名要在备案后再绑回服务号） |
| AI 工具对外提供服务（含网页版、API） | 必须 |
| 仅内网/团队内部访问、不对公网开放 | 不强制 |
| 服务器和域名都在境外、用户也在境外 | 不需要中国大陆 ICP 备案 |
````
