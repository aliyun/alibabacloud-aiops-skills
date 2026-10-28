# RAM permissions

RAM permissions this skill requires when it operates the IDaaS (EIAM) side in `cli` mode. Actions are declared one per line, with no wildcards (least privilege). Grant them to the RAM identity behind the `aliyun` CLI profile before starting; in `manual` mode the skill itself needs none of them (the administrator configures in the console).

- Source-side operations (the DingTalk / WeCom / Feishu admin consoles and their CLIs `dws` / `wecom-cli` / `lark-cli`) are not Alibaba Cloud resources and are not declared here.
- Entries marked **hidden interface** exist on the server but appear in neither the CLI metadata nor the public API portal (invoked with the PascalCase name + `--force`); their action names follow the API-name convention.
- No deletion actions are declared — the onboarding flow performs no deletions (organizational-unit cleanup is mentioned only as handover guidance in S8).
- **Every write action below stops at a user-confirmation point before execution** (main SKILL.md hard boundary 2). Read actions are equally bound by hard boundary 1: outputs that carry source-side secrets must be programmatically masked before display.

## Read-only (state queries and verification)

`eiam:ListIdentityProviders` — list the IDPs under the instance; the single call that also reads sync switches, the sync destination organizational unit, scheduled verification, and the incremental switch
`eiam:GetIdentityProvider` — single-IDP details (type triple, per-type configuration objects, statuses); ⚠️ returns source-side secrets in plaintext — mask the output before display
`eiam:GetIdentityProviderUdPullConfiguration` — inbound (pull) sync configuration: scope, scheduled verification, incremental switch, sync-protection thresholds
`eiam:GetIdentityProviderUdPushConfiguration` — outbound (push) sync configuration: the scope-mapping array and cadence switches
`eiam:GetIdentityProviderStatusCheckJob` — read the result of a connection/status verification job
`eiam:GetIdentityProviderAuthnConfiguration` — current values of the authentication configuration (hidden interface)
`eiam:GetIdentityProviderUserProfileMapping` — current user field mappings including the match key (hidden interface)
`eiam:GetIdentityProviderOrganizationalUnitProfileMapping` — current organizational-unit field mappings (hidden interface)
`eiam:GetIdentityProviderGroupProfileMapping` — current group field mappings (hidden interface)
`eiam:GetIdentityProviderUserProfileMeta` — mappable user fields and match-key candidates for the type (hidden interface)
`eiam:GetIdentityProviderOrganizationalUnitProfileMeta` — mappable organizational-unit fields (hidden interface)
`eiam:GetIdentityProviderGroupProfileMeta` — mappable group fields (hidden interface)
`eiam:VerifyIdentityProviderProfileMappingExpression` — validate a mapping expression's syntax and variable prefix (hidden interface)
`eiam:GetSynchronizationJob` — single sync job status and statistics buckets
`eiam:ListSynchronizationJobs` — sync job history
`eiam:ListOrganizationalUnits` — list the organizational tree (verify mirrored sub-organizations and account landing)
`eiam:GetOrganizationalUnit` — single organizational-unit details
`eiam:ListUsers` — list accounts (verify sync results, field values, `UserSourceId`)
`eiam:GetUser` — single-account details including organizational membership (S7 landing verification)
`eiam:ListDomains` — instance login domains (used to derive the DingTalk/Feishu redirect URI)
`eiam:GetNetworkAccessEndpoint` — the network access endpoint's current public egress IP ranges (WeCom trusted IP takes this as authoritative; the ranges change — read fresh every time)

## Write (configuration; each execution requires explicit user confirmation)

`eiam:CreateIdentityProvider` — create the IDP in one shot (credentials, sync scope, authentication; secrets transferred via command substitution, never through the conversation)
`eiam:UpdateIdentityProvider` — modify IDP information (e.g. rename after creation; WeCom update additionally requires the network access endpoint ID)
`eiam:CreateIdentityProviderStatusCheckJob` — trigger the connection/status verification job
`eiam:SetIdentityProviderUdPullConfiguration` — modify the inbound sync configuration (scope / cadence / incremental / protection thresholds)
`eiam:SetIdentityProviderUdPushConfiguration` — modify the outbound sync configuration (scope mappings)
`eiam:EnableIdentityProviderUdPull` — enable inbound sync
`eiam:DisableIdentityProviderUdPull` — disable inbound sync
`eiam:EnableIdentityProviderAuthn` — enable the authentication switch
`eiam:DisableIdentityProviderAuthn` — disable the authentication switch (e.g. when S0 locks in sync-only)
`eiam:SetIdentityProviderAuthnConfiguration` — modify the authentication configuration (hidden interface; overwrite-style — read back before writing)
`eiam:SetIdentityProviderUserProfileMapping` — modify user field mappings and the match key (hidden interface; overwrite-style, and omitting the match-key parameter clears it)
`eiam:SetIdentityProviderOrganizationalUnitProfileMapping` — modify organizational-unit field mappings (hidden interface; overwrite-style)
`eiam:SetIdentityProviderGroupProfileMapping` — modify group field mappings (hidden interface; overwrite-style)
`eiam:RunSynchronizationJob` — trigger a sync job (initial full sync / push; requires explicit user confirmation — deletion and overwrite risks, main SKILL.md hard boundary 3)
`eiam:BindUserAuthnSourceMapping` — manually bind a source identity to an existing IDaaS account (remediation when a synced username conflicts)
`eiam:CreateNetworkAccessEndpoint` — create a dedicated network access endpoint (WeCom dedicated egress prerequisite; the NAT/EIP/SNAT chain stays administrator-side)
`eiam:UpdateUser` — update an account's phone/email (WeCom outbound 60129 backfill recipe)
