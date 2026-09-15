# M2: Authorization Configuration Templates

Ready-to-apply JSON templates for the four cross-account authorization
surfaces. **Templates only - applying them is a write operation performed
by the user** (RAM console: role trust policy / permission policy; OSS
console: Bucket Policy). This skill never applies them.

## 1. RAM role TRUST POLICY templates

### 1.1 Service trust (replication / migration roles)

Lets the OSS service assume the role; the measured fix for replication /
migration NoPermission whose server-log carries an STS RequestId. Official
shape (source: help.aliyun.com `/zh/oss/user-guide/introduction-to-data-replication-permissions`):

```json
{
  "Statement": [
    {
      "Action": "sts:AssumeRole",
      "Effect": "Allow",
      "Principal": {
        "Service": [
          "oss.aliyuncs.com"
        ]
      }
    }
  ],
  "Version": "1"
}
```

Notes:
- Role type must be a CLOUD-SERVICE role (trusted entity = Alibaba Cloud
  Service, OSS). A cloud-ACCOUNT-typed role with this trust policy still
  fails (measured ticket pattern: wrong role type is a top cause).
- After editing the trust policy the fix takes effect on the next assume
  attempt - the replication rule does NOT need to be re-submitted.

### 1.2 Cross-account trust (peer account assumes the role)

Official RAM cross-account pattern (source: help.aliyun.com
`/zh/ram/use-cases/use-a-ram-role-to-grant-permissions-across-alibaba-cloud-accounts`):

```json
{
  "Statement": [
    {
      "Action": "sts:AssumeRole",
      "Effect": "Allow",
      "Principal": {
        "RAM": [
          "acs:ram::<peer-account-UID>:root"
        ]
      }
    }
  ],
  "Version": "1"
}
```

`:root` trusts the whole peer account; narrow to
`acs:ram::<peer-account-UID>:user/<ram-user-name>` to trust one RAM user.

## 2. Cross-account ACCESS: RAM permission policy on the role

Attached to the role created in the BUCKET-OWNER's account (least-privilege
shape; extend actions per the real need):

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["oss:ListObjects"],
      "Resource": ["acs:oss:*:*:<bucket-name>"]
    },
    {
      "Effect": "Allow",
      "Action": ["oss:GetObject", "oss:PutObject"],
      "Resource": ["acs:oss:*:*:<bucket-name>/*"]
    }
  ]
}
```

Resource-granularity pitfalls (measured ticket patterns):
- The bucket-level ARN (no `/*`) covers `oss:ListObjects`; the object-level
  ARN with `/*` covers GetObject/PutObject - missing either fails the flow.
- `oss:ListBuckets` is account-level and cannot be narrowed to one bucket;
  a peer limited to one bucket sees an empty console bucket list - that is
  expected, not an authorization bug.
- The RAM policy Resource only covers resources of the account the policy
  lives in; cross-account target resources need the Bucket Policy below.

## 3. Cross-account REPLICATION: dual grant

Source account A (RAM Policy on the replication role) - official minimal
shape (source: help.aliyun.com `/zh/oss/user-guide/introduction-to-data-replication-permissions`):

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["oss:ReplicateList", "oss:ReplicateGet"],
      "Resource": ["acs:oss:*:*:<src-bucket>", "acs:oss:*:*:<src-bucket>/*"]
    }
  ]
}
```

Destination account B (Bucket Policy on the destination bucket):

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "oss:ReplicateList",
        "oss:ReplicateGet",
        "oss:ReplicatePut",
        "oss:ReplicateDelete"
      ],
      "Principal": [
        "arn:sts::<src-uid>:assumed-role/<role-name>/*"
      ],
      "Resource": [
        "acs:oss:*:<dest-uid>:<dest-bucket>",
        "acs:oss:*:<dest-uid>:<dest-bucket>/*"
      ]
    }
  ]
}
```

- `src-uid` = UID of the source-bucket account, `role-name` = replication
  role created in account A (ALL-LOWERCASE, exact match), `dest-uid` /
  `dest-bucket` = destination bucket owner and name.
- One side missing -> NoPermission; granting `AliyunOSSFullAccess` on one
  side does NOT substitute the other side (measured ticket pattern).
- `oss:ReplicateDelete` is only needed for add/delete/change sync.

## 4. Bucket Policy Principal writing rules (do NOT mix with RAM syntax)

| Grant target | Bucket Policy Principal form |
|---|---|
| Another main account | bare UID digits, e.g. `"1234567890"` |
| Another account's RAM user | the RAM user's UID digits |
| Assumed-role identity | `"arn:sts::<main-account-UID>:assumed-role/<role>/<session-or-*>"` |
| Anyone (public - avoid) | `"*"` |

- RAM-policy ARN forms (`acs:ram::<uid>:root`) in a Bucket Policy Principal
  are a syntax misuse - the two policy languages must not be mixed.
- Bucket Policy Resource uses the OWNER UID position:
  `acs:oss:*:<owner-uid>:<bucket>(/*)`; RAM Policy Resource uses the
  account owning the policy's principal.
- `acs:SourceIp` conditions must be paired with `acs:SourceVpc`; do not
  invent unsupported condition keys.
- `StringEquals` is literal-only (no wildcards): `"acs:SourceVpc": ["*"]`
  needs `StringLike`, and "any VPC" / prefix matching needs `StringLike`
  too - see the Condition anti-patterns in
  references/cross-account-auth-decision-tree.md sec.6.

## 5. Verifying who is really accessing (log field guidance)

When access logs are available, the requester identity and cross-account
status come from the `extend_information` log field, NOT from a bare
requester-UID comparison. Official field name: `extend_information`
(source: help.aliyun.com/zh/sls/log-fields-17, log-fields-13, sls/oss -
all three consistent). Official splicing rule:
`requesterParentId,roleName,roleSessionName,roleOwnerId` separated by
half-width commas; the official note adds it "may continue to append new
fields", so index by position from the LEFT and never assume a fixed
total field count.

- plain request: logs `<requesterParentId>,,,,` - the FIRST
  comma-separated value is the requesting primary-account UID; compare it
  with `bucket_owner`.
  Example: `extend_information` = `1234567890,,,,` with
  `bucket_owner` = `1234567890` -> same-account.
- STS assumed-role request: logs
  `<requesterParentId>,<roleName>,<roleSessionName>,<roleOwnerId>,` - the
  role's OWNING primary-account UID is the FOURTH value (`roleOwnerId`);
  compare `roleOwnerId` with `bucket_owner` - NOT the first value (the
  assuming account, `requesterParentId`), because the STS temporary
  credential belongs to the role-owning account.
  Example: `extend_information` =
  `1952190735454941,BigDataOSSRole,di.dataworks.aliyuncs.com,1610080553270511,`
  -> the role belongs to account `1610080553270511` (the 4th value); compare
  THAT with `bucket_owner` to decide cross-account.
- A RAM-user UID differing from the main-account UID does NOT by itself
  mean cross-account.

SLS query template (TEMPLATE ONLY - this skill never executes log
queries; run it in the SLS console, or route to
`alibabacloud-oss-security-incident-forensics` whose 6-step SLS query
sequence EXECUTES read-only identity/traffic attribution):

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

Judgment rule: plain-request rows are cross-account when
`requester_main_uid != bucket_owner`; STS rows when
`role_owner_uid != bucket_owner` (full decision path:
references/cross-account-auth-decision-tree.md sec.7).

## 6. Official authorization semantics (verified against public docs 2026-08-27)

Sources:

- Role default trust scope: help.aliyun.com
  `/zh/oss/user-guide/cross-account-access-by-ram-role`
- Condition key list: help.aliyun.com
  `/zh/oss/user-guide/authorization-syntax-and-elements`
- Evaluation order: help.aliyun.com `/zh/oss/user-guide/authentication`
- Bucket Policy semantics: help.aliyun.com `/zh/oss/user-guide/oss-bucket-policy`
- Statement expiration: help.aliyun.com
  `/zh/oss/user-guide/policy-statement-expiration`

### 6.1 Role default trust scope (security pitfall)

After a cross-account RAM role is created, its default trust policy allows
ALL RAM users **and RAM roles** of the trusted (peer) account to assume the
role (official wording, translated: "After a RAM role is created, by default all RAM users AND RAM roles of account B are allowed to assume the role").
The RAM-role half is easy to miss in an audit: it means role-chaining (a role
in the peer account assuming this role) is open by default, which widens the
exposure surface. Narrow the trust policy to a specific RAM user
(`acs:ram::<peer-account-UID>:user/<ram-user-name>`) or a specific RAM role
(`acs:ram::<peer-account-UID>:role/<role-name>`) if the whole account should
not have access - flag this when reviewing a customer's role during an
authorization audit.

### 6.2 Official Condition key list (do NOT fabricate keys; verify against the official syntax doc)

Global (acs:) keys supported in OSS Bucket Policy conditions:
`acs:AccessId`, `acs:CurrentTime`, `acs:MFAPresent`, `acs:SecureTransport`,
`acs:SourceIp`, `acs:SourceVpc`, `acs:UserAgent`.

OSS-specific (oss:) keys: `oss:Prefix`, `oss:Delimiter`, `oss:BucketTag`,
`oss:ExistingObjectTag`, `oss:RequestObjectTag`, `oss:x-oss-acl`,
`oss:x-oss-object-acl`, `oss:object-remaining-retention-days`, plus the three
Access-Point keys `oss:DataAccessPointArn`, `oss:AccessPointNetworkOrigin`
and `oss:DataAccessPointAccount` (the Access-Point keys apply only when the
bucket is associated with an OSS access point / data access point). These 11
`oss:` keys are the condition keys listed in the official
authorization-syntax document; note that `oss:PutObjectRetention` appears in
the same official table but is an ACTION, not a condition key. This list is
the commonly-used set, not a closed whitelist: if a requested condition key
is not listed here, do NOT assert from memory that it is unsupported - first
re-check the official authorization-syntax document (via `_doc_lookup`) and
answer based on what it actually says; only tell the user a key is
unsupported when the official document confirms it. Never fabricate a policy
with an invented key.

### 6.3 Authorization evaluation order (why "I granted it but still 403")

Explicit Deny always wins. For non-anonymous requests OSS evaluates:
resource-directory Control Policy -> identity authentication -> session
policy -> RAM Policy + Bucket Policy -> ACL. For anonymous requests only
Bucket Policy and ACL are evaluated. A grant on one layer can still be
overridden by a Deny on another layer - check ALL layers before concluding
a grant is missing.

### 6.4 Bucket Policy semantics details

- A wildcard Principal (`*`) WITHOUT a Condition applies ONLY to users other
  than the bucket Owner (official wording, translated: "takes effect only for users other than the Bucket Owner") - the
  Owner's own identities are not affected by such a statement.
- A wildcard Principal (`*`) WITH a Condition applies to everyone including
  the bucket OWNER's own identities and anonymous users; an explicit Deny
  statement overrides any Allow (so a `*`+Condition Deny can lock out even
  the Owner, and a `*`+Condition Allow can expose data anonymously).
- Time-boxed grants / temporary bans: add an `acs:CurrentTime` condition so
  the statement auto-expires; there is no built-in statement TTL.

### 6.5 403 error-code attribution (EC in the XML body)

| EC | Meaning | First check |
|---|---|---|
| `0003-00000001` | Wrong AK or no permission at all | AK validity; whether any layer grants the action |
| `0003-00000101` | Hit a Bucket Policy DENY | The Deny statement's Condition (SourceIp/SourceVpc etc.) - and quote the hit Statement JSON in the answer |
| `0003-00000201` | RAM explicit Deny - this code is RAM-Policy-side ONLY; an explicit Deny always wins over every Allow, so adding a Bucket Policy Allow CANNOT fix it | Find and remove/narrow the explicit Deny statement in the RAM Policy (RAM user/role attached policies); never answer "add more Allow". Do NOT go searching the Bucket Policy for this code - a Bucket-Policy-side Deny returns `0003-00000101`, and a Deny on BOTH sides returns `0003-00000203` |
| `0003-00000202` | Not authorized (no matching Allow, no Deny) | Missing grant on the right layer |
| `0003-00000203` | Denied by BOTH sides' policies | RAM Policy and Bucket Policy together |
