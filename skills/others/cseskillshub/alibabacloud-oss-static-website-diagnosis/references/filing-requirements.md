# Domain Filing (ICP Filing) Requirements for OSS Static Websites

Guidance reference for the question "does my custom domain need ICP filing
before it can serve my OSS static website?". The diagnosis
script reports the bucket location; combine it with the rules below.

## 1. The rule in one sentence

Any CUSTOM DOMAIN bound to an OSS bucket located in a mainland region of
China
must hold a valid ICP filing issued by the Chinese authorities;
buckets in regions OUTSIDE mainland China do not require filing.

## 2. Region classification used by the diagnosis

Mainland China regions (ICP filing REQUIRED) — the bucket `location` matches
`oss-cn-*` **except** `oss-cn-hongkong`, **plus** the regionless-attribute
locations `oss-rg-china-mainland` / `rg-china-mainland`:

| Family | Examples |
|---|---|
| East China | oss-cn-hangzhou, oss-cn-shanghai, oss-cn-nanjing, oss-cn-fuzhou (East China 6 Fuzhou - local region - being decommissioned) |
| North China | oss-cn-qingdao, oss-cn-beijing, oss-cn-zhangjiakou, oss-cn-huhehaote, oss-cn-wulanchabu |
| South China | oss-cn-shenzhen, oss-cn-heyuan, oss-cn-guangzhou |
| Southwest China | oss-cn-chengdu |
| Central China | oss-cn-wuhan-lr (Central China 1 Wuhan - local region) |
| Northwest China | oss-cn-zhongwei (Northwest China 2 Zhongwei) |
| Finance-cloud variants | oss-cn-hangzhou-finance, oss-cn-shanghai-finance-1, oss-cn-shenzhen-finance-1 |
| Regionless-attribute | oss-rg-china-mainland, rg-china-mainland (data stored in mainland China per official doc document_detail/2248436.html:7) |

Regions WITHOUT filing requirement:

- `oss-cn-hongkong` — officially designated as outside mainland China
  (access-buckets-via-custom-domain-names:12 names Hong Kong explicitly;
  regions-and-endpoints:67 calls mainland-to-HK transfer "cross-border").
- All `oss-ap-*`, `oss-us-*`, `oss-eu-*`, `oss-me-*` regions (Singapore,
  US-West, EU-Central, ME-East-1, etc.).

The script computes `is_mainland_region(location)` from the GetBucketInfo
evidence and surfaces the corresponding knowledge line in the report.
The implementation uses an explicit whitelist (B-2/B-3 fix, 2026-09-03):
`^oss-cn-` excluding `oss-cn-hongkong`, plus `oss-rg-china-mainland` /
`rg-china-mainland`. NEVER use a bare `^oss-cn-` prefix regex.

## 3. Enforcement points

- **Binding**: the console rejects binding an unfiled domain to a mainland
  China bucket.
- **Serving**: even if a binding existed historically, unfiled domains are
  blocked from serving website traffic on mainland buckets.
- The default domain is never a valid substitute: it serves pages under the
  browser download policy only (render-vs-download.md).

## 4. Filing checklist for the user (manual guidance)

1. Confirm the domain registrar and filing subject (individual /
   enterprise) are eligible for ICP filing.
2. Complete the ICP filing through the Alibaba Cloud ICP Filing System
   (beian.aliyun.com) for a mainland region; filing typically takes days to
   weeks depending on the province.
3. After the filing number is issued, bind the domain to the bucket
   (console: Bucket -> Settings -> Domain Names) and add the DNS CNAME
   record pointing at the bucket's extranet endpoint.
4. Re-run `static_website_diagnosis.py` to confirm the binding is visible
   via ListBucketCname and the site renders through the custom domain.

If the user cannot file the domain (no mainland entity), the practical
options are: move the website bucket to a region outside mainland China, or
serve the site from another platform — guidance only; this skill performs
no migration or write operation.

## 5. Frequently confused points

- Filing is attached to the DOMAIN + mainland serving, not to the bucket
  ACL or the hosting configuration.
- Enabling static website hosting does NOT remove the filing requirement.
- One filing covers the domain; subdomains of an already-filed top domain
  (e.g. www. after filing example.com) follow the filing provider's rules.
- The diagnosis cannot query the ICP filing status itself (no public OSS
  API exposes it); it reports the REQUIREMENT based on the bucket region and
  advises manual verification.
