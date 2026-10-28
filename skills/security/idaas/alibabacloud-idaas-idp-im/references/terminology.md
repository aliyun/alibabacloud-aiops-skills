# Terminology sourcing and official wording basis · reference

The main SKILL.md "Terminology mapping" table holds only **which term to use**; this file holds only **why that term** — verbatim official citations and the official docs' own inconsistencies. The same information is never duplicated in both places.

Source links are at the end of the main SKILL.md under "External authoritative sources": **DingTalk guide** = `bind-idaas-to-dingtalk-inbound`, **WeCom guide** = `bind-idaas-to-wecom`, **Feishu guide** = `binding-fly-book`.

## Per-term basis

- **sync destination organizational unit** ← the DingTalk/WeCom/Feishu guides all phrase it as `同步目标：…通讯录数据将会导入到 IDaaS 的这个节点之下` ("the contacts data will be imported under this IDaaS node"); the DingTalk guide's prose additionally uses `目标节点` ("different enterprise accounts sync to different target nodes, for separation").
- **auto-created login organizational unit** ← no such configuration-item name exists in the official docs. The field name `AutoCreateUserConfig.TargetOrganizationalUnitIds` comes from CLI metadata (`create-identity-provider --auto-create-user-config` and `set-identity-provider-authn-configuration --auto-create-user-config`); the current value can be read back via the hidden interface `GetIdentityProviderAuthnConfiguration` (`--force`) (see the hidden-interfaces section of idp-model-openapi.md). `GetIdentityProvider` does not return authentication config (key set not fixed) — read authentication config via the hidden interface above. Initial value `ou_root`.
- **source node (source side)** ← WeCom guide: `如果进行数据同步，可见范围将作为同步的来源节点` ("if data sync is performed, the visibility scope serves as the source nodes for sync"). The visibility scope is the **source-side starting point**, opposite in direction to the IDaaS-side `同步目标` — this is the easiest pair to configure backwards.
- **mapping identifier** ← the DingTalk and WeCom guides share the sentence: `您可以在字段映射中设置映射标识，使用 IDaaS 账户的某个字段…与源侧用户的某个字段…进行匹配，如果匹配成功，将绑定并覆盖更新；否则将创建 IDaaS 账户` ("you can set a mapping identifier in field mapping to match an IDaaS account field … against a source-side user field …; on a successful match it binds and overwrites/updates; otherwise it creates the IDaaS account"). **The Feishu guide does not use this term** — it says `字段映射 / 匹配规则` (field mapping / matching rules) — which is why the Feishu reference does not force this term in.
- **primary key everything depends on** ← both the WeCom and Feishu guides carry the sentence: `由于此字段是 IDaaS 能唯一依赖的主键，如果该字段被修改，将导致对应的 IDaaS 账户被删除并重新创建，请谨慎修改` ("since this field is the primary key IDaaS can uniquely depend on, modifying it will cause the corresponding IDaaS account to be deleted and recreated — change it with care"). ⚠️ It and the "mapping identifier" are **two different concepts**: the mapping identifier is the IDaaS-side matching mechanism; the primary key everything depends on is a property of the source-side field.
- **identity provider** ← all three guides consistently use `身份提供方`; **`身份源` never appears in the official docs**. The SKILL.md frontmatter keeps "identity sources" (English) only as a trigger phrase matching how administrators colloquially speak.
- **organizational unit / account** ← consistent across all three guides: the IDaaS-side object is `账户` (account), the directory tree is `组织 / 组织架构 / 节点` (organization / org structure / node); `用户 / 成员` (user / member) refers exclusively to the source side; **`机构` `部门` (institution / department) are not used for the IDaaS side** (`部门` department is a source-side concept).
- **Incremental sync cadence differs per type — never generalize** ← DingTalk = **real-time** (`钉钉通讯录有变动，可实时将变动数据同步到 IDaaS 中` — "when the DingTalk contacts change, the changes can be synced to IDaaS in real time"); Feishu = **off by default**, an event notification must be configured before it can be enabled; WeCom = **not supported** (`由于企业微信不支持查询增量数据，IDaaS 将于每日凌晨自动全量同步` — "since WeCom does not support querying incremental data, IDaaS automatically runs a full sync every day in the early morning").
- **`定时校验`** ← the WeCom and Feishu guides' help docs have this configuration item; **the DingTalk guide does not mention it**. But that is a **documentation coverage gap, not a capability gap**: both the Feishu and DingTalk (orgapp) IDPs return **`PeriodicSyncStatus` (default `disabled`) and `PeriodicSyncConfig`** from `get-identity-provider-ud-pull-configuration`. Whether the DingTalk console displays this item follows the console's actual wording.
- **`定时同步` (scheduled sync) is not a coined term — it is also official wording**: in the CLI metadata, `--periodic-sync-config`'s official Chinese name is `定时同步配置` (scheduled-sync configuration), and `--periodic-sync-status` is `定时校验状态` (scheduled-verification status). That is, the same capability is called `定时校验` on the console/help-doc side and `定时同步` on the OpenAPI-metadata side. This skill's prose still uniformly uses `定时校验` (aligned with what the administrator sees in the console), but this must not be used to deny the `PeriodicSync*` fields.

## Official self-inconsistencies / documentation gaps

When talking to the administrator, the console's actual wording and actual values always prevail.

- **The naming and behavior description of sync protection are inconsistent across the official guides themselves**: the WeCom guide says `同步保护能力…自动取消同步任务` ("sync protection capability … automatically cancels the sync job"), the Feishu guide says `系统内置保护机制…自动终止同步` ("built-in protection mechanism … automatically terminates the sync"), **and the DingTalk guide does not mention this mechanism at all**. This skill uniformly calls it "sync protection" and uniformly describes the behavior as "auto-aborts that sync job".
- **The threshold "> 30 accounts or > 10 OUs" is a default** (the `PullProtectedRule` of the Feishu / DingTalk (orgapp) IDPs: `UserDeletedThreshold` is 30 for both, `OrganizationalUnitDeletedThreshold` is 10 for both). The WeCom guide says it can be adjusted to enterprise size — meaning it is a **configurable item, not a fixed constant**; the value shown in the console's `同步保护设置` prevails.
- **auto-created login organizational unit**: no such configuration-item name exists in the official docs (see above).
- **The OpenAPI fields for sync cadence**: both the Feishu / DingTalk (orgapp) IDPs return `PeriodicSyncStatus` (default `disabled`) + `PeriodicSyncConfig{PeriodicSyncType:"time", PeriodicSyncTimes:[hours]}`, with differing hour values (`[4]` / `[3,5]`). The incremental switch is `IncrementalCallbackStatus` (DingTalk-console-created IDPs `enabled`, Feishu `disabled`, consistent with the official statements that DingTalk incremental sync is real-time and Feishu's is off by default).

## Official English wording of console labels

The English renderings used in this skill's parenthetical glosses follow the **official English help docs** on the international site (`www.alibabacloud.com/help/en/idaas/eiam/user-guide/...`), verified against the five EN guides (DingTalk inbound/outbound, WeCom, Feishu inbound/outbound). Verified mapping:

| Chinese label | Official English | Source guide |
|---|---|---|
| `身份提供方` | Identity Providers (menu); also "IdPs" | all guides |
| `其他身份提供方` | Other IdPs | WeCom / Feishu |
| `同步目标` | Sync Target ("destination node" in prose) / Synchronization target | DingTalk / Feishu |
| `增量同步` | Incremental Sync / Incremental synchronization | DingTalk / Feishu |
| `触发全量同步` | Trigger a full sync | DingTalk |
| `钉钉扫码登录` | DingTalk QR code logon | DingTalk |
| `扫码登录` | QR Code Logon / QR code logon | WeCom / Feishu |
| `网页授权登录` | Web Authorization Logon | WeCom |
| `高级配置` | Advanced Configuration | DingTalk |
| `映射标识` | mapping identifier (inbound) / Mapping Identity (outbound) | DingTalk |
| `字段映射` | Field Mapping / Field Mappings | all guides |
| `授权范围` | authorization scope | DingTalk |
| `可见范围` | Visible To | WeCom |
| `显示名称` | Display Name | WeCom / Feishu |
| `企业 ID` / `企业编号` | Enterprise ID | WeCom / Feishu |
| `可信域名` | Trusted Domain Name | WeCom |
| `自备域名` | Self-provided domain name | WeCom |
| `自定义域名` | Custom domain name | WeCom |
| `企业可信 IP` | Enterprise Trusted IP | WeCom |
| `授权回调域` | Authorization callback domain | WeCom |
| `定时校验` | Scheduled verification (Feishu) / Scheduled Synchronization (WeCom) — the EN guides split the same way the CN docs vs OpenAPI metadata do | Feishu / WeCom |
| `同步保护` | synchronization protection ("built-in synchronization protection feature") | WeCom |
| `来源节点` | "source node for data synchronization" | WeCom |
| `可访问的数据范围` | Accessible Data Range | Feishu |
| `重定向 URL` | Redirect URL | Feishu |
| `IP 白名单` | IP whitelist | Feishu |
| `应用主页` / `应用首页地址` | Application homepage / Application homepage URL | Feishu / DingTalk outbound |
| `通讯录管理` | Address Book Management (permission group on the DingTalk open platform) | DingTalk outbound |
| `出口IP` / `回调域名` | Server Outbound IP / Callback domain name | DingTalk outbound |
| Wizard steps | Step 1: Select features / Step 2: Scan to activate / Step 3: Scan to connect | DingTalk |
| `账户` / `组织` / `组织架构` / `节点` | Accounts / organizational units (the IDaaS-side directory tree) | descriptive — consistent with the EN guides' prose, not verified menu labels |
| `定时校验周期` | the period of the scheduled verification | descriptive |
| `同步保护设置` | synchronization protection settings | WeCom (descriptive variant of the official "synchronization protection") |

Notes:

- **"logon", not "login"** — the EN guides consistently use "QR code logon" for `扫码登录`; this skill's prose follows it.
- **No official English exists for** `快捷绑定` (quick binding — the EN guide just titles the wizard "Bind DingTalk"), `工作台免登` (workspace auto-login), the auto-created login organizational unit, and the individual DingTalk permission names (e.g. `通讯录个人信息读权限`) — glosses there are this skill's descriptive translations, not official labels.
- The EN console itself was not inspected (the accessible authority is the EN help docs); if a term above ever disagrees with what the administrator's console actually shows, the console prevails (hard boundary 6).
