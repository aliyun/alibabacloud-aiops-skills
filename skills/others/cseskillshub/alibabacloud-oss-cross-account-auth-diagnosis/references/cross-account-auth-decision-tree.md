# M1: Cross-Account Authorization Failure Decision Tree

Attribution ladder for OSS cross-account access / replication / migration
authorization failures (NoPermission / AccessDenied). All checks here are
read-only; every authorization change is a template the user applies
manually - this skill never writes anything.

## 1. Step zero: which side owns the bucket?

Compare the caller account UID with the bucket owner UID (the script does
this via `GetBucketInfo.owner_id` vs `sts:GetCallerIdentity` AccountId):

- caller UID == owner UID -> same-account; the failing peer must be granted
  by THIS account (Bucket Policy and/or a RAM role created here).
- caller UID != owner UID -> cross-account from this caller's view; the
  grant must come from the OWNING account. A cross-account bucket is
  invisible to GetBucketInfo/ListBuckets of a non-owner (NoSuchBucket) -
  that itself is an ownership signal. Note: the message "The bucket you
  access does not belong to you" is, per the official doc, primarily a
  client-side pre-check permission failure (the credential lacks
  `oss:ListObjects` on the bucket-level resource, or `oss:GetBucketInfo`
  when the tool pre-checks it) and does NOT by itself indicate a bucket
  ownership problem - do not treat that message alone as an ownership
  signal; rely on the UID/owner_id comparison and NoSuchBucket instead.
- UID comparison caveats (distilled from access-log practice): a RAM-user
  UID differs from its main-account UID but is the SAME account; for an
  assumed-role (STS) request the relevant account is the one OWNING the
  role. Never conclude "cross-account" from a bare requester-UID mismatch.

## 2. Replication / migration NoPermission: the STS-RequestId method

Real-ticket case law (reqId diagnosis case 2, PutBucketReplication 403
NoPermission):

```
server-log of the failing request
+-- carries a SEPARATE STS RequestId
|     -> OSS internally AssumeRole'd the configured replication role and
|        STS REJECTED it
|     -> fix: the role TRUST POLICY. Principal.Service must contain
|        "oss.aliyuncs.com". After editing the trust policy the fix takes
|        effect on the next assume attempt - the replication rule does NOT
|        need to be re-submitted.
`-- NO STS RequestId
      -> OSS never attempted to assume the role
      -> fix: the role PERMISSION POLICY. Grant oss:ReplicateList /
         oss:ReplicateGet on the exact source bucket ARN (cross-account:
         plus a Bucket Policy on the destination bucket). Resource
         granularity matters - a missing or misspelled bucket ARN fails.
`-- server-log not collected
      -> inconclusive: verify BOTH branches before concluding.
```

Migration (online data migration service) follows the same shape: the
service role must trust the migration/OSS service principal and carry the
read permissions on the source bucket; the destination side needs the
write grant (Bucket Policy for cross-account).

## 3. Cross-account ACCESS (GetObject/PutObject/ListObjects) failures

```
Does the owning account expose the bucket to the peer?
+-- Bucket Policy missing (GetBucketPolicy -> NoSuchBucketPolicy,
|   measured 404 = "not configured", NOT an auth error)
|     -> owner must add a Bucket Policy naming the peer (bare UID for
|        direct access, arn:sts::<uid>:assumed-role/<role>/* for role
|        access) - template in references/auth-config-templates.md
+-- Bucket Policy present
|     -> static checks (implemented in check_bucket_policy, EFFECT-AWARE):
|        - read Statement.Effect FIRST: only Allow statements grant
|          anything. A Deny statement with Principal "*" is the measured
|          Alibaba Cloud automatic security-protection shape
|          (statement text commonly annotated "Created by Alibaba
|          Cloud Security, do not modify this action") - a NORMAL
|          security configuration: never report it as anonymous access,
|          never recommend removing / replacing / re-creating it.
|          An Allow statement with Principal "*" IS anonymous access
|          (warn + replace-with-peer-UID guidance).
|        - peer UID found in a DENY statement -> explicit rejection:
|          the peer is deliberately denied, an explicit Deny always
|          wins over every Allow (EC 0003-00000201, section 5) - the
|          fix direction is to remove/narrow the Deny, NOT to add
|          more Allow statements.
|        - peer UID / assumed-role principal missing (checked against
|          ALLOW statements only)
|        - dict-form Principal = RAM-policy syntax misuse (must be a LIST
|          of strings in Bucket Policy)
|        - acs:ram::<uid>:root in Principal = RAM-policy ARN misuse (write
|          the bare UID instead)
|        - role name case mismatch (role names are all-lowercase)
|        - Resource must be acs:oss:*:<dest-uid>:<bucket>(/*) in Bucket
|          Policy (owner UID position), NOT acs:oss:*:*:<bucket> copied
|          from RAM-policy examples
`-- RAM role path (peer assumes a role created by the owner)
      -> DUAL requirement: trust policy on the role trusts the peer
         (acs:ram::<peer-uid>:root) AND the role's permission policy
         covers the bucket ARNs; one side missing = AccessDenied.
```

## 4. AssumeRole failure routing

When the failing call is STS AssumeRole itself (the peer cannot obtain the
temporary credential):

1. RoleArn points at the WRONG account (`acs:ram::<other-uid>:role/...`
   copied from docs/another account) - STS cannot find or trust it.
2. A RAM-USER ARN (`acs:ram::<uid>:user/<name>`) passed as RoleArn -
   AssumeRole accepts RAM ROLES only; STS answers "The specified Role not
   exists".
3. `AliyunSTSAssumeRoleAccess` granted at RESOURCE-GROUP scope - AssumeRole
   is an account-level action; grant it at ACCOUNT level.
4. The role trust policy does not include the caller (peer account root /
   specific RAM user, or `oss.aliyuncs.com` for OSS-internal assumes).
5. The STS credential was obtained but the client keeps using the original
   account's long-lived AK (or drops the SecurityToken) - the cross-account
   AccessDenied persists even though authorization is correct.

## 5. Explicit Deny always wins: EC 0003-00000201

Ticket-measured shape (ported from the support-knowledge gap research,
0-hit in the 22-skill baseline): the request fails with `0003-00000201`
(RAM explicit Deny). The defining semantics:

- General principle: an EXPLICIT Deny on ANY evaluation layer always wins
  over every Allow. But the EC code tells you WHICH layer fired, so do not
  blur them: `0003-00000201` is RAM-Policy-side ONLY (official wording,
  translated: "Your request is denied by the RAM Policy"); a Bucket-Policy-side Deny returns `0003-00000101`;
  a Deny on BOTH sides returns `0003-00000203`. For `0003-00000201` a
  Bucket Policy Allow cannot fix the request - adding a Bucket Policy
  Allow is ineffective for this error.
- Fix direction (for `0003-00000201`): find and remove / narrow the explicit
  Deny statement in the RAM Policy (RAM user/role attached policies)
  (quote the hit Statement JSON in the answer - EC 0003-00000101 rule:
  naming the policy is not a diagnosis). Adding more Allow statements
  never helps.
- When this skill's policy check finds the peer UID inside a Deny
  statement, that IS this shape: `policy_check.deny_statements` carries
  the Deny statement originals for quoting.
- Evaluation-order background: resource-directory Control Policy ->
  identity authentication -> session policy -> RAM Policy + Bucket
  Policy -> ACL; a Deny on ANY layer overrides an Allow on another
  (see references/auth-config-templates.md sec.6.3).

## 6. Bucket Policy Condition anti-patterns (ported, measured)

### 6.1 StringEquals does not support wildcards - use StringLike

`StringEquals` is literal-only: `"acs:SourceVpc": ["*"]` under
`StringEquals` matches the LITERAL string `"*"`, never "any VPC". To
match any value (e.g. "not restricted to a VPC") use `StringLike` +
`["*"]`:

```json
"Condition": {
  "StringLike": { "acs:SourceVpc": ["*"] }
}
```

Use `StringEquals` only with a concrete VPC ID for exact matching;
prefix-style matching (e.g. `oss:Prefix`) also requires `StringLike`.

Related measured pitfall (same family): `acs:SourceIp` in a Bucket
Policy must be paired with `acs:SourceVpc`; for public-IP requests
(which carry no VPC attribute) use `StringLike` +
`"acs:SourceVpc": ["*"]` as the always-true VPC condition instead of
omitting it.

### 6.2 oss:Prefix only applies to prefix-parameter APIs

`oss:Prefix` matches only requests that carry a `prefix` query
parameter - i.e. ListObjects / ListObjectsV2. GetObject / PutObject /
DeleteObject requests have NO prefix parameter, so an `oss:Prefix`
condition NEVER matches them: the condition is equivalent to no
restriction at all. Never use `oss:Prefix` to restrict upload/download
behavior; to restrict by object-key suffix, put the wildcard in the
Resource element instead (`acs:oss:*:<uid>:<bucket>/*.html`).

## 7. Cross-account verification via extend_information (SLS template + forensics handoff)

The authoritative cross-account judgment comes from the access log's
`extend_information` field, never from a bare requester-UID mismatch
(official field name `extend_information`, source:
help.aliyun.com/zh/sls/log-fields-17, log-fields-13, sls/oss - all three
consistent; splicing rule `requesterParentId,roleName,roleSessionName,
roleOwnerId`, and the official note warns it "may continue to append new
fields" - index by position from the LEFT. Field semantics and examples:
references/auth-config-templates.md sec.5):

- plain request: logs `<requesterParentId>,,,,` - the FIRST
  comma-separated value = requester primary-account UID - compare with
  `bucket_owner`.
- STS AssumeRole request: logs
  `<requesterParentId>,<roleName>,<roleSessionName>,<roleOwnerId>,` - the
  FOURTH value (`roleOwnerId`) = the role-OWNING primary-account UID -
  compare THAT with `bucket_owner` (the first value is the assuming
  account, which is NOT the credential's account).

SLS query template (TEMPLATE ONLY - this skill never executes log
queries; hand it to the user for the SLS console, or route to
`alibabacloud-oss-security-incident-forensics`, which EXECUTES the
read-only 6-step SLS query sequence including identity/traffic
attribution):

```
* | SELECT requester,
         split_part(extend_information, ',', 1) AS requester_main_uid,
         split_part(extend_information, ',', 4) AS role_owner_uid,
         count(*) AS hits
  FROM log
  WHERE extend_information IS NOT NULL
  GROUP BY requester, requester_main_uid, role_owner_uid
  ORDER BY hits DESC
  LIMIT 100
```

Read it as: rows where requester_main_uid != bucket_owner (plain
requests) or role_owner_uid != bucket_owner (STS requests) are the
cross-account traffic; combine with the forensics skill's Top-IP/UA
sequence when abuse is suspected.

## 8. 403 localization main path: EncodedDiagnosticMessage + RAM permission-diagnosis

The OFFICIAL recommended way to localize a RAM-permission 403
(NoPermission / AccessDenied). When OSS denies a request for a
RAM-permission reason the 403 body carries an `<AccessDeniedDetail>` block
plus the OSS `<EC>` code. Official example (EC `0003-00000201`, source:
help.aliyun.com `/zh/oss/user-guide/0003-00000201`):

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Error>
  <Code>AccessDenied</Code>
  <Message>Access denied by bucket policy.</Message>
  <RequestId>65AF5037***5347E6D09</RequestId>
  <HostId>mybucket.oss-cn-hangzhou.aliyuncs.com</HostId>
  <AccessDeniedDetail>
    <PolicyType>AccountLevelIdentityBasedPolicy</PolicyType>
    <AuthPrincipalOwnerId>10323***2056</AuthPrincipalOwnerId>
    <AuthPrincipalType>SubUser</AuthPrincipalType>
    <AuthPrincipalDisplayName>20587***54611</AuthPrincipalDisplayName>
    <NoPermissionType>ExplicitDeny</NoPermissionType>
    <AuthAction>oss:PutBucketReferer</AuthAction>
    <EncodedDiagnosticMessage>AQIBIAAAACB1******Sb6kUQ==</EncodedDiagnosticMessage>
  </AccessDeniedDetail>
  <EC>0003-00000201</EC>
  <RecommendDoc>https://api.aliyun.com/troubleshoot?q=0003-00000201</RecommendDoc>
</Error>
```

### 8.1 The Message/EC inconsistency trap (do NOT trust the Message text)

In the official example the `<Message>` reads **"Access denied by bucket
policy."** but `<EC>` is `0003-00000201` (a RAM-Policy Deny, section 5) and
`<PolicyType>` is `AccountLevelIdentityBasedPolicy` (a RAM identity policy,
NOT a Bucket Policy). **The Message wording is misleading.** Attribute the
deny by **EC + PolicyType** (and, after decoding, the `MatchedPolicies`),
never by the Message text. The script's `interpret_access_denied_detail`
flags exactly this trap in `interpretation.message_ec_trap`.

### 8.2 Step A - read the plain AccessDeniedDetail (needs NO permission)

Even before any decode the AccessDeniedDetail fields already localize the
deny (official 4-step method, source: help.aliyun.com
`/zh/ram/support/how-to-troubleshoot-an-access-denied-error`):

1. **Who** - `AuthPrincipalType` (SubUser = RAM user / AssumedRoleUser =
   RAM role / Federated = SSO), `AuthPrincipalDisplayName` (RAM user = UID;
   RAM role = `RoleName:RoleSessionName`), `AuthPrincipalOwnerId` (the
   account UID the identity belongs to).
2. **Which action** - `AuthAction` is the denied/missing action (e.g.
   `oss:PutBucketReferer`); grant or remove THAT, never a guess.
3. **Which policy layer** - `PolicyType` decides WHERE to fix:

   | PolicyType | Layer | Fix direction |
   |---|---|---|
   | `ControlPolicy` | resource-directory control policy (permission boundary, highest priority) | contact the resource-directory MANAGEMENT account |
   | `SessionPolicy` | session policy attached at AssumeRole | check the session policy passed to the AssumeRole call |
   | `AssumeRolePolicy` | role TRUST policy | check the assumed role's trust policy (section 4) |
   | `AccountLevelIdentityBasedPolicy` | RAM identity policy (account scope) | check the permission policies attached to the caller RAM user/role |
   | `ResourceGroupLevelIdentityBasedPolicy` | RAM identity policy (resource-group scope) | check the resource-group-scoped policies |

4. **Deny kind** - `NoPermissionType`: `ExplicitDeny` = an explicit Deny
   fired (always wins over every Allow -> remove/narrow the Deny; adding
   Allow never helps, section 5); `ImplicitDeny` = no Allow matched -> the
   administrator must ADD an Allow for `AuthAction`.

### 8.3 Step B - decode the EncodedDiagnosticMessage (needs ram:DecodeDiagnosticMessage)

The `EncodedDiagnosticMessage` decodes (via RAM `DecodeDiagnosticMessage`,
Ram/2015-05-01, read-only action `ram:DecodeDiagnosticMessage`) into the
richer `DecodedDiagnosticMessage`: `ExplicitDeny` (bool),
`NoPermissionPolicyType`, `AuthAction`, `AuthResource`, `AuthPrincipal`,
`AuthConditions[]` (the ConditionKey/ConditionValues in play, e.g.
`acs:SourceIp`), and `MatchedPolicies[]` (the exact `Effect` /
`PolicyIdentifier` / `PolicyType` / `AttachedEntityType` / `AttachedScope`
that fired) - this names the precise policy to QUOTE in the answer.

Two decode routes:
- **Script**: `oss_cross_account_auth_diagnosis.py
  --encoded-diagnostic-message "<EncodedDiagnosticMessage OR the whole 403
  body>"` -> the report's `ram_403_diagnosis` section carries
  `interpretation` (Step A, always) plus `decoded_interpretation` (Step B,
  when the decode succeeds). The script also auto-extracts the detail from a
  GetBucketInfo 403 body (`_oss_client` captures the OSS `EC` + raw body).
- **Console**: paste the `EncodedDiagnosticMessage` into the RAM
  permission-diagnosis page
  `https://ram.console.aliyun.com/permissions/troubleshoot`.

**Degradation (official, and the MEASURED state for the evaluation role
`skillsclienttest` on account 1552974654746705)**: that role LACKS
`ram:DecodeDiagnosticMessage`, so RAM answers `403 NoPermission`. Per the
official doc, when you lack the diagnosis permission, hand the
`EncodedDiagnosticMessage` to an **account administrator** who holds
`ram:DecodeDiagnosticMessage` and have them open the RAM permission-diagnosis
page, then apply the authorization fix the diagnosis names. The script
degrades exactly this way: `[WARN]` on stderr +
`ram_403_diagnosis.decode.available=false` +
`ram_403_diagnosis.manual_decode_guidance` (page URL + administrator-handoff
steps). Step A still localizes the deny without any decode.

`DecodeDiagnosticMessage` is a read-only action; this skill only ever
DECODES (never applies any authorization change), and the decoded diagnosis
reflects only the account of the credential used to decode.

## 9. Official sources (verified)

- Cross-account access to OSS via RAM role:
  help.aliyun.com `/zh/oss/user-guide/cross-account-access-by-ram-role`
- Data replication permissions (trust policy with oss.aliyuncs.com,
  Replicate* minimal policy, cross-account dual grant):
  help.aliyun.com `/zh/oss/user-guide/introduction-to-data-replication-permissions`
- RAM cross-account pattern (trust policy Principal.RAM
  `acs:ram::<UID>:root`):
  help.aliyun.com `/zh/ram/use-cases/use-a-ram-role-to-grant-permissions-across-alibaba-cloud-accounts`
- RAM role overview (trust policy = identity trust boundary):
  help.aliyun.com `/zh/ram/user-guide/ram-role-overview`
- Bucket Policy overview:
  help.aliyun.com `/zh/oss/user-guide/bucket-policy`
- OSS EC `0003-00000201` (RAM-Policy Deny; the 403 XML carrying
  `<AccessDeniedDetail>` + `<EncodedDiagnosticMessage>`; RAM
  permission-diagnosis page; the Message/EC inconsistency example):
  help.aliyun.com `/zh/oss/user-guide/0003-00000201`
- RAM access-denied troubleshooting (the official 4-step AccessDeniedDetail
  interpretation; OpenAPI `AccessDeniedDetail` shape; permission-diagnosis
  page + `EncodedDiagnosticMessage` / RequestID reverse parsing):
  help.aliyun.com `/zh/ram/support/how-to-troubleshoot-an-access-denied-error`
- RAM `DecodeDiagnosticMessage` API contract (Ram/2015-05-01, read-only,
  `ram:DecodeDiagnosticMessage`; `DecodedDiagnosticMessage` response schema):
  api.aliyun.com `/api/Ram/2015-05-01/DecodeDiagnosticMessage`
