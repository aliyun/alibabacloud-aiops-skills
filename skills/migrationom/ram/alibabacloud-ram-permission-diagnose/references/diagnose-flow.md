# Diagnose Flow Reference

Detailed decision logic for RAM permission diagnosis. Consult this file when encountering complex or ambiguous scenarios.

---

## Identity Resolution

`AuthPrincipalType` and `AuthPrincipalDisplayName` are available in the raw error's `AccessDeniedDetail` — no decode needed. Resolve UserName before gap analysis when identity type is `SubUser`:

| `AuthPrincipalType` | `AuthPrincipalDisplayName` format | Resolution |
|---------------------|----------------------------------|------------|
| `SubUser` | Numeric UserId (e.g., `206007273725819551`) | Call `aliyun ims get-user --user-id <DisplayName>`, use returned `User.UserName` |
| `AssumedRoleUser` | `roleName:sessionName` (e.g., `my-role:session-1`) | Take the part before the colon as RoleName — no API needed |
| `RootUser` | Primary account identifier | Use directly — no resolution needed |

If `GetUser` fails (insufficient permission): mark as L0, fall back to raw error text.

---

## Permission Level (L0–L3)

Levels are implicit routing state — never declare or describe them to the user.

| Level | Confirmed When | Effect |
|-------|---------------|--------|
| L0 | `DecodeDiagnosticMessage` returns NoPermission | Root cause from raw text only; repair: Path B (incremental) + Path C |
| L1 | Decode succeeds, but policy query returns NoPermission | Skip gap analysis; repair: Path B (incremental) + Path C |
| L2 | Policy query returns results | Full gap analysis; repair: Path A (tentative) + Path B (with merge) + Path C |
| L3 | Write operation succeeds | Repair done; report result and undo command |

**Insufficient permission criteria**: ErrorCode `NoPermission`, `Forbidden`, or `AccessDenied`.

If user reports they have updated their own permissions: re-run Step 2 policy query to refresh level state.

---

## Root Cause Classification Decision Tree

```
ExplicitDeny = true?
  ├─ Yes → Explicit Deny path
  │        NoPermissionPolicyType = ControlPolicy?
  │          ├─ Yes → Root cause: CP control policy (out of scope, guide to manual)
  │          ├─ No (AccountLevelIdentityBasedPolicy) → Root cause: own policy Deny (fixable)
  │          └─ Unknown (field absent) → Query both ListPoliciesForUser + ListControlPolicies
  │
  └─ No (or no decoded info) → Missing Action path
       ├─ PolicyType = AssumeRolePolicy → Root cause: role trust policy not allowing caller
       ├─ MissingAction = sts:AssumeRole, PolicyType absent
       │    → Medium confidence: trust policy OR identity policy missing sts:AssumeRole
       │      Describe both; guide user to verify before choosing repair direction
       ├─ PrincipalARN contains AssumedRole/STS token → Root cause: STS credential insufficient
       ├─ ErrorCode = InvalidSecurityToken → Root cause: STS token expired
       ├─ Message contains ServiceLinkedRole → Root cause: SLR missing
       ├─ Error from OSS Bucket Policy etc. → Root cause: resource-side policy
       └─ Other → Root cause: missing Action (most common)
```

**Key principle**: When `DecodeDiagnosticMessage` succeeds and `NoPermissionPolicyType` has a clear value, treat it as authoritative. Do not append additional verification API calls to check other possible root causes.

---

## Gap Analysis Trigger Rules

| Root Cause | Trigger Gap Analysis | Notes |
|-----------|---------------------|-------|
| Missing Action | ✅ Must query | Query by identity type (see below) |
| Explicit Deny (NoPermissionPolicyType=AccountLevelIdentityBasedPolicy) | ✅ Query | Locate the Deny statement |
| Explicit Deny (NoPermissionPolicyType unknown) | ✅ Query + `ListControlPolicies` | Both policy and CP layer |
| Explicit Deny (NoPermissionPolicyType=ControlPolicy) | ❌ Skip | CP level, guide to manual |
| Trust Policy path | ✅ `GetRole` only | Get target role trust policy |
| SLR missing / resource-side policy / token expired | ❌ Skip | Direct output only |

**Identity type → Query API** (for root causes that trigger gap analysis):

| Identity Type | `AuthPrincipalType` | Query API |
|--------------|---------------------|-----------|
| RAM user | `SubUser` | `ListPoliciesForUser` (UserName from Step 1) + `GetPolicyVersion` (Custom only) |
| RAM role | `AssumedRoleUser` | `ListPoliciesForRole` (RoleName from DisplayName) + `GetPolicyVersion` (Custom only) |
| Primary account | `RootUser` | `ListControlPolicies` directly |

**System policies**: Use built-in knowledge to infer coverage — do not call `GetPolicyVersion`.

---

## Repair Pre-Query Rules

| Repair Type | Pre-query Required | Notes |
|-------------|-------------------|-------|
| Attach system policy | None | Pure write |
| Create new custom policy | None | Agent generates content |
| Append Action to existing custom policy | `GetPolicyVersion` + `ListPolicyVersions` | Must include all existing + new Actions in new version |
| Modify role Trust Policy | `GetRole` | Can reuse Step 2 result if already fetched |
| Create SLR | None | Pure write |

---

## Coverage Check (for caller skill permission hints)

Before generating recommendations in Step 3:

1. Scan conversation context for the most recent `Base directory: <path>` injected by a skill invocation
2. If found, try reading `<path>/references/ram-policies.md`
3. If either file is read, perform a **Coverage Check**:
   - Does the actual missing Action from the error appear covered? (exact match, wildcard, or reasonably implied)
   - **If clearly NOT covered**: include the missing Action in the primary recommendation; add note: "⚠ The Action `{missing_action}` triggered by this error is not declared in the skill's permission hints file and has been automatically added. Consider notifying the skill maintainer to update `references/ram-policies.md`."
   - **Otherwise**: use file as supplementary context, normal flow continues
4. If no file found: skip silently, no impact on flow

---

## Handling Each Root Cause

**Missing Action / own policy Deny**: Proceed to Step 3 recommendations → Step 4 repair.

**Role trust policy not allowing caller** (PolicyType=AssumeRolePolicy or medium-confidence sts:AssumeRole):
- Explain: trust policy of the target role must be updated to add the caller's ARN to Principal
- If role name is known: provide modification command directly (see `references/ram-cli-commands.md` → Trust Policy section)
- If unknown: provide `aliyun ram list-roles` and a template for the user to fill in
- Also note: caller's identity policy must also have `sts:AssumeRole` (see `AliyunSTSAssumeRoleAccess`)
- For medium-confidence: describe both possible root causes and guide user to verify first

**STS credential insufficient**:
- Explain: using STS temporary credential; missing permission must be added to the Role that generated the STS
- Provide Role name (from PrincipalARN) and suggested actions; do not auto-repair

**STS token expired**: Prompt user to re-obtain STS token; provide renewal command.

**SLR missing**: Provide creation command:
```bash
aliyun resourcemanager create-service-linked-role --service-name <service>.aliyuncs.com
```

**CP control policy**: Beyond single-account RAM scope; contact ResourceDirectory administrator.

**Resource-side policy (OSS Bucket Policy etc.)**: Explain distinction; provide resource-side modification guidance; do not follow RAM repair flow.
