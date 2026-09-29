# Error Code Map (WAF OpenAPI, both versions)

Use this to **classify** the error the customer received before touching parameters. This skill's scope is
**parameter-class** errors: the request's parameter name, format, value, or required-ness disagrees with the
official spec. Everything else is routed out (Phase 2).

The `Code` string is the authoritative classifier; the `Message` usually names the offending parameter
(e.g. `InvalidParameter.InstanceId`, `The specified parameter Rules is not valid`). The `RequestId` is only
needed for the OpenAPI diagnosis portal when the message is ambiguous.

## 1. Parameter-class errors (IN SCOPE)

| Code (or Code prefix) | HTTP | Typical meaning | First thing to check |
|-----------------------|------|-----------------|----------------------|
| `InvalidParameter` / `InvalidParameters` | 400 | A value/format is wrong | Diff every param against the spec (Phase 4) |
| `InvalidParameter.<Name>` | 400 | The named parameter is wrong | Go straight to `<Name>`; check type / enum / format |
| `MissingParameter` / `MissingParameter.<Name>` | 400 | A required parameter is absent | Add `<Name>`; confirm required set from the spec |
| `InvalidParameter.Format` / `*.Malformed` | 400 | Value has the wrong shape | JSON-string params, IP/CIDR, port range, time format |
| `10900` (`Invalid parameter`) | 400 | Generic WAF invalid-parameter | Diff params; the message text usually names the field |
| `Defense.Control.InvalidParameter` | 400 | WAF 3.0 defense-plane invalid param | Diff params of the defense action |
| `AclParamError` | 400 | ACL rule parameter invalid | Check the rule `conditions` / action JSON structure |
| `Defense.Control.*Invalid` (e.g. `DefenseResourceNameInvalid`, `DefenseIpBlacklistIpInvalid`, `DefenseAntiscanRuleConfigInvalid`) | 400 | A specific field value is illegal | The code names the field; fix its value/format |
| `Defense.Control.*NotEmpty` / `*IpEmpty` | 400 | A field that must not be empty was empty | Supply the required non-empty value |
| `Defense.Control.*NotExist` (e.g. `DefenseResourceGroupNotExist`, `InvalidDefenseRuleID`) | 400 | An ID/name references something absent | The value is well-formed but does not exist — verify the ID |
| `InvalidIncludeSubDomainWithPreload` | 400 | Cross-parameter dependency violated | When `HstsPreload=true`, `HstsIncludeSubDomain` must be `true` |
| `CertFormatError` / `CertKeyNotMatch` / `CertDomainNotMatch` / `CertExpiredError` | 400 | Certificate parameter content is invalid | PEM format, key match, domain coverage, expiry |
| `BusinessInvalidArgument` | 403 | Specified parameters are invalid | Treat as parameter-class; diff params |

> **Wrong-version is also a root cause.** A CLI call that returns
> `This command is not available in the current API version (2021-10-01)` (or an `api not found` /
> `InvalidAction`-style error) means the action belongs to the **other** WAF version. This is diagnosed like a
> parameter problem, not routed out (the version model is covered in SKILL.md and its version-differences reference).

## 2. Non-parameter errors (OUT OF SCOPE — route, do not "fix parameters")

| Code | HTTP | Class | Route to |
|------|------|-------|----------|
| `InvalidAccessKeyId.NotFound` / `SignatureDoesNotMatch` / `InvalidSecurityToken.*` | 400/403 | Credential | Re-configure credentials outside the session; never echo AK/SK |
| `Forbidden` / `Forbidden.RAM` / `NoPermission` / `*.AssumeRoleFailed` | 403 | RAM permission | `ram-permission-diagnose`; grant the action's RAM permission |
| `Throttling` / `Throttling.User` / `Throttling.Api` | 429/400 | Rate limit | Back off; WAF limit ~5 calls/s per uid |
| `InvalidApi.NotPurchase` / `FunctionAvailableError` / `*.NotSupport*` / `ComboError` | 403/400 | Not purchased / edition limit | Check instance edition & feature enablement |
| `InstanceNotExist` / `InvalidInstanceId.NotFound` (instance-level) | 400/404 | Wrong instance/region | Confirm the instance exists in the target region |
| `InternalError` / `11001` / `500` / `ServiceUnavailable` | 500/503 | Server-side | Retry with backoff; if persistent, open a ticket with the RequestId |
| `Defense.Control.DefenseInOperation` / `*TooFrequent` / `*Uploading` | 400 | Transient state | Wait and retry; not a parameter defect |

**Rule:** classify before collecting missing inputs or using tools. For `Throttling*`, give a final rate-limit
answer without asking for action/version. For `Forbidden*` / `NoPermission`, state RAM/out-of-scope and ask for
both Action/API and version only to prepare least-privilege RAM guidance, then wait. For every section 2 code,
do not fetch specs, diff parameters, invoke CLI, inspect the account, or attempt a parameter correction.

## 3. Reading the message to name the parameter

Most parameter-class messages embed the culprit. Patterns to extract:
- `InvalidParameter.<Name>` / `MissingParameter.<Name>` → the parameter is `<Name>`.
- `The specified parameter <Name> is not valid` / `参数 <Name> 不合法` → `<Name>`.
- `The parameter <Name> is invalid. When <A> is <v>, <Name> must be <w>` → cross-parameter dependency.
- WAF `Defense.Control.<Area><Reason>` codes → `<Area>` names the object (Resource / Rule / Template / Ip / Cert),
  `<Reason>` names the defect (`Invalid` = bad value, `NotExist` = absent, `NotEmpty`/`Empty` = empty, `OverSize`/`OutOfRange` = over quota).

When the message names no parameter (bare `InvalidParameter` / `10900`), fall back to the full param-by-param
diff (Phase 4) and, if still ambiguous, look the `RequestId` up in the OpenAPI diagnosis portal
(https://next.api.aliyun.com/home).
