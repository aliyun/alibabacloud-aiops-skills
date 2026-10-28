# DingTalk identity provider (IDP) onboarding · reference

This file carries the S0–S8 skeleton of the main SKILL.md and covers only DingTalk-specific fields, source-side steps, and pitfalls.

**Set the direction first (S0; when unclear, guide the user to confirm — never default it)**: for inbound (pull, DingTalk → IDaaS), read chapters A/B plus the later topic sections (authentication / default mapping / organizational units); for outbound (push, IDaaS → DingTalk), read chapter C. The two directions differ completely in source-side preparation, IDaaS configuration, and risk surface.

## Two binding modes (inbound; pick the mode first)

| Mode | Best for | Source-side preparation | Can it fetch phone/email? |
|---|---|---|---|
| **Quick binding (third-party app)** | Fast onboarding — a scan-to-authorize is all it takes | No AppKey/AppSecret needed; the DingTalk admin scans a QR code to authorize | **No** (phone numbers/emails cannot be fetched in batch) |
| **Advanced configuration (enterprise-internal first-party app)** | Full user fields needed (phone, email) | DingTalk enterprise-internal app `AppKey` + `AppSecret` | Yes (subject to permissions and account type) |

Rule of thumb: if the customer only wants "DingTalk QR code logon + syncing the basic contacts", quick binding suffices; if "phone numbers/emails must also land in IDaaS", advanced configuration is mandatory.

## A. Quick binding (inbound)

1. IDaaS console → `快速开始` or `身份提供方` → `快捷绑定钉钉`.
2. **`Step1 选择场景`** (choose scenarios):
   - `同步目标` (**sync destination organizational unit**): the DingTalk contacts are imported under this unit (required).
   - `增量同步` (incremental sync): changes in the DingTalk contacts are synced in real time (optional).
   - `钉钉扫码登录` (DingTalk QR code logon): creates and enables QR code logon (check it if authentication is wanted).
   - `触发全量同步` (trigger full sync): imports everything immediately after binding (recommended to check on the first run).
3. **`Step2 扫码开通`** (scan to activate): IDaaS shows a QR code → the DingTalk admin scans it → the app activation page opens → activate for free → pick the usage scope → activate now → open the app. (If already activated, click `确认应用已开通，下一步`.)
4. **`Step3 扫码绑定`** (Scan to connect): in the DingTalk app, tap `钉钉管理员扫码绑定` → scan the IDaaS QR code → confirm authorization. Binding done.
5. **Adjust the source-side authorization scope**: DingTalk admin backend → `应用管理` → find the `阿里云 IDaaS` app → adjust `授权范围`. It decides how many people get synced.

## B. Advanced configuration (first-party app, for the full field set)

1. IDaaS → `身份提供方` → open the DingTalk IDP management page → switch **`高级配置`** from `未开启` to enabled.
2. Advanced-configuration **`Step1 选择场景`** (choose scenarios): the docs note it is not yet configurable → click `下一步` directly.
3. **Create a DingTalk enterprise-internal app** (the DingTalk admin, on the DingTalk Open Platform `https://open-dev.dingtalk.com/fe/app#/corp/app`):
   - `添加应用` → app type `H5 微应用`, development mode `企业自研`, fill in name/description → confirm creation.
   - In the app detail page, copy `AppKey` and `AppSecret` from the `应用凭证` area.
4. **Fill back into IDaaS** (advanced configuration `Step2 创建应用`): `CorpId` (auto-filled by IDaaS), `AppKey`, `AppSecret` → `确认授权` (IDaaS tests the connection).
5. **Grant sync permissions** (Step3 `分配权限`, on the DingTalk app page):
   - `权限管理` → check the needed permissions under `通讯录管理` (Address Book Management) + the needed permissions under `应用管理` → apply in batch.
   - **Permission list (on the first-party app's `权限管理` page)**:

     | Permission name | Permission point | Purpose |
     |---|---|---|
     | `通讯录个人信息读权限` (contacts personal-info read) | `Contact.User.Read` | Fetches user personal info; **a hard dependency of QR code logon** — without it even `AuthnStatus=enabled` cannot log in |
     | `用户 access token 基础权限` (under the `获取凭证` group) | `open_app_api_base` | **A hard dependency of QR code logon** (new apps lack it; the login page reports `无权访问该APP` — "no access to this app"); it serves token exchange for the **user identity** and is a separate line from the app-credential chain used by sync (the `qyapi_*` series) — do not conflate them |
     | `成员信息读权限` (member info read) | `qyapi_get_member` | Queries user details / department userid lists / admin lists etc.; required for sync |
     | `通讯录部门信息读权限` (contacts department info read) | `qyapi_get_department_list` | Department details / department lists / parent-department lists; required for organizational-unit mirroring |
     | `通讯录部门成员读权限` (contacts department-member read) | `qyapi_get_department_member` | Full/simple department user info and role details; required for sync |
     | `企业员工手机号信息` (employee phone number) | `fieldMobile` | Fetches the phone number in user details; maps to `mobile→phoneNumber` |
     | `邮箱等个人信息` (email and other personal info) | `fieldEmail` | Fetches the email in user details; maps to `email→email` |
     | `根据手机号获取成员基本信息权限` (fetch member basic info by phone number) | `qyapi_get_member_by_mobile` | Reverse-looks up users by phone number; not a hard dependency of sync/login — only needed for the "match by phone-number lookup" scenario |
     | `通讯录数据管理权限` (contacts data management, Address Book Management group) | `qyapi_manage_addresslist` | **The core write permission for outbound (push)** — IDaaS relies on it to write the DingTalk contacts when pushing; not needed for inbound |

     All the permission points above are marked **`无需审批`** on the DingTalk side — the permission-application step has no admin approval like Feishu's. But "check it and it takes effect" has a premise: a permission counts only after entering the **effective snapshot of a published version** — an app never released (`versionStatus=INIT`) has no effective permissions at all; **permissions added after a release must be published in a new version** to take effect (e.g. adding `open_app_api_base` after v1.0.0 is released: without a new version login still errors; after v1.0.1 goes out it recovers). The DingTalk Open Platform `权限管理` page display is authoritative (hard boundary 6).
   - For the **source-side authorization scope**, pick `全部员工` (or narrow it as needed; narrowing/adjusting goes through DingTalk admin backend → `应用管理` → `阿里云 IDaaS` → `授权范围`).
   - Back in IDaaS, click `确认授权`; it verifies whether the contacts-management permissions are in place.
6. **Field mapping (Step4)**: at creation IDaaS **already carries the default mapping** (`userid → username` etc.; see "Default field mapping" below) — this step is **adjust-as-needed**, not configuring from scratch. Adjusted or not, it must be finalized **before the initial full sync** (main SKILL.md S6 hard gate: present the mapping table and mapping identifier to the user for **explicit confirmation** — keeping the factory defaults is no exception) — changing the **primary key everything depends on** causes existing accounts to be deleted and recreated. Common adjustments: use the DingTalk phone number as the IDaaS username and the DingTalk email as the IDaaS email; match existing accounts by phone number (i.e. the `映射标识` — a hit binds and updates, a miss creates a new account).

## C. Outbound (push, IDaaS → DingTalk)

Opposite in direction to chapters A/B: **IDaaS-side organizational units/accounts are pushed into the DingTalk contacts**. The data flow reverses and so does the risk surface — **what gets written is DingTalk-side data** (zero changes to IDaaS-side accounts), and `UdPushConfig` has no counterpart of `PullProtectedRule` — **no delete-protection backstop** (main SKILL.md hard boundary 3). **Confirm with the user at S0 which of the two dimensions to do**: sync push is the main outbound scenario; **QR code logon is mechanically available too** — the outbound app is simultaneously registered as an OIDC authentication source (created with `AuthnStatus=enabled`; the DingTalk QR-code method appears on the login page by default), and the same AppKey/AppSecret serves the login chain; enabling it requires the three hard dependencies of the authentication section of chapter A (released version, `Contact.User.Read`/`open_app_api_base` permissions in the effective snapshot, Redirect URI filled back on the DingTalk side), and QR-code-login triage is the same as chapter A. Official doc: bind IDaaS to DingTalk (outbound) `https://help.aliyun.com/zh/idaas/eiam/user-guide/bind-idaas-to-dingtalk-outbound`.

**Always pilot with a small scope first**: narrow `SourceScopes` to a dedicated test OU and point `TargetScope` at an isolated test department; verify the push behavior before opening it up to the production org — same phone number means overwrite (see C.3), and a mis-configured match surface will batch-rewrite real member profiles on the DingTalk side; pushed changes **do not roll back when the IDP is deleted**.

### C.1 Source-side (DingTalk) preparation

1. **Create an enterprise-internal app**: same as B.3 (`dws devapp +create` → `+credentials-get`; AppKey/AppSecret passed directly via command substitution, never entering the conversation).
2. **Permissions**: the core write permission `qyapi_manage_addresslist` (the Address Book Management group's `通讯录数据管理权限` — outbound writes the contacts through it); check off the read permissions per the B.5 list.
3. **Create the target department** (the push needs a DingTalk-side department as `TargetScope`; a dedicated isolated one is recommended):
   - `dws contact dept create` is not available (reports `ability_not_full_open`) — use the OpenAPI escape hatch:
     ```bash
     dws api POST https://oapi.dingtalk.com/topapi/v2/department/create \
       --client-id <appKey> --client-secret <secret> \
       --data '{"name":"<中文名>","parent_id":1}'
     ```
   - Three pitfalls: ① the escape hatch must **pass the app credential pair explicitly** (`--client-id`/`--client-secret`; the default credential's encrypted token does not work with raw APIs); ② **the department name must be Chinese** — an English name reports 40035 `不合法的参数 name` ("invalid parameter name"; same family as the 67010 app-name pitfall: when a name errors out, switch to Chinese first before investigating); ③ neither `/v1.0/departments` (404) nor the legacy `topapi/department/create` (no v2; `远程服务不存在` — "remote service not found") exists — don't try them.
   - Escape-hatch GET query parameters must go through the `--params` flag; appending `?key=value` directly to the URL gets silently dropped.
4. **Release for effect**: same as chapter B (permissions must be released to enter the effective snapshot; `dws devapp +version-create` needs `--yes` for non-interactive use; `version publish` occasionally throws a transient `PREPARE_CALL_TOOL_ERROR` — a retry passes). Being able to create a department with the app's own token = the permission chain suffices for the IDaaS push (IDaaS uses the same credential set).
5. **Fill back the security settings** (the three items `出口IP/回调域名/应用首页地址` — Server Outbound IP / Callback domain name / Application homepage URL — of the official outbound doc): the `--ip-whitelist` / `--redirect-urls` / `--sso-urls` flags of `dws dev app security config`. ⚠️ **The IP whitelist accepts single IPs only, not CIDRs** (passing `x.x.x.x/27` reports 41000 `IP地址的格式不正确` — "incorrect IP address format"); when doing sync only, leaving the whitelist **empty** is fine (= no source-IP restriction; sync is unaffected).

### C.2 Create the outbound IDP on the IDaaS side

The `create-identity-provider` recipe is the same as B.4 (kebab plugin form with `Key=Value` object parameters; the full recipe is step 1 of the write path in `idp-model-openapi.md`), with three differences:

- **Type URN**: `urn:alibaba:idaas:idp:alibaba:dingtalk:push`.
- **The scope configuration goes through `UdPushConfig.UdSyncScopeConfigs` (an array)**, structurally different from pull's single object `UdPullConfig.UdSyncScopeConfig`:
  ```text
  --ud-push-config "UdSyncScopeConfigs[0].SourceScopes[0]=<IDaaS organizational unit ID>"
  --ud-push-config "UdSyncScopeConfigs[0].TargetScope=<DingTalk dept_id, numeric>"
  ```
  Semantics = push the IDaaS organizational units/accounts under `SourceScopes` beneath the DingTalk `TargetScope` department; the array can hold multiple "IDaaS org → DingTalk department" mappings.
- **Switch states**: created with `UdPushStatus=enabled` (no extra enable needed); the server auto-fills `DingtalkProvisioningConfig.AuthedDepartmentIds=[{DeptId:1}]` (the DingTalk root department).

Read-back: `get-identity-provider-ud-push-configuration` (kebab-case parameters) returns the scope configuration; `set-identity-provider-ud-push-configuration` can modify it, ⚠️ `--incremental-callback-status` is mandatory (same trap as the pull-side set), and the scope parameter takes the **JSON list** form (the CLI does not accept flattened dotted names; see the UdPushConfiguration section of `idp-model-openapi.md`). `DingtalkVersion` remains mandatory.

### C.3 Field mapping and match key (direction reversed)

- **The factory mapping direction reverses**: `user.* → idpUser.*` (displayName→name, phoneNumber→mobile, phoneRegion→state_code, email→email, userId→userid), the opposite of inbound (`idpUser.* → user.*`) — the source is the IDaaS account, the target is the DingTalk member.
- **The match key `UserMappingIdentityName` ships as `idpUser.mobile` (phone number)**: the push matches DingTalk members by phone number — a hit binds and **overwrites/updates** (name and other mapped fields get rewritten with IDaaS values), a miss **creates** a new DingTalk member. Same number means overwrite; to test the "match-and-update" path, use an IDaaS test account carrying the same phone number as an existing DingTalk member. **The match key is not fixed and can be changed**: the candidate set is defined by the "usable as match key" metadata of `GetIdentityProviderUserProfileMeta`, e.g. `idpUser.userid` — userid is stable, so a member changing phone numbers never loses the match; accounts synced inbound under the default mapping (userid→username) carry the DingTalk userid as `username`, so the mapping `user.username`→`idpUser.userid` binds existing members stably by userid.
- DingTalk-side target fields: userid / name (required) / state_code / mobile (required) / org_email / job_number / title / email / remark. Extension fields (e.g. office location work_place) are added via the console's `修改 > 设置字段映射`; the field identifier must be the official DingTalk field name and must be unique.
- Reads/writes go through the hidden interfaces `Get/SetIdentityProviderUserProfileMapping` (invocation form as in chapter B's ⚠️ pitfall; **the same pair serves pull and push — the server auto-detects the direction from the IDP type**, no parameter distinction needed). Set is an overwrite-style write — read back before changing; **omitting `--UserMappingIdentityName` clears the match key** (the server sets that field unconditionally) — when adjusting mapping entries, always carry the match-key parameter, otherwise the push loses its matching ability and treats the full sync as pure creation. Expression validation only checks the **variable prefix** (push side must be `user.`, pull side `idpUser.`), never the field name — a wrong field name is silently skipped at sync runtime; don't count on validation to catch it.

### C.4 Trigger the push and verify

- Triggering follows main SKILL.md S7: pass the S6 gate first — present the mapping table and match key to the user for **explicit confirmation** (keeping factory defaults included); never trigger before it; `run-synchronization-job --target-type identity_provider --target-id <push_idp_id>` (the trigger itself also needs explicit user confirmation) → follow up with `get-synchronization-job`.
- Job statistics land in the **`Binded`** bucket (match-hit bind-and-update), a different counting system from inbound's Created/Same; the job record likewise carries statistics only, no failure reasons.
- **Departments are appended, not replaced**: the push adds members into the target department but **never removes** them from their existing DingTalk departments (zero damage to existing department membership — additions only) — do not verify against the expectation "overwrite-update = department takeover".
- Organizational-unit mirroring: IDaaS sub-units under `SourceScopes` are mirrored as sub-departments under the target department (nothing is created if the source has no sub-units).
- **Pushed changes do not roll back**: deleting the IDP or the test data restores none of the DingTalk-side fields already overwritten (name etc.) — cleanup requires manual restoration: query with `dws contact user get`; but `dws contact user update` for changing name/department membership **is blocked by `ability_not_full_open`** (same as department creation) — restore via the escape hatch `topapi/v2/user/update` (`name` restores the name, `dept_id_list` restores the original department list, e.g. `"1,<original_deptId>"`); delete test departments via the escape hatch `topapi/v2/department/delete`, ⚠️ a `60005` means members still remain — members "appended" by the push must first be moved back to their original departments via `dept_id_list` before deleting.
- Outbound does not modify IDaaS-side accounts (zero changes to IDaaS data after a push); verification centers on the DingTalk side: the target department's member list, field comparison for matched members, and data integrity of other departments.
- **Three-step root-cause check when the job reports success but "nothing changed" on the DingTalk side**: ① check against the match key (factory default is phone number; if changed, use the new key) — when the IDaaS account does not match an existing DingTalk member (e.g. different phone number), the push went down the **create** path; look for a **new member** under the `TargetScope` department instead of staring at whether existing members' profiles changed; ② unchanged department membership of existing members is expected (the "append, not replace" note above); what to look for is **additions** in the target department; ③ verify the scope configuration: does `SourceScopes` cover the IDaaS org the account sits in, and is the `TargetScope` department ID correct (read back with `get-identity-provider-ud-push-configuration`).

## Authentication (QR code logon)

- After quick binding checks `钉钉扫码登录`, IDaaS generates the login method `钉钉扫码登录`, enabled by default.
- Management entry: IDaaS console → `身份提供方` / `登录`. Users can then scan to log into IDaaS or the applications it manages.
- **The DingTalk side must grant the `通讯录个人信息读权限` `Contact.User.Read`**: without it, QR code logon still fails even when the IDaaS side shows `AuthnStatus=enabled` and `LastStatusCheckJobResult=success`. It is one of the contacts permissions to check in B.5 `分配权限` (**full permission table in the B.5 list**), but the wizard never proactively warns "unchecked = login failure", so it is easily missed.
- **Three hard dependencies of first-party-app QR code logon (missing any one errors out)**:
  1. **The app has a published version**: with a new app in `versionStatus=INIT` (never released), no permissions take effect; scanning reports `无权访问该APP`;
  2. **The `open_app_api_base` permission has entered the effective snapshot** (see the B.5 table): a login hard dependency alongside `Contact.User.Read`; permissions added after a release require publishing a new version (the B.5 concluding line);
  3. **IDaaS's Redirect URI has been filled back on the DingTalk side** (login redirect URL): without it the error is `无效的appid`.
  Error mapping: **`无权访问该APP`** = never released, or the permission is not in the effective snapshot; **`无效的appid`** = Redirect URI not registered. The CLI paths are respectively `dws dev app version publish` and `dws dev app security config --redirect-urls`.
- **Three ways to obtain the Redirect URI**: ① derived by rule: `https://<IDaaS login domain>/login/common/oauth2/callback`; ② look up the login domain with `aliyun eiam list-domains`; ③ actually extract the callback value from the QR code on the IDaaS login page's QR code logon (identical to ①). Console equivalent entry: DingTalk Open Platform `安全设置 → 登录重定向 URL`.
- **QR code probe (no IDaaS involved; probes the DingTalk side directly; for root-causing S7 login errors)**: `curl -s --connect-timeout 10 --max-time 30 "https://oapi.dingtalk.com/connect/qrconnect?appid=<AppKey>&response_type=code&scope=snsapi_login&state=x&redirect_uri=<URL-encoded callback>" | grep -oE "<title>[^<]*</title>"` — `<title>无效的appid</title>` means the Redirect URI is not registered; a normal `二维码登录` title means the DingTalk-side appid + callback are ready (note the probe does **not** cover the release/permission chain — those two problems still only surface on a real scan).
- **The authentication dimension requires one real manual login test**: `AuthnStatus=enabled` is just the switch state, not proof of being able to log in. After configuration, have the user do a real scan and watch them get into IDaaS — only then does the authentication dimension pass (main SKILL.md S7).
- `DingtalkLoginVersion` defaults to `new_version` (the new QR code logon); `old_version` is the legacy one — newly created IDPs generally need no change.

## Default field mapping

When a DingTalk IDP is created, IDaaS **already carries a default field-mapping set** (not empty; no need to configure from scratch). Defaults:

| DingTalk field | → IDaaS account field | Notes |
|---|---|---|
| `userid` | `username` | **Primary key everything depends on**; a hit binds and updates, a miss creates |
| `name` | `displayName` | Display name |
| `state_code` | `phoneRegion` | Value is `86` |
| `mobile` | `phoneNumber` | Requires the contacts phone-number permission |
| `email` | `email` | Requires the contacts email permission |
| `remark` | `description` | Description |

- **Keeping the default `userid` as the primary key everything depends on is fine**: it is the stable, unchanging identifier on the DingTalk side. Do not switch it to phone number/email for "readability" — phone numbers change, emails may be empty, and changing it causes existing accounts to be deleted and recreated (main SKILL.md hard boundary 3). Readability is what `displayName` is for.
- When an individual field is empty after sync, run the three-step root-cause check "not filled on the source side → permission not granted → mapping rule altered" before treating it as a bug (e.g. an empty account Email is most often caused by the DingTalk source not having an email configured; the mapping rule itself is fine).
- ✅ **Mappings are readable/writable via CLI**: `GetIdentityProviderUserProfileMapping` / `SetIdentityProviderUserProfileMapping` / `GetIdentityProviderAuthnConfiguration` **really exist server-side**, but neither the CLI metadata nor the portal api-docs lists them (interface existence cannot be judged from CLI metadata alone); they must be called with the PascalCase name + `--force` (detection method and invocation form in the hidden-interface ⚠️ block of `idp-model-openapi.md`). Changing mappings is a write operation — stop at the confirmation point.

## The two IDaaS organizational-unit settings (easily missed)

Where synced-in accounts land and where accounts auto-created at QR code logon land are **two independent settings**; both default to `ou_root` and must be changed separately:

| Purpose | Field | Notes |
|---|---|---|
| **Sync destination organizational unit** (console `同步目标`) | `UdPullConfiguration.UdSyncScopeConfig.TargetScope` (both names are real, belonging to different interfaces: `list-identity-providers` returns the flattened `UdPullTargetScope`, `get-identity-provider-ud-pull-configuration` returns `UdSyncScopeConfig.TargetScope`; the two values agree; `get-identity-provider` returns **neither**) | Accounts synced in by full/incremental sync hang under this unit |
| **Auto-created login organizational unit** | `AutoCreateUserConfig.TargetOrganizationalUnitIds` | If no matching account exists at QR code logon, IDaaS auto-creates one; the new account lands here |

Consequence of changing only one: synced-in accounts and auto-created login accounts land in different organizational units.

Factory values of the related switches (the authentication configuration can be read back via the hidden interface `GetIdentityProviderAuthnConfiguration` (`--force`) for all current values of `AutoCreateUserStatus`/`AutoUpdateUserStatus`/`AutoMatchUserStatus`/`MappingBindingStatus`/`TargetOrganizationalUnitIds`; writes go through `set-identity-provider-authn-configuration`, **overwrite-style** — read back first and carry all fields when writing):

- `AutoCreateUserStatus` / `AutoUpdateUserStatus` / `AutoMatchUserStatus`: all factory-default to `disabled`; auto-creation/auto-update/auto-matching of existing accounts requires explicitly enabling them.
- `MappingBindingStatus`: factory `enabled`, default expression `idpUser.email → user.email`, used to match and bind source-side users to existing IDaaS accounts.
- The **auto-created login organizational unit** (`AutoCreateUserConfig.TargetOrganizationalUnitIds`) is likewise readable via the hidden interface; defaults to `ou_root`.

> Also: source-side departments are **mirrored as sub-organizational-units under the sync destination organizational unit** (e.g. the DingTalk `产品部` → a sub-OU under that unit), and accounts land in the sub-units rather than directly under the sync destination unit itself. Finding no accounts under the unit itself ≠ sync failure — query together with the sub-units (`list-organizational-units` + `list-users`).

## OpenAPI-side fields (for read-side verification; see idp-model-openapi.md)

- `AuthnSourceSupplier` = `urn:alibaba:idaas:idp:alibaba:dingtalk`
- `IdentityProviderType` = `...:dingtalk:pull` (inbound sync) / `...:dingtalk:push` (outbound)
- **There is also `urn:alibaba:idaas:idp:alibaba:dingtalk:orgapp:pull`**: DingTalk IDPs created through advanced configuration (enterprise-internal first-party app) return this value with the `orgapp` segment, which is absent from the official enum table. **This URN is accepted as a creation input of `create-identity-provider`** — cli mode uses exactly it to create first-party-app IDPs; mistakenly using the old URN `...:dingtalk:pull` reports a misleading `实例状态不支持` ("instance status not supported") error (see step 1 of the write path in `idp-model-openapi.md`). When filtering IDPs by type, do not compare against the documented enum only — prefix matching with `...:dingtalk:` is more robust.
- `DingtalkAppConfig`: `AppKey` / `AppSecret` / `CorpId` / `DingtalkLoginVersion`(old_version|new_version) / `DingtalkVersion`(public_dingtalk|private_dingtalk) / `EncryptKey` / `VerificationToken`
- `DingtalkProvisioningConfig`: `CorpId` / `CorpName` / `AuthedDepartmentIds[]`(DeptId,DeptName) / `AuthedUsers[]`(Name,UserId)

## CLI assistance (cli mode)

Tools: `dws` (source side) + `aliyun` (IDaaS side). Installation/authentication/boundaries and credential-transfer principles: see `cli-tooling.md`; AppKey/AppSecret are passed directly via command substitution and never enter the conversation.

- **Quick binding (chapter A) has no CLI equivalent** — scan-to-activate/scan-to-bind are browser interactions. For full automation in cli mode, the only path is chapter B's advanced configuration (first-party app).
- CLI mapping for chapter B steps: B.3 create app/fetch credentials = `dws devapp +create` (the return carries appKey directly) → `+credentials-get` (credential JSON paths `data.appKey`/`data.appSecret`); B.5 grant permissions = `dws dev app permission add` (scopeValue is the permission-point table above — **do not miss either `Contact.User.Read` or `open_app_api_base`**); S3 callback fill-back = `dws dev app security config --redirect-urls "<IDaaS callback URI>"`; permissions/config taking effect = `dws dev app version create` → `version publish` (⚠️ the `+version-publish` shortcut is blocked by dws's safety gate; the full path works; unreleased apps and permissions added after a release both stay ineffective — see the authentication section above); B.4 fill back into IDaaS = `aliyun eiam create-identity-provider` in one shot (credentials, sync, authentication, mapping included; **kebab plugin form with `Key=Value` object parameters — recipe in the write path of `idp-model-openapi.md`**; type URN is `...:dingtalk:orgapp:pull`); B.6 adjust mapping = hidden interfaces `Get/SetIdentityProviderUserProfileMapping` (read back before changing).
- **CLI mapping for chapter C (outbound) steps**: source-side app creation/permissions/release use the same chapter-B commands (with `qyapi_manage_addresslist` as the core permission point; escape-hatch department creation in C.1); IDaaS-side creation = `create-identity-provider` with the same recipe, type URN `...:dingtalk:push`, scope via `--ud-push-config "UdSyncScopeConfigs[0].*"` (array; see C.2); read-back/modify = `get-identity-provider-ud-push-configuration` / `set-identity-provider-ud-push-configuration` (the latter requires `--incremental-callback-status`); mapping = the same pair of hidden interfaces (auto direction detection; see C.3).
- Initial full sync (requires explicit user confirmation): `run-synchronization-job --instance-id … --target-type identity_provider --target-id <idp_id>` → follow up with `get-synchronization-job` → inbound verification: `list-organizational-units` + `list-users` (**query together with sub-units**; see the mirroring note above); outbound verification happens on the DingTalk side (`dws contact` to check target-department members and fields; see C.4).
- The full IDaaS-side write-path order and parameter traps: see the "IDaaS-side write path in CLI execution mode" section of `idp-model-openapi.md`.
- Still manual: the first `dws` OAuth device-flow authorization; the version-release approver decision; the authentication-dimension real QR code logon test (S7).

## Pitfalls and reminders

- Quick binding ≠ advanced configuration: the former cannot fetch phone/email; if the customer wants these fields, switching to a first-party app is mandatory.
- Dedicated DingTalk (`private_dingtalk`) and standard DingTalk (`public_dingtalk`) are configured differently; confirm the customer's DingTalk edition first.
- Credentials (AppKey/AppSecret) are filled by the administrator; the skill never asks for plaintext or echoes it (main SKILL.md hard boundary 1).
- How many people get synced is decided by the **source-side authorization scope** (the DingTalk-side `授权范围`), not unilaterally by IDaaS; changing the scope happens in the DingTalk admin backend.
- **`AdvancedStatus=disabled` does not mean "credentials not configured"**: it means the advanced-configuration capability is off — IDPs created via quick binding are also `disabled`. To judge whether credentials are configured, check whether the fields inside `DingtalkAppConfig` have values; do not use `AdvancedStatus` as the basis.
- **Multiple DingTalk IDPs can coexist on one instance** (two DingTalk IDPs from different corps coexist without conflict). When a DingTalk IDP already exists, no need to reuse it — create an independent one per corp.
- **DingTalk IDPs also have `定时校验` (`PeriodicSyncStatus`)**: DingTalk (orgapp) IDPs return `PeriodicSyncStatus=disabled` + `PeriodicSyncConfig{PeriodicSyncType:"time", PeriodicSyncTimes:[3,5]}`; Feishu IDPs have the same field. The DingTalk help doc not mentioning this configuration item ≠ the capability does not exist; IDPs created by the console wizard have `IncrementalCallbackStatus=enabled` (matching "DingTalk incremental = real-time"), **but IDPs created via CLI `create-identity-provider` have it `disabled` — the two creation paths ship different factory values**; in cli mode, real-time incremental sync requires explicitly enabling it after creation with `set-identity-provider-ud-pull-configuration` (whose `--incremental-callback-status` is a mandatory parameter anyway).
- **`UdPullStatus=enabled` is just the switch, not proof a sync ever ran**: check whether `UpdateTime` equals `CreateTime` — identical values mean no sync has run since creation. Switch on yet zero accounts: check this first, then the authorization scope.
- **Deleting an IDP does not cascade-delete the accounts and organizational units it synced in**: their `UserSourceId` will point to a source that no longer exists, becoming orphan data. Call it out in the handover (main SKILL.md S8).
