# Scenario template library

Users state intent, not policy parameters. The agent does four things: recognize the scenario → collect missing inputs → generate the intent file from the template (for ca_lifecycle.py plan) → explain the consequences to the user via the hit preview.

## Intent file structure

```json
{
  "schema_version": 1,
  "intent_name": "scenario-identifier",
  "policies": [
    {"ConditionalAccessPolicyName": "...", "Description": "optional", "Priority": null,
     "DecisionConfig": {"Effect": "allow|deny", "MfaType": "directly_access|mfa_required",
       "MfaAuthenticationMethods": ["ia_webauthn"], "MfaAuthenticationIntervalSeconds": 300,
       "ActiveSessionReuseStatus": "enabled|disabled"},
     "ConditionsConfig": {"Applications": {"IncludeApplications": ["app_x"]},
       "Users": {"IncludeUsers": [], "IncludeGroups": [], "IncludeOrganizationalUnits": [],
                  "ExcludeUsers": [], "ExcludeGroups": [], "ExcludeOrganizationalUnits": []},
       "NetworkZones": {"IncludeNetworkZones": ["network_xxx"], "ExcludeNetworkZones": []}}}
  ]
}
```

- `Priority: null` means plan allocates a free priority automatically (recommended).
- **Network zones are referenced, never managed**: `network_xxx` must be an existing NetworkZone ID from discovery (this skill does not create/modify/delete network zones — they are instance-level shared resources). When the user gives no ID, first list the existing candidates for them to choose from; if a new zone is needed, have the user create it in the console and come back to regenerate the plan.
- **The MFA-free interval is fixed at 300 seconds**: the intent may omit MfaAuthenticationIntervalSeconds (plan injects 300 for mfa_required policies); any other value is rejected at local validation.
- **The app portal is referenced by the fixed ID `iap_user_portal`** (the only configurable system application; the default user_custom query cannot find it, so entity validation special-cases the fixed constant): an allow policy may target the portal (e.g. "signing in to the portal requires MFA").
- **Access targets can only be user_custom applications or the portal**: other system applications (Admin Portal, Config Portal, etc.) cannot be conditional access targets; referencing one is rejected at discovery (`entity_not_configurable`) — guide the user to a different choice.
- When an organizational unit is excluded, accounts inside it do not hit the policy even if individually included by another scope (official semantics; implemented in the simulator).

## Template 1: office IP only for a specific application

Trigger words: only the company network / office network / intranet may sign in to app X; deny non-office IPs.

Collect: the application (name → ID resolved via List), the office network zone (an existing NetworkZone `network_` ID; if absent, guide the user to create it in the console first — this skill does not create network zones).

```json
{
  "schema_version": 1, "intent_name": "office-ip-only",
  "policies": [
    {"ConditionalAccessPolicyName": "app-office-allow", "Priority": null,
     "DecisionConfig": {"Effect": "allow", "MfaType": "directly_access"},
     "ConditionsConfig": {"Applications": {"IncludeApplications": ["app_x"]},
       "Users": {}, "NetworkZones": {"IncludeNetworkZones": ["network_office"]}}},
    {"ConditionalAccessPolicyName": "app-outside-deny", "Priority": null,
     "DecisionConfig": {"Effect": "deny"},
     "ConditionsConfig": {"Applications": {"IncludeApplications": ["app_x"]},
       "Users": {}, "NetworkZones": {"IncludeNetworkZones": []}}}
  ]
}
```

Caution: **the fallback deny must bind the same IncludeApplications**. When an official typical scenario leaves the access target unspecified, always narrow it down per this template.

## Template 2: mandatory second-factor authentication for a specific application

Trigger words: accessing app X requires second-factor verification / an OTP / a fingerprint; add an extra layer of verification.

```json
{
  "schema_version": 1, "intent_name": "app-mfa-required",
  "policies": [
    {"ConditionalAccessPolicyName": "app-mfa-required", "Priority": null,
     "DecisionConfig": {"Effect": "allow", "MfaType": "mfa_required",
       "MfaAuthenticationMethods": ["ia_webauthn", "ia_totp"]},
     "ConditionsConfig": {"Applications": {"IncludeApplications": ["app_x"]},
       "Users": {}, "NetworkZones": {}}}
  ]
}
```

Key points: multiple methods may be selected; satisfying any one of them at login is enough. **Session reuse unspecified means disabled**: the intent does not write `ActiveSessionReuseStatus` (the server default matches the read-back — every SSO login requires MFA); write `enabled` only when the user explicitly asks for "no repeat second-factor within the interval of the same session / auto-pass" (the interval is fixed at 300 seconds — a skill decision; the intent omits the field and plan injects it). **Methods are user-specified**: when the request does not mention methods, ask first (choices: ia_otp_sms/ia_otp_email/ia_totp/ia_webauthn); never default to all methods or reuse another policy's method set — the combination above is an example, not a default.

## Template 3: high-sensitivity application, MFA on every access

Trigger words: app X requires verification on every login; no MFA-free reuse.

Same as Template 2: when session reuse is unspecified, the configuration is identical (MFA every time); this template exists only to recognize the intent where the user explicitly demands "verify on every login, no reuse", and writes no additional `ActiveSessionReuseStatus`.

## Template 4: differentiated by group

Trigger words: group A gets direct access, group B needs MFA; different departments, different requirements.

One policy per group (group IDs resolved via ListGroups), each with its own decision. Priorities across groups are staggered automatically by plan in allocation order; mutually exclusive scenarios (group B also matching group A's entry) rely on Users.IncludeGroups scoping, which naturally separates them. A user in multiple groups is governed by whichever policy hits first by priority — the plan's hit preview must cover such users.

```json
{"ConditionalAccessPolicyName": "group-b-mfa", "Priority": null,
 "DecisionConfig": {"Effect": "allow", "MfaType": "mfa_required", "MfaAuthenticationMethods": ["ia_totp"]},
 "ConditionsConfig": {"Applications": {"IncludeApplications": ["app_x"]},
   "Users": {"IncludeGroups": ["group_b"]}, "NetworkZones": {}}}
```

## Template 5: no MFA on the office network, MFA outside (best value)

Trigger words: no second factor on the company network, but required outside; traveling / from home requires verification.

Only one quota slot: office IPs are allowed through with no MFA; traffic outside falls back to the default policy (allow + MFA, configured globally on the console "second-factor authentication" page — outside this skill's scope). Requires the existing office NetworkZone `network_` ID (same upfront collection as Template 1).

```json
{
  "schema_version": 1, "intent_name": "office-no-mfa",
  "policies": [
    {"ConditionalAccessPolicyName": "office-directly-access", "Priority": null,
     "DecisionConfig": {"Effect": "allow", "MfaType": "directly_access"},
     "ConditionsConfig": {"Applications": {"IncludeApplications": ["app_x"]},
       "Users": {}, "NetworkZones": {"IncludeNetworkZones": ["network_office"]}}}
  ]
}
```

Note: the default policy's MFA requirement is controlled globally by the second-factor authentication page; the preview wording must say "outside the office network the default policy applies (allow + per the console second-factor settings)" and must not promise specific methods.

## Fixed flow after generating the intent

1. `python3 scripts/ca_lifecycle.py plan --plan-file PLAN.json --intent-file INTENT.json --instance-id ID --eiam-profile PROFILE [--sim-user U --sim-app A --sim-ip IP ...]`
2. plan local validation failure → fix the intent; nothing reaches the cloud.
3. Confirm with a human-readable summary: per-policy decision/conditions/priority + quota information + the hit-preview conclusion + SHA256, as tables or bullets — never the full plan JSON; get one confirmation.
4. `python3 scripts/ca_lifecycle.py apply --plan-file PLAN.json --approved-plan SHA256`.
