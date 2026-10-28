# WeCom identity provider (IDP) onboarding · reference

This file carries the S0–S8 skeleton of the main SKILL.md and covers only the WeCom-specific fields, source-side steps, and pitfalls. WeCom has the **strictest network/domain prerequisites of the three types**.

**Set the direction first (S0; when unclear, guide the user to confirm — never default it)**: for inbound (pull, WeCom → IDaaS), read the sections from "Prerequisites" through "Sensitive-field sync" (including CLI assistance); for outbound (push, IDaaS → WeCom), read the "Outbound (push)" chapter. The two directions differ completely in source-side preparation, IDaaS configuration, and risk surface — **the biggest difference between outbound and inbound is the dual credentials** (one Secret suffices for inbound; outbound requires both Secrets).

## Prerequisites (fix these first — hard boundary 4)

| Prerequisite | Notes |
|---|---|
| Dedicated endpoint / dedicated public egress IP | IDaaS calls WeCom APIs through a dedicated public egress IP; if no dedicated endpoint is available, add one first. This IP depends on a NAT+EIP+SNAT chain (billable resources, built by the administrator) — see "Dedicated public egress IP prerequisites and NAE creation" below. |
| Trusted domain | The domain's owning entity must match the WeCom verified entity. The IDaaS instance's default domain (`*.aliyunidaas.com`) is rejected by WeCom (it flags the domain owner as a third-party ISV) — configure a domain owned by the enterprise entity in IDaaS first (`个性化 > 自定义域名`) before running this flow. |
| Domain type | `自备域名` (Self-provided domain name): supports only non-sensitive contacts sync + WeCom QR code logon; `自定义域名` (Custom domain name, IDaaS `个性化 > 自定义域名 > 添加`): additionally supports sensitive-field sync + WeCom Web Authorization Logon / workspace auto-login. |
| One trusted IP serves exactly one enterprise | An egress IP reused across multiple enterprises is classified by WeCom as an ISV scenario, making the contacts/identity-verification APIs unusable. |

## Dedicated public egress IP prerequisites and NAE creation

A "dedicated public egress IP" is not a single resource. The chain: **dedicated endpoint (NAE; dual vSwitch/dual ENI recommended) → internet NAT gateway in the same VPC + SNAT entry → EIP**. The value pasted into WeCom's `企业可信 IP` is **the address of the EIP bound to the NAT gateway** (console: `网络端点 > 专属公网出口 IP > 点击查看`). After changing or releasing the EIP, update the trusted IP on the WeCom side and re-run the connection verification — otherwise sync and verification both break.

- **Division of labor**: the NAE is created by this flow (console or `aliyun eiam create-network-access-endpoint`; in cli mode the skill can do it on the user's behalf); **NAT/EIP/SNAT are VPC billable resources and an administrator-side prerequisite — this skill never builds them on the user's behalf** — it only states the readiness conditions below; the chain itself is built by the administrator, or an existing egress is reused. Whether the chain works is judged by the network item of the connection verification (S4).
- **NAT/EIP/SNAT readiness conditions (confirm with the administrator before starting)**: an internet NAT gateway already exists in the same VPC, with an EIP bound to it and SNAT entries created (each `SourceCIDR` covers one of the NAE's vSwitch CIDRs, egress pointing to that EIP). Billing composition: the NAT gateway (LCU + instance fee) + the EIP (configuration fee + traffic fee) are pay-as-you-go resources — state this before starting; unsubscribing/releasing resources is the customer's operations decision and out of this skill's scope.
- **NAE creation essentials** (`aliyun eiam create-network-access-endpoint`): the name accepts ASCII only (Chinese triggers `InvalidParameter.NetworkAccessEndpointName`); `--vswitchids` is mandatory — omitting it creates an empty endpoint with no ENI (running but no egress IP; the only fix is to delete and recreate); the dedicated-endpoint quota per instance is 1 (exceeding it reports `ExceedQuota.NetworkAccessEndpoint`). Some regions support only some availability zones (e.g. Hangzhou i/j/k); an existing vSwitch in the default VPC may not be in the list and a new one may be required; the official requirement is > 2 usable IPs — two vSwitches in different availability zones are recommended for resilience.

## Source side (WeCom admin backend `https://work.weixin.qq.com/wework_admin/frame#apps`)

1. **Create a self-built app**: `应用管理 > 应用 > 企业自建应用`. Configure the app logo / app name / app description / **`可见范围`** (the WeCom-side **source-side authorization scope**: determines which departments and members IDaaS can access; departments and members only — tags are not supported).
2. **Take the CorpID**: `我的企业 > 企业信息` → `企业 ID` (Enterprise ID, i.e. the Corp ID).
3. **Take the AgentId / Secret**: `应用管理 > <the self-built app>` → `AgentId` and the app `Secret` (click `查看` → confirm → fetch it from the WeCom team messages).
4. **Configure the trusted domain**: app detail page > `设置可信域名` → enter the trusted domain used for WeCom OAuth2 web authorization (the owning entity must match the WeCom verified enterprise; the protocol prefix/path are not part of the check — the domain itself must match) → complete the domain-ownership verification per WeCom's instructions.
5. **Configure the enterprise trusted IP**: app detail page > `企业可信 IP` → paste the IDaaS dedicated public egress IP.
6. **Configure the authorization callback domain**: app detail page > `设置企业微信授权登录 > Web 网页 > 设置授权回调域` → paste the `授权回调域` copied from the IDaaS binding wizard. When a custom domain is used, also configure `应用主页地址/网页` (the workspace auto-login entry; use the IDaaS custom domain).

## IDaaS-side binding

Entry: IDaaS console `https://yundun.console.aliyun.com/?p=idaas` → select the instance → **`身份提供方 > 其他身份提供方 > 企业微信`**. (Add a dedicated endpoint first if none is available.)

- **Basic information**: `显示名称` (Display Name, chosen by the administrator), `企业 ID` (Enterprise ID, the WeCom CorpID).
- **App information**: `AgentId`, `Secret` (the self-built app's Secret, filled by the administrator; the OpenAPI write maps to `--we-com-config CorpSecret=…` — the same single Secret).
- **Development information**: `可信域名` (Trusted Domain Name; same value as WeCom), `域名类型` (self-provided/custom), `企业可信 IP` (Enterprise Trusted IP; select the dedicated-endpoint egress IP), `授权回调域` (Authorization callback domain; same as WeCom) → next.
- **Permissions/visibility scope**: confirm the WeCom app's `可见范围` (Visible To; official wording: it `将作为同步的来源节点` — "will serve as the source nodes of the sync"; it is the WeCom-side starting point, opposite in direction to the IDaaS-side `同步目标`; departments + members only).
- **Choosing scenarios**:
  - Sync: `同步目标` (**sync destination organizational unit**), `定时校验` (WeCom **does not support incremental sync** → IDaaS automatically runs a full sync every day in the early morning; a full sync can also be triggered manually); **sync protection**: deleting > 30 accounts or > 10 organizational units in one run auto-aborts that sync job (threshold tunable to enterprise size). `映射标识`: e.g. WeCom `userid` → IDaaS account name; a hit binds and overwrites/updates, a miss creates a new account.
  - `扫码登录` (QR code logon): once enabled, a WeCom QR code logon method appears in the IDaaS login menu and is usable immediately.
  - `网页授权登录` (Web Authorization Logon): enabled by default with a custom domain; supports workspace auto-login + sensitive-data sync after user authorization.
- **Field mapping**: users (`userid` is the **primary key everything depends on** for IDaaS; name/alias → display name; phone/email → sensitive fields requiring user authorization) + departments (department name → organizational-unit name; department ID/hierarchy → organizational-unit identifier/parent unit).

## QR code logon consistency (the most common pitfall)

The following three must be **exactly identical**, otherwise the QR code logon redirect fails:
```
IDaaS EIAM login-page domain = IDaaS WeCom IDP authorization callback domain = WeCom app authorization callback domain
```
With a custom domain the recommendation is: set it as the default domain + enable auto-redirect + use the same custom domain for both the IDaaS and WeCom callbacks.

## Sensitive-field sync (phone/email etc.)

- Sensitive fields: avatar/gender/phone/email/enterprise email/personal QR code/address.
- Since 2022-06-20 20:00, apart from contacts sync, WeCom APIs no longer return these fields unless the user explicitly authorizes via WeCom OAuth2.0.
- Sync condition: the user enters IDaaS from the WeCom environment → manually consents on the authorization page → IDaaS uses the WeCom phone number as the account phone and the enterprise email as the account email (personal email if there is no enterprise email).
- Admin side: WeCom `我的企业 > 通讯录管理 > 成员资料显示` must allow displaying phone/email etc. Within 30 days after authorization the consent page is not shown again; users can change it in the app detail page under `个人敏感信息授权管理`.

## Outbound (push, IDaaS → WeCom)

Push IDaaS-side organizations/accounts **into the WeCom contacts**. The data flow is the reverse of inbound and the risk surface reverses too (hard boundary 3): it writes **WeCom-side data** — a match-key hit means **overwrite-update** (fields such as name get rewritten with IDaaS values), and `UdPushConfig` has no counterpart to `PullProtectedRule` — no deletion protection exists — so a small-scope trial run isolated in a dedicated department/test enterprise is mandatory, verified before opening up; pushed changes **are not rolled back when the IDP is deleted**. In S0 confirm with the user which of the sync/authentication dimensions to do (the outbound app is simultaneously registered as an authentication source, created with `AuthnStatus=enabled`; when doing sync only, the creation recipe explicitly passes `--authn-config AuthnStatus=disabled`).

### Source-side preparation (dual credentials + trusted IPs in two places)

The biggest difference between outbound and inbound is the **dual credentials — both Secrets are required**, each validated live at creation (corpSecret+AgentId exchanged for a token with the visibility scope checked non-empty; contactSecret exchanged for a token separately):

1. **Self-built app credential (corpSecret)**: create the app, take the CorpID/AgentId/Secret, **configure the egress IP in the self-built app's `企业可信 IP`** — same as inbound "Source side" steps 1/2/3/5. The push's write operations go through the contacts credential, but reading member/department details goes through the app credential, so this chain is still required.
2. **Contacts-sync credential (contactSecret)**: the card at **`安全与管理 → 管理工具 → 通讯录管理分组 → 通讯录同步`** in the WeCom admin backend's left sidebar (not under `我的企业`): change the permission to **`读取并编辑通讯录`** (read-only by default), set the **writable scope** (it must cover the target department), view the `Secret`, and configure the **enterprise trusted IP** (⚠️ an independent configuration item — it and the self-built app's trusted IP are **two locations; the same egress IP must be configured in both**).
3. **Network endpoint**: same as inbound — an NAE is required (`--network-access-endpoint-id`); for the egress-IP chain prerequisites see "Dedicated public egress IP prerequisites and NAE creation" above.
4. **Target department**: the push needs a WeCom-side department ID as the `TargetScope` (the root department ID is `1`); a dedicated isolated department is recommended, and the contacts-sync `可写范围` must cover it, otherwise write operations are rejected.
5. **For QR code logon, additionally configure**: trusted domain + authorization callback domain (same as inbound "Source side" steps 4/6; the three-domain-identity rule is in "QR code logon consistency").

Troubleshooting error-code triage: `301042`/`60020` = trusted IP not allowed (check both trusted-IP locations against the **current** egress IP — the egress segment can change); `60011`/`48002` = insufficient contacts write permission (check `读取并编辑通讯录` + the writable scope); `46004` = person not found; `60129` = see the dedicated section below. Use `department/simplelist` as the connectivity probe (`department/get`/`department/list` have been forbidden for IPs newly added by contacts sync since 2022-08-15).

### Creating the outbound IDP on the IDaaS side

The `create-identity-provider` recipe is the same as inbound (kebab plugin form with `Key=Value` object parameters; see step 1 of the write path in `idp-model-openapi.md`), with three differences:

- **Type URN**: `urn:alibaba:idaas:idp:tencent:wecom:push` (not in the official IdentityProviderType enumeration, but usable as a creation input — the enumeration is incomplete, match by prefix; see `idp-model-openapi.md`).
- **Dual credentials**: both `--we-com-config CorpSecret=…` (self-built app) and `--we-com-config ContactSecret=…` (contacts sync) are **required**; `CorpId`/`AgentId` as usual under the same object flag, and `TrustableDomain`/`AuthorizeCallbackDomain` (plus `--network-access-endpoint-id`) are recommended to match inbound. At creation, IDaaS calls WeCom live to validate both Secrets — either one being wrong fails the creation.
- **The scope configuration goes through `UdSyncScopeConfigs` (an array)**, structurally different from pull's single-object `UdSyncScopeConfig`:
  ```text
  --ud-push-config "UdSyncScopeConfigs[0].SourceScopes[0]=<IDaaS organizational unit ID>" \
  --ud-push-config "UdSyncScopeConfigs[0].TargetScope=<WeCom department ID>"
  ```
  Semantics = push the IDaaS organizations/accounts under `SourceScopes` into the WeCom department `TargetScope`; multiple mappings can be configured. Configuring SourceScopes with an empty TargetScope errors out. Creation sets `UdPushStatus=enabled`; to change the scope later use `set-identity-provider-ud-push-configuration` (the scope parameters take a JSON list and `--incremental-callback-status` is mandatory — the same shape as the Feishu push; see `idp-model-openapi.md`).

### Field mapping and match key (direction reversed)

- **Default mapping direction reversed**: `user.* → idpUser.*` (opposite of inbound — the source is the IDaaS account, the target is the WeCom member), 5 entries: `user.username→idpUser.userid`, `user.displayName→idpUser.name`, `ExtractPhoneNumber(user.phoneNumber)→idpUser.mobile`, `user.phoneRegion→idpUser.state_code`, `user.email→idpUser.email` (written transactionally at creation; read back and verify with the hidden interface `GetIdentityProviderUserProfileMapping`).
- **Default match key `idpUser.userid`** (candidates `userid`/`mobile`/`email`; unlike the DingTalk push default of mobile). Match semantics: the IDaaS account is reverse-looked-up against existing WeCom members by userId → mobile (in `+<region code>` form) → email (enterprise email first, personal email as fallback), in that priority order; if every lookup fails, it is handled as a create. The mapping identifier is changeable; after a change, existing members are re-claimed under the new identifier, with a risk of misjudged creates. ⚠️ **Phone/email reverse lookups are quota-limited**: once erroneous queries exceed 20% of the enterprise headcount, the API cannot be called for 1 day — do not repeatedly trial-push large numbers of wrong numbers.
- **Default department mapping identifier `idpOrganizationalUnit.name`** (name is the only candidate): matches existing WeCom departments by the `(parentId, name)` pair.

### Triggering the push and verifying

- Triggering is the same as main SKILL.md S7: pass the S6 gate first (mapping table + match key shown to the user for **explicit confirmation** — keeping the defaults is no exception); `run-synchronization-job --instance-id … --target-type identity_provider --target-id <push_idp_id>` (the trigger requires explicit user confirmation) → follow up with `get-synchronization-job` (kebab-case parameters; `--synchronization-job-id` is mandatory).
- **Statistics buckets are named by operation type (`Created`/`Updated`), unlike the DingTalk/Feishu `Binded` system**: creates land in `Created`, overwrite-updates land in `Updated`; **the binding is established on the first push's `Created`**, and subsequent full syncs automatically take the overwrite-update path — changing a value on the IDaaS side rewrites the WeCom-side field, a direct manifestation of the overwrite-update risk surface.
- **A full push does not delete WeCom-side users** (deletion goes only through the incremental-event path); department changes are carried by the update's `parentid`/`main_department`/`department` fields. `mobile`/`email`/`biz_mail`/`telephone`/`address` are WeCom fields that **cannot be read back** — when they hit a mapping, every full-sync round sends them in full; that is expected behavior, not an anomaly.
- ⚠️ **The CLI sync-job interface returns only a wrapper-level error**: when the whole final round of user records fails, the job reports only `ALL_USER_EXECUTE_FAILED: all wecom user records in final round failed, count:N` — **the underlying WeCom error codes must be taken from the console's job-detail page** (`generate-download-url-for-synchronization-job` does not support identity_provider-type jobs, so no per-row detail can be obtained).
- Verification focuses on the WeCom side: the target department's member list and field comparison of pushed members (name/phone etc.); outbound does not modify IDaaS-side accounts.

### Pitfall: 60129 missing mobile or email (WeCom hard validation on member creation)

WeCom member creation **hard-requires at least one of phone/email** (used for the activation invite) — when an IDaaS account has neither, the first push of that user necessarily fails with `WeComError.60129 missing mobile or email`. Backfill a phone number on the IDaaS account first, then re-push:

```bash
aliyun eiam update-user --profile <p> --instance-id <InstanceId> --user-id <user_id> \
  --phone-number 13800000001 --phone-region 86 --phone-number-verified true
```

`--phone-region` takes `86` (no `+`/`00` prefix); setting a phone number requires simultaneously setting `--phone-number-verified true`; WeCom validates format only, so a fake test number passes. 60129 belongs to WeCom's business-validation layer — seeing it means both trusted-IP locations and the contacts write permission already pass (otherwise 301042/60020/60011/48002 would appear first).

### Authentication dimension (optional: QR code logon)

The outbound app is simultaneously registered as an OIDC authentication source: created with `AuthnStatus=enabled`, the WeCom QR-code method appears on the login page by default (explicitly disable it when doing sync only — see the chapter head). The same corpSecret+AgentId carries the OAuth chain, and the source-side prerequisites are the same as inbound QR code logon: trusted domain + authorization callback domain identical across the three locations (see "QR code logon consistency") and the logging-in user must be inside the self-built app's **`可见范围`**. Difference from inbound: **manual binding only** (account binding `mappingBinding` is on from creation; auto-match/auto-create/auto-update are permanently off — passing enabled values to the Set interface reports `WECOM_PUSH_AUTO_AUTHN_CONFIG_UNSUPPORTED`); WeCom cannot be the sole login method. Only a live manual QR code logon test in S7 counts as the authentication dimension achieved.

## CLI assistance (cli mode)

Tools: `wecom-cli` (source side) + `aliyun` (IDaaS side); for installation/auth see `cli-tooling.md`.

- **Tell the user honestly: WeCom in cli mode is inevitably a hybrid**. `wecom-cli` **has no app-management capability** (check `wecom-cli --help` for the live truth): creating self-built apps, taking AgentId/Secret, configuring trusted domains/enterprise trusted IPs/authorization callback domains, and setting the visibility scope are all unsupported → all six "Source side" steps above **fall back to manual** (declared per step, never silent).
- `wecom-cli`'s actual use in this flow: **source-side data verification** — search members by name/pinyin/alias and fetch basic member info, used for step ① of the root-cause check when "sync count is zero / fields are empty" (does this person actually exist within the source-side visibility scope).
- The IDaaS side is fully CLI-capable: `aliyun eiam create-identity-provider` (**object parameters as `Key=Value` pairs**: `--we-com-config CorpId=… CorpSecret=… …`; nested JSON is rejected by the server — recipe in the `idp-model-openapi.md` write path). Secrets cannot be obtained via CLI → placeholder templates filled locally by the user, or manual console entry (credential transfer principle 2 in `cli-tooling.md`).
- NAE creation is also in the IDaaS-side CLI scope (`create-network-access-endpoint`; command and pitfalls in "Dedicated public egress IP prerequisites and NAE creation" above); **NAT/EIP/SNAT are never built on the user's behalf** — the NAT chain and vSwitch readiness are administrator-side prerequisites; when not ready, state the conditions and wait for the administrator to configure them before continuing; never execute the VPC-side creation in their place.
- The complete IDaaS-side write path is in `idp-model-openapi.md` ("The IDaaS-side write path for CLI mode"); the initial full sync uses `run-synchronization-job` (requires user confirmation). The conclusions that WeCom does not support incremental sync and that a full sync runs automatically every early morning hold unchanged in cli mode.
- **CLI correspondence of the outbound (push) steps**: see the "Outbound (push)" chapter above — the source-side contacts-sync Secret/permissions/two trusted-IP locations all live in the WeCom admin backend (manual; `wecom-cli` has no such capability); on the IDaaS side, creation via `create-identity-provider` (URN `...:tencent:wecom:push` + **dual Secrets** + the `--ud-push-config "UdSyncScopeConfigs[0].*"` bracket array — both Secrets go through placeholder templates/temp files, never through the conversation); scope changes via `set-identity-provider-ud-push-configuration` (JSON-list shape); mapping and match key via the same hidden-interface pair (a default match key `idpUser.userid` ships out of the box); trigger and verification as in S7; the underlying WeCom error codes for push failures come from the console's job-detail page (the CLI job interface gives only wrapper-level errors).
- Still manual: the scan/interactive flows of WeCom credential configuration, and the authentication-dimension live QR code logon test (S7).

## Pitfalls and reminders

- `userid` is the **primary key everything depends on** for IDaaS; modifying it causes the corresponding IDaaS account to be **deleted and recreated** — change it with care (hard boundary 3).
- WeCom **does not support incremental sync** → only two sync cadences exist, `每日凌晨全量` (daily early-morning full sync) + manual full sync; never promise customers "real-time incremental".
- Secrets/trusted IPs/callback domains are filled and configured by the administrator; the skill never requests plaintext and never fills them in on their behalf (hard boundaries 1 and 2).
- **Inbound** needs only one Secret: the OpenAPI write passes `--we-com-config CorpSecret=…` (i.e. the self-built app's `Secret`). The metadata's `ContactSecret` field (the CLI nested-shape parameter name is `--we-com-config`, not `--wecom-config`) need not be provided — omitting it affects nothing in creation, connection verification, sync, or QR code logon. **This does not apply to outbound** — both Secrets are required there; see the "Outbound (push)" chapter.
