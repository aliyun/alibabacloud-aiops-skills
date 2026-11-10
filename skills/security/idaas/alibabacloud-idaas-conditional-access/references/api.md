# EIAM conditional access API reference (2021-12-01)

Field names and enum values are verified against the official Alibaba Cloud API documentation and live testing.

## Policy CRUD

| Action | Access level | Request parameters | Returns |
| --- | --- | --- | --- |
| CreateConditionalAccessPolicy | create | InstanceId, ConditionalAccessPolicyName (required), ConditionalAccessPolicyType (required), DecisionType (required), EvaluateAt (required), Description, DecisionConfig, ConditionsConfig, Priority (1-100), ClientToken | ConditionalAccessPolicyId, RequestId |
| ListConditionalAccessPolicies | list | InstanceId, NextToken, MaxResults, PreviousToken | ConditionalAccessPolicies[], TotalCount, NextToken, PreviousToken |
| GetConditionalAccessPolicy | get | InstanceId, ConditionalAccessPolicyId | ConditionalAccessPolicy (full object) |
| UpdateConditionalAccessPolicy | update | InstanceId, ConditionalAccessPolicyId, ConditionalAccessPolicyName (required), DecisionType (required), DecisionConfig, ConditionsConfig, Priority, ClientToken | RequestId |
| DeleteConditionalAccessPolicy | delete | InstanceId, ConditionalAccessPolicyId | RequestId |
| EnableConditionalAccessPolicy | update | InstanceId, ConditionalAccessPolicyId | RequestId |
| DisableConditionalAccessPolicy | update | InstanceId, ConditionalAccessPolicyId | RequestId |

Note: the Delete documentation requires "the policy is no longer in use; deletion is irreversible", but **declares no API-level forced disable-first**; this skill still runs the hard sequence disable → observe → delete. Create's ConditionalAccessPolicyType is fixed to `arn:alibaba:idaas:authn:access:policy:system` (accepted in live testing). Update's DecisionType example shows `reportOnly` (report-only mode); the full enum is unverified — **this skill only writes `enforcement`**; reportOnly is neither used nor tested.

## Policy object fields (List/Get returns)

InstanceId, ConditionalAccessPolicyId, ConditionalAccessPolicyName, Description, ConditionalAccessPolicyType, Status (enabled/disabled), DecisionType, EvaluateAt, Priority (1-100; default policy 1001), DecisionConfig, ConditionsConfig, CreateTime, LastUpdatedTime (Unix milliseconds).

- **Default policy identification**: custom policies also carry Type `arn:alibaba:idaas:authn:access:policy:system` (confirmed by the Get documentation example), so Type cannot mark the default policy; identify it by Priority outside 1-100 (default 1001). **Live-verified: ListConditionalAccessPolicies does not return the default policy** — the hit preview must synthesize the fallback entry (built into ca_preflight.simulate).
- **Policy ID prefix**: live-verified `cap_` (the documentation's request example `cap_11111` and return example `cp_xxxxx` disagree); always trust the API return value, never hardcode a prefix check.

## DecisionConfig

| Field | Enum |
| --- | --- |
| Effect | `allow` / `deny` (**the actual return is capitalized `Allow`/`Deny`, live-verified; the scripts always normalize to lowercase before comparing**) |
| MfaType | `directly_access` (direct access) / `mfa_required` (second-factor required) |
| MfaAuthenticationMethods | `ia_otp_sms` (SMS) / `ia_otp_email` (email) / `ia_totp` (one-time password) / `ia_webauthn` |
| MfaAuthenticationIntervalSeconds | 300-86400 (seconds); **this skill always sends 300** (custom values are not exposed; the server also synthesizes 300 for omitted fields) |
| ActiveSessionReuseStatus | `enabled` / `disabled` (session reuse, MFA-free) |

## ConditionsConfig

| Domain | Fields | Notes |
| --- | --- | --- |
| Applications | IncludeApplications / ExcludeApplications | Application IDs; an empty Include = all applications (portal included) |
| Users | IncludeUsers / ExcludeUsers / IncludeGroups / ExcludeGroups / IncludeOrganizationalUnits / ExcludeOrganizationalUnits | User/group/organizational-unit IDs; an all-empty Include = all users; excluding an organizational unit overrides individual inclusion |
| NetworkZones | IncludeNetworkZones / ExcludeNetworkZones | Network zone IDs; empty = no restriction |

## Network zones (console "Network Zones" = API NetworkZone)

**This skill only discovers read-only and references by ID; it does not create/modify/delete network zones** (instance-level shared resource, out of scope).

| Action | Request parameters | Returns |
| --- | --- | --- |
| ListNetworkZones | InstanceId, NextToken, MaxResults, PreviousToken, NetworkZoneIds (filter) | NetworkZones[], TotalCount, NextToken |

NetworkZone object: InstanceId, NetworkZoneId, NetworkZoneName, Description, NetworkZoneType (`arn:alibaba:idaas:network:zone:classic` / `:vpc`), VpcId, Ipv4Cidrs, Ipv6Cidrs. **No Status/CreateTime fields**. The vpc type requires VpcId, and membership cannot be determined locally from a source IP — the hit preview marks it as approximate.

## Application list (for entity validation)

ListApplications: InstanceId, PageNumber/PageSize (classic pagination, unlike the token pagination of policies), ApplicationIds (filter), ApplicationName (left-fuzzy), ApplicationCreationType (`system_init` / `user_custom` / `all`, default user_custom — returns only user-created applications; pass `all` to include system applications), ApplicationIdentityType (default application), other filters omitted. Returns Applications[]: ApplicationId, ApplicationName, Status, ApplicationSourceType, ApplicationCreationType, Features, etc.

**Configurable-target semantics (product-confirmed + live-verified)**: what the default user_custom query does not list are system applications — **system applications cannot be conditional access targets; the portal `iap_user_portal` is the sole exception**. Entity validation therefore runs in two stages: first by ID under the default user_custom query (only configurable applications pass); unresolved IDs are re-checked by ID with `ApplicationCreationType=all` + `ApplicationIdentityType=all` — a hit there reports `entity_not_configurable` (system application, not configurable); only still-unresolved IDs are `entity_missing` (nonexistent).

**There is no portal flag field**; the portal application ID is the fixed constant `iap_user_portal` (queryable with `ApplicationCreationType=all`: the by-ID filter returns exactly 1 row, and it also appears in the unfiltered full list; the default user_custom query cannot find it — Name="User Portal", `system_init`). The portal is the only configurable system application, and entity validation special-cases the fixed constant (it never appears in referenced_apps_missing/not_configurable).

## Pagination and parameter encoding (live-verified 2026-10-21 on aliyun CLI 3.5.1; not inferred from docs)

### Pagination

| API | Pagination | Script implementation |
| --- | --- | --- |
| Policies / network zones | NextToken / MaxResults cursor | `paginate_tokens` (repeated-token loop guard) |
| Applications | PageNumber / PageSize | `paginate_pages` |

Note: **a short page ≠ the full set** — a single under-sized response may be the last page or a filtered short page; pagination terminates on "no next token", never treat one response as the full set.

### CLI parameter encoding (routed by parameter shape)

| Parameter shape | Sendable via aliyun CLI? | Notes |
| --- | --- | --- |
| Scalars (InstanceId, Priority, …) | ✅ direct flag | No special handling |
| Arrays (ApplicationIds, Ipv4Cidrs, …) | ✅ flat indexed flags | `--ApplicationIds.1 app_a --ApplicationIds.2 app_b`; **a JSON array string returns 400** (live-verified `InvalidApplicationIds`) |
| Objects (DecisionConfig, ConditionsConfig) | ❌ **cannot be sent via the CLI** | Both routes are dead: the JSON string is rejected by the server (live-verified `InvalidDecisionConfig: Illegal parameter serialization format. Flat format is required.`); dot-path flags (`--DecisionConfig.Effect`) are rejected locally by the CLI as invalid parameters |

### The only route for object parameters: SDK transport

Policy Create/Update carries DecisionConfig / ConditionsConfig objects and **must go through the ca_lifecycle built-in SDK transport** (tea-openapi generic client), never the aliyun CLI:

- **Wire format** (confirmed by console packet capture; the SDK's `OpenApiUtil.query` expansion matches the capture field for field): flat dot-path query parameters —
  - `DecisionConfig.Effect=Allow` (**Effect is capitalized on the wire**; MfaType / ActiveSessionReuseStatus stay lowercase)
  - `DecisionConfig.MfaAuthenticationMethods.1=ia_otp_sms` (arrays remain flat-indexed under dot paths)
  - `ConditionsConfig.Applications.IncludeApplications.1=app_x`
- **Credential prerequisite**: the SDK credential chain is independent of the CLI profile — before writing, verify both sides via GetCallerIdentity and require the accounts to match, preventing the SDK from falling back to a bare default credential and writing to the wrong account.

### Server-side Create behavior (read-back verification basis)

- **Synthesized defaults** (live-verified): Create fills defaults for unspecified DecisionConfig fields — `MfaAuthenticationIntervalSeconds=300`, `ActiveSessionReuseStatus="disabled"`, and a deny policy sent without MfaType gets `MfaType="directly_access"`. **Read-back verification uses "requested fields are covered" semantics** (ca_lifecycle.covers); strict equality would wrongly reject a correct creation.
- **Status defaults to enabled after creation** (no compensating Enable call needed; the script keeps the fallback).
- **Minimal deny DecisionConfig**: `Effect=Deny` alone creates successfully (no MfaType / methods / interval needed); the read-back fills the same defaults.