# Feishu / Lark identity provider (IDP) onboarding · reference

This file carries the S0–S8 skeleton of the main SKILL.md and covers only the Feishu-specific fields, permission scopes, event callbacks, and pitfalls. (Feishu and international Lark are two separate documentation sets; this file is about Feishu.)

**Set the direction first (S0; when unclear, guide the user to confirm — never default it)**: for inbound (pull, Feishu → IDaaS), read the sections from "Source side" through "Field mapping" (including CLI assistance); for outbound (push, IDaaS → Feishu), read the "Outbound (push)" chapter. The two directions differ completely in source-side preparation, IDaaS configuration, and risk surface.

The IDaaS binding wizard has four steps: **App permission configuration → Development configuration → Choosing scenarios → Field mapping**. Entry point: `身份提供方 > 其他身份提供方 > 飞书`.

## Source side (Feishu Open Platform, enterprise self-built app)

1. Create an **enterprise self-built app** and enter the app detail page.
2. Take `App ID` and `App Secret` from **`凭证与基础信息`** (backfill into IDaaS).
3. Under **`权限管理 > 开通权限`**, switch to `应用身份权限 tenant_access_token`, select `通讯录` on the left, and tick the scopes:

| Permission | scope | Necessity |
|---|---|---|
| Get basic contacts information | `contact:contact.base:readonly` | Required |
| Get user user ID | `contact:user.employee_id:readonly` | Required |
| Get basic department information | `contact:department.base:readonly` | Required |
| Get contacts department organizational structure information | `contact:department.organize:readonly` | Requires release + administrator approval |
| Get basic user information | `contact:user.base:readonly` | Required |
| Get user organizational structure information | `contact:user.department:readonly` | Requires release + administrator approval |
| Get user email information | `contact:user.email:readonly` | Optional (tick only if email must be synced) |
| Get user phone number | `contact:user.phone:readonly` | Optional; requires release + administrator approval |
| Get user employment information | `contact:user.employee:readonly` | Optional (enterprise email); requires release + administrator approval |

The first six are required for core sync + login; email/phone/employee are on demand. Some permissions require **submitting a release request → review by an administrator in the Feishu admin console**.

> Step 1 of the IDaaS binding wizard, `应用权限配置`, lists a permission checklist of **9 items including this row** (each carrying `需要审核 / 非必需` tags); the S4 verification checks against that list item by item, and **the list shown in the console is authoritative**. Also: the default field mapping has **no target field for enterprise email** — even with `employee` ticked, enterprise email is not synced out.

4. **`可访问的数据范围`** (Accessible Data Range — the **source-side authorization scope** on the Feishu side): `权限管理 > 可访问的数据范围` > choose `与应用的可用范围一致` > `保存`. (This determines which Feishu users/departments can be synced and can log in.)
5. Return to IDaaS and click `下一步`; IDaaS verifies the API permissions and the data permissions, letting you through only when all are present.

## Development configuration (IDaaS ↔ Feishu, two-way backfill)

- Fill in on the IDaaS side: `显示名称` (Display Name), `企业编号` (Enterprise ID, at `飞书管理后台 > 企业管理 > 企业概览`, below the enterprise name, starting with `FE`).
- **Redirect URL**: copy the two URLs from the IDaaS `开发信息` page → paste them under `添加` in the Feishu app's `安全设置 > 重定向 URL`.
- **App homepage** (configure only when workspace auto-login is wanted): copy the `应用主页` URL from IDaaS → in Feishu under `添加应用能力 > 网页应用`, fill `桌面端主页`/`移动端主页` with that URL; for the open method `在飞书内新标签页打开` is recommended → `保存`.
- **IP allowlist** (optional, when source IPs must be restricted): in IDaaS choose shared endpoint/dedicated endpoint → expand the egress IPs → copy them in the Feishu format → paste them under `应用安全设置 > IP 白名单 > 批量修改` in Feishu.

Data directions: Feishu → IDaaS = App ID / App Secret / enterprise number / Encrypt Key / Verification Token; IDaaS → Feishu = redirect URL / app homepage / egress IPs / event request URL.

## Choosing scenarios (sync + authentication)

- **Sync**: `同步目标` (**sync destination organizational unit**), `定时校验` (**off by default in the wizard**, i.e. `PeriodicSyncStatus=disabled`: unless it is enabled manually or a sync is triggered manually, it **never syncs**; once enabled it defaults to a full sync every day in the early morning, `PeriodicSyncConfig={PeriodicSyncType:"time", PeriodicSyncTimes:[4]}`. **This field is not Feishu-specific** — the DingTalk (orgapp) IDP also returns `PeriodicSyncStatus`, likewise `disabled`), `定时校验周期` (defaults to daily; customizable with Cron). Matching relies on the field mapping (e.g. IDaaS account name ↔ Feishu `userid`): a hit binds and updates, a miss creates a new account; **sync protection**: a run that would delete > 30 accounts or > 10 organizational units auto-aborts that sync run. (The official Feishu documentation does not use the term "mapping identifier"; it says `字段映射 / 匹配规则` — see the terminology reference.)
- **Incremental sync** (off by default; turn it on manually after binding): in IDaaS, under `身份提供方 > 目标应用 > 修改 > 事件配置`, fill in `Encrypt Key` and `Verification Token` (taken from Feishu's `事件与回调 > 加密策略`) → IDaaS displays the `请求地址` → copy it into Feishu's `事件与回调 > 事件配置`, choose `将事件发送至开发者服务器` as the subscription method, and paste the request URL. Subscribe to these events:
  ```
  contact.department.created_v3 / deleted_v3 / updated_v3
  contact.user.created_v3 / deleted_v3 / updated_v3
  contact.scope.updated_v3
  ```
- **Authentication**: `扫码登录` (once enabled, Feishu QR code logon appears on the IDaaS login page and can log users into IDaaS and its managed apps); with the app homepage configured, workspace auto-login into IDaaS from the Feishu workspace is also supported.

## Field mapping

- Scenarios that need mapping: IDaaS already has accounts/organizational units; Feishu members/departments must be bound to existing accounts; IDaaS account fields must be filled from Feishu fields.
- Key fields: Feishu `userid` (**the primary key everything depends on**) ↔ IDaaS account fields; Feishu department attributes ↔ IDaaS organizational unit fields.
- **Factory default mapping**: `idpUser.user_id→user.username` (mapped to `username`, i.e. **the primary key everything depends on**), `idpUser.name→user.displayName`, `ExtractPhoneRegion(idpUser.mobile)→user.phoneRegion`, `ExtractPhoneNumber(idpUser.mobile)→user.phoneNumber`, `idpUser.email→user.email`; **no target field for enterprise email**.

## Outbound (push, IDaaS → Feishu)

The reverse of inbound: **IDaaS-side organizational units/accounts are pushed into the Feishu contacts**. The data flow is reversed, and so is the risk surface — **what gets written is Feishu-side data** (zero changes to IDaaS-side accounts), and `UdPushConfig` has no counterpart to `PullProtectedRule`, i.e. **no deletion-protection fallback** (main SKILL.md hard boundary 3). **For both dimensions, confirm with the user at S0 which ones to do**: sync push is the primary outbound scenario; **QR code logon is equally available** — the outbound app is simultaneously registered as an OIDC authentication source (created with `AuthnStatus=enabled`; the Feishu QR-code method appears on the login page by default), letting users scan the same app's code with Feishu to log into IDaaS; see the "Authentication dimension" section below for the configuration. Official documentation: bind IDaaS to Feishu (outbound) `https://help.aliyun.com/zh/idaas/eiam/user-guide/bind-feishu-outbound`.

**A small-scope trial run must come first**: shrink `SourceScopes` to a dedicated test OU, point `TargetScope` at an isolated test department, and open up to the production organizational units only after the push behavior checks out — already-pushed changes **do not roll back when the IDP is deleted**.

### Source side (Feishu) preparation

1. **Create an enterprise self-built app**: same as steps 1–2 of the inbound "Source side" section (App ID / App Secret / enterprise number; the AppSecret cannot be exported in plaintext — inject it via a temporary file; see the "CLI assistance" section).
2. **Permissions**: tick them under `权限管理 > 开通权限 > 切到『应用身份权限 tenant_access_token』` — the core write scope `contact:contact` (contacts read/write; outbound writes to contacts through it) plus the read scopes from the inbound list, ticked the same way (`contact:contact.base:readonly` / `contact:user.base:readonly` / `contact:department.base:readonly` / `contact:user.id:readonly`, etc.); submit the release and wait for administrator approval to take effect (release rules as in inbound). Being able to create a department with the same app identity = the write-permission chain suffices to support IDaaS pushes (IDaaS uses the same set of credentials).
3. **Data scope** (`可访问的数据范围`) must cover the target department; `全部成员` is recommended — when the data scope does not include the department, bot calls to the department APIs fail with `40004 no dept authority`.
4. **Create the target department** (the push needs a Feishu-side department as `TargetScope`; a dedicated, isolated department is recommended):
   ```bash
   lark-cli api POST /open-apis/contact/v3/departments --as bot \
     --data '{"name":"<部门名>","parent_department_id":"0"}'
   ```
   Two pitfalls: ① the path has **no `/create` suffix** (`/open-apis/contact/v3/departments/create` returns 404); ② the body field is `parent_department_id` (not `parent_id`), with `"0"` for the root department. The response carries two IDs — **record the `department_id`, not the `open_department_id`** (the reason is in the next section).

### ⚠️ TargetScope must be a custom department_id

On the IDaaS side, Feishu department operations are always located by the **custom `department_id`** (e.g. `e89g6a382g2e724c`), and `TargetScope` must be filled with it — **never with `open_department_id` (the `od-` prefix)**. Note that `department_id_type` in lark-cli / the native Feishu APIs **defaults to `open_department_id`**: interfaces such as scopes return the `od-` format when called directly — **do not copy that straight into the IDaaS configuration**; read back the `department_id` field value via `GET /open-apis/contact/v3/departments/:department_id` (or from the create-department response). Symptoms of filling it wrong: IDP creation **does not error** (creation does not validate department existence); the error surfaces only when the push is triggered: `OperationFailed.SynchronizationJob.PushTargetNotExist: Target identity provider was not exist node:od-…`. When listing a department's members or changing a member's department affiliation by the custom ID, the Feishu API must be passed `department_id_type=department_id` explicitly (the default `od-`-based lookup returns empty).

### Creating the outbound IDP on the IDaaS side

The `create-identity-provider` recipe is the same as the inbound "cli-mode recipe and API chain" section (kebab plugin form with `Key=Value` object parameters; for the full recipe see step 1 of the IDaaS-side write path for CLI mode in `idp-model-openapi.md`), with three differences:

- **Type URN**: `urn:alibaba:idaas:idp:bytedance:lark:push`.
- **Scope configuration goes through `UdSyncScopeConfigs` (an array)**, a different structure from pull's single-object `UdSyncScopeConfig`:
  ```text
  --ud-push-config "UdSyncScopeConfigs[0].SourceScopes[0]=<IDaaS organizational unit ID>"
  --ud-push-config "UdSyncScopeConfigs[0].TargetScope=<Feishu department_id>"
  ```
  Semantics = the IDaaS organizational units/accounts under `SourceScopes` are pushed under the Feishu `TargetScope` department; the array can hold multiple "IDaaS organizational unit → Feishu department" mappings.
- **Credentials**: `--lark-config AppId=…` / `AppSecret=…` / `EnterpriseNumber=…` — all three required (EncryptKey/VerificationToken optional). Creation calls Feishu in real time to fetch the token and the authorization scope — wrong credentials fail with `LarkError.CredentialError ... 10014 app secret invalid`. `UdPushStatus=enabled` upon creation.

Changing scopes / the incremental switch: `set-identity-provider-ud-push-configuration`; ⚠️ **the CLI shape differs from Create** — flattened dot-notation is not recognized (`--UdSyncScopeConfigs.1.SourceScopes.1` fails with unknown flag); the scope parameter must be passed as a **JSON list**: `--ud-sync-scope-configs '[{"SourceScopes":["ou_…"],"TargetScope":"<department_id>"}]'`; `--incremental-callback-status` is mandatory (the same trap as the pull-side set).

### Field mapping and match key (direction reversal + ⚠️ no default match key)

- **Default mapping direction reversed**: `user.* → idpUser.*` (username→user_id, displayName→name, email→email, `IIF(IsPresent(user.phoneRegion), Append("+", user.phoneRegion, user.phoneNumber), user.phoneNumber)`→mobile, phoneRegion→phoneRegion) — the reverse of inbound (`idpUser.* → user.*`): the source is the IDaaS account and the target is the Feishu member. The mobile entry is **expression-typed** and yields the international format with the `+` prefix (e.g. `+8613800138000`).
- **⚠️ Feishu push ships with no default match key** (unlike the DingTalk push default of `idpUser.mobile`): after creation, the `GetIdentityProviderUserProfileMapping` response contains **no `UserMappingIdentityName`** — without an explicit Set, every push handles each account as a **create**, so a repeated full push = duplicated Feishu members. **After creation you must explicitly Set the match key**: `SetIdentityProviderUserProfileMapping --UserMappingIdentityName=idpUser.mobile` (the official documentation recommends the phone number, which is unique in Feishu; candidate fields usable as the match key = `idpUser.user_id` / `idpUser.email` / `idpUser.mobile`). Set is an overwriting, full write — **you must carry every mapping entry** (Get it back first and carry the entries unchanged when modifying); anything omitted is lost (for the general pitfall that omitting `--UserMappingIdentityName` clears it, see the hidden-interface block in `idp-model-openapi.md`).

### Triggering the push and verifying

- Triggering follows the main SKILL.md S7: pass the S6 gate first — present the mapping table and the match key to the user for **explicit confirmation** (no exception even when the factory defaults are kept); you must not trigger until it is confirmed; `run-synchronization-job --instance-id … --target-type identity_provider --target-id <push_idp_id>` (the trigger itself likewise requires explicit user confirmation) → follow up with `get-synchronization-job`.
- Job statistics: match hits land in the **`Binded`** bucket, creates in the `Created` bucket (unlike the inbound Created/Same scheme); the job record has only the aggregate numbers, with no per-item failure reasons.
- **Departments are appended, not replaced**: the push adds members to the target department but **does not move them out** of their existing Feishu departments (zero disruption to existing affiliations — additions only, no removals) — do not run acceptance against the expectation that "overwrite-update = department takeover".
- Outbound does not modify IDaaS-side accounts; verification centers on the Feishu side: the target department's member list (pass `department_id_type` in the query), field comparison of the matched members, and the data integrity of the other departments.
- **Pushed changes do not roll back**: deleting the IDP will not restore the Feishu-side fields already overwritten (name etc.) — cleanup must be done by hand: restore/modify member profiles via `PATCH /open-apis/contact/v3/users/:user_id` (for department-type parameters, likewise mind `department_id_type`); delete a department via `DELETE /open-apis/contact/v3/departments/:department_id`, moving the members out first when it still contains any.

### Authentication dimension (optional: QR code logon)

The outbound app shares **the same App ID/App Secret and OAuth flow** as inbound; the contacts scopes already enabled on the source side for sync are enough to carry the login chain — **the only source-side configuration that must be added is the redirect URL backfill**. When S0 locks in sync only, skip this section; it is also recommended to explicitly pass `--authn-config AuthnStatus=disabled` when creating the IDP to turn off the login entry (the default is `enabled`, which puts the Feishu QR-code method on the login page).

- **Backfill the redirect URL on the Feishu side (hard prerequisite)**: the callback URL from the IDaaS `身份提供方` details, `https://<IDaaS登录域名>/login/common/oauth2/callback` → add it in the Feishu developer console under `安全设置 > 重定向 URL`. Every login domain in use must be added (when a custom domain and the default domain are both in use, add both). This sits on the Feishu management plane and **is console-configurable only** (no OpenAPI/CLI write path; see the S3 item in "CLI assistance"); **it takes effect on save, no release approval required**.
- **Symptoms and diagnosis when the configuration is missing**: after Feishu QR-code is chosen on the IDaaS login page, the QR-code page reports `错误码 4401 该应用暂不可用，请联系应用开发者`. Use the probe to locate the root cause (faster than submitting a log ID to support):
  ```bash
  curl -sL --connect-timeout 10 --max-time 30 "https://open.feishu.cn/open-apis/authen/v1/index?app_id=<AppID>&redirect_uri=<URL编码后的回调URL>"
  ```
  Landing on accounts.feishu.cn with `"code":20029, "message":"redirect_uri 请求不合法"` = the Feishu-side redirect URLs do not include this callback; when it is configured correctly, the call returns the normal QR-code page HTML.
- **S7 manual live login test**: choose Feishu QR-code on the login page → scan and confirm with the Feishu App → log into IDaaS as the corresponding Feishu member. Being able to push (the app-identity chain) does not equal being able to log in (the OAuth chain) — accept the two dimensions separately; when `登录自动创建账户` is enabled, the main SKILL.md S5 rule "login auto-created nodes align with the sync-source organization" applies equally.

## CLI assistance (cli mode)

Tools: `lark-cli` (source side) + `aliyun` (IDaaS side); for installation/authentication/output contract (judge success/failure by `ok` and the exit code, not by `code`) see `cli-tooling.md`.

- **Create the app**: `lark-cli config init` (`--new`) outputs an authorization link that **the user must complete once in a browser** — it is not headless; in cli mode this step is "CLI initiates + human in the browser".
- **S4 permissions (⚠️ `auth login` ≠ the permissions sync needs)**: Feishu has two identity types and S4 must tell them apart — **QR code logon authentication runs on `用户身份 user_access_token`**, which is exactly what `lark-cli auth login --scope <scope>` grants; **account sync runs on `应用身份 tenant_access_token` (App ID + App Secret)**, whereas the scopes granted by `auth login` attach only to the user identity — the tenant identity reading contacts fails with `99991672 has not applied for the required scope(s)` (even when the scope is already inside a released version). **App-identity scopes cannot be granted through any CLI/public OpenAPI** (an app cannot use its own access_token to grant itself more permissions = security by design); they must be ticked item by item in the developer console under `权限管理 > 开通权限 > 切到『应用身份权限 tenant_access_token』页 > 通讯录` (publishing the sensitive items phone/email/employee_id may trigger enterprise-administrator approval). Therefore `auth check --scope` exit 0 **only proves the user identity holds the permissions and cannot serve as the sync-side S4 gate**; the sync-side gate is passed only when `lark-cli api ... --as bot` actually reads a real user's user_id/mobile successfully (for the pass criteria see the "cli-mode recipe and API chain" section below).
- **S3 backfill-type steps are console-only**: redirect URL / app homepage / IP allowlist / event request URL all sit on the Feishu **management plane** (developer console `安全设置` etc.) with **no public OpenAPI write interface**; `lark-cli` cannot change them (the `application` domain offers only slash-command CRUD, with no scope/version/security commands), and the `aliyun` CLI has even less reach (it serves the IDaaS side). In cli mode these spots always fall back to manual: the user fills them in by hand in the developer console. The callback URL rule = `https://<IDaaS登录域名>/login/common/oauth2/callback`.
- **Source-side data verification**: `lark-cli contact` searches users by name/email/phone number (step ① of the three-step root-cause check in the failure table).
- **The IDaaS side is all-CLI**: `aliyun eiam create-identity-provider` (**object parameters as `Key=Value` pairs** such as `--lark-config AppId=…` / `AppSecret=…`; nested JSON is rejected by the server side; the enterprise number is non-sensitive and may enter the conversation, while AppSecret/EncryptKey/VerificationToken go through placeholder templates and stay out of the conversation) → for the write path see "IDaaS-side write path for CLI mode" in `idp-model-openapi.md`.
- **When the AppSecret should not pass through CLI/temporary files → create the IDP in the console with manual pasting**: the Feishu AppSecret cannot be exported in plaintext from lark-cli (encrypted in the keychain, masked by `config show`); the plaintext exists only on the developer console's `凭证与基础信息` page. When the user does not want temporary-file injection, the safest route is **manual pasting in the console throughout**: copy the AppSecret in the developer console → paste it at the `应用凭证` step of the IDaaS console `身份提供方 > 其他身份提供方 > 飞书` binding wizard → IDaaS validates the permissions on the spot. The credential never passes through CLI/conversation; once created, sync/verification can still be run on the user's behalf back in cli mode. For step-by-step guidance see item 2a of "Credential transfer principles" in `cli-tooling.md`.
- **CLI counterparts of the outbound (push) steps**: see the "Outbound (push)" chapter above — create the target department with `lark-cli api POST /open-apis/contact/v3/departments --as bot`; create on the IDaaS side with `create-identity-provider` (URN `...:bytedance:lark:push` + the bracket-subscript `UdSyncScopeConfigs[0].*` array); change scopes with `set-identity-provider-ud-push-configuration` (**JSON-list shape**); mapping and match key go through the same pair of hidden interfaces (**the match key must be Set explicitly** — there is no default); triggering and verification as in S7. To enable QR code logon: the redirect URL backfill sits on the management plane and is console-only (see the "Authentication dimension" section); the live login test stays manual.
- Still manual: browser authorization, Feishu release approval, the authentication-dimension live QR code logon test (S7).

### cli-mode recipe and API chain (Feishu)

- **create-identity-provider recipe**: structurally the same as DingTalk orgapp, with the configuration object swapped to `--lark-config` (object parameters as `Key=Value` pairs). `--lark-config AppId=…` / `AppSecret=…` / `EnterpriseNumber=…` (the enterprise number is non-sensitive and may enter the conversation) + `--ud-pull-config UdSyncScopeConfig.TargetScope=<ou_id>` + `--authn-config AuthnStatus=enabled` + `--auto-create-user-config AutoCreateUserStatus=disabled` + `--client-token <uuid>`. Read back the three dimensions (`get-identity-provider` / `get-identity-provider-ud-pull-configuration` / hidden interface `GetIdentityProviderAuthnConfiguration`) and verify item by item; after creation the `EnterpriseNumber` appears in both `Description` and `IdentityProviderExternalId`.
- **Rename pitfall**: `--identity-provider-name` is ignored at creation (the default name is `入方向飞书IdP`); for the rename parameter shape, propagation delay, and general rules such as "do not chain renames", see step 1 of "IDaaS-side write path for CLI mode" in `idp-model-openapi.md`.
- **Injecting the AppSecret without putting it through the conversation (lark-cli cannot export plaintext)**: lark-cli stores the AppSecret encrypted in the keychain and `config show` masks it as `****` — **plaintext cannot be exported**; the only authoritative source of the plaintext is the developer console's `凭证与基础信息` page. Recommended temporary-file method: the user enters it silently with `read -rs` in their own terminal → writes it to a 600-permission temporary file → the command injects it via command substitution with `--lark-config AppSecret="$(cat /tmp/.xxx)"` → after verification, `rm -P` overwrites and erases it. ⚠️ **When the user's shell is zsh**: bash's `read -rs -p "prompt" VAR` fails in zsh with `read: -p: no coprocess` (zsh `-p` = read from a coprocess); the correct zsh form is `read -rs "VAR?prompt"`, or wrap it in `bash -c '…'`.
- **token_types diagnostic (pinpoints the identity type the scope was granted to)**: `lark-cli api GET /open-apis/application/v6/applications/<app_id>/app_versions --params '{"lang":"zh_cn","page_size":10}' --as bot`; inspect each scope's `token_types` inside the released versions (`status=1` and `publish_time` non-empty and non-zero): only `['user']` = user identity only, invisible to tenant; containing `'tenant'` = the app identity can use it. This pinpoints "99991672 means the app-identity permission was not enabled" faster than repeated read attempts. Note that the path in `lark-cli api` **must not carry a query string** — query parameters go through `--params`; the version API must be called with `--as bot` (the user identity fails with 99991668).
- **Sync API chain**: ① **connectivity/credential pre-check (non-destructive; run it before the sync)** `create-identity-provider-status-check-job --instance-id --identity-provider-id` → `get-identity-provider-status-check-job` (⚠️ **you must also pass `--identity-provider-status-check-job-id <jobId>`**, otherwise it fails with required); all four JobCheckItems (network/credential `lark_credential`/authorization `operate_authorization`) returning success = the credential + permission chain is up. ② **identifier-collision re-check**: `list-users` has **no `--username` exact filter** — investigate with `--organizational-unit-id` (check whether the target node is empty) / `--phone-number` / `--email` / `--display-name-starts-with`; the Feishu primary key maps `user_id→username`, so confirm before syncing that the target username is not already occupied by an existing account. ③ **trigger the full sync**: `run-synchronization-job --instance-id --target-type identity_provider --target-id <idp_id>` (no scope-config = a full sync over the already-configured TargetScope; requires the user's explicit go-ahead) → `get-synchronization-job --synchronization-job-id <jobId>` to read `Status` and `Result.UserStatistics.Created.{Total,Success,Failed}`. Phone numbers in `list-users` output are masked by IDaaS itself (`177******84`); no extra masking is needed.

## OpenAPI-side corresponding fields (see idp-model-openapi.md)

- `AuthnSourceSupplier` = `urn:alibaba:idaas:idp:bytedance:lark`; `IdentityProviderType` = `...:bytedance:lark:pull` (inbound sync) / `...:bytedance:lark:push` (outbound)
- `LarkConfig`: `AppId` / `AppSecret` / `EncryptKey` / `EnterpriseNumber` / `VerificationToken`

## Pitfalls and reminders

- The Feishu `userid` is **the primary key everything depends on**; changing it causes the corresponding IDaaS account to be **deleted and recreated** — change it with care (hard boundary 3).
- A failed permission verification is mostly a `contact:*` scope not enabled or missing release approval → guide the user to obtain approval in the Feishu admin console and retry.
- Phone/email are sensitive fields that need the corresponding scopes + release approval; do not presume a bug.
- Each of the three sync-cadence items must be confirmed separately: **incremental sync** is not on by default and needs the event callback configured separately (Encrypt Key/Verification Token/request URL); `定时校验` is likewise off as shipped; **with neither enabled, `全量同步` can only be triggered manually**.
- App Secret and the like are filled in by the administrator themselves; the skill never asks for plaintext and never echoes it back (hard boundary 1).
